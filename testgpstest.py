import asyncio
import websockets
import json
import cv2
import base64
import zlib


async def connect():
    async with websockets.connect("ws://192.168.0.45:8080", ping_interval=20, ping_timeout=20) as websocket:
        response = {
            "id": 'a',
            "teamNo": '27',
            "latitude": 36.342884769981346,
            "longitude": 127.42815124487925
        }

        command = {"command": 'UpdateLocation'}
        ifimage = {"signal": '@'}

        new_response1 = [command] + [response] + [ifimage]
        new_response_str = json.dumps(new_response1)
        print(new_response_str)

        await websocket.send(new_response_str)

        message = await websocket.recv()
        print(message)


asyncio.get_event_loop().run_until_complete(connect())
