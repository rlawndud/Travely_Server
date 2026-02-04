import asyncio

from websocketserver import WebsocketServer

server = WebsocketServer(hostadr="0.0.0.0", port=8080)
asyncio.run(server.run())
