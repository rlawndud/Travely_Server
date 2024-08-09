import asyncio
import websockets
import json
import cv2
import base64
import zlib

async def connect():
    async with websockets.connect("ws://10.101.154.50:8080", ping_interval=20, ping_timeout=20) as websocket:
        user_mode = 'TestSendImage'
        print("[회원사진추가]")

        image = cv2.imread("C:/Users/user/Desktop/11.jpg")
        _, buffer1 = cv2.imencode('.jpg', image)
        image_byte = base64.b64encode(buffer1).decode('utf-8')

        compress_data = zlib.compress(image_byte)


        if user_mode == 'TestSendImage':
            response = json.dumps({
                "id": '1',
                "image": compress_data
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
