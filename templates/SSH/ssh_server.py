import paramiko
import socket
import threading
import os

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
        try:
            output = os.popen(command).read()
            channel.send(output)
        except Exception as e:
            channel.send(str(e))
        channel.send_exit_status(0)
        return True

def start_ssh_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', 2200))
    server.listen(100)
    print('Listening for SSH connection...')

    while True:
        client, addr = server.accept()
        print('Connection from:', addr)
        t = paramiko.Transport(client)
        t.add_server_key(host_key)
        server_handler = SSHServerHandler()
        try:
            t.start_server(server=server_handler)
        except paramiko.SSHException:
            print('SSH negotiation failed.')
            continue

        channel = t.accept(20)
        if channel is None:
            print('No channel.')
            continue

        print('Authenticated!')
        while True:
            try:
                data = channel.recv(1024)
                if not data:
                    break
                print("Received command:", data.decode())
            except Exception as e:
                print('Exception:', e)
                break

        t.close()

if __name__ == '__main__':
    start_ssh_server()
