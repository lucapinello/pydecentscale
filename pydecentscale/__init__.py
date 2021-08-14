#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2021 Luca Pinello
# Released under GPLv3

__version__ = "0.3.0"


import asyncio
import threading
from threading import Thread
from itertools import cycle
from bleak import BleakScanner,BleakClient


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
    
    def __init__(self, *args, timeout=20, fix_dropped_command=True, **kwargs):
        super().__init__(*args, **kwargs)

        self.client = None
        self.timeout=timeout
        self.connected=False
        self.fix_dropped_command=fix_dropped_command
        self.weight = None   

         
        #Constants
        self.CHAR_READ='0000FFF4-0000-1000-8000-00805F9B34FB'
        self.CHAR_WRITE='000036f5-0000-1000-8000-00805f9b34fb'
        
        
        #Tare the scale by sending "030FFD000000F1". 
        #Each tare needs to increment the 3rd byte pair, 
        #so you can cycle (for instance) though "030FFE000000F2" "030FFF000000F3" "030F000000000C".
        
        tare_commands=[  bytearray.fromhex(c) for c in ['030F000000000C','030F010000000D','030F020000000E']]
        self.tare_commands=cycle(tare_commands)
                
        self.led_on_command=bytearray.fromhex('030A0101000009')
        self.led_off_command=bytearray.fromhex('030A0000000009')
        self.start_time_command=bytearray.fromhex('030B030000000B')
        self.stop_time_command=bytearray.fromhex("030B0000000008")
        self.reset_time_command=bytearray.fromhex("030B020000000A" )
        
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
    

    
    async def _tare(self):

        await self.client.write_gatt_char(self.CHAR_WRITE,next(self.tare_commands))
        
        if self.fix_dropped_command:
            await asyncio.sleep(0.2)
            await self.client.write_gatt_char(self.CHAR_WRITE,next(self.tare_commands))

  
    async def _led_on(self):
        await self.client.write_gatt_char(self.CHAR_WRITE,self.led_on_command)
        
        if self.fix_dropped_command:
            await asyncio.sleep(0.2)
            await self.client.write_gatt_char(self.CHAR_WRITE,self.led_on_command)


    async def _led_off(self):
        await self.client.write_gatt_char(self.CHAR_WRITE,self.led_off_command)
        
        if self.fix_dropped_command:
            await asyncio.sleep(0.2)
            await self.client.write_gatt_char(self.CHAR_WRITE,self.led_off_command)
        
  
    async def _start_time(self):
        await self.client.write_gatt_char(self.CHAR_WRITE,self.start_time_command)
        
        if self.fix_dropped_command:
            await asyncio.sleep(0.2)
            await self.client.write_gatt_char(self.CHAR_WRITE,self.start_time_command)
        

    async def _stop_time(self):
        await self.client.write_gatt_char(self.CHAR_WRITE,self.stop_time_command)
       
        if self.fix_dropped_command:        
            await asyncio.sleep(0.2)
            await self.client.write_gatt_char(self.CHAR_WRITE,self.stop_time_command)
        
    
    async def _reset_time(self):
        await self.client.write_gatt_char(self.CHAR_WRITE,self.reset_time_command)
        
        if self.fix_dropped_command:
            await asyncio.sleep(0.2)
            await self.client.write_gatt_char(self.CHAR_WRITE,self.reset_time_command)
  

    def notification_handler(self,sender, data):
        self.weight=int.from_bytes(data[2:4], byteorder='big', signed=True)/10

    async def _enable_notification(self):
        await self.client.start_notify(self.CHAR_READ, self.notification_handler)
        await asyncio.sleep(1)
        
             
    async def _disable_notification(self):
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
                self.led_off()
                self.led_on()
        else:
            print('Already connected.')
    
        return self.connected
                
    def disconnect(self):
        if self.connected:
            self.connected= not self.run_coro(self._disconnect())
        else:
            print('Already disconnected.')
        
        return self.connected
            
    def auto_connect(self,n_retries=3):    
              
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
    def led_on(self):   
        self.run_coro(self._led_on())
 

        

