import socket
import time
hostname = socket.gethostname()
local_IP = socket.gethostbyname(hostname)

server = (local_IP, 3000)
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect(server)

sentence = 'tui la client 1'

try:
    # client_socket.send(sentence.encode())
    # time.sleep(3)

    flag = 'register'
    client_socket.send(flag.encode())
    
    if client_socket.recv(1024).decode() == 'OK':
        account = 'huy,huy281204'
        client_socket.send(account.encode())
        status = client_socket.recv(1024).decode()
        print(status)

except Exception as e:
    print(f"Error connecting to server: {e}")
finally:
    client_socket.close()