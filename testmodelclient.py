import socket
import pickle
import os
import pymysql
import time
import base64
import numpy as np
import cv2
import json

# DB사용을 위한 전역변수
conn = None
cur = None


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

def send_images_to_server(server_host, server_port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((server_host, server_port))
        teamno = 10

        sql = 'select tm.UserID, m.UsName from teammem tm join member m on m.UserID = tm.UserID where tm.teamNo = %s and isaccept = true;'
        val = (teamno,)

        cur.execute(sql, val)
        rows = cur.fetchall()

        #responses = {}

        if rows:
            for row in rows:
                id = row[0]
                name = row[1]

                sql = 'select UsFace from memfaceimg where UserID = %s;'
                val = (id,)

                cur.execute(sql, val)
                row = cur.fetchall()
                user_face = row[0]

                face_string = user_face[0]

                datas = []

                parts = face_string.split('$')
                if len(parts) > 1:
                    print(len(parts))
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

                    imgs = [image1, image2, image3, image4, image5]

                    jpg_images = [encode_image_to_jpg(img) for img in imgs]

                    names = []

                    datas.append((name, image1))
                    datas.append((name, image2))
                    datas.append((name, image3))
                    datas.append((name, image4))
                    datas.append((name, image5))

                    names.append(name)
                    names.append(name)
                    names.append(name)
                    names.append(name)
                    names.append(name)

                    # 전송할 데이터 준비
                    data = {
                        'create_room': 'False',
                        'photo_analyze': 'True',
                        'room_index': 1,
                        'member_names': '',
                        'photo': jpg_images[1]
                    }

                    # 데이터를 pickle로 직렬화하여 전송
                    serialized_data = pickle.dumps(data)
                    data_size = len(serialized_data)

                    data_size_bytes = data_size.to_bytes(4, byteorder='big')

                    sock.sendall(data_size_bytes + serialized_data)

        # 서버에서의 응답 수신
        received_data = sock.recv(8192)

        real_received_data = pickle.loads(received_data)

        face = real_received_data['face_predictions']
        #object = real_received_data['objects_predictions']
        background = real_received_data['background_predictions']

        print("모델 서버 응답:", face)
        #print("모델 서버 응답:", object)
        print("모델 서버 응답:", background)


if __name__ == "__main__":

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

    send_images_to_server('220.90.180.88', 5001)
