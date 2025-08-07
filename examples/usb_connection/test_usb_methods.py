from read_from_usb import DecentScaleUSB
import logging

def demo_scale_usage():
    scale = DecentScaleUSB()
    try:
        print("Connecting to scale...")
        if not scale.connect():
            print("Failed to connect to scale.")
            return
      
        print("Starting to read weight from scale for 5 seconds...")
        

        print("start reading for 10 seconds")
        scale.start_reading(10) 
        if scale.read_thread is not None:
            scale.read_thread.join()
        print("Reading thread finished.")
        print("Sending tare command...")
        scale.tare()
        scale.stop_reading()

    except Exception as e:
        logging.error(f"Demo error: {e}")
    finally:
        scale.disconnect()
        print("Scale disconnected.")

if __name__ == "__main__":
    demo_scale_usage()