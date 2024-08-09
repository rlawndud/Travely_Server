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
            "pw": 'a'
        }

        command = {"command": 'Login'}
        ifimage = {"signal": '@'}

        new_response1 = [command] + [response] + [ifimage]
        new_response_str = json.dumps(new_response1)
        print(new_response_str)

        await websocket.send(new_response_str)

        message = await websocket.recv()
        print(message)

        response = {
            "teamNo": 25,
            "teamName": '이거로테스트하시오행님',
            "addid": '1'
        }

        command = {"command": 'AddTeamMember'}
        ifimage = {"signal": '@'}

        new_response1 = [command] + [response] + [ifimage]
        new_response_str = json.dumps(new_response1)
        print(new_response_str)

        await websocket.send(new_response_str)

        message = await websocket.recv()
        print(message)


        # response2 = {
        #     "teamName": 'aa',
        #     "LeaderId": 'a'
        # }
        #
        # command = {"command": "AddTeam"}
        # new_response2 = [command] + [response2] + [ifimage]
        # new_response_str = json.dumps(new_response2)
        #
        # # Send data in chunks
        # await websocket.send(new_response_str)
        #
        # message = await websocket.recv()
        # print(message)


asyncio.get_event_loop().run_until_complete(connect())
