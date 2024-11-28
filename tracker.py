from parameter import *
from helper import *
from torrent import *

logging.basicConfig(
                        filename='tracker.log',
                        level=logging.INFO,
                        format='%(asctime)s - %(message)s',
                        filemode='a'
                    )

class Tracker:
    def __init__(self, db_path='tracker.db'):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.lock = threading.Lock()
        self.tracker_socket = None
        self.init_database()
        # info_hash -> {filename, size, peers}
        self.files_info: Dict[str, Dict] = {} # info_hash -> {filename, size, peers: dict bitfield with peer id as key, num_pieces, pieces_point} }

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
        logging.info(f"Started handling connection from {addr}")
        while True:
            try:
                logging.info(f"Waiting for data from {addr}")
                data = recv_msg(client_socket)
                if data is None:
                    logging.info(f"Client {addr} disconnected")
                    break
                info = pickle.loads(data)
                logging.info(f"Received {info['type']} request from {addr}")


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
                elif info['type'] == UPDATE_PIECE_POINT:
                    self.update_peer_pieces(info['peer_id'], info['info_hash'], info['piece_index'])
                elif info['type'] == HANDSHAKE:
                    self.handshake_service(client_socket, info)
            except Exception as e:
                logging.error(f"Error handling peer {addr}: {str(e)}")
                traceback.print_exc()
                break
        logging.info(f"Finished handling connection from {addr}")
    def handshake_service(self, client_socket, info):
        logging.info(f"Heard handshake request from {info['port']}")
        send_msg(client_socket, {'type': HANDSHAKE, 'message': 'Handshake successful'})
    # SERVICE FUNCTIONS
    def register_service(self, client_socket, info):
        user, passwd, ip, port = info['username'], info['password'], info['ip'], info['port']
        logging.info(f"Processing registration request for user: {user}")
        try:
            record = self.getAccountByUsername(user)
            if record:
                logging.warning(f"Registration failed: Account {user} already exists")
                msg = {
                    'type': REGISTER_FAIL,
                    'message': 'Account already exists'
                }
                send_msg(client_socket, msg)
            else:
                self.insertUser(user, passwd, ip, port)
                peer_id = self.getPeerId(user)
                logging.info(f"Successfully registered user {user} with peer ID: {peer_id}")
                msg = {
                    'type': REGISTER_SUCCESS,
                    'message': 'Registration successful! Please login.',
                    'peer_id': peer_id
                }
                send_msg(client_socket, msg)
        except Exception as e:
            logging.error(f"Registration error for user {user}: {str(e)}")
            traceback.print_exc()
            send_msg(client_socket, {
                'type': REGISTER_FAIL,
                'message': 'Internal server error'
            })

    def login_service(self, client_socket, info):
        user, passwd, ip, port = info['username'], info['password'], info['ip'], info['port']
        logging.info(f"Processing login request for user: {user}")
        try:
            record = self.getAccountByUsername(user)
            if record:
                if record[2] == passwd:
                    peer_id = self.getPeerId(user)
                    logging.info(f"User {user} logged in successfully with peer ID: {peer_id}")
                    msg = {
                        'type': LOGIN_SUCCESS,
                        'message': 'Login successful',
                        'peer_id': peer_id
                    }
                    send_msg(client_socket, msg)
                    self.updateLogin(peer_id, ip, port)
                else:
                    logging.warning(f"Login failed for user {user}: Incorrect password")
                    msg = {
                        'type': LOGIN_FAIL,
                        'message': 'Incorrect password'
                    }
                    send_msg(client_socket, msg)
            else:
                logging.warning(f"Login failed: Account not found for user {user}")
                msg = {
                    'type': LOGIN_FAIL,
                    'message': 'Account not found'
                }
                send_msg(client_socket, msg)
        except Exception as e:
            logging.error(f"Login error for user {user}: {str(e)}")
            traceback.print_exc()
            send_msg(client_socket, {
                'type': LOGIN_FAIL,
                'message': 'Internal server error'
            })

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
        bitfield = info['bitfield']
        logging.info(f"Processing publish request for file: {filename} from peer: {peer_id}")
        logging.info(f"File details - Hash: {info_hash}, Size: {filesize} bytes")
        logging.info(f"Initial bitfield from peer: {bitfield}")
        
        if info_hash not in self.files_info:
            num_pieces = (filesize+PIECE_SIZE-1)//PIECE_SIZE
            self.files_info[info_hash] = {
                'filename': filename,
                'size': filesize,
                'peers': {},
                'num_pieces': num_pieces,
                'pieces_point': [0]*num_pieces
            }
            logging.info(f"Created new file entry:")
            logging.info(f"- Number of pieces: {num_pieces}")
            logging.info(f"- Piece size: {PIECE_SIZE} bytes")
            logging.info(f"- Initial pieces_point: {self.files_info[info_hash]['pieces_point']}")
        
        self.files_info[info_hash]['peers'][peer_id] = bitfield
        logging.info(f"Updated peer {peer_id} bitfield for file {filename}")
        logging.info(f"Current peers for file {filename}: {list(self.files_info[info_hash]['peers'].keys())}")

        # if info_hash in self.files_info:
        #     self.files_info[info_hash]['peers'].add(peer_id)
        # else:
        #     self.files_info[info_hash] = {
        #         'filename': filename,
        #         'size': filesize,
        #         'peers': {peer_id}
        #     }

        print(f"Peer {peer_id} published file {filename}")
        send_msg(client_socket, {
            'type': PUBLISH_SUCCESS,
            'message': 'Publish successful'
        })
        logging.info(f"Successfully published file {filename} by peer {peer_id}")
        
    def initialize_peer_start_download(self, peer_id, info_hash):
        num_pieces = self.files_info[info_hash]['num_pieces']
        if peer_id not in self.files_info[info_hash]['peers']:
            self.files_info[info_hash]['peers'][peer_id] = '0' * num_pieces
        logging.info(f"Initialized peer {peer_id} for download:")
        logging.info(f"- File hash: {info_hash}")
        logging.info(f"- Number of pieces: {num_pieces}")
        logging.info(f"- Initial bitfield: {self.files_info[info_hash]['peers'][peer_id]}")
        
    def update_peer_pieces(self, peer_id, info_hash, piece_index):
        logging.info(f"Updating piece information:")
        logging.info(f"- Peer ID: {peer_id}")
        logging.info(f"- File hash: {info_hash}")
        logging.info(f"- Piece index: {piece_index}")
        
        try:
            # Log before update
            logging.info(f"Before update:")
            logging.info(f"- Current bitfield: {self.files_info[info_hash]['peers'][peer_id]}")
            logging.info(f"- Current piece points: {self.files_info[info_hash]['pieces_point']}")
            
            current_bitfield = self.files_info[info_hash]['peers'][peer_id]
            new_bitfield = (
                current_bitfield[:piece_index] + 
                '1' + 
                current_bitfield[piece_index + 1:]
            )
            self.files_info[info_hash]['peers'][peer_id] = new_bitfield
            self.files_info[info_hash]['pieces_point'][piece_index] += 1
            
            # Log after update
            logging.info(f"After update:")
            logging.info(f"- Updated bitfield: {self.files_info[info_hash]['peers'][peer_id]}")
            logging.info(f"- Updated piece points: {self.files_info[info_hash]['pieces_point']}")
            logging.info(f"- New point value for piece {piece_index}: {self.files_info[info_hash]['pieces_point'][piece_index]}")
            
        except Exception as e:
            logging.error(f"Error updating piece information: {str(e)}")
            logging.error(f"Current state:")
            logging.error(f"- File info exists: {info_hash in self.files_info}")
            if info_hash in self.files_info:
                logging.error(f"- Peer exists: {peer_id in self.files_info[info_hash]['peers']}")
                logging.error(f"- Number of pieces: {len(self.files_info[info_hash]['pieces_point'])}")
            traceback.print_exc()
        
        
    def fetch_service(self, client_socket, info):
        info_hash = info['info_hash']
        peer_id = info['peer_id']
        logging.info(f"Processing fetch request for file hash: {info_hash} from peer: {peer_id}")

        if info_hash not in self.files_info:
            logging.warning(f"Fetch failed: File with hash {info_hash} not found")
            send_msg(client_socket, {
                'type': FETCH_FAIL,
                'message': 'File not found'
            })
            return

        file_info = self.files_info[info_hash]
        logging.info(f"File details:")
        logging.info(f"- Filename: {file_info['filename']}")
        logging.info(f"- Size: {file_info['size']} bytes")
        logging.info(f"- Number of pieces: {file_info['num_pieces']}")
        logging.info(f"- Current piece points: {file_info['pieces_point']}")

        online_peers = []
        pieces_point = self.files_info[info_hash]['pieces_point']
        for seeder_id in self.files_info[info_hash]['peers']:
            if seeder_id != peer_id and self.is_peer_online(seeder_id):
                peer_info = self.getIpandPortByPeerID(seeder_id)
                if peer_info:
                    ip, port = peer_info
                    online_peers.append((seeder_id, ip, port))
                    peer_bitfield = self.files_info[info_hash]['peers'][seeder_id]
                    logging.info(f"Found online peer {seeder_id} at {ip}:{port}")
                    logging.info(f"Peer {seeder_id} bitfield: {peer_bitfield}")

        if online_peers:
            self.initialize_peer_start_download(peer_id, info_hash)
            logging.info(f"Initialized download for peer {peer_id}, file {info_hash}")
            logging.info(f"Initial peer bitfield: {self.files_info[info_hash]['peers'][peer_id]}")
            send_msg(client_socket, {
                'type': FETCH_SUCCESS,
                'peers': online_peers,
                'pieces_point': pieces_point
            })
            logging.info(f"Sent {len(online_peers)} peers to requesting peer {peer_id}")
            logging.info(f"Current piece points sent: {pieces_point}")
        else:
            logging.warning(f"Fetch failed: No online peers found for file {info_hash}")
            send_msg(client_socket, {
                'type': FETCH_FAIL,
                'message': 'No peers available'
            })

    def get_files_service(self, client_socket, info):
        logging.info("Processing get_files request")
        available_files = []
        
        logging.info("Current files in tracker:")
        for info_hash, file_info in self.files_info.items():
            logging.info(f"File: {file_info['filename']}")
            logging.info(f"- Hash: {info_hash}")
            logging.info(f"- Size: {file_info['size']} bytes")
            logging.info(f"- Number of pieces: {file_info['num_pieces']}")
            logging.info(f"- Piece points: {file_info['pieces_point']}")
            logging.info(f"- Connected peers: {list(file_info['peers'].keys())}")
            
            if any(self.is_peer_online(peer_id) for peer_id in file_info['peers']):
                available_files.append({
                    'filename': file_info['filename'],
                    'size': file_info['size'],
                    'info_hash': info_hash
                })
                logging.info(f"Added to available files: {file_info['filename']}")

        send_msg(client_socket, {
            'type': GET_FILES_SUCCESS,
            'files': available_files
        })
        logging.info(f"Sent list of {len(available_files)} available files")

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
