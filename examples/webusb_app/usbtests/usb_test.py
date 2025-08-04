import usb.core
import usb.util

def list_usb_devices():
    """
    Finds and prints details for all connected USB devices.
    """
    print("--- Searching for connected USB devices ---")

    # Find all connected devices
    devices = usb.core.find(find_all=True)

    # If no devices are found, exit
    if devices is None:
        print("No USB devices found.")
        return

    # Iterate over all found devices
    for i, dev in enumerate(devices):
        print(f"\n--- Device {i+1} ---")
        print(f"  Vendor ID (VID): 0x{dev.idVendor:04x}")
        print(f"  Product ID (PID): 0x{dev.idProduct:04x}")

        # Try to get string descriptors (manufacturer, product, serial)
        # This can fail due to permissions or if the descriptor is not set
        try:
            # The device must be accessed to read string descriptors
            # We don't need to claim it, just access it.
            if dev.manufacturer:
                print(f"  Manufacturer: {dev.manufacturer}")
            if dev.product:
                print(f"  Product: {dev.product}")
            if dev.serial_number:
                print(f"  Serial Number: {dev.serial_number}")
        except usb.core.USBError as e:
            print(f"  Could not read string descriptors: {e}")
        except Exception as e:
            # Sometimes other errors can occur on specific OSes
            print(f"  An error occurred while reading descriptors: {e}")

        # Iterate through configurations (a device can have multiple)
        for cfg in dev:
            print(f"  Configuration {cfg.bConfigurationValue}:")
            # Iterate through interfaces (the USB equivalent of services)
            for intf in cfg:
                print(f"    Interface {intf.bInterfaceNumber}, AltSetting {intf.bAlternateSetting}:")
                print(f"      Interface Class: {intf.bInterfaceClass}")
                print(f"      Interface SubClass: {intf.bInterfaceSubClass}")

if __name__ == "__main__":
    list_usb_devices()
