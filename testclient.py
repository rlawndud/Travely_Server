import asyncio
import websockets
import json

my_name = '정의찬'

async def connect():
    async with websockets.connect("ws://220.90.180.89:8080", ping_interval=20, ping_timeout=20) as websocket:
        user_mode = 'Logout'
        print("[회원가입]")

        if user_mode == 'Logout':
            response = json.dumps({
                "id": "hwshin",
            })

            data = json.loads(response)

            command = {"command": "Logout"}
            ifimage = {"signal": "@"}
            new_response = [command] + [data] + [ifimage]

            # new_response를 JSON 문자열로 변환
            new_response_str = json.dumps(new_response)

            await websocket.send(new_response_str)


asyncio.get_event_loop().run_until_complete(connect())
