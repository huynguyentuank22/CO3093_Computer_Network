import threading
import socket

hostname = socket.gethostname()
local_IP = socket.gethostbyname(hostname)

class PeerCentral():
    def __init__(self):
        self.HOST = local_IP
        self.PORT_TCP = 3000
        self.central_client_socket = None

    def run(self):
        self.central_client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.central_client_socket.connect((self.HOST, self.PORT_TCP))
            self.central_client_socket.send('con cu'.encode())
            self.central_client_socket.close()
        except:
            print('Error connecting to central server')

if __name__ == '__main__':
    client = PeerCentral()
    client.run()