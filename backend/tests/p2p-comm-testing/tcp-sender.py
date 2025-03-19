import socket

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect(("192.168.1.100", 5005))

message = "Hello, TCP packet!"
client_socket.send(message.encode())

client_socket.close()
