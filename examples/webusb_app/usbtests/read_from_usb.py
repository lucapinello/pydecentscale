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
            enable_weight_command = bytearray.fromhex('03 20 01')
            print(f"Sending 'Enable Weight' command: {enable_weight_command.hex(' ')}")
            dev.write(ep_out.bEndpointAddress, enable_weight_command)
            print("'Enable Weight' command sent successfully.")

        except usb.core.USBError as e:
            print(f"Error sending command: {e}")
        monitor_time = 5 #seconds
        print(f"\nReading data from IN endpoint 0x{ep_in.bEndpointAddress:02x} for {monitor_time} seconds...")
        print("-" * 40)

        data_buffer = bytearray()
        protocol_mode = None  # Can be 'text', 'binary', or None
        start_time = time.time()
        last_command_time = time.time()
        
        while time.time() - start_time < monitor_time:  # Increased runtime for better detection
            try:
                if time.time() - last_command_time > 2:
                    try:
                        print("Sending 'Enable Weight' keep-alive command...")
                        dev.write(ep_out.bEndpointAddress, enable_weight_command)
                        last_command_time = time.time()
                    except usb.core.USBError as e:
                        logging.error(f"Error sending keep-alive command: {e}")
                        break

                data = dev.read(ep_in.bEndpointAddress, ep_in.wMaxPacketSize, timeout=1000)
                if not data:
                    continue

                data_buffer.extend(data.tobytes())

                # --- Protocol Detection ---
                if protocol_mode is None:
                    if b"Weight:" in data_buffer:
                        logging.info("Detected TEXT protocol.")
                        protocol_mode = 'text'
                    elif b'\x03' in data_buffer:
                        logging.info("Detected BINARY protocol.")
                        protocol_mode = 'binary'

                # --- Protocol-Specific Processing ---
                if protocol_mode == 'text':
                    text_data = data_buffer.decode('ascii', errors='ignore')
                    logging.info('text_data buffer: %s', text_data)
                    lines = text_data.split('\n')
                    for i in range(len(lines) - 1):
                        line = lines[i]
                        if "Weight:" in line:
                            try:
                                weight_str = line.split("Weight:")[1].strip()
                                weight_value = float(weight_str)
                                logging.info(f">>> SUCCESS! Decoded Weight: {weight_value} <<<")
                            except (IndexError, ValueError) as e:
                                logging.warning(f"Could not parse weight from line: '{line}'. Error: {e}")
                    if lines:
                        data_buffer = bytearray(lines[-1], 'ascii')
                    else:
                        data_buffer.clear()

                elif protocol_mode == 'binary':
                    while len(data_buffer) >= 7:
                        logging.info('binary data buffer: %s', data_buffer)
                        start_index = data_buffer.find(0x03)
                        if start_index == -1:
                            break 
                        if start_index > 0:
                            data_buffer = data_buffer[start_index:]
                        if len(data_buffer) < 7:
                            break
                        
                        packet = data_buffer[:7]
                        calculated_xor = functools.reduce(operator.xor, packet[:-1])

                        if calculated_xor == packet[-1]:
                            logging.info("  [OK] Packet.hex found: %s", {packet.hex(' ')})
                            if packet[1] in [0xCA, 0xCE]:
                                weight_raw = int.from_bytes(packet[2:4], byteorder='big', signed=True)
                                weight_grams = weight_raw / 10.0
                                logging.info(f"\n>>> SUCCESS! Decoded Weight: {weight_grams:.1f} g <<<\n")
                            data_buffer = data_buffer[7:]
                        else:
                            logging.warning(f"  [FAIL] Checksum failed. Packet: {packet.hex(' ')}")
                            data_buffer.pop(0)

            except usb.core.USBError as e:
                if 'timed out' in str(e).lower():
                    logging.info("Read timed out, waiting for more data...")
                    continue
                else:
                    logging.error(f"USB Read Error: {e}")
                    break
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if dev:
            print("Sending Tare Command Now")
            tare_command = bytearray.fromhex('03 0F 01 00 00 01 0C')
            print(f"Sending 'tare_command' command: {tare_command}")
            dev.write(ep_out.bEndpointAddress, tare_command)
            print("'tare_command' command sent successfully.")
            print("\nReleasing device.")
            usb.util.dispose_resources(dev)

if __name__ == "__main__":
    main()
