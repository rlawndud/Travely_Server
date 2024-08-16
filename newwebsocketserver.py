import asyncio
import time
import threading
import base64
import cv2
import numpy as np
import pickle
import websockets
from websockets.exceptions import ConnectionClosedError
import json
import socket
from socket import error as SocketError
import logging
import pymysql
import requests
from datetime import datetime

logging.basicConfig(filename='server.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# DB사용을 위한 전역변수
conn = None
cur = None


# *********************************************************************************
# utils 웅애
# *********************************************************************************

def get_season(month):
    if month in [12, 1, 2]:
        return "겨울"
    elif month in [3, 4, 5]:
        return "봄"
    elif month in [6, 7, 8]:
        return "여름"
    elif month in [9, 10, 11]:
        return "가을"


async def send_error(websocket, message):
    response = json.dumps({
        "error": message
    })
    new_response = response + '@'
    await websocket.send(new_response)


async def send_chunks(websocket, message, chunk_size=65536):
    try:
        for i in range(0, len(message), chunk_size):
            chunk = message[i:i + chunk_size]
            #print(f"Sending chunk {i // chunk_size + 1}: {chunk[:50]}...")  # Print part of the chunk for debugging
            await websocket.send(chunk)
            await asyncio.sleep(0.01)  # 잠시 대기하여 데이터를 처리할 시간을 줌
    except Exception as e:
        logger.error("Error sending chunks: %s", e)


def connect_to_db():
    global conn
    try:
        conn = pymysql.connect(
            host="127.0.0.1",
            user="root",
            password="1234",
            db="bit",
            charset="utf8"
        )
        print("Database connection successful.")
        return conn
    except pymysql.MySQLError as e:
        print(f"Database connection failed: {e}")
        return None


def encode_image_to_jpg(image):
    # 이미지를 메모리 내에서 .jpg로 인코딩
    is_success, buffer = cv2.imencode('.jpg', image)
    if not is_success:
        raise ValueError("Failed to encode image.")
    return buffer.tobytes()


async def connect_to_server(host, port):
    while True:
        try:
            reader, writer = await asyncio.open_connection(host, port)
            logger.info("Successfully connected to server.")
            return reader, writer
        except Exception as e:
            logger.warning(f"Connection failed: {e}. Retrying in 5 seconds...")
            await asyncio.sleep(5)  # 재연결 대기 시간


# kakao 위치데이터로 주소얻어오기
def get_address(lat, lng):
    url = "https://dapi.kakao.com/v2/local/geo/coord2regioncode.json?x=" + lng + "&y=" + lat
    # 'KaKaoAK '는 그대로 두시고 개인키만 지우고 입력해 주세요.
    # ex) KakaoAK 6af8d4826f0e56c54bc794fa8a294
    headers = {"Authorization": "KakaoAK 47016d6fd880e9e9b236c571fa9ff0b2"}
    api_json = requests.get(url, headers=headers)
    full_address = json.loads(api_json.text)

    return full_address


# ***************************************************************************

class WebsocketServer:

    def __init__(self, hostadr, port):
        #서버의 ip주소
        self.server = None
        self.hostadr = hostadr
        #사용할 포트번호
        self.port = port
        #오류시 띄울 로그의 강도(WARNING이면 코드실행에 문제가 생길경우에 로그를 발생시킨다는 뜻)
        logger.setLevel(logging.INFO)

        self.isloginclient = []
        self.connected_clients = set()

        # 모델통신
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverhost = '220.90.180.88'
        self.serverport = 5001
        self.reader = None
        self.writer = None
        self.lock = asyncio.Lock()

    def handle_input(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.input_loop())

    async def input_loop(self):
        while True:
            choice = input("서버 컨트롤(0: 서버종료, 1: 현재 접속중인 클라출력, 2: 로그인중인 클라 출력, 3:팀 초대 다시보내기(수동)): ")

            if choice == '0':
                # 서버를 종료하는 로직
                print("Stopping server...")
                await self.shutdown_server()
                break

            elif choice == '1':
                # 현재 접속중인 클라이언트 목록 출력
                print(f"Current connected clients: {self.connected_clients}")

            elif choice == '2':
                # 현재 접속중인 클라이언트 중 로그인한 클라이언트의 아이디 출력
                print(f"현재 로그인한 id 출력")
                for islog_cli in self.isloginclient:
                    print(islog_cli['id'])
            elif choice == '3':
                print("접속중인 클라이언트중 팀초대 요청이 있는 클라이언트에게 초대보내기")
                await self.background_addteammember()
            else:
                print("Invalid choice.")

    async def shutdown_server(self):
        self.server.close()
        await self.server.wait_closed()
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
        print("Server stopped.")

    async def run(self):
        self.server = await websockets.serve(self.control, self.hostadr, self.port, ping_interval=20, ping_timeout=20, timeout=60,
                                             max_size=None)
        logger.info("server start datdebayo!")

        #스레드로 서버 커맨드관리
        input_thread = threading.Thread(target=self.handle_input)
        input_thread.start()

        await self.server.wait_closed()

    # 기능을 관리하는 부분
    async def control(self, websocket, path):
        self.connected_clients.add(websocket)
        buffer = ""

        global conn, cur

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
                print(buffer)
                if "@" in buffer:
                    try:
                        data = json.loads(buffer)
                        buffer = ""
                        if data[0]['command'] == 'ping':
                            await self.handle_ping(websocket, path)  #클라이언트 접속 확인(수동)
                        elif data[0]['command'] == 'AddMember':
                            await self.handle_addmember(websocket, path, data)  # 회원가입
                        elif data[0]['command'] == 'AddMemImg':
                            await self.handle_addmemimg(websocket, path, data)  # 회원가입(얼굴이미지)
                        elif data[0]['command'] == 'DeleteMember':
                            await self.handle_deletemember(websocket, path, data)  # 회원탈퇴
                        elif data[0]['command'] == 'Login':
                            await self.handle_login(websocket, path, data)  # 로그인
                        elif data[0]['command'] == 'Logout':
                            await self.handle_logout(websocket, path, data)  # 로그아웃
                        elif data[0]['command'] == 'IdDuplicate':
                            await self.handle_Idduplicate(websocket, path, data)  # 아이디 중복확인
                        elif data[0]['command'] == 'AddImage':
                            await self.handle_addimage(websocket, path, data)
                        elif data[0]['command'] == 'GetAllImage':
                            await self.handle_getallimage(websocket, path, data)  # 이미지 전부받기
                        elif data[0]['command'] == 'AddFriend':
                            await self.handle_addfriend(websocket, path, data)  # 친구추가
                        elif data[0]['command'] == 'RefreshAddFriend':
                            await self.handle_refreshaddfriend(websocket, path, data)  # 받은 친구추가 불러오기
                        elif data[0]['command'] == 'AcceptFriend':
                            await self.handle_acceptfriend(websocket, path, data)  # 친구받기
                        elif data[0]['command'] == 'GetMyFriend':
                            await self.handle_getmyfriend(websocket, path, data)  # 내 친구 불러오기
                        elif data[0]['command'] == 'DeleteFriend':
                            await self.handle_deletefriend(websocket, path, data)
                        elif data[0]['command'] == 'AddTeam':
                            await self.handle_addteam(websocket, path, data)  # 팀 만들기
                        elif data[0]['command'] == 'AddTeamMember':
                            await self.handle_addteammember(websocket, path, data)  # 팀원 추가
                        elif data[0]['command'] == 'AddTeamMemberS':
                            await self.handle_addteammembers(websocket, path, data)
                        elif data[0]['command'] == 'AcceptTeamRequest':
                            await self.handle_acceptteamrequest(websocket, path, data)  # 팀 가입 수락
                        elif data[0]['command'] == 'GetMyTeamInfo':
                            await self.handle_getmyteaminfo(websocket, path, data)
                        elif data[0]['command'] == 'DeleteTeam':
                            await self.handle_deleteteam(websocket, path, data)
                        elif data[0]['command'] == 'TravelStart':
                            await self.handle_travelstart(websocket, path, data)
                        elif data[0]['command'] == 'UpdateLocation':
                            await self.handle_updatelocation(websocket, path, data)
                        else:
                            print(f"Unknown command received: {data['command']}")
                            await send_error(websocket, "Unknown command")
                    except json.JSONDecodeError as e:
                        logger.warning("JSON parsing error: %s", e)
                        if websocket.open:
                            await send_error(websocket, "Invalid data format")
                else:
                    print("데이터 형식이 규칙과 달라!!")
        except websockets.ConnectionClosed as e:
            print(f"Connection closed: {e.code} - {e.reason}")
        except ConnectionResetError as e:
            print(f"Connection reset: {e}")
        except Exception as e:
            logger.warning(f"An unexpected error occurred: {e}")
        finally:
            # for islog_cli in self.isloginclient:
            #     if websocket == islog_cli["socket"]:
            #         self.isloginclient.remove(islog_cli)
            self.connected_clients.remove(websocket)

    async def handle_ping(self, websocket, path):
        response = json.dumps({'response': 'pong'})
        new_response = response + '@'
        await websocket.send(new_response)

    # **********************************************************************
    # 회원관리 기능
    # **********************************************************************

    #로그인
    async def handle_login(self, websocket, path, data):

        global conn, cur

        try:
            id = data[1]['id']
            pw = data[1]['pw']

            for client in self.isloginclient:
                if client['id'] == id:
                    response = json.dumps({
                        "result": "False"
                    })

                    new_response = response + '@'
                    await websocket.send(new_response)
                    return

            print(id, pw)
            # DB => 멤버 생성
            sql = f"select * from member where UserID = %s and UserPW = %s;"
            val = (id, pw)
            cur.execute(sql, val)

            rows = cur.fetchall()
            conn.commit()

            if rows:
                for item in rows:
                    id = item[0]
                    pw = item[1]
                    phone = item[2]
                    name = item[3]

                    # 로그인한 클라이언트 관리
                    islog_client = {"socket": websocket, "id": id}
                    self.isloginclient.append(islog_client)

                    response = json.dumps({
                        "id": id,
                        "pw": pw,
                        "phone": phone,
                        "name": name
                    })

                    new_response = response + '@'
                    await websocket.send(new_response)
            else:
                response = json.dumps({
                    "result": "False"
                })
                new_response = response + '@'
                await websocket.send(new_response)
        except websockets.exceptions.ConnectionClosedError as e:
            logger.warning("WebSocket connection closed 'Login': %s", e)
        except SocketError as e:
            logger.warning("Socket error occurred 'Login': %s", e)
        except json.JSONDecodeError as e:
            logger.warning("JSON parsing error 'Login': %s", e)
        except pymysql.MySQLError as e:
            logger.warning("Database operation failed 'Login': %s", e)
            if websocket.open:
                await send_error(websocket, "DB 오류 발생")
            else:
                logger.warning("WebSocket connection already closed 'Login'.")
        except Exception as e:
            logger.warning("An unexpected error occurred 'Login': %s", e)
            if websocket.open:
                await send_error(websocket, "기타 오류 발생")
            else:
                logger.warning("WebSocket connection already closed 'Login'.")

    #로그아웃
    async def handle_logout(self, websocket, path, data):
        try:
            id = data[1]['id']

            for client in self.isloginclient:
                if client['id'] == id:
                    self.isloginclient.remove(client)
                    response = json.dumps({
                        "result": "True"
                    })

                    new_response = response + '@'
                    await websocket.send(new_response)
                else:
                    response = json.dumps({
                        "result": "False"
                    })
                    new_response = response + '@'
                    await websocket.send(new_response)
        except websockets.exceptions.ConnectionClosedError as e:
            logger.warning("WebSocket connection closed 'Logout': %s", e)
        except SocketError as e:
            logger.warning("Socket error occurred: %s", e)
        except Exception as e:
            logger.warning("An unexpected error occurred 'Logout': %s", e)
            if websocket.open:
                await send_error(websocket, "기타 오류 발생")
            else:
                logger.warning("WebSocket connection already closed 'Login'.")

    #아이디 중복검사
    async def handle_Idduplicate(self, websocket, path, data):
        global conn, cur

        try:
            id = data[1]["id"]

            sql = f"select exists (select * from member where UserID = %s) as success;"
            val = id
            cur.execute(sql, val)

            row = cur.fetchall()
            if row[0][0] == 1:
                response = json.dumps({
                    "result": "True"
                })

                new_response = response + '@'
                await websocket.send(new_response)
            else:
                response = json.dumps({
                    "result": "False"
                })
                new_response = response + '@'
                await websocket.send(new_response)

            conn.commit()
        except SocketError as e:
            logger.warning("Socket error occurred 'IdDuplicate' : %s", e)
        except json.JSONDecodeError as e:
            logger.warning("JSON parsing error: %s", e)
        except pymysql.MySQLError as e:
            logger.warning("Database operation failed 'IdDuplicate': %s", e)
            if websocket.open:
                await send_error(websocket, "False")
            else:
                logger.warning("WebSocket connection already closed 'IdDuplicate'.")
        except Exception as e:
            logger.warning("An unexpected error occurred 'IdDuplicate': %s", e)
            if websocket.open:
                await send_error(websocket, "기타 오류 발생")
            else:
                logger.warning("WebSocket connection already closed 'IdDuplicate'.")

    #회원가입
    async def handle_addmember(self, websocket, path, data):

        global conn, cur

        try:
            id = data[1]['id']
            pw = data[1]['pw']
            name = data[1]['name']
            phone = data[1]['phone']

            # DB => 멤버 생성
            sql = f"insert into member values(%s, %s, %s, %s);"
            val = (id, pw, phone, name)
            cur.execute(sql, val)
            conn.commit()

            response = json.dumps({
                "result": "True"
            })

            new_response = response + '@'
            await websocket.send(new_response)
        except websockets.exceptions.ConnectionClosedError as e:
            logger.warning("WebSocket connection closed 'AddMember': %s", e)
        except SocketError as e:
            logger.warning("Socket error occurred 'AddMember': %s", e)
        except json.JSONDecodeError as e:
            logger.warning("JSON parsing error 'AddMember': %s", e)
        except pymysql.MySQLError as e:
            logger.warning("Database operation failed 'AddMember': %s", e)
            if websocket.open:
                await send_error(websocket, "False")
            else:
                logger.warning("WebSocket connection already closed 'AddMember'.")
        except Exception as e:
            logger.warning("An unexpected error occurred 'AddMember': %s", e)
            if websocket.open:
                await send_error(websocket, "기타 오류 발생")
            else:
                logger.warning("WebSocket connection already closed 'AddMember'.")

    #회원가입(얼굴사진)
    async def handle_addmemimg(self, websocket, path, data):
        global conn, cur

        try:
            id = data[1]['id']
            name = data[1]["name"]
            imgbyte = data[1]["face"]

            # DB => 멤버 생성
            sql = f"insert into memfaceimg values(%s, %s, %s);"
            val = (id, name, imgbyte)
            cur.execute(sql, val)
            conn.commit()

            response = json.dumps({
                "result": "True"
            })

            new_response = response + '@'
            await websocket.send(new_response)
        except websockets.exceptions.ConnectionClosedError as e:
            logger.warning("WebSocket connection closed 'AddMemImg': %s", e)
        except SocketError as e:
            logger.warning("Socket error occurred 'AddMemImg': %s", e)
        except json.JSONDecodeError as e:
            logger.warning("JSON parsing error 'AddMemImg': %s", e)
        except pymysql.MySQLError as e:
            logger.warning("Database operation failed 'AddMemImg': %s", e)
            if websocket.open:
                await send_error(websocket, "DB 오류 발생")
            else:
                logger.warning("WebSocket connection already closed 'AddMemImg'.")
        except Exception as e:
            logger.warning("An unexpected error occurred 'AddMemImg': %s", e)
            if websocket.open:
                await send_error(websocket, "기타 오류 발생")
            else:
                logger.warning("WebSocket connection already closed 'AddMemImg'.")

    #회원탈퇴
    async def handle_deletemember(self, websocket, path, data):
        global cur, conn
        try:
            id = data[1]['id']

            # sql = 'delete from teammem where teamNo = ? and UserID = '';'
            # val = (id,)
            # cur.execute(sql, val)
            # conn.commit()

            sql = 'delete from member where UserID = %s;'
            val = (id,)
            cur.execute(sql, val)
            conn.commit()

            for client in self.isloginclient:
                if client['id'] == id:
                    self.isloginclient.remove(client)

            response = json.dumps({
                "result": "True"
            })
            new_response = response + '@'
            await websocket.send(new_response)
        except websockets.exceptions.ConnectionClosedError as e:
            logger.warning("WebSocket connection closed 'DeleteMember': %s", e)
        except SocketError as e:
            logger.warning("Socket error occurred 'DeleteMember': %s", e)
        except json.JSONDecodeError as e:
            logger.warning("JSON parsing error 'DeleteMember': %s", e)
        except pymysql.MySQLError as e:
            logger.warning("Database operation failed 'DeleteMember': %s", e)
            if websocket.open:
                await send_error(websocket, "False")
            else:
                logger.warning("WebSocket connection already closed 'DeleteMember'.")
        except Exception as e:
            logger.warning("An unexpected error occurred 'DeleteMember': %s", e)
            if websocket.open:
                await send_error(websocket, "기타 오류 발생")
            else:
                logger.warning("WebSocket connection already closed 'DeleteMember'.")

    # *****************************************************************

    async def handle_addimage(self, websocket, path, data):
        global conn, cur
        try:
            if data[0]['command'] == 'AddImage':
                id = data[1]['id']
                teamno = data[1]['teamno']
                img_data = data[1]['image']
                location = data[1]['location']
                date = data[1]['date']

                # 데이터 전처리
                latitude = location['latitude']  # 위도
                longitude = location['longitude']  # 경도
                full_address = get_address(f'{latitude}', f'{longitude}')
                addarr = full_address['documents']

                address = addarr[0]['address_name']

                date_object = datetime.strptime(date, "%Y/%m/%d %H:%M:%S")

                month = date_object.month

                # 계절 추출
                season = get_season(month)

                # 모델 경유
                image_data = base64.b64decode(img_data)
                nparr = np.frombuffer(image_data, np.uint8)
                image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                jpg_img = encode_image_to_jpg(image)

                print("데이터 전처리 완료")

                # 전송할 데이터 준비
                data_to_send = {
                    'create_room': 'False',
                    'photo_analyze': 'True',
                    'delete_room': 'False',
                    'room_index': teamno,
                    'member_names': '',
                    'photo': jpg_img
                }
                real_received_data = await self.manage_connection(self.serverhost, self.serverport, data_to_send)
                print(real_received_data)

                face = real_received_data['face_predictions']
                background = real_received_data['background_predictions']
                caption = real_received_data['captions_predictions']

                sql = 'INSERT INTO Images VALUES (NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);'
                val = (id, img_data, teamno, face, background, caption, latitude, longitude, address, date, season)
                cur.execute(sql, val)
                conn.commit()

                sql = 'select UserID from teammem where teamNo = %s and isaccept = true;'
                val = (teamno,)
                cur.execute(sql, val)
                rows = cur.fetchall()
                print(rows)

                if rows:
                    for row in rows:
                        team_id = row[0]

                        for client in self.isloginclient:
                            if client['id'] == team_id:
                                websocket1 = client['socket']

                                response = json.dumps({
                                    "command": 'UpdateImageSignal',
                                    "result": "True"})
                                await websocket1.send(response + '@')
                else:
                    response = json.dumps({
                        "result": "False"
                    })
                    new_response = response + '@'
                    await websocket.send(new_response)
        except websockets.exceptions.ConnectionClosedError as e:
            logger.warning("WebSocket connection closed 'AddImage': %s", e)
        except SocketError as e:
            logger.warning("Socket error occurred 'AddImage': %s", e)
        except json.JSONDecodeError as e:
            logger.warning("JSON parsing error 'AddImage': %s", e)
        except pymysql.MySQLError as e:
            logger.warning("Database operation failed 'AddImage': %s", e)
            if websocket.open:
                await send_error(websocket, "DB 오류 발생")
            else:
                logger.warning("WebSocket connection already closed 'AddImage'.")
        except Exception as e:
            logger.warning("Error handling 'AddImage': %s", e)
            if websocket.open:
                await send_error(websocket, "Error occurred")
            else:
                logger.warning("WebSocket connection already closed 'AddImage'.")

    async def handle_getallimage(self, websocket, path, data):
        global conn, cur
        sql = 'select * from Images where (teamNo = %s '
        ad = 'or teamNo = %s '
        ifff = 'and Image_No > %s '
        odb = 'order by Image_No asc'
        orend = ') '
        end = ';'
        try:
            teamnos = data[1]['team']
            last_img_num = data[1]["last_img_num"]

            teamnos_tuple = tuple(teamnos)

            if last_img_num is None:
                realadd = ad * (len(teamnos) - 1)
                rerealadd = sql + realadd + orend
                realsql = rerealadd + odb + end
                val = teamnos_tuple
                print(realsql)

                cur.execute(realsql, val)
                rows = cur.fetchall()

                if rows is not None:
                    for datas in rows:
                        img_num = datas[0]
                        id = datas[1]
                        img_data = datas[2]
                        teamno = datas[3]
                        pre_face = datas[4]
                        pre_background = datas[5]
                        pre_caption = datas[6]
                        latitude = datas[7]
                        longitude = datas[8]
                        location = datas[9]
                        date = datas[10]
                        season = datas[11]
                        response = json.dumps({
                            'command': 'UpdateImage',
                            "img_num": img_num,
                            "id": id,
                            "img_data": img_data,
                            "teamno": teamno,
                            "pre_face": pre_face,
                            "pre_background": pre_background,
                            "pre_caption": pre_caption,
                            "latitude": latitude,
                            "longitude": longitude,
                            "location": location,
                            "date": date,
                            "season": season
                        })

                        new_response = response + '@'

                        await send_chunks(websocket, new_response)

            else:
                if isinstance(last_img_num, int):
                    last_img_num = [last_img_num]

                last_img_num_tuple = tuple(last_img_num)
                realadd = ad * (len(teamnos) - 1)
                realsql = sql + realadd + orend + ifff + odb + end
                val = teamnos_tuple + last_img_num_tuple
                print(realsql)

                cur.execute(realsql, val)
                rows = cur.fetchall()

                if rows is not None:
                    for datas in rows:
                        img_num = datas[0]
                        id = datas[1]
                        img_data = datas[2]
                        teamno = datas[3]
                        pre_face = datas[4]
                        pre_background = datas[5]
                        pre_caption = datas[6]
                        latitude = datas[7]
                        longitude = datas[8]
                        location = datas[9]
                        date = datas[10]
                        season = datas[11]
                        response = json.dumps({
                            'command': 'UpdateImage',
                            "img_num": img_num,
                            "id": id,
                            "img_data": img_data,
                            "teamno": teamno,
                            "pre_face": pre_face,
                            "pre_background": pre_background,
                            "pre_caption": pre_caption,
                            "latitude": latitude,
                            "longitude": longitude,
                            "location": location,
                            "date": date,
                            "season": season
                        })

                        new_response = response + '@'

                        await send_chunks(websocket, new_response)

                else:
                    response = json.dumps({
                        "result": "False"
                    })
                    new_response = response + '@'
                    await websocket.send(new_response)
        except websockets.exceptions.ConnectionClosedError as e:
            logger.warning("WebSocket connection closed 'GetAllImage': %s", e)
        except SocketError as e:
            logger.warning("Socket error occurred 'GetAllImage': %s", e)
        except json.JSONDecodeError as e:
            logger.warning("JSON parsing error 'GetAllImage': %s", e)
        except pymysql.MySQLError as e:
            logger.warning("Database operation failed 'GetAllImage': %s", e)
            if websocket.open:
                await send_error(websocket, "DB 오류 발생")
            else:
                logger.warning("WebSocket connection already closed 'GetAllImage'.")
        except Exception as e:
            logger.warning("Error handling 'GetAllImage': %s", e)
            if websocket.open:
                response = json.dumps({
                    "result": "False"
                })
                new_response = response + '@'
                await websocket.send(new_response)
            else:
                logger.warning("WebSocket connection already closed 'GetAllImage'.")

    # **********************************************************************
    # 친구 기능
    # **********************************************************************

    async def handle_addfriend(self, websocket, path, data):
        global cur, conn
        try:
            from_id = data[1]['from_id']
            to_id = data[1]['to_id']

            sql = "insert into friendcontrol (from_mem_id, to_mem_id, is_friend) select %s, %s, true where %s != %s and not exists (select 1 from friendcontrol where from_mem_id = %s and to_mem_id = %s and is_friend = true);"
            val = (from_id, to_id, from_id, to_id, from_id, to_id)
            cur.execute(sql, val)

            if cur.rowcount == 0:
                response = json.dumps({
                    "result": "False"
                })
                new_response = response + '@'
                await websocket.send(new_response)
                return

            conn.commit()

            sql = "insert into friendcontrol (from_mem_id, to_mem_id, is_friend) select %s, %s, false where  %s != %s and not exists (select 1 from friendcontrol where from_mem_id = %s and to_mem_id = %s and is_friend = false);"
            val = (to_id, from_id, to_id, from_id, to_id, from_id)
            cur.execute(sql, val)
            conn.commit()

            response = json.dumps({
                "result": "True"
            })

            new_response = response + '@'
            await websocket.send(new_response)

        except websockets.exceptions.ConnectionClosedError as e:
            logger.warning("WebSocket connection closed 'AddFriend': %s", e)
        except SocketError as e:
            logger.warning("Socket error occurred 'AddFriend': %s", e)
        except json.JSONDecodeError as e:
            logger.warning("JSON parsing error 'AddFriend': %s", e)
        except pymysql.MySQLError as e:
            logger.warning("Database operation failed 'AddFriend': %s", e)
            if websocket.open:
                await send_error(websocket, "DB 오류 발생")
            else:
                logger.warning("WebSocket connection already closed 'AddFriend'.")
        except Exception as e:
            logger.warning("Error handling 'AddFriend': %s", e)
            if websocket.open:
                await send_error(websocket, "Error occurred")
            else:
                logger.warning("WebSocket connection already closed 'AddFriend'.")

    async def handle_refreshaddfriend(self, websocket, path, data):
        global conn, cur
        try:
            id = data[1]['id']

            sql = "select fc.to_mem_id, m.UsName from friendcontrol fc join member m on fc.to_mem_id = m.UserID where fc.from_mem_id = %s and fc.is_friend = false;"
            val = (id,)
            cur.execute(sql, val)
            conn.commit()
            rows = cur.fetchall()

            to_ids = []
            to_names = []

            for row in rows:
                to_id = row[0]
                to_name = row[1]

                to_ids.append(to_id)
                to_names.append(to_name)

            response = json.dumps({
                "to_ids": to_ids,
                "to_names": to_names
            })
            new_response = response + '@'
            await websocket.send(new_response)
        except websockets.exceptions.ConnectionClosedError as e:
            logger.warning("WebSocket connection closed 'RefreshAddFriend': %s", e)
        except SocketError as e:
            logger.warning("Socket error occurred 'RefreshAddFriend': %s", e)
        except json.JSONDecodeError as e:
            logger.warning("JSON parsing error 'RefreshAddFriend': %s", e)
        except pymysql.MySQLError as e:
            logger.warning("Database operation failed 'RefreshAddFriend': %s", e)
            if websocket.open:
                await send_error(websocket, "DB 오류 발생")
            else:
                logger.warning("WebSocket connection already closed 'RefreshAddFriend'.")
        except Exception as e:
            logger.warning("Error handling 'RefreshAddFriend': %s", e)
            if websocket.open:
                await send_error(websocket, "Error occurred")
            else:
                logger.warning("WebSocket connection already closed 'RefreshAddFriend'.")

    async def handle_acceptfriend(self, websocket, path, data):
        global cur, conn

        try:
            from_id = data[1]['from_id']
            to_id = data[1]['to_id']
            are_we = data[1]['are_we']

            if are_we:
                sql = 'update friendcontrol set is_friend = true where from_mem_id = %s and to_mem_id = %s;'
                val = (to_id, from_id)
                cur.execute(sql, val)
                conn.commit()

                response = json.dumps({
                    "result": "True"
                })

                new_response = response + '@'
                await websocket.send(new_response)

            else:
                sql = 'delete from friendcontrol where from_mem_id = %s and to_mem_id = %s;'
                val = (from_id, to_id)
                cur.execute(sql, val)
                conn.commit()

                sql = 'delete from friendcontrol where from_mem_id = %s and to_mem_id = %s;'
                val = (to_id, from_id)
                cur.execute(sql, val)
                conn.commit()

                response = json.dumps({
                    "result": "False"
                })
                await websocket.send(response)
        except websockets.exceptions.ConnectionClosedError as e:
            logger.warning("WebSocket connection closed 'AcceptFriend': %s", e)
        except SocketError as e:
            logger.warning("Socket error occurred 'AcceptFriend': %s", e)
        except json.JSONDecodeError as e:
            logger.warning("JSON parsing error 'AcceptFriend': %s", e)
        except pymysql.MySQLError as e:
            logger.warning("Database operation failed 'AcceptFriend': %s", e)
            if websocket.open:
                await send_error(websocket, "DB 오류 발생")
            else:
                logger.warning("WebSocket connection already closed 'AcceptFriend'.")
        except Exception as e:
            logger.warning("Error handling 'AcceptFriend': %s", e)
            if websocket.open:
                await send_error(websocket, "Error occurred")
            else:
                logger.warning("WebSocket connection already closed 'AcceptFriend'.")

    async def handle_getmyfriend(self, websocket, path, data):
        global cur, conn

        try:
            my_id = data[1]['id']

            sql = 'select distinct fc1.to_mem_id, m.usname from friendcontrol fc1 join friendcontrol fc2 on fc1.to_mem_id = fc2.from_mem_id join member m on fc1.to_mem_id = m.userid where fc1.from_mem_id = %s and fc1.is_friend = true and fc2.is_friend = true;'
            val = (my_id,)
            cur.execute(sql, val)
            conn.commit()

            rows = cur.fetchall()

            my_friends_id = []
            my_fridend_name = []

            for row in rows:
                friend_id = row[0]
                friend_name = row[1]

                my_friends_id.append(friend_id)
                my_fridend_name.append(friend_name)

            response = json.dumps({
                "my_friends_id": my_friends_id,
                'my_fridend_name': my_fridend_name
            })
            new_response = response + '@'
            await websocket.send(new_response)
        except websockets.exceptions.ConnectionClosedError as e:
            logger.warning("WebSocket connection closed 'GetMyFriend': %s", e)
        except SocketError as e:
            logger.warning("Socket error occurred 'GetMyFriend': %s", e)
        except json.JSONDecodeError as e:
            logger.warning("JSON parsing error 'GetMyFriend': %s", e)
        except pymysql.MySQLError as e:
            logger.warning("Database operation failed 'GetMyFriend': %s", e)
            if websocket.open:
                await send_error(websocket, "DB 오류 발생")
            else:
                logger.warning("WebSocket connection already closed.")
        except Exception as e:
            logger.warning("Error handling 'GetMyFriend': %s", e)
            if websocket.open:
                await send_error(websocket, "Error occurred")
            else:
                logger.warning("WebSocket connection already closed 'GetMyFriend'.")

    async def handle_deletefriend(self, websocket, path, data):
        global cur, conn
        try:
            from_id = data[1]['from_id']
            to_id = data[1]['to_id']

            sql = 'delete from friendcontrol where from_mem_id = %s and to_mem_id = %s;'
            val = (from_id, to_id)
            cur.execute(sql, val)
            conn.commit()

            sql = 'delete from friendcontrol where from_mem_id = %s and to_mem_id = %s;'
            val = (to_id, from_id)
            cur.execute(sql, val)
            conn.commit()

            response = json.dumps({
                "result": "True"
            })
            await websocket.send(response + '@')
        except websockets.exceptions.ConnectionClosedError as e:
            logger.warning("WebSocket connection closed 'DeleteFriend': %s", e)
        except SocketError as e:
            logger.warning("Socket error occurred 'DeleteFriend': %s", e)
        except json.JSONDecodeError as e:
            logger.warning("JSON parsing error 'DeleteFriend': %s", e)
        except pymysql.MySQLError as e:
            logger.warning("Database operation failed 'DeleteFriend': %s", e)
            if websocket.open:
                await send_error(websocket, "DB 오류 발생")
            else:
                logger.warning("WebSocket connection already closed.")
        except Exception as e:
            logger.warning("Error handling 'DeleteFriend': %s", e)
            if websocket.open:
                await send_error(websocket, "Error occurred")
            else:
                logger.warning("WebSocket connection already closed 'DeleteFriend'.")

    # **********************************************************************

    # **********************************************************************
    # 팀 기능
    # **********************************************************************

    # 팀 생성
    async def handle_addteam(self, websocket, path, data):
        global cur, conn

        try:
            teamname = data[1]['teamName']
            id = data[1]['LeaderId']

            sql1 = 'insert into team (teamNo, teamName, LeaderID) select null, %s, %s where not exists (select 1 from team where LeaderID = %s and teamName = %s);'
            val1 = (teamname, id, id, teamname)

            cur.execute(sql1, val1)
            if cur.rowcount == 0:
                response = json.dumps({
                    "result": "False"
                })
                new_response = response + '@'
                await websocket.send(new_response)
                return

            conn.commit()

            sql2 = 'select teamNo from team where LeaderID = %s and teamName = %s;'
            val2 = (id, teamname)

            cur.execute(sql2, val2)
            conn.commit()

            row = cur.fetchall()

            if row:
                teamno = row[0][0]

                sql3 = 'insert into teammem values(%s, %s, %s, true);'
                val3 = (teamno, teamname, id)
                cur.execute(sql3, val3)
                conn.commit()

                response = json.dumps({
                    "teamno": teamno,
                    "teamName": teamname,
                    "LeaderID": id
                })

                new_response = response + '@'
                await websocket.send(new_response)
            else:
                response = json.dumps({
                    "result": "False"
                })
                new_response = response + '@'
                await websocket.send(new_response)
        except websockets.exceptions.ConnectionClosedError as e:
            logger.warning("WebSocket connection closed 'AddTeam': %s", e)
        except SocketError as e:
            logger.warning("Socket error occurred 'AddTeam': %s", e)
        except json.JSONDecodeError as e:
            logger.warning("JSON parsing error 'AddTeam': %s", e)
        except pymysql.MySQLError as e:
            logger.warning("Database operation failed 'AddTeam': %s", e)
            if websocket.open:
                await send_error(websocket, "False")
            else:
                logger.warning("WebSocket connection already closed 'AddTeam'.")
        except Exception as e:
            logger.warning("An unexpected error occurred 'AddTeam': %s", e)
            if websocket.open:
                await send_error(websocket, "기타 오류 발생")
            else:
                logger.warning("WebSocket connection already closed 'AddTeam'.")

    # 팀 초대
    async def handle_addteammember(self, websocket, path, data):
        global cur, conn

        try:
            teamno = data[1]['teamNo']
            teamname = data[1]['teamName']
            addid = data[1]['addid']

            sql = 'insert into teammem (teamNo, teamName, UserID, isaccept) select %s, %s, %s, false where not exists (select 1 from teammem where teamNo = %s and teamName = %s and UserID = %s and isaccept = false);'
            val = (teamno, teamname, addid, teamno, teamname, addid)

            cur.execute(sql, val)

            if cur.rowcount == 0:
                response = json.dumps({
                    "result": "False"
                })
                new_response = response + '@'
                await websocket.send(new_response)
                return

            conn.commit()
            response = json.dumps({
                "result": "True"
            })
            new_response = response + '@'
            await websocket.send(new_response)

            for client in self.isloginclient:
                if client['id'] == addid:
                    websocket1 = client['socket']

                    response = json.dumps({
                        "command": "JoinTeamRequest",
                        "teamno": teamno,
                        "teamName": teamname,
                        "addid": addid
                    })

                    new_response = response + '@'

                    await websocket1.send(new_response)
        except websockets.exceptions.ConnectionClosedError as e:
            logger.warning("WebSocket connection closed 'AddTeamMember': %s", e)
        except SocketError as e:
            logger.warning("Socket error occurred 'AddTeamMember': %s", e)
        except json.JSONDecodeError as e:
            logger.warning("JSON parsing error 'AddTeamMember': %s", e)
        except pymysql.MySQLError as e:
            logger.warning("Database operation failed 'AddTeamMember': %s", e)
            if websocket.open:
                await send_error(websocket, "False")
            else:
                logger.warning("WebSocket connection already closed 'AddTeamMember'.")
        except Exception as e:
            logger.warning("An unexpected error occurred 'AddTeamMember': %s", e)
            if websocket.open:
                await send_error(websocket, "False")
            else:
                logger.warning("WebSocket connection already closed 'AddTeamMember'.")

    async def handle_addteammembers(self, websocket, path, data):
        global cur, conn

        try:
            teamno = data[1]['teamNo']
            teamname = data[1]['teamName']
            addids = data[1]['addids']
            my_id = data[1]['my_id']

            if addids is None:
                response = json.dumps({
                    "result": "False"
                })
                new_response = response + '@'
                await websocket.send(new_response)
                return

            sql = 'select UsName from member where UserID = %s;'
            val = (my_id,)

            cur.execute(sql, val)
            row = cur.fetchall()

            if row:
                name = row[0]

                for id in addids:
                    sql = 'insert into teammem (teamNo, teamName, UserID, isaccept) select %s, %s, %s, true where not exists (select 1 from teammem where teamNo = %s and teamName = %s and UserID = %s and isaccept = true);'
                    val = (teamno, teamname, id, teamno, teamname, id)

                    cur.execute(sql, val)

                    if cur.rowcount == 0:
                        response = json.dumps({
                            "result": "False"
                        })
                        new_response = response + '@'
                        await websocket.send(new_response)
                        continue
                    conn.commit()

                    for client in self.isloginclient:
                        if client['id'] == id:
                            websocket1 = client['socket']

                            response = json.dumps({
                                "command": "JoinedTeamSignal",
                                "teamno": teamno,
                                "teamName": teamname,
                                "from_name": name
                            })

                            new_response = response + '@'

                            await websocket1.send(new_response)

                for id in addids:
                    for client in self.isloginclient:
                        if client['id'] == id:
                            websocket1 = client['socket']

                            response = json.dumps({
                                "command": 'UpdateTeamSignal',
                                "result": "True"})
                            await websocket1.send(response + '@')

                await self.handle_travelstart(websocket, path, data)
            else:
                response = json.dumps({
                    "result": "False"
                })
                new_response = response + '@'
                await websocket.send(new_response)
        except websockets.exceptions.ConnectionClosedError as e:
            logger.warning("WebSocket connection closed 'AddTeamMemberS': %s", e)
        except SocketError as e:
            logger.warning("Socket error occurred 'AddTeamMemberS': %s", e)
        except json.JSONDecodeError as e:
            logger.warning("JSON parsing error 'AddTeamMemberS': %s", e)
        except pymysql.MySQLError as e:
            logger.warning("Database operation failed 'AddTeamMemberS': %s", e)
            if websocket.open:
                await send_error(websocket, "False")
            else:
                logger.warning("WebSocket connection already closed 'AddTeamMemberS'.")
        except Exception as e:
            logger.warning("An unexpected error occurred 'AddTeamMemberS': %s", e)
            if websocket.open:
                await send_error(websocket, "False")
            else:
                logger.warning("WebSocket connection already closed 'AddTeamMemberS'.")

    async def handle_acceptteamrequest(self, websocket, path, data):
        global cur, conn
        try:
            teamno = data[1]['teamno']
            teamname = data[1]['teamName']
            addid = data[1]['addid']
            isexcept = data[1]['isexcept']

            if isexcept:
                sql = 'update teammem set isaccept = true where teamNo = %s and teamName = %s and UserID = %s;'
                val = (teamno, teamname, addid)
                cur.execute(sql, val)
                conn.commit()

                sql1 = 'select UserID from teammem where teamNo = %s and isaccept = true;'
                val1 = (teamno,)
                cur.execute(sql1, val1)
                rows = cur.fetchall()

                if rows:
                    for row in rows:
                        team_id = row[0]
                        for client in self.isloginclient:
                            if client['id'] == team_id:
                                websocket1 = client['socket']

                                response = json.dumps({
                                    "command": 'UpdateTeamSignal',
                                    "result": "True"})
                                await websocket1.send(response + '@')
            else:
                sql = 'delete from teammem where teamNo = %s and teamName = %s and UserID = %s;'
                val = (teamno, teamname, addid)
                cur.execute(sql, val)
                conn.commit()

                response = json.dumps({
                    "result": "False"
                })
                new_response = response + '@'
                await websocket.send(new_response)
        except websockets.exceptions.ConnectionClosedError as e:
            logger.warning("WebSocket connection closed 'AcceptTeamRequest': %s", e)
        except SocketError as e:
            logger.warning("Socket error occurred 'AcceptTeamRequest': %s", e)
        except json.JSONDecodeError as e:
            logger.warning("JSON parsing error 'AcceptTeamRequest': %s", e)
        except pymysql.MySQLError as e:
            logger.warning("Database operation failed 'AcceptTeamRequest': %s", e)
            if websocket.open:
                await send_error(websocket, "False")
            else:
                logger.warning("WebSocket connection already closed 'AcceptTeamRequest'.")
        except Exception as e:
            logger.warning("An unexpected error occurred 'AcceptTeamRequest': %s", e)
            if websocket.open:
                await send_error(websocket, "False")
            else:
                logger.warning("WebSocket connection already closed 'AcceptTeamRequest'.")

    async def handle_getmyteaminfo(self, websocket, path, data):
        global cur, conn
        try:
            id = data[1]['id']

            sql = 'select teamNo, teamName from teammem where UserID = %s and isaccept = true;'
            val = (id,)
            cur.execute(sql, val)

            rows = cur.fetchall()

            team_infors = []

            if rows:
                for row in rows:
                    teamno = row[0]
                    teamname = row[1]

                    sql = 'select tm.UserID, m.UsName from teammem tm join member m on m.UserID = tm.UserID where tm.teamNo = %s and tm.teamName = %s and isaccept = true;'
                    val = (teamno, teamname)

                    cur.execute(sql, val)
                    mem_rows = cur.fetchall()

                    teaminfo = {
                        "teamNo": teamno,
                        "teamName": teamname,
                        "teammems": mem_rows
                    }

                    team_infors.append(teaminfo)

                #response = json.dumps(team_infors)
                real_response = {"teams": team_infors}
                new_real_response = json.dumps(real_response)

                new_response = new_real_response + '@'

                await websocket.send(new_response)
            else:
                response = json.dumps({
                    "result": "False"
                })
                new_response = response + '@'
                await websocket.send(new_response)
        except websockets.exceptions.ConnectionClosedError as e:
            logger.warning("WebSocket connection closed 'GetMyTeamInfo': %s", e)
        except SocketError as e:
            logger.warning("Socket error occurred 'GetMyTeamInfo': %s", e)
        except json.JSONDecodeError as e:
            logger.warning("JSON parsing error 'GetMyTeamInfo': %s", e)
        except pymysql.MySQLError as e:
            logger.warning("Database operation failed 'GetMyTeamInfo': %s", e)
            if websocket.open:
                await send_error(websocket, "False")
            else:
                logger.warning("WebSocket connection already closed 'GetMyTeamInfo'.")
        except Exception as e:
            logger.warning("An unexpected error occurred 'GetMyTeamInfo': %s", e)
            if websocket.open:
                await send_error(websocket, "False")
            else:
                logger.warning("WebSocket connection already closed 'GetMyTeamInfo'.")

    async def handle_deleteteam(self, websocket, path, data):
        global cur, conn
        try:
            team_no = data[1]['team_no']
            id = data[1]['id']

            sql = 'select count(*) from teammem where teamNo = %s;'
            val = (team_no,)

            cur.execute(sql, val)
            row = cur.fetchall()

            if row:
                if row[0][0] == 1:
                    sql = 'delete from teammem where teamNo = %s and UserID = %s;'
                    val = (team_no, id)

                    cur.execute(sql, val)
                    conn.commit()

                    sql = 'delete from Images where teamNo = %s;'
                    val = (team_no,)

                    cur.execute(sql, val)
                    conn.commit()

                    sql = 'delete from team where teamNo = %s;'
                    val = (team_no,)

                    cur.execute(sql, val)
                    conn.commit()

                    # 전송할 데이터 준비
                    data = {
                        'create_room': 'False',
                        'photo_analyze': 'False',
                        'delete_room': 'True',
                        'room_index': team_no,
                        'member_names': '',
                        'photos': ''
                    }

                    real_received_data = await self.manage_connection(self.serverhost, self.serverport, data)
                    if real_received_data is False:
                        await send_error(websocket, 'False')
                    print("모델 서버 응답:", real_received_data)

                    response = json.dumps({
                        "result": "True"
                    })
                    new_response = response + '@'
                    await websocket.send(new_response)
                else:
                    sql = 'delete from teammem where teamNo = %s and UserID = %s;'
                    val = (team_no, id)

                    cur.execute(sql, val)
                    conn.commit()
                    response = json.dumps({
                        "result": "True"
                    })
                    new_response = response + '@'
                    await websocket.send(new_response)

                    sql1 = 'select UserID from teammem where teamNo = %s and isaccept = true;'
                    val1 = (team_no,)
                    cur.execute(sql1, val1)
                    rows = cur.fetchall()

                    if rows:
                        for row in rows:
                            team_id = row[0]
                            for client in self.isloginclient:
                                if client['id'] == team_id:
                                    websocket1 = client['socket']

                                    response = json.dumps({
                                        "command": 'UpdateTeamSignal',
                                        "result": "True"})
                                    await websocket1.send(response + '@')
            else:
                response = json.dumps({
                    "result": "False"
                })
                new_response = response + '@'
                await websocket.send(new_response)
        except websockets.exceptions.ConnectionClosedError as e:
            logger.warning("WebSocket connection closed 'DeleteTeam': %s", e)
        except SocketError as e:
            logger.warning("Socket error occurred 'DeleteTeam': %s", e)
        except json.JSONDecodeError as e:
            logger.warning("JSON parsing error 'DeleteTeam': %s", e)
        except pymysql.MySQLError as e:
            logger.warning("Database operation failed 'DeleteTeam': %s", e)
            if websocket.open:
                await send_error(websocket, "False")
            else:
                logger.warning("WebSocket connection already closed 'DeleteTeam'.")
        except Exception as e:
            logger.warning("An unexpected error occurred 'DeleteTeam': %s", e)
            if websocket.open:
                await send_error(websocket, "False")
            else:
                logger.warning("WebSocket connection already closed 'DeleteTeam'.")

    # **********************************************************************

    # **********************************************************************
    # 이미지 관련 기능
    # **********************************************************************

    # **********************************************************************

    # 모델서버 관련기능
    async def handle_travelstart(self, websocket, path, data):
        global cur, conn
        try:
            teamno = data[1]['teamNo']

            sql = 'select tm.UserID, m.UsName from teammem tm join member m on m.UserID = tm.UserID where tm.teamNo = %s and isaccept = true;'
            val = (teamno,)

            cur.execute(sql, val)
            rows = cur.fetchall()

            if rows:
                names = []
                imgs = []

                for row in rows:
                    id = row[0]
                    name = row[1]

                    sql = 'select UsFace from memfaceimg where UserID = %s;'
                    val = (id,)

                    cur.execute(sql, val)
                    row1 = cur.fetchall()
                    if row1:
                        user_face = row1[0]

                        face_string = user_face[0]

                        parts = face_string.split('$')
                        if len(parts) > 1:
                            img1, img2, img3, img4, img5, _ = parts

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

                            imgs.append(image1)
                            imgs.append(image2)
                            imgs.append(image3)
                            imgs.append(image4)
                            imgs.append(image5)

                            names.append(name)
                            names.append(name)
                            names.append(name)
                            names.append(name)
                            names.append(name)
                        else:
                            await send_error(websocket, 'False')
                            return

                jpg_images = [encode_image_to_jpg(img) for img in imgs]

                # 전송할 데이터 준비
                data = {
                    'create_room': 'True',
                    'photo_analyze': 'False',
                    'delete_room': 'False',
                    'room_index': teamno,
                    'member_names': names,
                    'photos': jpg_images
                }

                real_received_data = await self.manage_connection(self.serverhost, self.serverport, data)
                if real_received_data is False:
                    await send_error(websocket, 'False')
                print("모델 서버 응답:", real_received_data)
                response = json.dumps({
                    "result": "True"
                })
                new_response = response + '@'
                await websocket.send(new_response)
            else:
                await send_error(websocket, 'False')
                return
        except websockets.exceptions.ConnectionClosedError as e:
            logger.warning("WebSocket connection closed 'TravelStart': %s", e)
        except SocketError as e:
            logger.warning("Socket error occurred 'TravelStart': %s", e)
        except pymysql.MySQLError as e:
            logger.warning("Database operation failed 'TravelStart': %s", e)
        except Exception as e:
            logger.warning("An unexpected error occurred 'TravelStart': %s", e)

    async def send_data_to_model(self, reader, writer, data_to_send):
        try:
            # 데이터를 pickle로 직렬화하여 전송
            serialized_data = pickle.dumps(data_to_send)
            data_size = len(serialized_data)
            data_size_bytes = data_size.to_bytes(4, byteorder='big')

            writer.write(data_size_bytes + serialized_data)
            await writer.drain()
            logger.info("Data sent to model server")

            chunk = await reader.read()

            real_received_data = pickle.loads(chunk)
            logger.info("Data received from model server")
            logger.info(real_received_data)

            # 추가적인 처리 로직
            return real_received_data

        except Exception as e:
            logger.error(f"An error occurred during data transfer: {e}")
            return False

    async def manage_connection(self, host, port, data_to_send):
        while True:
            reader, writer = await connect_to_server(host, port)
            success = await self.send_data_to_model(reader, writer, data_to_send)
            if not success:
                writer.close()
                await writer.wait_closed()
                logger.info("Reconnecting due to a data transfer failure...")
                return False
            else:
                return success

    # ************************************************************************
    # 서버 => 클라이언트 백그라운드
    # *************************************************************************

    # 팀초대 보내기
    async def background_addteammember(self):
        global cur, conn
        try:
            sql = "select * from teammem where isaccept = false;"

            cur.execute(sql)
            rows = cur.fetchall()

            for row in rows:
                teamno = row[0]
                teamname = row[1]
                userid = row[2]
                for client in self.isloginclient:
                    if client['id'] == userid:
                        websocket1 = client['socket']
                        response = json.dumps({
                            "command": "JoinTeamRequest",
                            "teamno": teamno,
                            "teamName": teamname,
                            "addid": userid
                        })
                        new_response = response + '@'
                        await websocket1.send(new_response)
        except websockets.exceptions.ConnectionClosedError as e:
            logger.warning("WebSocket connection closed 'Back_AddTeamMember': %s", e)
        except SocketError as e:
            logger.warning("Socket error occurred 'Back_AddTeamMember': %s", e)
        except json.JSONDecodeError as e:
            logger.warning("JSON parsing error 'Back_AddTeamMember': %s", e)
        except pymysql.MySQLError as e:
            logger.warning("Database operation failed 'Back_AddTeamMember': %s", e)
        except Exception as e:
            logger.warning("An unexpected error occurred 'Back_AddTeamMember': %s", e)

    # *************************************************************************

    # ************************************************************************
    # 실시간 기능!!
    # *************************************************************************

    async def handle_updatelocation(self, websocket, path, data):
        global cur, conn

        try:
            logger.info("UpdateInfo 시작 테스트")
            id = data[1]['id']
            name = data[1]['name']
            latitude = data[1]['latitude']
            longitude = data[1]['longitude']
            teamno = data[1]['teamNo']

            count = 0
            print("위치 갱신 호출받은 멤버: ", count)

            if teamno is None:
                response = json.dumps({
                    "result": "False"
                })
                new_response = response + '@'
                await websocket.send(new_response)
                return

            sql = 'select tm.UserID from teammem tm join member m on m.UserID = tm.UserID where teamNo = %s and isaccept = true;'
            val = (teamno,)

            cur.execute(sql, val)
            rows = cur.fetchall()

            if rows:
                for row in rows:
                    teammem_id = row[0]
                    for client in self.isloginclient:
                        if client['id'] == teammem_id:
                            websocket1 = client['socket']
                            response = json.dumps({
                                "command": 'TeamLocationUpdate',
                                "id": id,
                                'teamNo': teamno,
                                "userName": name,
                                "latitude": latitude,
                                "longitude": longitude
                            })

                            await websocket1.send(response + '@')
                            count += 1
                            print("위치 갱신 호출받은 멤버: ", count)
            else:
                response = json.dumps({
                    "result": "False"
                })
                new_response = response + '@'
                await websocket.send(new_response)
        except websockets.exceptions.ConnectionClosedError as e:
            logger.warning("WebSocket connection closed 'UpdateLocation': %s", e)
        except SocketError as e:
            logger.warning("Socket error occurred 'UpdateLocation': %s", e)
        except json.JSONDecodeError as e:
            logger.warning("JSON parsing error 'UpdateLocation': %s", e)
        except pymysql.MySQLError as e:
            logger.warning("Database operation failed 'UpdateLocation': %s", e)
            if websocket.open:
                await send_error(websocket, "False")
            else:
                logger.warning("WebSocket connection already closed 'UpdateLocation'.")
        except Exception as e:
            logger.warning("An unexpected error occurred 'UpdateLocation': %s", e)
            if websocket.open:
                await send_error(websocket, "False")
            else:
                logger.warning("WebSocket connection already closed 'UpdateLocation'.")
