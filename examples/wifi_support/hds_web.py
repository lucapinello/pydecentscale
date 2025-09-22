import asyncio
import websockets
import json
import logging
import socket
##this will only work with half decent scale with firmware v3.0.0
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class ScaleWebSocketClient:
    def __init__(self, host="hds.local", port=80):
        self.host = host
        self.port = port
        self.uri = f"ws://{host}/snapshot"
        self.weight = 0.0
        self.connected = False
        self.reconnect_delay = 1  # Start with 1 second delay

    async def connect(self):
        """Connect to the scale's WebSocket server with improved error handling"""
        try:
            # Configure WebSocket with higher timeouts due to latency
            self.websocket = await websockets.connect(
                self.uri,
                ping_interval=30,  # Increased ping interval
                ping_timeout=10,   # Shorter ping timeout
                close_timeout=5,   # Shorter close timeout
                max_size=2**20,    # Larger message size limit
            )
            self.connected = True
            self.reconnect_delay = 1  # Reset delay on successful connection
            logging.info(f"Connected to scale WebSocket server at {self.uri}")
            return True
            
        except websockets.exceptions.NegotiationError as e:
            logging.error(f"Server rejected connection (status code {e.status_code})")
            return False
            
        except (websockets.exceptions.WebSocketException, 
                ConnectionRefusedError, 
                asyncio.TimeoutError,
                socket.gaierror) as e:
            logging.error(f"Connection failed: {str(e)}")
            return False

    async def tare(self):
        """Send tare command to scale"""
        if self.connected:
            try:
                await self.websocket.send('tare')
                logging.info("Tare command sent")
                return True
            except Exception as e:
                logging.error(f"Failed to send tare command: {e}")
                return False
        return False

    async def read_weight(self):
        """Read weight updates from the scale with automatic reconnection"""
        while True:
            if not self.connected:
                logging.info(f"Attempting to reconnect in {self.reconnect_delay} seconds...")
                await asyncio.sleep(self.reconnect_delay)
                if await self.connect():
                    self.reconnect_delay = 1
                else:
                    self.reconnect_delay = min(self.reconnect_delay * 2, 60)
                    continue

            try:
                message = await self.websocket.recv()
                data = json.loads(message)
                if 'grams' in data:
                    self.weight = data['grams']
                    print(f"Current weight: {self.weight}g  ", end='\r') 
                
            except (websockets.exceptions.ConnectionClosed, 
                    websockets.exceptions.WebSocketException) as e:
                logging.warning(f"Connection lost: {str(e)}")
                self.connected = False
                continue
            
            except json.JSONDecodeError as e:
                logging.error(f"Invalid JSON received: {str(e)}")
                continue
                
            except Exception as e:
                logging.error(f"Unexpected error: {str(e)}")
                self.connected = False
                await asyncio.sleep(1)

    async def disconnect(self):
        """Disconnect from the scale"""
        if self.connected:
            await self.websocket.close()
            self.connected = False
            logging.info("Disconnected from scale")

async def main():
    client = ScaleWebSocketClient()
    
    try:
        if await client.connect():
            print("Connected to HDS Websocket! Will disconnect after 30 seconds.")
            try:
                async with asyncio.timeout(30):
                    await client.read_weight()
            except asyncio.TimeoutError:
                await client.tare()
                print("\nAutomatically disconnecting after 30 seconds.")
    except KeyboardInterrupt:
        logging.info("Stopping...")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())