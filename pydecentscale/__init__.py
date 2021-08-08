#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2021 Luca Pinello
# Released under GPLv3

__version__ = "0.1.0"


import asyncio
import nest_asyncio
nest_asyncio.apply()
from itertools import cycle
from bleak import BleakScanner,BleakClient


class DecentScale:
    def __init__(self,timeout=20, fix_dropped_command=True):
        self.client = None
        self.timeout=timeout
        self.connected=False
        self.weight=None
        self.fix_dropped_command=fix_dropped_command
        self.loop = asyncio.get_event_loop()
         
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
        
        try:
            await self.client.connect(timeout=self.timeout)
        except Exception as e:
            print('Error:%s\nTrying again...' %e)
            return False   
        
        return True

                  
    async def _disconnect(self):
        await self.client.disconnect()
        

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
        
    async def _enable_notification(self):
       
        await self.client.start_notify(self.CHAR_READ, self.notification_handler)

        if self.fix_dropped_command:
            await asyncio.sleep(0.2)
            await self.client.start_notify(self.CHAR_READ, self.notification_handler)

        while(True):
            await asyncio.sleep(1.0)
            
    async def _disable_notification(self):
        await self.client.stop_notify(self.CHAR_READ) 

        
    def notification_handler(self,sender, data):
        self.weight=int.from_bytes(data[2:4], byteorder='big', signed=True)/10

    
    def connect(self,address=None):
        if not self.connected:
            if self.loop.run_until_complete(self._connect(address)):
                self.connected=True
                
        return self.connected    
    
    def disconnect(self):
        if self.connected:
            self.loop.run_until_complete(self._disconnect())
            self.connected=False
  

    def enable_notification(self):   
        asyncio.run_coroutine_threadsafe(self._enable_notification(), loop=self.loop)
        
    
    def disable_notification(self):   
        self.loop.run_until_complete(self._disable_notification())
        
    
    def find_address(self):   
        return self.loop.run_until_complete(self._find_address())
    
    
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
                    return True
        
        return False
    
    def tare(self):   
        self.loop.run_until_complete(self._tare())
        
    def start_time(self):   
        self.loop.run_until_complete(self._start_time())
    
    def stop_time(self):   
        self.loop.run_until_complete(self._stop_time())
                   
    def reset_time(self):   
        self.loop.run_until_complete(self._reset_time())

    def led_off(self):   
        self.loop.run_until_complete(self._led_off())
                   
    def led_on(self):   
        self.loop.run_until_complete(self._led_on())
        

