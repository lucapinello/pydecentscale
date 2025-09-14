import usb.core
import usb.util
import time
import functools
import operator
import logging
import threading

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(threadName)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s')

class DecentScaleUSB:
    def __init__(self, vendor_id=0x1a86, product_id=0x7522):
        """
        Initializes the DecentScaleUSB object.
        """
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.dev = None
        self.ep_in = None
        self.ep_out = None
        self.is_reading = False
        self.read_thread = None
        self.protocol_mode = None
        self.weight = 0.0

    def _init_ch340(self):
        """
        Initializes the CH340 chip for serial communication.
        """
        logging.info("Performing CH340 initialization sequence...")
        self.dev.ctrl_transfer(0x40, 0x9A, 0x2518, 0x0000, None)
        self.dev.ctrl_transfer(0x40, 0x9A, 0x2518, 0x00C3, None)
        logging.info("CH340 initialized.")
    def enable_USB_weight_command (self):
        """
        Sends a weight enable command to the HDS.
        """
        enable_weight_command = bytearray.fromhex('03 20 01')
        try:
                print("Enable USB weight command sent")
                if self.send_command(enable_weight_command):
                    return True 
        except usb.core.USBError as e:
            logging.error("Error sending command:%s",e)
            return False
    def connect(self) -> bool:
        """
        Finds, initializes, and connects to the USB scale.
        Returns True on success, False on failure.
        """
        self.dev = usb.core.find(idVendor=self.vendor_id, idProduct=self.product_id)
        if self.dev is None:
            logging.error(f"Device with VID=0x{self.vendor_id:04x} PID=0x{self.product_id:04x} not found.")
            return False

        logging.info("Device found. Initializing...")
        if self.dev.is_kernel_driver_active(0):
            logging.info("Detaching kernel driver...")
            self.dev.detach_kernel_driver(0)
        
        self.dev.set_configuration()
        self._init_ch340()
        
        cfg = self.dev.get_active_configuration()
        intf = cfg[(0, 0)]

        self.ep_in = usb.util.find_descriptor(intf, custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN)
        self.ep_out = usb.util.find_descriptor(intf, custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT)

        if self.ep_in is None or self.ep_out is None:
            logging.error("Could not find IN/OUT endpoints.")
            return False
        self.enable_USB_weight_command()
        logging.info("Device connected successfully.")
        return True
    
    def send_command(self, command: bytes):
        """
        Sends a command to the USB device.
        """
        try:
            self.dev.write(self.ep_out.bEndpointAddress, command)
            logging.info("Command sent successfully.%s",command)
            return True
        except usb.core.USBError as e:
            logging.error("Error sending command:%s",e)
            return False
    
        
    def tare(self):
        """
        Sends a tare command to the USB device.
        """
        tare_command = bytearray.fromhex('03 0F 01 00 00 01 0C')
        try:
            self.dev.write(self.ep_out.bEndpointAddress, tare_command)
            print("Tare command sent successfully.")
            return True
        except usb.core.USBError as e:
            logging.error("Error sending command:%s",e)
            return False
    def _detect_protocol(self, data_buffer: bytearray):
        """
        Detects if the incoming data is text or binary protocol.
        Sets self.protocol_mode accordingly.
        """
        if b"Weight:" in data_buffer:
            print("Detected TEXT protocol.")
            self.protocol_mode = 'text'
        elif b'\x03' in data_buffer:
            print("Detected BINARY protocol.")
            self.protocol_mode = 'binary'

    def _extract_weight(self, data_buffer: bytearray):
        """
        Extracts and updates self.weight based on the current protocol_mode.
        Returns the updated weight.
        """
        if self.protocol_mode == 'text':
            text_data = data_buffer.decode('ascii', errors='ignore')
            lines = text_data.split('\n')
            for i in range(len(lines) - 1):
                line = lines[i]
                if "Weight:" in line:
                    try:
                        weight_str = line.split("Weight:")[1].strip()
                        self.weight = float(weight_str)
                        print(f"Current Weight: {self.weight}g")
                    except (IndexError, ValueError) as e:
                        logging.warning(f"Could not parse weight from line: '{line}'. Error: {e}")
            if lines:
                return bytearray(lines[-1], 'ascii')
            else:
                return bytearray()
        elif self.protocol_mode == 'binary':
            while len(data_buffer) >= 7:
                start_index = data_buffer.find(0x03)
                if start_index == -1: break
                if len(data_buffer) < start_index + 7: break

                packet = data_buffer[start_index:start_index+7]
                calculated_xor = functools.reduce(operator.xor, packet[:-1])

                if calculated_xor == packet[-1]:
                    if packet[1] in [0xCA, 0xCE]:
                        weight_raw = int.from_bytes(packet[2:4], byteorder='big', signed=True)
                        self.weight = weight_raw / 10.0
                        print(f"  Current Weight: {self.weight}g")
                    data_buffer = data_buffer[start_index+7:]
                else:
                    data_buffer.pop(start_index)
            return data_buffer
        return data_buffer

    def _read_loop(self, monitor_time: int = None):
        """
        Internal method to run in a separate thread, reading and parsing data.
        If monitor_time is set (in seconds), the loop will run for that duration.
        Only accepts int or None.
        """
        if monitor_time is not None and not isinstance(monitor_time, int):
            raise TypeError("monitor_time must be an int or None")

        data_buffer = bytearray()
        last_command_time = time.time()
        start_time = time.time()

        while self.is_reading:
            if monitor_time is not None and (time.time() - start_time) >= monitor_time:
                print(f"Monitor time of {monitor_time}s reached, stopping read loop.")
                break
            try:
                if time.time() - last_command_time > 2:
                    if not self.enable_USB_weight_command:
                        break
                    last_command_time = time.time()

                data = self.dev.read(self.ep_in.bEndpointAddress, self.ep_in.wMaxPacketSize, timeout=1000)
                if not data:
                    continue

                data_buffer.extend(data.tobytes())

                if self.protocol_mode is None:
                    self._detect_protocol(data_buffer)

                data_buffer = self._extract_weight(data_buffer)

            except usb.core.USBError as e:
                if 'timed out' not in str(e).lower():
                    logging.error(f"USB Read Error: {e}")
                    self.is_reading = False
        print("Read loop stopped.")

    def start_reading(self, monitor_time: int = None):
        """
        Starts the background thread to read data from the scale.
        """
        if self.is_reading:
            logging.warning("Reading thread already started.")
            return
        
        self.is_reading = True
        self.read_thread = threading.Thread(target=self._read_loop, args=(monitor_time,), name="ScaleReadThread")
        self.read_thread.daemon = True
        self.read_thread.start()
        logging.info("Started background reading thread.")

    def stop_reading(self):
        """
        Stops the background reading thread.
        """
        if not self.is_reading:
            logging.warning("Reading thread is not running.")
            return

        self.is_reading = False
        self.read_thread.join() # Wait for the thread to finish
        print("Stopped background reading thread.")

    def disconnect(self):
        """
        Stops reading and releases the USB device.
        """
        if self.is_reading:
            self.stop_reading()
        
        if self.dev:
            print("Releasing device.")
            usb.util.dispose_resources(self.dev)
            self.dev = None

if __name__ == '__main__':
    scale = DecentScaleUSB()
    try:
        if scale.connect():
            scale.start_reading()
            print("Reading from scale for 15 seconds...")
            for _ in range(15):
                print(f"  Current Weight: {scale.weight}g", end='\r')
                time.sleep(1)
            print("\nFinished reading.")
    except Exception as e:
        logging.error(f"An error occurred in the main application: {e}")
    finally:
        scale.disconnect()
        print("Application finished.")