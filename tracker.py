import socket
import threading
import sqlite3
import pickle
import traceback
from parameter import *
from helper import *

HOST_NAME = socket.gethostname()
HOST = socket.gethostbyname(HOST_NAME)
PORT = 5050


class TrackerServer:
    def __init__(self, db_path='tracker.db'):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.lock = threading.Lock()
        self.tracker_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tracker_socket.bind((HOST, PORT))
        self.tracker_socket.listen(QUEUE_SIZE)
        self.create_tables()

    def create_tables(self):
        with self.lock:
            self.cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                username TEXT UNIQUE,
                                password TEXT,
                                ip TEXT,
                                port INTEGER,
                                status INTEGER
                              )''')
            self.conn.commit()

    def handle_peer(self, client_socket, addr):
        print(f"Handling connection from {addr}")
        while True:
            try:
                print(f"Waiting for data from {addr}")
                data = recv_msg(client_socket)
                if data is None:
                    print(f"Client {addr} disconnected")
                    break
                print(f"Received {len(data)} bytes from {addr}")
                info = pickle.loads(data)
                print(f"Received message from {addr}: {info['type']}")
                if info['type'] == REGISTER:
                    self.register_service(client_socket, info)
                # ... handle other message types ...
            except Exception as e:
                print(f"Error handling peer {addr}: {e}")
                traceback.print_exc()
                break
        client_socket.close()
        print(f"Connection closed for {addr}")

    def register_service(self, client_socket, info):
        user, passwd, ip, port = info['username'], info['password'], info['ip'], info['port']
        print(f"Registering user: {user}")
        try:
            record = self.getAccountByUsername(user)
            if record:
                print(f"User {user} already exists")
                self.sendMsg(client_socket, {'type': REGISTER_FAILED, 'message': 'Account has already been used'})
            else:
                self.insertUser(user, passwd, ip, port)
                peer_id = self.getPeerId(user)
                print(f"User {user} registered successfully with peer_id {peer_id}")
                self.sendMsg(client_socket, {'type': REGISTER_SUCCESSFUL, 'message': 'Account created successfully', 'peer_id': peer_id})
        except Exception as e:
            print(f"Error in register_service: {e}")
            traceback.print_exc()
            self.sendMsg(client_socket, {'type': REGISTER_FAILED, 'message': 'Internal server error'})
            
    def login_service(self, client_socket, info):
        
        pass

    def sendMsg(self, client_socket, msg):
        try:
            send_msg(client_socket, msg)
            print(f"Sent message: {msg['type']}")
        except Exception as e:
            print(f"Error sending message: {e}")
            traceback.print_exc()

    def getPeerId(self, user):
        self.cursor.execute("SELECT id FROM users WHERE username = ?", (user,))
        return self.cursor.fetchone()[0]

    def getAccountByUsername(self, user):
        self.cursor.execute("SELECT * FROM users WHERE username = ?", (user,))
        return self.cursor.fetchone()

    def insertUser(self, user, passwd, ip, port):
        with self.lock:
            self.cursor.execute("INSERT INTO users (username, password, ip, port, status) VALUES (?, ?, ?, ?, 0)", 
                                (user, passwd, ip, port))
            self.conn.commit()

    
    def run(self):
        print(f"Tracker server is listening on {HOST}:{PORT}")
        while True:
            try:
                client_socket, addr = self.tracker_socket.accept()
                print(f"New connection from {addr}")
                client_thread = threading.Thread(target=self.handle_peer, args=(client_socket, addr))
                client_thread.start()
            except Exception as e:
                print(f"Error accepting connection: {e}")
                traceback.print_exc()


if __name__ == '__main__':
    tracker = TrackerServer()
    tracker.run()
