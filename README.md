## 실행 방법
### Main Server
1. Travely_Server 파일을 PyCharm으로 실행
2. websocketserver 파일에서 모델서버와의 연결을 위해 serverhost와 serverport를 AI서버의 주소에 맞게 값을 변경
```python
# 모델통신
self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
self.serverhost = '220.90.180.88'
self.serverport = 5001
self.reader = None
self.writer = None
self.lock = asyncio.Lock()
```
3. MYSQL과 연동을 위해 websocketserver파일에서 유저명, 비밀번호, 참조할 DB의 이름을 설정
```python
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
```
4. 서버 실행을 위해 server파일에서 ip주소와 port번호를 서버컴퓨터의 환경에 맞게 값을 변경. 그 후 server 파일 실행
```python
server = WebsocketServer(hostadr="0.0.0.0", port=8080)
```

## 전체 프로젝트 레포지토리
https://github.com/rlawndud/Travely.git
