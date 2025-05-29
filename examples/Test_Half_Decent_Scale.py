#!/usr/bin/env python
# coding: utf-8
# Example for Half Decent Scale with heartbeat support

from pydecentscale import DecentScale
import time


# Create the DecentScale object with heartbeat enabled
# The Half Decent Scale requires a heartbeat every 5 seconds
print('Creating DecentScale object with heartbeat support...')
ds = DecentScale(enable_heartbeat=True)


# Connect to the scale
print('Connecting to Half Decent Scale...')
if ds.auto_connect():
    
    print(f'Connected! Firmware: {ds.get_firmware_version()}')
    
    # Enable notifications - this will also start the heartbeat loop
    print('\nEnabling notifications (heartbeat will start automatically)...')
    ds.enable_notification()
    
    # The heartbeat is now being sent automatically every 4 seconds
    # to ensure we stay within the 5-second requirement
    
    print('\nReading weight for 30 seconds...')
    print('(Heartbeat is being sent automatically in the background)')
    
    start_time = time.time()
    while time.time() - start_time < 30:
        if ds.weight is not None:
            weight_data = ds.get_weight_with_timestamp()
            if weight_data['timestamp']:
                ts = weight_data['timestamp']
                print(f"Weight: {weight_data['weight']:.1f}g at {ts['minutes']}:{ts['seconds']:02d}.{ts['deciseconds']}", end='\r')
            else:
                print(f"Weight: {weight_data['weight']:.1f}g", end='\r')
        time.sleep(0.1)
    
    print('\n\nTesting tare with heartbeat enabled...')
    ds.tare()
    time.sleep(2)
    
    print('\nDisabling notifications (heartbeat will stop)...')
    ds.disable_notification()
    
    print('\nDisconnecting...')
    ds.disconnect()
    
else:
    print('Failed to connect to scale')

print('\nDemo complete!')