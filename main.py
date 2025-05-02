import time
from pydecentscale import DecentScale


# Define your callback function
def on_weight_change(weight, ts, stable):
    print(f"New weight received: {weight:.1f}g at {ts}s, stable: {stable}")


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
