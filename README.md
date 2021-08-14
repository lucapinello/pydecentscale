# pydecentscale

Python module to interact with the Decent Scale scales (https://decentespresso.com/scale) via Bluetooth (BLE).

Big thanks to **John Buckman** from Decent for sending a free scale to develop this library!

## TLDR
----

```
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
````

An illustrative example with all the available functions is provided in /examples as Python script or interactive [Jupyter Notebook](https://nbviewer.jupyter.org/github/lucapinello/pydecentscale/blob/main/examples/Test_Scale.ipynb)

Enjoy!






