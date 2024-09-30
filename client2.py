import socket

hostname = socket.gethostname()
local_IP = socket.gethostbyname(hostname)

server = (local_IP, 3000)
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect(server)

sentence = 'tui la client 2'

client_socket.send(sentence.encode())
