import asyncio
import websockets
import paramiko
import threading
import socket

async def ssh_server(websocket, path):
    host_key = paramiko.RSAKey(filename='test_rsa.key')

    class SSHServerHandler(paramiko.ServerInterface):
        def __init__(self):
            self.event = threading.Event()

        def check_channel_request(self, kind, chanid):
            if kind == 'session':
                return paramiko.OPEN_SUCCEEDED
            return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

        def check_auth_password(self, username, password):
            if (username == 'test') and (password == 'password'):
                return paramiko.AUTH_SUCCESSFUL
            return paramiko.AUTH_FAILED

        def get_allowed_auths(self, username):
            return 'password'

        def check_channel_exec_request(self, channel, command):
            channel.send('You said: ' + command)
            channel.send_exit_status(0)
            return True

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', 2200))
    server.listen(100)
    print('Listening for connection...')

    client, addr = server.accept()
    print('Connection from:', addr)
    t = paramiko.Transport(client)
    t.add_server_key(host_key)
    server_handler = SSHServerHandler()
    try:
        t.start_server(server=server_handler)
    except paramiko.SSHException:
        print('SSH negotiation failed.')

    channel = t.accept(20)
    if channel is None:
        print('No channel.')
        return

    print('Authenticated!')

    while True:
        data = await websocket.recv()
        if not data:
            break
        channel.send(data)
        response = channel.recv(1024).decode()
        await websocket.send(response)

    t.close()

start_server = websockets.serve(ssh_server, "localhost", 8765)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
