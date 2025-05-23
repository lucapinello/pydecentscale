# pydecentscale

Python module to interact with the Decent Scale scales (https://decentespresso.com/scale) via Bluetooth (BLE).

Big thanks to **John Buckman** from Decent for sending a free scale to develop this library!

## TLDR
----

```shell
uv sync
source .venv/bin/activate
python main.py
```

```python
import time
from pydecentscale import DecentScale


# Define your callback function
def on_weight_change(weight, ts):
    print(f"New weight received: {weight:.1f}g at {ts}s")


# Create the DecentScale object
ds = DecentScale()

# Scan and connect to the first available decent scale
ds.auto_connect()

ds.add_weight_callback(on_weight_change)

# To read the current weight we need to first enable the BLE notifications
ds.enable_notification()

# Wait for weight messages to be received by our callback function
print('Reading values...')
time.sleep(50)

print('Disconnecting...')
ds.remove_weight_callback(on_weight_change)  # Optionally remove our callback (will be removed in disconnect function)
ds.disconnect()
````

An illustrative example with all the available functions is provided in /examples as Python script or interactive [Jupyter Notebook](https://nbviewer.jupyter.org/github/lucapinello/pydecentscale/blob/main/examples/Test_Scale.ipynb)

Enjoy!






