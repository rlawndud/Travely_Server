import asyncio
import websockets
import json
import cv2
import base64

my_name = '정의찬'

async def send_chunks(websocket, message, chunk_size=65536):
    for i in range(0, len(message), chunk_size):
        chunk = message[i:i + chunk_size]
        print("보내는 양:", i)
        await websocket.send(chunk)
        await asyncio.sleep(0.3)  # 잠시 대기하여 서버가 데이터를 처리할 시간을 줌

async def connect():
    async with websockets.connect("ws://10.101.154.50:8080", ping_interval=20, ping_timeout=20) as websocket:
        user_mode = 'AddMemImg'
        print("[회원사진추가]")

        image1 = cv2.imread("C:/Users/user/Desktop/1.jpg")
        _, buffer1 = cv2.imencode('.jpg', image1)
        image1_byte = base64.b64encode(buffer1).decode('utf-8')

        image2 = cv2.imread("C:/Users/user/Desktop/2.jpg")
        _, buffer2 = cv2.imencode('.jpg', image2)
        image2_byte = base64.b64encode(buffer2).decode('utf-8')

        image3 = cv2.imread("C:/Users/user/Desktop/3.jpg")
        _, buffer3 = cv2.imencode('.jpg', image3)
        image3_byte = base64.b64encode(buffer3).decode('utf-8')

        image4 = cv2.imread("C:/Users/user/Desktop/9.jpg")
        _, buffer4 = cv2.imencode('.jpg', image4)
        image4_byte = base64.b64encode(buffer4).decode('utf-8')

        image5 = cv2.imread("C:/Users/user/Desktop/11.jpg")
        _, buffer5 = cv2.imencode('.jpg', image5)
        image5_byte = base64.b64encode(buffer5).decode('utf-8')

        # Combine all image bytes
        image_allstr = '$'.join([image1_byte, image2_byte, image3_byte, image4_byte, image5_byte])

        print("이미지 크기", len(image_allstr))
        if user_mode == 'AddMemImg':
            response = json.dumps({
                "id": 'a',
                "name": 'aaa',
                "face": image_allstr,
            })


            data = json.loads(response)
            command = {"command": "AddMemImg"}
            ifimage = {"signal": "@"}
            new_response = [command] + [data] + [ifimage]

            # new_response를 JSON 문자열로 변환
            new_response_str = json.dumps(new_response)

            # Send data in chunks
            #await send_chunks(websocket, new_response_str)
            await websocket.send(new_response_str)

asyncio.get_event_loop().run_until_complete(connect())
