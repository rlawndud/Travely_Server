import asyncio

from newwebsocketserver import WebsocketServer

#10.101.152.35
#220.90.180.89
#192.168.0.45

server = WebsocketServer(hostadr="0.0.0.0", port=8080)
asyncio.run(server.run())