
from pydecentscale import DecentScale
import time
from datetime import datetime
#Create the DecentScale object
ds=DecentScale()
#Scan and connect to the first available decent scale
ds.auto_connect()
#To read the current weight we need to first enable the BLE notifications
ds.enable_notification()
__version__ = '1.0'
def read_weight(total_seconds, interval):
    """
    Read weight for specified duration at given intervals
    total_seconds: how long to run
    interval: how often to read (in seconds)
    """
    start_time = time.time()
    elapsed_time = 0

    try:
        while elapsed_time < total_seconds:
            
            weight = ds.weight 
            
            current_time = datetime.now().strftime("%H:%M:%S")
            print(f"Time: {current_time} - Weight: {weight:.1f} grams", end='\r')
            
            time.sleep(interval)
            elapsed_time = time.time() - start_time
            
    except KeyboardInterrupt:
        print("\nProgram stopped by user")
    except Exception as e:
        print(f"\nError occurred: {e}")
    finally:
        print("\nMeasurement completed")

def main():
    print("Decent Weight Measurement Program")
    print("=========================")
    
    try:
        length = int(input("How many seconds to measure? "))
        frequency = float(input("How often to measure (seconds)? "))
        
        if length <= 0 or frequency <= 0:
            raise ValueError("Time values must be positive")
        if frequency > length:
            raise ValueError("Frequency cannot be larger than total time")
            
        print(f"\nStarting measurement for {length} seconds")
        print(f"Reading every {frequency} seconds")
        print("Press Ctrl+C to stop\n")
        
        read_weight(length, frequency)
        
    except ValueError as e:
        print(f"Invalid input: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

# Run the program
main()
#disconnect after main finishes 
ds.disconnect()