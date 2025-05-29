#!/usr/bin/env python
# coding: utf-8
# Example demonstrating firmware v2 compatibility features

from pydecentscale import DecentScale
import asyncio
import time


# Create the DecentScale object
# enable_heartbeat=True for Half Decent Scale support
ds = DecentScale(enable_heartbeat=False)


# Scan and connect to the first available decent scale
print('Connecting to Decent Scale...')
if ds.auto_connect():
    
    # Check firmware version
    print(f'Firmware version: {ds.get_firmware_version()}')
    print(f'Battery level: {ds.get_battery_level()}%')
    print(f'Weight unit: {ds.get_weight_unit()}')
    
    
    # Enable notifications to start receiving weight data
    print('\nEnabling notifications...')
    ds.enable_notification()
    time.sleep(1)
    
    
    # Read weight values with timestamps (if firmware v1.2+)
    print('\nReading weight values...')
    for i in range(20):
        if ds.weight is not None:
            weight_data = ds.get_weight_with_timestamp()
            if weight_data['timestamp']:
                ts = weight_data['timestamp']
                print(f"Weight: {weight_data['weight']:.1f}g at {ts['minutes']}:{ts['seconds']:02d}.{ts['deciseconds']}")
            else:
                print(f"Weight: {weight_data['weight']:.1f}g")
        time.sleep(0.2)
    
    
    # Test LED control with unit selection
    print('\nTesting LED control...')
    
    # Turn on LED in grams mode
    ds.led_on('g')
    time.sleep(1)
    
    # Turn off LED
    ds.led_off()
    time.sleep(1)
    
    # Turn on LED in ounces mode (firmware v1.1+)
    if ds.get_firmware_version() and ds.get_firmware_version() >= '1.1':
        print('Testing ounces display...')
        ds.led_on('oz')
        time.sleep(2)
        ds.led_on('g')  # Switch back to grams
    
    
    # Test tare with new command format
    print('\nTesting tare function...')
    ds.tare()
    time.sleep(1)
    
    
    # Test timer functions
    print('\nTesting timer...')
    ds.start_time()
    time.sleep(3)
    ds.stop_time()
    time.sleep(1)
    ds.reset_time()
    
    
    # Test power off command (firmware v1.2+)
    if ds.get_firmware_version() and ds.get_firmware_version() >= '1.2':
        print('\nPower off command available (not executing to keep scale on)')
        # Uncomment to actually power off:
        # ds.power_off()
    
    
    # Disable notifications
    print('\nDisabling notifications...')
    ds.disable_notification()
    time.sleep(1)
    
    
    # Disconnect
    print('\nDisconnecting...')
    ds.disconnect()
    

print('\nDemo complete!')