import socket, select
import sqlite3
from threading import Thread
import time
import traceback

hostname = socket.gethostname()
local_IP = socket.gethostbyname(hostname)

print('Hostname:', hostname) # TABLET-GA927AEQ
print('Local IP:', local_IP) # 192.168.1.163

HOST = local_IP

def sendMsg(conn, msg):
    try:
        conn.send(msg.encode())
    except:
        conn.close()
    
class TCPserver(Thread):
    SOCKET_LIST = []

    def __init__(self):
        Thread.__init__(self)
        self.HOST = HOST
        self.PORT = 3000
        self.server_socket = None
        self.running = 1

    def run(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Cho phép tái sử dụng địa chỉ IP và port
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.server_socket.bind((self.HOST, self.PORT))
        self.server_socket.listen(100) # so luong toi da ket noi co the co trong queue

        self.SOCKET_LIST = [self.server_socket]
        print('TCP server started on port', self.PORT)

        while 1:
            try:
                ready_to_read, _, _ = select.select(self.SOCKET_LIST, [], [], 0)
            except:
                self.SOCKET_LIST = filter(lambda item: item.fileno > 0, self.SOCKET_LIST)
                continue
            for sock in ready_to_read:
                if sock == self.server_socket:
                    self.conn, self.addr = self.server_socket.accept()
                    self.SOCKET_LIST.append(self.conn)
                    print('Client (%s, %s) connected' % self.addr)
                    print(self.conn.recv(1024).decode())
                    central = CentralServer(self.conn, self.addr) 
                    central.start()
    
    def kill(self):
        self.running = 0
        # self.server_socket.close()


# Central Server
class CentralServer(Thread):
    def __init__ (self, conn, addr) -> None:
        Thread.__init__(self)
        self.ClientList = [] # list of online client
        self.conn = conn
        self.addr = addr
        self.running = 1

    # type of request from peers
    def run(self):
        self.initDatabaseConn()
        print('Server start listening on', self.addr)
        while self.running:
            try:
                request =  self.conn.recv(1024).decode()
                print('Client request to Server:', request)
                # Registration service
                if request == 'register':
                    print('register service') 
                    self.registerService()
                # Join service - update user status and provide new IP-Port
                elif request == 'login':
                    print('login service')
                    self.loginService()
                # Serch service - find a person to chat with
                elif request == 'search':
                    print('search service')
                    self.searchService()
                else:
                    print('Invalid request')
            except:
                print(f'Client {self.addr} is not online or having connection errors!')
                break

    # implement service
    def registerService(self):
        user, passwd = self.conn.recv(1024).decode().split(',')
        print(user, passwd)
        record = self.getAccountByUsername(user)
        if record != []:
            sendMsg(self.conn, 'Account has been used')
        else:
            try:
                self.insertUser(user, passwd)
                sendMsg(self.conn, 'Account created successfully')
            except:
                sendMsg(self.conn, 'Error. Try again...')
                
    def loginService(self):
        user, passwd, ip, port = self.conn.recv(1024).decode().split(',')
        record = self.getAccountByUsernameAndPassword(user, passwd)
        if record == []:
            sendMsg(self.conn, 'The account or password does not exist')
        else:
            try:
                self.updateUser(user, passwd, ip, port)
                sendMsg(self.conn, 'Connected successfully')
                sendMsg(self.conn, user)
            except Exception as e:
                sendMsg(self.conn, 'Query erorr. Retrying...')
                # traceback.print_exc()
    
    def searchService(self):
        user = self.conn.recv(1024).decode()
        record = self.getAddressByUsername(user)
        if not record:
            sendMsg(self.conn, 'The account is either offline or does not exist')
        else:
            data = str(record[0][0] + ',' + record[0][1])
            sendMsg(self.conn, data)

    def getOnlineUsersService(self):
        records = self.getAccountsOnline()
        sendMsg(self.conn, str([record[1] for record in records])) # get all user online
    
    # database method
    def initDatabaseConn(self):
        print('Init database')
        self.connector = sqlite3.connect('accounts.db')
        self.cursor = self.connector.cursor()
        # self.cursor.execute('''CREATE TABLE users
        #                     (username TEXT NOT NULL UNIQUE,
        #                     password TEXT NOT NULL,
        #                     ip TEXT,
        #                     port INTEGER,
        #                     status INTEGER)''')
        # self.connector.commit()

    def closeDatabaseConn(self):
        self.cursor.close()

    def getAccountByUsername(self, user):
        self.cursor.execute(f"""SELECT * FROM users WHERE username = {user}""")
        records = self.cursor.fetchall()
        return records
    
    def getAccountByUsernameAndPassword(self, user, passwd):
        self.cursor.execute(f"""SELECT * FROM users WHERE username = {user} AND password = {passwd}""")
        records = self.cursor.fetchall()
        return records
    
    def getAccountsOnline(self):
        self.cursor.execute("SELECT * FROM users WHERE status = 1")
        records = self.cursor.fetchall()
        return records
    
    def getAddressByUsername(self, user):
        self.cursor.execute(f"""SELECT ip, port FROM users WHERE username = {user} AND status = 1""")
        records = self.cursor.fetchall()
        return records
    
    def insertUser(self, user, passwd):
        self.cursor.execute(f"""INSERT INTO users (username, password, status) VALUES ({user}, {passwd}, 0)""")
        self.connector.commit()

    def updateUser(self, user, ip, port):
        self.cursor.execute(f"""UPDATE user SET status = 1, ip = {ip}, port = {port} WHERE username = {user}""")
        self.connector.commit()

if __name__ == '__main__':
    tcpThread = TCPserver()
    tcpThread.start()

