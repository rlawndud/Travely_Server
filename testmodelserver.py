import asyncio
import json


class ClientConnectionHandler:
    """서버에 대한 클라이언트 연결을 나타내는 클래스."""

    def __init__(self, reader, writer):
        """
        클라이언트 연결 핸들러를 초기화합니다.

        매개변수:
        reader: 클라이언트로부터 데이터를 읽기 위한 스트림
        writer: 클라이언트로 데이터를 쓰기 위한 스트림
        """

        # reader 스트림을 인스턴스 변수로 저장합니다.
        self.reader = reader

        # writer 스트림을 인스턴스 변수로 저장합니다.
        self.writer = writer

        # 클라이언트의 주소 정보를 저장합니다.
        self.addr = writer.get_extra_info('peername')

        #이미지를 한번에 받을 수 없어서 나눠져서 전송된 데이터들을 버퍼에 저장
        self.buffer = ""

    async def handle(self):
        """클라이언트 연결을 처리합니다."""

        # 클라이언트가 연결되었음을 출력합니다.
        print(f"클라이언트 연결됨: {self.addr}")

        try:
            # 클라이언트로부터 메시지를 읽는 루프를 시작합니다. read_loop 함수가 종료되기를 대기하게 됩니다. 이때 제어권을 넘기고 메시지가 수신되면 재개합니다.
            await self.read_loop()
        except Exception as e:

            # 예외가 발생하면 예외 정보를 출력합니다.
            print(f"{self.addr}에서 처리되지 않은 예외 발생: {e}")
        finally:

            # 연결이 종료되었음을 출력합니다.
            print(f"{self.addr}와의 연결이 종료되었습니다.")

    async def read_loop(self):
        """클라이언트로부터 메시지를 읽고 'quit' 메시지를 처리합니다."""
        while True:  # 무한 루프를 시작합니다.
            try:

                # 클라이언트로부터 최대 100바이트를 읽습니다. 데이터를 수신할때 까지 대기합니다.
                # 이벤트 루프가 데이터 수신을 감지하면 실행 재개 되도록 합니다.
                data = await self.reader.read()

                # data가 빈 바이트열이라면 연결이 종료된 것으로 보고 무한루프를 종료합니다.
                #
                # StreamReader.read 메서드는 다음과 같은 상황에서 빈 바이트열을 반환할 수 있습니다:
                # 서버가 연결을 닫은 경우: 서버가 연결을 닫으면 클라이언트에서 더 이상 읽을 데이터가 없게 됩니다.
                # 네트워크 오류가 발생한 경우: 네트워크 오류로 인해 연결이 끊길 수 있습니다.
                if not data:
                    break

                    # 수신된 데이터를 디코딩하고 양쪽 공백을 제거합니다.
                message = data.decode().strip()

                self.buffer += message
                if "@" in self.buffer:
                    data = json.loads(self.buffer)
                    self.buffer = ""
                    if data[0]['command'] == 'teammemsface': # 얼굴이미지 학습?

                        id = data[1]['id']
                        name = data[1]['name']
                        img_data = data[1]['img_data']



                # 수신된 메시지가 'quit'을 포함하는지 확인합니다.
                if "quit" in message.lower():

                    # 클라이언트가 'quit'을 보냈음을 출력합니다.
                    print(f"클라이언트 {self.addr}가 'quit'을 보냈습니다. 연결을 종료합니다.")

                    # writer 스트림을 닫습니다.
                    self.writer.close()

                    # writer 스트림이 완전히 닫힐 때까지 대기합니다.
                    await self.writer.wait_closed()
                    break  # 루프를 종료합니다.
                else:
                    # 수신된 메시지를 클라이언트에게 다시 보냅니다 (에코).
                    self.writer.write(data)  # 수신된 데이터를 다시 전송합니다.
                    await self.writer.drain()  # 버퍼가 비워질 때까지 대기합니다.
            except ConnectionResetError:
                print(f"{self.addr}와의 연결이 끊어졌습니다")  # 연결이 끊어졌음을 출력합니다.
                break  # 루프를 종료합니다.


async def client_connected_cb(reader, writer):
    """클라이언트가 연결될 때 호출되는 콜백 함수."""

    # 새로운 클라이언트가 서버에 접속할 때마다 해당 클라이언트를 처리할 새로운 핸들러 객체를 생성합니다.
    handler = ClientConnectionHandler(reader, writer)

    # 클라이언트 연결을 처리합니다.
    await handler.handle()


class Server:
    """비동기 서버를 나타내는 클래스."""

    # 호스트를 '127.0.0.1'로 설정하여 IPv4만 사용하도록 합니다.
    def __init__(self, host: str = '127.0.0.1', port: int = 8888):
        """
        서버를 초기화합니다.

        매개변수:
        host (str): 서버가 바인딩할 호스트 주소.
        port (int): 서버가 바인딩할 포트 번호.
        """
        self.host = host  # 호스트 주소를 저장합니다.
        self.port = port  # 포트 번호를 저장합니다.

    async def run(self):
        """서버를 실행합니다."""
        server = await asyncio.start_server(
            client_connected_cb,  # 클라이언트가 연결될 때 호출되는 콜백 함수.
            host=self.host,  # 서버가 바인딩할 호스트 주소.
            port=self.port,  # 서버가 바인딩할 포트 번호.
        )

        # 서버가 바인딩된 주소들을 문자열로 변환합니다.
        addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)

        # 서버가 실행 중임을 출력합니다.
        print(f'서버 실행 중: {addrs}')

        # 서버가 무한히 실행되도록 합니다.
        await server.serve_forever()


if __name__ == '__main__':
    # Server 인스턴스를 생성합니다.
    server = Server()

    # server.run 함수를 실행하면서 이벤트 루프를 시작합니다.
    asyncio.run(server.run())