from parameter import *
from helper import *
from torrent import *


class Tracker:
    def __init__(self, db_path='tracker.db'):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.lock = threading.Lock()
        self.tracker_socket = None
        self.init_database()
        # info_hash -> {filename, size, peers}
        self.files_info: Dict[str, Dict] = {}

    def run(self, HOST='localhost', PORT=5050, MAX_CONNECTIONS=100):
        self.tracker_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tracker_socket.bind((HOST, PORT))
        self.tracker_socket.listen(MAX_CONNECTIONS)
        print(f"Tracker is running on {HOST}:{PORT}")
        while True:
            try:
                client_socket, addr = self.tracker_socket.accept()
                print(f"New connection from {addr}")
                client_thread = threading.Thread(
                    target=self.handle_peer, args=(client_socket, addr))
                client_thread.start()
            except Exception as e:
                print(f"Error accepting connection: {e}")
                traceback.print_exc()
            except KeyboardInterrupt:
                print("Program interrupted by user.")
                break

    def handle_peer(self, client_socket, addr):
        print(f"Handling connection from {addr}")
        while True:
            try:
                print(f"Waiting for data from {addr}")
                data = recv_msg(client_socket)
                if data is None:
                    print(f"Client {addr} disconnected")
                    break
                info = pickle.loads(data)
                print(f"Received data from {addr}: {info['type']}")

                if info['type'] == REGISTER:
                    self.register_service(client_socket, info)
                elif info['type'] == LOGIN:
                    self.login_service(client_socket, info)
                elif info['type'] == PUBLISH:
                    self.publish_service(client_socket, info)
                elif info['type'] == FETCH:
                    self.fetch_service(client_socket, info)
                elif info['type'] == GET_FILES:
                    self.get_files_service(client_socket, info)
                elif info['type'] == LOGOUT:
                    self.logout_service(client_socket, info)
                    break
            except Exception as e:
                print(f"Error handling peer {addr}: {e}")
                traceback.print_exc()
                break
        print(f"Connection from {addr} closed")

    # SERVICE FUNCTIONS
    def register_service(self, client_socket, info):
        user, passwd, ip, port = info['username'], info['password'], info['ip'], info['port']
        print(f"Registering user: {user}")
        try:
            record = self.getAccountByUsername(user)
            if record:
                print(f"Account {user} already exists")
                msg = {
                    'type': REGISTER_FAIL,
                    'message': 'Account already exists'
                }
                send_msg(client_socket, msg)
            else:
                self.insertUser(user, passwd, ip, port)
                peer_id = self.getPeerId(user)
                print(f"Account {user} registered with peer ID: {peer_id}")
                msg = {
                    'type': REGISTER_SUCCESS,
                    'message': 'Registration successful! Please login.',
                    'peer_id': peer_id
                }
                send_msg(client_socket, msg)
        except Exception as e:
            print(f"Error registering user {user}: {e}")
            traceback.print_exc()
            send_msg(client_socket, {
                'type': REGISTER_FAIL,
                'message': 'Internal server error'
            })

    def login_service(self, client_socket, info):
        user, passwd, ip, port = info['username'], info['password'], info['ip'], info['port']
        print(f"Logging in user: {user}")
        try:
            record = self.getAccountByUsername(user)
            if record:
                if record[2] == passwd:
                    peer_id = self.getPeerId(user)
                    msg = {
                        'type': LOGIN_SUCCESS,
                        'message': 'Login successful',
                        'peer_id': peer_id
                    }
                    send_msg(client_socket, msg)
                    self.updateLogin(peer_id, ip, port)
                else:
                    msg = {
                        'type': LOGIN_FAIL,
                        'message': 'Incorrect password'
                    }
                    send_msg(client_socket, msg)
            else:
                msg = {
                    'type': LOGIN_FAIL,
                    'message': 'Account not found'
                }
                send_msg(client_socket, msg)
        except Exception as e:
            print(f"Error in login_service: {e}")
            traceback.print_exc()
            send_msg(client_socket, {
                'type': LOGIN_FAIL,
                'message': 'Internal server error'})

    def logout_service(self, client_socket, info):
        peer_id = info['peer_id']
        self.updateLogout(peer_id)
        send_msg(client_socket, {
            'type': LOGOUT_SUCCESS,
            'message': 'Logout successful'
        })

    def publish_service(self, client_socket, info):
        info_hash, peer_id = info['info_hash'], info['peer_id']
        filename = info['filename']
        filesize = info['filesize']

        if info_hash not in self.files_info:
            self.files_info[info_hash] = {
                'filename': filename,
                'size': filesize,
                'peers': set()
            }
        self.files_info[info_hash]['peers'].add(peer_id)

        if info_hash in self.files_info:
            self.files_info[info_hash]['peers'].add(peer_id)
        else:
            self.files_info[info_hash] = {
                'filename': filename,
                'size': filesize,
                'peers': {peer_id}
            }

        print(f"Peer {peer_id} published file {filename}")
        send_msg(client_socket, {
            'type': PUBLISH_SUCCESS,
            'message': 'Publish successful'
        })

    def fetch_service(self, client_socket, info):
        info_hash = info['info_hash']
        peer_id = info['peer_id']
        # First check if the info_hash exists
        if info_hash not in self.files_info:
            send_msg(client_socket, {
                'type': FETCH_FAIL,
                'message': 'File not found'
            })
            return

        # Get online peers and their connection info
        online_peers = []
        for peer_id in self.files_info[info_hash]['peers']:
            if self.is_peer_online(peer_id):
                peer_info = self.getIpandPortByPeerID(peer_id)
                if peer_info:  # Only add if we got valid connection info
                    ip, port = peer_info
                    online_peers.append((peer_id,ip, port))

        if online_peers:
            send_msg(client_socket, {
                'type': FETCH_SUCCESS,
                'peers': online_peers
            })
        else:
            send_msg(client_socket, {
                'type': FETCH_FAIL,
                'message': 'No peers available'
            })

    def get_files_service(self, client_socket, info):
        available_files = []
        for info_hash, file_info in self.files_info.items():
            if any(self.is_peer_online(peer_id) for peer_id in file_info['peers']):
                available_files.append({
                    'filename': file_info['filename'],
                    'size': file_info['size'],
                    'info_hash': info_hash
                })

        send_msg(client_socket, {
            'type': GET_FILES_SUCCESS,
            'files': available_files
        })

    # Database functions

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

    def getAccountByUsername(self, user):
        self.cursor.execute("SELECT * FROM users WHERE username = ?", (user,))
        return self.cursor.fetchone()

    def getPeerId(self, user):
        self.cursor.execute("SELECT id FROM users WHERE username = ?", (user,))
        return self.cursor.fetchone()[0]

    def getIpandPortByPeerID(self, peer_id):
        self.cursor.execute("SELECT ip, port FROM users WHERE id = ? AND status = 1", (peer_id,))
        return self.cursor.fetchone()
    
    def updateLogin(self, id, ip, port):
        with self.lock:
            self.cursor.execute(
                "UPDATE users SET ip = ?, port = ?, status = 1 WHERE id = ?", (ip, port, id))
            self.conn.commit()

    def updateLogout(self, id):
        with self.lock:
            self.cursor.execute(
                "UPDATE users SET status = 0 WHERE id = ?", (id,))
            self.conn.commit()

    def insertUser(self, user, passwd, ip, port):
        with self.lock:
            self.cursor.execute("INSERT INTO users (username, password, ip, port, status) VALUES (?, ?, ?, ?, 0)",
                                (user, passwd, ip, port))
            self.conn.commit()

    def is_peer_online(self, peer_id):
        self.cursor.execute(
            "SELECT status FROM users WHERE id = ?", (peer_id,))
        result = self.cursor.fetchone()
        return result and result[0] == 1


if __name__ == '__main__':
    tracker = Tracker()
    tracker.run()
