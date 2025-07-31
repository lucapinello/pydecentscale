#!/usr/bin/env python
# coding: utf-8
# Example for Half Decent Scale with heartbeat support

from pydecentscale import DecentScale
import time
import logging
import sys

# Configure logging to see detailed output from the pydecentscale library
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# Create the DecentScale object with heartbeat enabled
# The Half Decent Scale requires a heartbeat every 5 seconds
print('Creating DecentScale object with heartbeat support...')
ds = DecentScale(enable_heartbeat=True)


# Connect to the scale. The connect() method now handles enabling notifications.
print('Connecting to Half Decent Scale...')
if ds.auto_connect():
    
    # The connection is now established, and notifications (including the heartbeat) are active.
    print(f'Connected! Firmware: {ds.get_firmware_version()}')
    
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
    
    # Disabling notifications is still useful if you want to stop receiving data
    # but stay connected. It will also stop the heartbeat.
    print('\nDisabling notifications (heartbeat will stop)...')
    ds.disable_notification()
    
    print('\nDisconnecting...')
    ds.disconnect()
    
else:
    print('Failed to connect to scale')

print('\nDemo complete!')