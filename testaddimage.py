import asyncio
import websockets
import json
import cv2
import base64


async def connect():
    async with websockets.connect("ws://192.168.0.45:8080", ping_interval=20, ping_timeout=20) as websocket:
        user_mode = 'AddImage'
        print("[회원사진추가]")

        image = cv2.imread("C:/Users/user/Desktop/11.jpg")
        _, buffer1 = cv2.imencode('.jpg', image)
        image_byte = base64.b64encode(buffer1).decode('utf-8')

        #print("압축전", len(image_byte))

        image_byte_bytes = base64.b64decode(image_byte)

        #compress_data = zlib.compress(image_byte_bytes)

        #compress_data_str = base64.b64encode(compress_data).decode('utf-8')

        #print("압축후", len(compress_data))

        if user_mode == 'AddImage':
            response = json.dumps({
                "id": '1',
                "teamno": 25,
                "image": image_byte
            })

            data = json.loads(response)
            command = {"command": "AddImage"}
            ifimage = {"signal": "@"}
            new_response = [command] + [data] + [ifimage]

            # new_response를 JSON 문자열로 변환
            new_response_str = json.dumps(new_response)

            # Send data in chunks
            await websocket.send(new_response_str)

asyncio.get_event_loop().run_until_complete(connect())
