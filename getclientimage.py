import asyncio
import websockets
import json
import cv2
import base64
import numpy as np


async def send_chunks(websocket, message, chunk_size=65536):
    try:
        for i in range(0, len(message), chunk_size):
            chunk = message[i:i + chunk_size]
            print(f"Sending chunk {i // chunk_size + 1}: {chunk[:50]}...")  # Print part of the chunk for debugging
            await websocket.send(chunk)
            await asyncio.sleep(0.1)  # 잠시 대기하여 데이터를 처리할 시간을 줌
    except Exception as e:
        print("Error sending chunks: %s", e)

# 이미지 크기 조정 함수
def resize_image(image, width, height):
    # 비율에 따라 조정된 크기로 리사이즈
    h, w = image.shape[:2]
    scale = min(width / w, height / h)
    new_w = int(w * scale)
    new_h = int(h * scale)
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return resized

async def connect():
    """Connect to the WebSocket server and handle communication."""
    try:
        async with websockets.connect("ws://10.101.152.35:8080", ping_interval=20, ping_timeout=20) as websocket:
            user_mode = 'GetMemImg'
            print("[Requesting member image]")
            if user_mode == 'GetMemImg':
                response = json.dumps({
                    "UserID": "a"
                })

                data = json.loads(response)
                command = {"command": "GetMemImg"}
                ifimage = {"signal": "@"}
                new_response = [command, data, ifimage]
                #new_response = [command, data]

                # Convert new_response to JSON string
                new_response_str = json.dumps(new_response)

                # Send data in chunks
                await send_chunks(websocket, new_response_str)

            buffer = ""
            timeout = 300  # Timeout duration in seconds
            while True:
                try:
                    # Await message with a timeout
                    message = await asyncio.wait_for(websocket.recv(), timeout=timeout)
                    buffer += message  # Append received chunk to buffer
                    print(buffer)

                    if "@" in buffer:
                        parts = buffer.split('$')
                        if len(parts) > 1:
                            print(len(parts))
                            img1, img2, img3, img4, img5 = parts  # Assuming the first part is the image data
                            buffer = ""  # Reset buffer after processing

                            print('Data received and processed.')


                            image_data1 = base64.b64decode(img1)
                            image_data2 = base64.b64decode(img2)
                            image_data3 = base64.b64decode(img3)
                            image_data4 = base64.b64decode(img4)
                            image_data5 = base64.b64decode(img5)

                            nparr1 = np.frombuffer(image_data1, np.uint8)
                            nparr2 = np.frombuffer(image_data2, np.uint8)
                            nparr3 = np.frombuffer(image_data3, np.uint8)
                            nparr4 = np.frombuffer(image_data4, np.uint8)
                            nparr5 = np.frombuffer(image_data5, np.uint8)

                            image1 = cv2.imdecode(nparr1, cv2.IMREAD_COLOR)
                            image2 = cv2.imdecode(nparr2, cv2.IMREAD_COLOR)
                            image3 = cv2.imdecode(nparr3, cv2.IMREAD_COLOR)
                            image4 = cv2.imdecode(nparr4, cv2.IMREAD_COLOR)
                            image5 = cv2.imdecode(nparr5, cv2.IMREAD_COLOR)

                            cv2.imwrite('image1.jpg', image1)
                            cv2.imwrite('image2.jpg', image2)
                            cv2.imwrite('image3.jpg', image3)
                            cv2.imwrite('image4.jpg', image4)
                            cv2.imwrite('image5.jpg', image5)


                            cv2.imshow('Decoded Image', image1)
                            cv2.waitKey(0)
                            cv2.imshow('Decoded Image', image2)
                            cv2.waitKey(0)
                            cv2.imshow('Decoded Image', image3)
                            cv2.waitKey(0)
                            cv2.imshow('Decoded Image', image4)
                            cv2.waitKey(0)
                            cv2.imshow('Decoded Image', image5)
                            cv2.waitKey(0)
                            cv2.destroyAllWindows()
                            break

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
