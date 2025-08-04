import usb.core
import usb.util
import time
import functools
import operator
import logging
# Use the VID and PID from your device
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s')

VENDOR_ID = 0x1a86
PRODUCT_ID = 0x7522

def init_ch340(device):
    """
    Initializes the CH340 chip. This sequence is required to set up
    serial communication parameters like baud rate.
    """
    print("Performing CH340 initialization sequence...")
    # This sequence is specific to the CH340 chip
    device.ctrl_transfer(0x40, 0x9A, 0x2518, 0x0000, None) # Vendor-specific init command
    device.ctrl_transfer(0x40, 0x9A, 0x2518, 0x00C3, None) # Sets line control (e.g., 8 data bits, no parity, 1 stop bit)
    print("CH340 initialized.")

def main():
    """
    Connects to a specific USB device and prints all data read from it.
    """
    dev = None
    try:
        # Find the device
        dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)

        if dev is None:
            raise ValueError(f"Device with VID=0x{VENDOR_ID:04x} PID=0x{PRODUCT_ID:04x} not found.")

        print("Device found. Initializing...")

        # Detach kernel driver if active (important on Linux/macOS)
        if dev.is_kernel_driver_active(0):
            print("Detaching kernel driver...")
            dev.detach_kernel_driver(0)

        # Set the active configuration.
        dev.set_configuration()

        # Perform the CH340 init sequence
        init_ch340(dev)

        # Get an endpoint instance
        cfg = dev.get_active_configuration()
        intf = cfg[(0, 0)]

        ep_in = usb.util.find_descriptor(
            intf,
            custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN
        )

        ep_out = usb.util.find_descriptor(
            intf,
            custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
        )

        if ep_in is None or ep_out is None:
            raise IOError("Could not find IN endpoint.")

        # Define and send the wake-up command to start the data stream
        # This is a critical step to get the scale to send weight data.
        # Let's try a different command to see if the device responds differently.
        # wake_up_command = bytearray.fromhex('030A0101000009') # Original "LED On" command
        wake_up_command = bytearray.fromhex('030A0101000009') # "LED On" command
        try:
            print(f"Sending command to OUT endpoint 0x{ep_out.bEndpointAddress:02x}: {wake_up_command.hex(' ')}")
            dev.write(ep_out.bEndpointAddress, wake_up_command)
            print("Command sent successfully.")

            # Per your request, send the "Enable Weight via USB" command.
            # The full 7-byte command is 03 20 01 00 00 00 22 (with XOR checksum)
            enable_weight_command = bytearray.fromhex('03200100000022')
            print(f"Sending 'Enable Weight' command: {enable_weight_command.hex(' ')}")
            dev.write(ep_out.bEndpointAddress, enable_weight_command)
            print("'Enable Weight' command sent successfully.")

        except usb.core.USBError as e:
            print(f"Error sending command: {e}")

        print(f"\nReading data from IN endpoint 0x{ep_in.bEndpointAddress:02x} for 10 seconds...")
        print("-" * 40)

        data_buffer = bytearray()
        logging.info('data buffer1:%s',data_buffer)
        start_time = time.time()
        last_command_time = time.time()
        while time.time() - start_time < 10:
            try:
                # The device seems to stop sending data, so we will periodically ask for it again.
                # This acts as a "keep-alive" by re-sending the enable weight command.
                if time.time() - last_command_time > 2:
                    try:
                        print("Sending 'Enable Weight' keep-alive command...")
                        dev.write(ep_out.bEndpointAddress, enable_weight_command)
                        last_command_time = time.time()
                    except usb.core.USBError as e:
                        print(f"Error sending keep-alive command: {e}")
                        break

                data = dev.read(ep_in.bEndpointAddress, ep_in.wMaxPacketSize, timeout=1000)
                if data:
                    data_buffer.extend(data.tobytes())
                    print("data", data)
                    logging.info('data buffer: %s', data_buffer.hex())
                    logging.info('data buffer: %s', data_buffer)
                # Process the buffer to find and parse valid packets.
                while len(data_buffer) >= 7:
                    # Find the start of a packet (0x03)
                    start_index = data_buffer.find(0x03)
                    if start_index == -1:
                        data_buffer.clear() # No start byte, clear buffer
                        break

                    # Discard any garbage data before the packet
                    if start_index > 0:
                        data_buffer = data_buffer[start_index:]

                    # If we don't have a full packet after slicing, wait for more data
                    if len(data_buffer) < 7:
                        break

                    packet = data_buffer[:7]
                    calculated_xor = functools.reduce(operator.xor, packet[:-1])

                    if calculated_xor == packet[-1]: # Checksum is valid
                        print(f"  [OK] Packet found with valid checksum: {packet.hex(' ')}")
                        if packet[1] in [0xCA, 0xCE]: # It's a weight packet
                            weight_raw = int.from_bytes(packet[2:4], byteorder='big', signed=True)
                            weight_grams = weight_raw / 10.0
                            print(f"\n>>> SUCCESS! Decoded Weight: {weight_grams:.1f} g (from raw integer: {weight_raw}) <<<\n")
                        data_buffer = data_buffer[7:] # Remove processed packet
                    else:
                        print(f"  [FAIL] Packet found but checksum failed. Packet: {packet.hex(' ')}, Expected XOR: {packet[-1]}, Calculated: {calculated_xor}")
                        data_buffer.pop(0) # Bad checksum, discard the 0x03 byte and search again

            except usb.core.USBError as e:
                # A timeout error is expected if the scale doesn't send data continuously.
                # We check for the error string for cross-platform compatibility.
                if 'timed out' in str(e).lower():
                    print("Read timed out, waiting for more data...")
                    continue  # This is expected, just continue the loop
                else:
                    print(f"USB Read Error: {e}")
                    break
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if dev:
            print("\nReleasing device.")
            usb.util.dispose_resources(dev)

if __name__ == "__main__":
    main()
