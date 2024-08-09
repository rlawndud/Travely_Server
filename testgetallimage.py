import asyncio
import websockets
import json
import cv2
import base64
import numpy as np



async def connect():
    """Connect to the WebSocket server and handle communication."""
    try:
        async with websockets.connect("ws://10.101.154.50:8080", ping_interval=20, ping_timeout=20) as websocket:
            user_mode = 'GetAllImage'
            print("[Requesting member image]")
            if user_mode == 'GetAllImage':
                response = json.dumps({
                    "id": "a"
                })

                data = json.loads(response)
                command = {"command": "GetAllImage"}
                ifimage = {"signal": "@"}
                new_response = [command, data, ifimage]
                #new_response = [command, data]

                # Convert new_response to JSON string
                new_response_str = json.dumps(new_response)

                # Send data in chunks
                await websocket.send(new_response_str)

            timeout = 300
            while True:
                try:
                    # Await message with a timeout
                    message = await asyncio.wait_for(websocket.recv(), timeout=timeout)

                    if "@" in message:
                        data = json.loads(message)
                        img_data = data[1]['img_data']

                        image_data_re = base64.b64decode(img_data)
                        nparr = np.frombuffer(image_data_re, np.uint8)
                        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                        cv2.imshow('Decoded Image', image)
                        cv2.waitKey(0)
                        cv2.destroyAllWindows()


                except asyncio.TimeoutError:
                    print("Timed out while waiting for message.")
                    break
                except websockets.exceptions.ConnectionClosedError as e:
                    print(f"WebSocket connection closed: {e}")
                    break
                except Exception as e:
                    print(f"An error occurred: {e}")
                    break
    except Exception as e:
        print(f"Failed to connect or encountered an error: {e}")


asyncio.get_event_loop().run_until_complete(connect())
