import asyncio
import websockets
import json
import base64
from PIL import Image
import io

async def send_chunks(websocket, message, chunk_size=65536):
    try:
        for i in range(0, len(message), chunk_size):
            chunk = message[i:i + chunk_size]
            print(f"Sending chunk {i // chunk_size + 1}: {chunk[:50]}...")  # Print part of the chunk for debugging
            await websocket.send(chunk)
            await asyncio.sleep(0.1)  # 잠시 대기하여 데이터를 처리할 시간을 줌
    except Exception as e:
        print("Error sending chunks: %s", e)

async def receive_chunks(websocket):
    buffer = ""
    timeout = 300  # Timeout duration in seconds
    while True:
        try:
            message = await asyncio.wait_for(websocket.recv(), timeout=timeout)
            buffer += message  # Append received chunk to buffer
            print(buffer)

            if "@" in buffer:
                test_data = json.loads(buffer)
                return test_data
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

async def connect():
    async with websockets.connect("ws://220.90.180.89:8080", ping_interval=10, ping_timeout=20) as websocket:
        user_mode = 'TestChatImg'
        print("[회원사진추가]")

        image = Image.open("C:/Users/user/Desktop/12.jpeg")

        with io.BytesIO() as output:
            image.save(output, format="JPEG")
            image_bytes = output.getvalue()

        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        print("이미지 크기", len(image_bytes))
        if user_mode == 'TestChatImg':
            response = json.dumps({
                "UserID": 'iwantto',
                "UsName": '갠차나갠차나닝닝닝',
                "UsImage": image_base64,
            })

            command = {"command": 'TestChatImg'}
            ifimage = {"signal": '@'}
            new_response = [command, response, ifimage]

            new_response_str = json.dumps(new_response)

            await send_chunks(websocket, new_response_str)

            while True:
                try:
                    client_image_json = await receive_chunks(websocket)

                    if client_image_json is None:
                        print("사진 안옴!!1")
                    else:
                        for item in client_image_json:
                            if "command" in item:
                                print(f"Command: {item['command']}")
                            else:
                                real_item = json.loads(item)
                                image_base64 = real_item['UsImage']
                                image_bytes = base64.b64decode(image_base64)

                                image_from_bytes = Image.open(io.BytesIO(image_bytes))

                                image_from_bytes.show()
                except Exception as e:
                    print(e)
                    continue



asyncio.get_event_loop().run_until_complete(connect())
