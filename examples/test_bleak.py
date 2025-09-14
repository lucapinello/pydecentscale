import asyncio
from bleak import BleakClient, BleakScanner

DEVICE_NAME = "Decent Scale"
SERVICE_UUID = "0000FFF0-0000-1000-8000-00805F9B34FB"
CHAR_UUID = "0000FFF4-0000-1000-8000-00805F9B34FB"

async def main():
    print("Scanning for BLE devices...")
    devices = await BleakScanner.discover(timeout=5.0)
    target = next((d for d in devices if d.name == DEVICE_NAME), None)

    if not target:
        print(f"Device '{DEVICE_NAME}' not found.")
        return

    async with BleakClient(target.address) as client:
        if not client.is_connected:
            print("Failed to connect.")
            return
        print(f"Connected to {DEVICE_NAME}.")

        # Access services (no longer an async method)
        services = client.services
        service = services.get_service(SERVICE_UUID)
        if not service:
            print(f"Service {SERVICE_UUID} not found.")
            return

        char = service.get_characteristic(CHAR_UUID)
        if not char:
            print(f"Characteristic {CHAR_UUID} not found in service.")
            return

        # Read value
        value = await client.read_gatt_char(CHAR_UUID)
        print(f"Value from {CHAR_UUID}: {value} (raw bytes)")
        try:
            print("As string:", value.decode("utf-8"))
        except UnicodeDecodeError:
            print("Value could not be decoded as UTF-8.")

if __name__ == "__main__":
    asyncio.run(main())