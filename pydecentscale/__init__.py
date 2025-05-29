#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2021 Luca Pinello
# Released under GPLv3

__version__ = "0.4.0"

import asyncio
import binascii
import functools
import logging
import operator
import threading
import time
from itertools import cycle
import sys

from bleak import BleakScanner, BleakClient

logger = logging.getLogger(__name__)


class AsyncioEventLoopThread(threading.Thread):
    def __init__(self, *args, loop=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.loop = asyncio.new_event_loop()
        self.running = False

    def run(self):
        self.running = True
        self.loop.run_forever()

    def run_coro(self, coro,wait_for_result=True):
        
        if wait_for_result:
            return asyncio.run_coroutine_threadsafe(coro, loop=self.loop).result()
        else:
            return asyncio.run_coroutine_threadsafe(coro, loop=self.loop)

    def stop(self):
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.join()
        self.running = False


class DecentScale(AsyncioEventLoopThread):
    
    def __init__(self, *args, timeout=20, fix_dropped_command=True, enable_heartbeat=False, **kwargs):
        super().__init__(*args, **kwargs)

        self.client = None
        self.timeout=timeout
        self.connected=False
        self.fix_dropped_command=fix_dropped_command
        self.dropped_command_sleep = 0.05  # API Docs says 50ms
        self.weight = None
        self.firmware_version = None
        self.battery_level = None
        self.weight_unit = 'g'
        self.enable_heartbeat = enable_heartbeat
        self.last_heartbeat = None
        self.heartbeat_task = None
        self.timestamp = None  # For firmware v1.2+   

         
        #Constants
        self.CHAR_READ='0000FFF4-0000-1000-8000-00805F9B34FB'
        self.CHAR_WRITE='000036f5-0000-1000-8000-00805f9b34fb'
        
        
        #Tare command structure updated for new firmware
        #Byte 6 controls heartbeat: 00=disable, 01=enable
        
        self.tare_counter = 0
                
        self.led_on_command_grams=bytearray.fromhex('030A0101000009')
        self.led_on_command_ounces=bytearray.fromhex('030A0101010008')
        self.led_off_command=bytearray.fromhex('030A0000000009')
        self.power_off_command=bytearray.fromhex('030A020000000B')
        self.start_time_command=bytearray.fromhex('030B030000000B')
        self.stop_time_command=bytearray.fromhex("030B0000000008")
        self.reset_time_command=bytearray.fromhex("030B020000000A" )
        self.heartbeat_command=bytearray.fromhex("030A03FFFF000A")
        
        self.daemon=True
        super().start()
        
    def check_connection(func):
        def is_connected(self):
            if self.connected:
                func(self)
            else:
                print("Scale is not connected.")
        return is_connected

    async def _find_address(self):
        
        device = await BleakScanner.find_device_by_filter(
        lambda d, ad: d.name and d.name == 'Decent Scale'
        ,timeout=self.timeout)
        
        if device:
            return device.address
        else:
            print('Error: Scale not found. Trying again...')
    

    def calculate_xor(self, data):
        """Calculate XOR checksum for the first 6 bytes"""
        xor = 0
        for i in range(6):
            xor ^= data[i]
        return xor
    
    def generate_tare_command(self):
        """Generate tare command with incrementing counter and heartbeat option"""
        # Increment counter (0-255)
        self.tare_counter = (self.tare_counter + 1) % 256
        
        # Build command: 03 0F <counter> 00 00 <heartbeat> <xor>
        cmd = bytearray([0x03, 0x0F, self.tare_counter, 0x00, 0x00, 0x01 if self.enable_heartbeat else 0x00, 0x00])
        
        # Calculate and set XOR
        cmd[6] = self.calculate_xor(cmd)
        
        return cmd

    async def _connect(self, address):
        
        self.client = BleakClient(address)
        
        if not self.running:
            super().start()
        
        try:
            return await self.client.connect(timeout=self.timeout)
        except Exception as e:
            print('Error:%s\nTrying again...' %e)
            return False   
        
    async def _disconnect(self):
        return await self.client.disconnect()   

    async def __send(self, cmd):
        """Send commands with firmware v1.0 bugfix (resending)"""
        await self.client.write_gatt_char(self.CHAR_WRITE, cmd)
        if self.fix_dropped_command:
            await asyncio.sleep(self.dropped_command_sleep)
            await self.client.write_gatt_char(self.CHAR_WRITE, cmd)

        # Wait 200ms for the command to finish
        # Alternative: receive the notifications and check if the command was acknowledged
        await asyncio.sleep(0.2)

    async def _tare(self):
        await self.__send(self.generate_tare_command())

    async def _led_on(self, unit='g'):
        if unit == 'oz':
            await self.__send(self.led_on_command_ounces)
        else:
            await self.__send(self.led_on_command_grams)

    async def _led_off(self):
        await self.__send(self.led_off_command)
    
    async def _power_off(self):
        """Power off command (firmware v1.2+)"""
        await self.__send(self.power_off_command)

    async def _start_time(self):
        await self.__send(self.start_time_command)

    async def _stop_time(self):
        await self.__send(self.stop_time_command)

    async def _reset_time(self):
        await self.__send(self.reset_time_command)
        
    async def _send_heartbeat(self):
        """Send heartbeat command for Half Decent Scale"""
        if self.enable_heartbeat and self.connected:
            await self.__send(self.heartbeat_command)
            
    async def _heartbeat_loop(self):
        """Heartbeat loop that runs every 4 seconds"""
        while self.connected and self.enable_heartbeat:
            await self._send_heartbeat()
            await asyncio.sleep(4)  # Send every 4 seconds (requirement is < 5 seconds)

    def notification_handler(self, sender, data):
        if data[0] != 0x03 or (len(data) != 7 and len(data) != 10):
            # Basic sanity check - support both 7 and 10 byte messages
            logger.info("Invalid notification: not a Decent Scale?")
            return

        # Calculate XOR based on message length
        if len(data) == 7:
            xor_msg = functools.reduce(operator.xor, data[:-1])
        else:  # 10 byte message
            xor_msg = functools.reduce(operator.xor, data[:-1])
            
        if xor_msg != data[-1]:
            logger.warning("XOR verification failed for notification")
            return
            
        if sys.version_info >= (3, 8):
            logger.debug(f"Received Notification at {time.time()}: {binascii.hexlify(data, sep=':')}")
        else:
            logger.debug(f"Received Notification at {time.time()}: {binascii.hexlify(data)}")
        
        # Have to decide by type of the package
        type_ = data[1]

        if type_ in [0xCA, 0xCE]:
            # Weight information
            self.weight = int.from_bytes(data[2:4], byteorder='big', signed=True) / 10
            
            # If 10-byte message (firmware v1.2+), extract timestamp
            if len(data) == 10:
                minutes = data[4]
                seconds = data[5]
                deciseconds = data[6]
                self.timestamp = {'minutes': minutes, 'seconds': seconds, 'deciseconds': deciseconds}
                logger.debug(f"Weight: {self.weight}g at {minutes}:{seconds:02d}.{deciseconds}")
                
        elif type_ == 0xAA:
            # Button press
            logger.debug(f"Button press: {data[2]}, duration: {data[3]}")
            
        elif type_ == 0x0F:
            # Tare response
            if len(data) >= 7 and data[5] == 0xFE:
                logger.debug("Tare command confirmed")
                
        elif type_ == 0x0A:
            # LED on/off response -> returns units, battery level, and firmware version
            if len(data) >= 7:
                self.weight_unit = 'oz' if data[3] == 0x01 else 'g'
                self.battery_level = data[4] if data[4] != 0xFF else 'USB'
                
                # Firmware version mapping
                fw_map = {0xFE: '1.0', 0x02: '1.1', 0x03: '1.2'}
                self.firmware_version = fw_map.get(data[5], f'Unknown ({data[5]:02x})')
                
                logger.debug(f"Scale info - Unit: {self.weight_unit}, Battery: {self.battery_level}%, Firmware: {self.firmware_version}")
                
        elif type_ == 0x0B:
            # Timer info
            pass
        else:
            logger.warning(f"Unknown Notification Type received: 0x{type_:02x}")

    async def _enable_notification(self):
        await self.client.start_notify(self.CHAR_READ, self.notification_handler)
        await asyncio.sleep(1)
        
        # Start heartbeat if enabled
        if self.enable_heartbeat:
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
             
    async def _disable_notification(self):
        # Cancel heartbeat task if running
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
            self.heartbeat_task = None
            
        await self.client.stop_notify(self.CHAR_READ) 

    @check_connection    
    def enable_notification(self):   
        return self.run_coro(self._enable_notification())
    
    @check_connection 
    def disable_notification(self):   
        self.weight=None
        return self.run_coro(self._disable_notification())
 
    def find_address(self):   
        return self.run_coro(self._find_address())

    
    def connect(self,address):
        if not self.connected:
            self.connected= self.run_coro(self._connect(address))
            
            if self.connected:
                # Turn on LED to get firmware version
                self.led_on()
                # Give time for notification response
                time.sleep(0.5)
        else:
            print('Already connected.')
    
        return self.connected
                
    def disconnect(self):
        if self.connected:
            # Cancel heartbeat task if running
            if self.heartbeat_task:
                self.run_coro(self._disable_notification(), wait_for_result=False)
            
            self.connected = not self.run_coro(self._disconnect())
        else:
            print('Already disconnected.')
        
        return not self.connected
            
    def auto_connect(self,n_retries=3):    
        address = None

        for i in range(n_retries):
            address=self.find_address()
            if address:
                print('Found Decent Scale: %s' % address)
                break
            else:
                print(i)
        
        if address:        
            for i in range(n_retries):
                if self.connect(address):
                    print('Scale connected!')
                    return True
                
        
        print('Autoconnect failed. Make sure the scale is on.')
        return False
    
    @check_connection 
    def tare(self):   
        self.run_coro(self._tare())
        
    @check_connection 
    def start_time(self):   
        self.run_coro(self._start_time())
    
    @check_connection 
    def stop_time(self):   
        self.run_coro(self._stop_time())
                   
    @check_connection 
    def reset_time(self):   
        self.run_coro(self._reset_time())

    @check_connection 
    def led_off(self):   
        self.run_coro(self._led_off())
    
    @check_connection
    def power_off(self):
        """Power off the scale (firmware v1.2+)"""
        if self.firmware_version and self.firmware_version >= '1.2':
            self.run_coro(self._power_off())
        else:
            logger.warning("Power off command requires firmware v1.2 or newer")
                   
    @check_connection 
    def led_on(self, unit='g'):   
        self.run_coro(self._led_on(unit))
 
    
    def get_firmware_version(self):
        """Get the firmware version of the connected scale"""
        return self.firmware_version
    
    def get_battery_level(self):
        """Get the battery level (percentage or 'USB' if USB powered)"""
        return self.battery_level
    
    def get_weight_unit(self):
        """Get the current weight unit displayed on scale ('g' or 'oz')"""
        return self.weight_unit
    
    def get_weight_with_timestamp(self):
        """Get weight with timestamp (firmware v1.2+ only)"""
        if self.timestamp:
            return {'weight': self.weight, 'timestamp': self.timestamp}
        return {'weight': self.weight, 'timestamp': None}

        

