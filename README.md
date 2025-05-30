# pydecentscale

Python module to interact with the Decent Scale scales (https://decentespresso.com/scale) via Bluetooth (BLE).

Big thanks to **John Buckman** from Decent for sending a free scale to develop this library!

Also thanks to @mithornhill for contributing code for the new firnware!

## Version 0.4.0 - Firmware v2 Compatibility Update

This version adds support for new Decent Scale firmware versions (v1.1, v1.2+) and the Half Decent Scale model while maintaining backward compatibility with firmware v1.0.

## Features

- Auto-discovery and connection to Decent Scale
- Real-time weight reading via BLE notifications (7-byte and 10-byte formats)
- Weight timestamps for flow rate calculations (firmware v1.2+)
- Firmware version detection
- Battery level monitoring
- Tare function with heartbeat support
- LED display control (grams/ounces selection)
- Timer control (start/stop/reset)
- Power off command (firmware v1.2+)
- Automatic command retry for firmware v1.0 bug
- Half Decent Scale heartbeat support

## Installation

```bash
pip install pydecentscale
```

## Firmware Compatibility

- **v1.0**: Original firmware with command retry workaround
- **v1.1**: Added ounces display, button handling changes
- **v1.2+**: 10-byte weight messages with timestamps, power off command
- **Half Decent Scale**: Requires heartbeat every 5 seconds

## TLDR

```python
from pydecentscale import DecentScale
import asyncio

#Create the DecentScale object
ds=DecentScale()

#Scan and connect to the first available decent scale
ds.auto_connect()

#To read the current weight we need to first enable the BLE notifications
ds.enable_notification()

#Now we can read the current value, this continously read and print values for 5 seconds as fast as they arrive
print('Reading values...')
for i in range(50):
    if ds.weight:
        print('current weight:%.1f' % ds.weight, end='\r')
    asyncio.run( asyncio.sleep(0.1))

print('Disconnecting...')
#Finally we can disconnect
ds.disconnect()
```

## Detailed Example

```python
from pydecentscale import DecentScale
import time

# Create the scale object
ds = DecentScale()

# For Half Decent Scale, enable heartbeat:
# ds = DecentScale(enable_heartbeat=True)

# Connect to the scale
if ds.auto_connect():
    print(f'Connected! Firmware: {ds.get_firmware_version()}')
    
    # Enable weight notifications
    ds.enable_notification()
    
    # Read weight for 5 seconds
    for i in range(50):
        if ds.weight:
            print(f'Weight: {ds.weight}g')
        time.sleep(0.1)
    
    # Get weight with timestamp (firmware v1.2+)
    data = ds.get_weight_with_timestamp()
    if data['timestamp']:
        print(f"Weight: {data['weight']}g at {data['timestamp']}")
    
    # Tare the scale
    ds.tare()
    
    # Control the LED
    ds.led_on()  # Default: grams
    ds.led_on('oz')  # Ounces (firmware v1.1+)
    time.sleep(1)
    ds.led_off()
    
    # Check battery level
    print(f'Battery: {ds.get_battery_level()}%')
    
    # Disconnect
    ds.disconnect()
```

## API Reference

### DecentScale class

#### Constructor
```python
DecentScale(timeout=20, fix_dropped_command=True, enable_heartbeat=False)
```
- `timeout`: BLE connection timeout in seconds
- `fix_dropped_command`: Enable automatic command retry for firmware v1.0 bug
- `enable_heartbeat`: Enable heartbeat for Half Decent Scale (sends keepalive every 4 seconds)

#### Properties
- `weight`: Current weight in grams (None if notifications not enabled)
- `connected`: Connection status
- `firmware_version`: Detected firmware version (after LED command)
- `battery_level`: Battery percentage or 'USB' if USB powered
- `weight_unit`: Current display unit ('g' or 'oz')
- `timestamp`: Weight timestamp dict with minutes, seconds, deciseconds (firmware v1.2+)

#### Methods

- `auto_connect(n_retries=3)`: Scan and connect to the first available Decent Scale
- `find_address()`: Find the BLE address of a Decent Scale
- `connect(address)`: Connect to a scale with known address
- `disconnect()`: Disconnect from the scale
- `enable_notification()`: Start receiving weight notifications (and heartbeat if enabled)
- `disable_notification()`: Stop receiving weight notifications
- `tare()`: Zero the scale
- `led_on(unit='g')`: Turn on the LED display ('g' for grams, 'oz' for ounces)
- `led_off()`: Turn off the LED display
- `power_off()`: Power off the scale (firmware v1.2+ only)
- `start_time()`: Start the timer
- `stop_time()`: Stop the timer
- `reset_time()`: Reset the timer to zero
- `get_firmware_version()`: Get the firmware version
- `get_battery_level()`: Get battery level (% or 'USB')
- `get_weight_unit()`: Get current weight unit
- `get_weight_with_timestamp()`: Get weight with timestamp info

## Examples

Example scripts are provided in the `/examples` directory:
- `Test_Scale.py` - Basic usage example
- `Test_Scale_V2.py` - Demonstrates new firmware v2 features
- `Test_Half_Decent_Scale.py` - Example for Half Decent Scale with heartbeat
- `Test_Scale.ipynb` - Interactive [Jupyter Notebook](https://nbviewer.jupyter.org/github/lucapinello/pydecentscale/blob/main/examples/Test_Scale.ipynb)

## Changelog

### v0.4.0
- Added support for firmware v1.1, v1.2, and newer
- Added 10-byte weight message support with timestamps
- Added firmware version detection
- Added battery level monitoring
- Added Half Decent Scale heartbeat support
- Added power off command
- Added ounces display option
- Updated tare command structure
- Improved notification handler for multiple message formats

### v0.3.1
- Python 3.7 compatibility fix

### v0.3.0
- Initial public release

Enjoy!
