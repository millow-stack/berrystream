import socket as s

server = s.socket(s.AF_BLUETOOTH, s.SOCK_STREAM, s.BTPROTO_RFCOMM);
server.bind(("00:1a:7d:da:71:13", 4));
server.listen(1);

client, addr = server.acccept();

try:
    while True:
        msg = input('> ');
        client.send(msg.encode('utf-8'));
        data = client.rec(1024);
        if not data:
            break
        print(data.decode('utf-8'));
except OSError as e:
    pass

client.close();
server.close();