from parameter import *
from helper import *

class Tracker:
    def __init__(self, db_path='tracker.db'):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.lock = threading.Lock()
        self.tracker_socket = None
        self.init_database()
        self.files_info: Dict[str, Dict] = {}  # info_hash -> {filename, size, peers}
        self.logger = setup_logger('tracker')

    def run(self, HOST='localhost', PORT=5050):
        self.tracker_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tracker_socket.bind((HOST, PORT))
        self.tracker_socket.listen(100)
        self.logger.info(f"Tracker is running on {HOST}:{PORT}")
        
        while True:
            try:
                client_socket, addr = self.tracker_socket.accept()
                self.logger.info(f"New connection from {addr}")
                client_thread = threading.Thread(
                    target=self.handle_peer, args=(client_socket, addr))
                client_thread.start()
            except Exception as e:
                self.logger.error(f"Error accepting connection: {e}")
            except KeyboardInterrupt:
                self.logger.info("Tracker shutting down.")
                break

        self.tracker_socket.close()

    def handle_peer(self, client_socket, addr):
        while True:
            try:
                data = recv_msg(client_socket)
                if data is None:
                    self.logger.info(f"Client {addr} disconnected")
                    break
                
                self.logger.info(f"Received data from {addr}: {data['type']}")
                
                if data['type'] == REGISTER:
                    self.register_service(client_socket, data)
                elif data['type'] == LOGIN:
                    self.login_service(client_socket, data)
                elif data['type'] == PUBLISH:
                    self.publish_service(client_socket, data)
                elif data['type'] == FETCH:
                    self.fetch_service(client_socket, data)
                elif data['type'] == GET_FILES:
                    self.get_files_service(client_socket, data)
                elif data['type'] == UPDATE_BITFIELD:
                    self.update_bitfield_service(client_socket, data)
                elif data['type'] == LOGOUT:
                    self.logout_service(client_socket, data)
                    break
            except Exception as e:
                self.logger.error(f"Error handling peer {addr}: {e}")
                break

        client_socket.close()

    def register_service(self, client_socket, data):
        user, passwd, ip, port = data['username'], data['password'], data['ip'], data['port']
        try:
            with self.lock:
                self.cursor.execute("SELECT * FROM users WHERE username = ?", (user,))
                if self.cursor.fetchone():
                    send_msg(client_socket, {'type': REGISTER_FAIL, 'message': 'Username already exists'})
                else:
                    self.cursor.execute("INSERT INTO users (username, password, ip, port, status) VALUES (?, ?, ?, ?, 0)",
                                        (user, passwd, ip, port))
                    self.conn.commit()
                    peer_id = self.cursor.lastrowid
                    send_msg(client_socket, {'type': REGISTER_SUCCESS, 'peer_id': peer_id})
        except Exception as e:
            self.logger.error(f"Error in register_service: {e}")
            send_msg(client_socket, {'type': REGISTER_FAIL, 'message': 'Internal server error'})

    def login_service(self, client_socket, data):
        user, passwd, ip, port = data['username'], data['password'], data['ip'], data['port']
        try:
            with self.lock:
                self.cursor.execute("SELECT id, password FROM users WHERE username = ?", (user,))
                result = self.cursor.fetchone()
                if result and result[1] == passwd:
                    peer_id = result[0]
                    self.cursor.execute("UPDATE users SET ip = ?, port = ?, status = 1 WHERE id = ?", (ip, port, peer_id))
                    self.conn.commit()
                    send_msg(client_socket, {'type': LOGIN_SUCCESS, 'peer_id': peer_id})
                else:
                    send_msg(client_socket, {'type': LOGIN_FAIL, 'message': 'Invalid credentials'})
        except Exception as e:
            self.logger.error(f"Error in login_service: {e}")
            send_msg(client_socket, {'type': LOGIN_FAIL, 'message': 'Internal server error'})

    def publish_service(self, client_socket, data):
        info_hash, peer_id = data['info_hash'], data['peer_id']
        filename, filesize = data['filename'], data['filesize']
        bitfield = data['bitfield']
        
        with self.lock:
            if info_hash not in self.files_info:
                self.files_info[info_hash] = {
                    'filename': filename,
                    'size': filesize,
                    'peers': {}
                }
            self.files_info[info_hash]['peers'][peer_id] = BitField.from_bytes(bitfield, calculate_num_pieces(filesize))
        
        send_msg(client_socket, {'type': PUBLISH_SUCCESS})

    def fetch_service(self, client_socket, data):
        info_hash, peer_id = data['info_hash'], data['peer_id']
        if info_hash in self.files_info:
            peers = [
                (pid, self.get_peer_info(pid))
                for pid, bf in self.files_info[info_hash]['peers'].items()
                if pid != peer_id and self.is_peer_online(pid)
            ]
            send_msg(client_socket, {'type': FETCH_SUCCESS, 'peers': peers})
        else:
            send_msg(client_socket, {'type': FETCH_SUCCESS, 'peers': []})

    def get_files_service(self, client_socket, data):
        files = [
            {
                'info_hash': info_hash,
                'filename': file_info['filename'],
                'size': file_info['size'],
                'num_peers': len(file_info['peers'])
            }
            for info_hash, file_info in self.files_info.items()
            if any(self.is_peer_online(pid) for pid in file_info['peers'])
        ]
        send_msg(client_socket, {'type': GET_FILES_SUCCESS, 'files': files})

    def update_bitfield_service(self, client_socket, data):
        info_hash, peer_id, bitfield = data['info_hash'], data['peer_id'], data['bitfield']
        with self.lock:
            if info_hash in self.files_info and peer_id in self.files_info[info_hash]['peers']:
                self.files_info[info_hash]['peers'][peer_id] = BitField.from_bytes(bitfield, len(bitfield) * 8)

    def logout_service(self, client_socket, data):
        peer_id = data['peer_id']
        with self.lock:
            self.cursor.execute("UPDATE users SET status = 0 WHERE id = ?", (peer_id,))
            self.conn.commit()

    def init_database(self):
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

    def get_peer_info(self, peer_id):
        self.cursor.execute("SELECT ip, port FROM users WHERE id = ? AND status = 1", (peer_id,))
        return self.cursor.fetchone()

    def is_peer_online(self, peer_id):
        self.cursor.execute("SELECT status FROM users WHERE id = ?", (peer_id,))
        result = self.cursor.fetchone()
        return result and result[0] == 1

if __name__ == '__main__':
    tracker = Tracker()
    tracker.run()