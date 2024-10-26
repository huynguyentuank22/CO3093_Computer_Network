import threading
import socket, select
# from protocol import Encode

FORMAT = 'utf-8'
SIZE = 1024

hostname = socket.gethostname()
local_IP = socket.gethostbyname(hostname)

class PeerCentral():
    def __init__(self):
        self.HOST = local_IP
        self.PORT_TCP = 3000
        self.central_client_socket = None
        self.username = None
        self.password = None
        self.ip_addr = None
        self.port = None
        # self.Encoder = None
        
    def run(self):
        self.central_client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.central_client_socket.connect((self.HOST, self.PORT_TCP))
        except:
            print('Error connecting to central server')
        
    def rergisterClient(self, username, passwd):
        self.central_client_socket.send('register'.encode(FORMAT))
        # flag = self.central_client_socket.recv(SIZE).decode(FORMAT)
        # if flag == 'OK':
        self.username = username
        self.password = passwd

        data = str(self.username) + ',' + str(self.password)

        self.central_client_socket.send(data.encode(FORMAT))
        status = self.central_client_socket.recv(SIZE).decode(FORMAT)
        print(status)
    
    def loginClient(self, username, passwd):
        hostname = socket.gethostname()
        ip_addr = socket.gethostbyname_ex(hostname)[2][-1]

        self.central_client_socket.send('login'.encode(FORMAT))
        # flag = self.central_client_socket.recv(SIZE).decode(FORMAT)
        # if flag == 'OK':
        self.username = username
        self.password = passwd
        self.ip_addr = ip_addr
        self.port = 80
        # self.Encoder = Encode(self.ip_addr, self.port)
        
        print(self.ip_addr)
        data = f"{self.username},{self.password},{self.ip_addr},{self.port}"

        self.central_client_socket.send(data.encode(FORMAT))
        status = self.central_client_socket.recv(SIZE).decode(FORMAT)
        print(status)

    def exit(self):
        self.central_client_socket.close()


class PeerServer(threading.Thread):
    ClientList = [] # List of online client
    peerIP = None
    peerPort = None
    def __init__(self, peerName, peerIP):
        threading.Thread.__init__(self)
        self.ClientList = []
        self.peerName = peerName
        self.peerIP = peerIP
        self.listenPort = 80

        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.peerIP, int(self.listenPort)))

    def run(self):
        self.server.listen(100)
        print('Start listening on port', self.listenPort)
        inputs = [self.server]

        while 1:
            try:
                read_to_read, _, _ = select.select(inputs, [], [], 0)
                for s in read_to_read:
                    if s == self.server:
                        conn, addr = s.accept()
                        conn.send('OK'.encode(FORMAT))

                        self.ClientList.append(conn)
                    else:
                        print('Hihi')
            except Exception as e:
                print(e)
                

class PeerClient(threading.Thread):
    def __init__(self, name, conn, ip, port, opponent_name):
        threading.Thread.__init__(self)
        self.name = name
        self.conn = conn
        self.ip = ip
        self.port = port
        self.opponent_name = opponent_name
        # self.Encoder = Encode(ip, port)
        self.running = 1

    def run(self):
        return
        
if __name__ == '__main__':
    central = PeerCentral()
    central.run()
    while 1:
        option = int(input('Enter option: '))
        if option == 1:
            account = input('Enter your account: ')
            user, passwd = account.split(',')
            central.rergisterClient(user, passwd)
        elif option == 2:
            user = input('Enter user: ')
            passwd = input('Enter password: ')
            print(user, passwd)
            central.loginClient(user, passwd)
        else:
            central.exit()
            break