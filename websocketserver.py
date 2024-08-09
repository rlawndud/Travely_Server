import asyncio
import websockets
import json
from socket import error as SocketError
import logging
import pymysql
import time

from websockets.exceptions import ConnectionClosedOK

connected_clients = set()
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

# DB사용을 위한 전역변수
conn = None
cur = None


#*********************************************************************************
# utils
#*********************************************************************************

async def send_chunks(websocket, message, chunk_size=65536):
    try:
        for i in range(0, len(message), chunk_size):
            chunk = message[i:i + chunk_size]
            print(f"Sending chunk {i // chunk_size + 1}: {chunk[:50]}...")  # Print part of the chunk for debugging
            await websocket.send(chunk)
            await asyncio.sleep(0.1)  # 잠시 대기하여 데이터를 처리할 시간을 줌
    except Exception as e:
        logger.error("Error sending chunks: %s", e)


def connect_to_db():
    global conn
    try:
        conn = pymysql.connect(
            host="127.0.0.1",
            user="root",
            password="1234",
            db="wb39",
            charset="utf8"
        )
        print("Database connection successful.")
        return conn
    except pymysql.MySQLError as e:
        print(f"Database connection failed: {e}")
        return None

#*********************************************************************************
# handles
#*********************************************************************************

async def handle_ping(websocket, path):
    response = json.dumps({'response': 'pong'})
    await websocket.send(response)


async def handle_broadcast(websocket, path):
    response = json.dumps({'response': 'broadcast received'})
    await asyncio.gather(*[ws.send(response) for ws in connected_clients])


async def handle_addmember(websocket, path, data):
    global conn, cur

    try:
        print(data)
        print("여기 들어옴?")
        for item in data:
            if "command" in item:
                print(f"Command: {item['command']}")
            else:
                id = item['UserID']
                pw = item['UserPW']
                phone = item['UsPhone']
                name = item['UsName']

                print(id, pw, phone, name)
                # DB => 멤버 생성
                sql = f"insert into member values(%s, %s, %s, %s);"
                val = (id, pw, phone, name)
                cur.execute(sql, val)
                conn.commit()

                await websocket.send("성공")

    except SocketError as e:
        logger.warning("Socket error occurred: %s", e)
    except json.JSONDecodeError as e:
        logger.warning("JSON parsing error: %s", e)
    except pymysql.MySQLError as e:
        logger.warning("Database operation failed: %s", e)
        if websocket.open:
            await websocket.send("DB 오류 발생")
        else:
            logger.warning("WebSocket connection already closed.")
    except Exception as e:
        logger.warning("An unexpected error occurred: %s", e)
        if websocket.open:
            await websocket.send("기타 오류 발생")
        else:
            logger.warning("WebSocket connection already closed.")


async def handle_addmemimg(websocket, path, data):
    global conn, cur

    try:
        print(data)
        print("여기 들어옴?")
        for item in data:
            if "command" in item:
                print(f"Command: {item['command']}")
            else:
                id = item["UserID"]
                name = item["UsName"]
                imgbyte = item["UsFace"]

                # DB => 멤버 생성
                sql = f"insert into memfaceimg values(%s, %s, %s);"
                val = (id, name, imgbyte)
                cur.execute(sql, val)
                conn.commit()

                await websocket.send("성공")

    except SocketError as e:
        logger.warning("Socket error occurred: %s", e)
    except json.JSONDecodeError as e:
        logger.warning("JSON parsing error: %s", e)
    except pymysql.MySQLError as e:
        logger.warning("Database operation failed: %s", e)
        if websocket.open:
            await websocket.send("DB 오류 발생")
        else:
            logger.warning("WebSocket connection already closed.")
    except Exception as e:
        logger.warning("An unexpected error occurred: %s", e)
        if websocket.open:
            await websocket.send("기타 오류 발생")
        else:
            logger.warning("WebSocket connection already closed.")


async def handle_getmemimg(websocket, path, data):
    global conn, cur
    try:
        print(data)
        if data[0]['command'] == 'GetMemImg' and 'UserID' in data[1]:
            id = data[1]['UserID']
            sql = "SELECT UsFace FROM memfaceimg WHERE UserID = %s;"
            cur.execute(sql, (id,))
            rows = cur.fetchall()
            if rows:
                imgs_str = rows[0][0]
                send_imgs_str = imgs_str + '@'
                await send_chunks(websocket, send_imgs_str)
            else:
                await websocket.send("No image found")
        else:
            await websocket.send("Invalid data format")
    except websockets.exceptions.ConnectionClosedError as e:
        logger.warning("WebSocket connection closed: %s", e)
    except Exception as e:
        logger.warning("Error handling 'GetMemImg': %s", e)
        if websocket.open:
            await websocket.send("Error occurred")
        else:
            logger.warning("WebSocket connection already closed.")
    except SocketError as e:
        logger.warning("Socket error occurred: %s", e)
    except json.JSONDecodeError as e:
        logger.warning("JSON parsing error: %s", e)
    except pymysql.MySQLError as e:
        logger.warning("Database operation failed: %s", e)
        if websocket.open:
            await websocket.send("DB 오류 발생")
        else:
            logger.warning("WebSocket connection already closed.")
    except Exception as e:
        logger.warning("An unexpected error occurred: %s", e)
        if websocket.open:
            await websocket.send("기타 오류 발생")
        else:
            logger.warning("WebSocket connection already closed.")


buffer = ""


async def echo(websocket, path):
    global conn, cur, buffer
    connected_clients.add(websocket)
    print(connected_clients)
    # 연결 시도
    while conn is None:
        conn = connect_to_db()
        if conn is None:
            print("Reconnecting in 5 seconds...")
            time.sleep(5)
        else:
            try:
                cur = conn.cursor()
            except pymysql.MySQLError as e:
                print(f"Cursor creation failed: {e}")
                cur = None

    try:
        async for message in websocket:
            buffer += message
            if "@" in buffer:
                try:
                    data = json.loads(buffer)
                    buffer = ""
                    if data[0]['command'] == 'ping':
                        await handle_ping(websocket, path)
                    elif data[0]['command'] == 'broadcast':
                        await handle_broadcast(websocket, path)
                    elif data[0]['command'] == 'AddMember':
                        await handle_addmember(websocket, path, data)
                    elif data[0]['command'] == 'AddMemImg':
                        await handle_addmemimg(websocket, path, data)
                    elif data[0]['command'] == 'GetMemImg':
                        await handle_getmemimg(websocket, path, data)
                    else:
                        print(f"Unknown command received: {data['command']}")
                        await websocket.send("Unknown command")
                except json.JSONDecodeError as e:
                    logger.warning("JSON parsing error: %s", e)
                    if websocket.open:
                        await websocket.send("Invalid data format")
            else:
                #print("데이터 형식이 규칙과 달라!!")
                await websocket.send("데이터 형식이 규칙과 다르잖아 임마!")
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"Connection closed: {e}")
    except ConnectionResetError as e:
        print(f"Connection reset: {e}")
    finally:
        connected_clients.remove(websocket)
        print(connected_clients)
        print("접속종료")


async def main():
    async with websockets.serve(echo, "0.0.0.0", 8080, ping_interval=20, ping_timeout=20, max_size=None):
        print("Running Server......")
        await asyncio.Future()  # run forever


asyncio.run(main())
