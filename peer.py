from parameter import *
from helper import *
from torrent import Torrent

class Peer:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.peer_id = None
        self.username = None
        self.tracker_socket = None
        self.listen_socket = None
        self.torrents = {}  # info_hash -> Torrent
        self.downloads = {}  # info_hash -> DownloadManager
        self.uploads = {}  # (info_hash, peer_id) -> UploadManager
        self.peer_connections = {}  # peer_id -> PeerConnection
        self.available_files = []
        self.logger = setup_logger('peer')

    def connect_to_tracker(self, tracker_host, tracker_port):
        self.tracker_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tracker_socket.connect((tracker_host, tracker_port))
        self.logger.info(f"Connected to tracker at {tracker_host}:{tracker_port}")

    def register(self, username, password):
        message = {
            'type': REGISTER,
            'username': username,
            'password': password,
            'ip': self.ip,
            'port': self.port
        }
        send_msg(self.tracker_socket, message)
        response = recv_msg(self.tracker_socket)
        if response['type'] == REGISTER_SUCCESS:
            self.peer_id = response['peer_id']
            self.username = username
            self.logger.info(f"Registered successfully. Peer ID: {self.peer_id}")
            return True
        else:
            self.logger.error(f"Registration failed: {response.get('message', 'Unknown error')}")
            return False

    def login(self, username, password):
        message = {
            'type': LOGIN,
            'username': username,
            'password': password,
            'ip': self.ip,
            'port': self.port
        }
        send_msg(self.tracker_socket, message)
        response = recv_msg(self.tracker_socket)
        if response['type'] == LOGIN_SUCCESS:
            self.peer_id = response['peer_id']
            self.username = username
            self.logger.info(f"Logged in successfully. Peer ID: {self.peer_id}")
            return True
        else:
            self.logger.error(f"Login failed: {response.get('message', 'Unknown error')}")
            return False

    def publish_file(self, file_path):
        try:
            torrent = Torrent(file_path)
            self.torrents[torrent.info_hash] = torrent
            message = {
                'type': PUBLISH,
                'peer_id': self.peer_id,
                'info_hash': torrent.info_hash,
                'filename': torrent.file_name,
                'filesize': torrent.file_size,
                'bitfield': torrent.bitfield.to_bytes()
            }
            send_msg(self.tracker_socket, message)
            response = recv_msg(self.tracker_socket)
            if response['type'] == PUBLISH_SUCCESS:
                self.logger.info(f"Successfully published {file_path}")
                return True
            else:
                self.logger.error(f"Failed to publish {file_path}")
                return False
        except Exception as e:
            self.logger.error(f"Error publishing file: {e}")
            return False

    def get_available_files(self):
        message = {'type': GET_FILES, 'peer_id': self.peer_id}
        send_msg(self.tracker_socket, message)
        response = recv_msg(self.tracker_socket)
        if response['type'] == GET_FILES_SUCCESS:
            self.available_files = response['files']
            return self.available_files
        else:
            self.logger.error("Failed to get available files")
            return []

    def start_download(self, file_index):
        file_info = self.available_files[file_index]
        info_hash = file_info['info_hash']
        message = {'type': FETCH, 'peer_id': self.peer_id, 'info_hash': info_hash}
        send_msg(self.tracker_socket, message)
        response = recv_msg(self.tracker_socket)
        if response['type'] == FETCH_SUCCESS:
            peers = response['peers']
            if not peers:
                self.logger.error("No peers available for download")
                return False
            download_manager = DownloadManager(self, file_info, peers)
            self.downloads[info_hash] = download_manager
            download_manager.start()
            return True
        else:
            self.logger.error("Failed to fetch peer list for download")
            return False

    def handle_incoming_connection(self, client_socket, addr):
        try:
            handshake = recv_msg(client_socket)
            if handshake['type'] != HANDSHAKE:
                raise ValueError("Invalid handshake")
            info_hash = handshake['info_hash']
            peer_id = handshake['peer_id']
            if info_hash not in self.torrents:
                raise ValueError("Unknown info_hash")
            upload_manager = UploadManager(self, self.torrents[info_hash], peer_id, client_socket)
            self.uploads[(info_hash, peer_id)] = upload_manager
            upload_manager.start()
        except Exception as e:
            self.logger.error(f"Error handling incoming connection: {e}")
            client_socket.close()

    def start_listening(self):
        self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listen_socket.bind((self.ip, self.port))
        self.listen_socket.listen(5)
        self.logger.info(f"Listening for incoming connections on {self.ip}:{self.port}")
        while True:
            client_socket, addr = self.listen_socket.accept()
            threading.Thread(target=self.handle_incoming_connection, args=(client_socket, addr)).start()

    def update_tracker_bitfield(self, info_hash):
        if info_hash in self.torrents:
            message = {
                'type': UPDATE_BITFIELD,
                'peer_id': self.peer_id,
                'info_hash': info_hash,
                'bitfield': self.torrents[info_hash].bitfield.to_bytes()
            }
            send_msg(self.tracker_socket, message)

    def logout(self):
        message = {'type': LOGOUT, 'peer_id': self.peer_id}
        send_msg(self.tracker_socket, message)
        self.tracker_socket.close()
        self.listen_socket.close()
        self.logger.info("Logged out and closed connections")

class DownloadManager:
    def __init__(self, peer, file_info, peers):
        self.peer = peer
        self.file_info = file_info
        self.peers = peers
        self.bitfield = BitField(calculate_num_pieces(file_info['size']))
        self.pieces = {}
        self.peer_connections = {}
        self.logger = setup_logger('download_manager')

    def start(self):
        for peer_id, (ip, port) in self.peers:
            conn = PeerConnection(self.peer, peer_id, ip, port, self.file_info['info_hash'])
            self.peer_connections[peer_id] = conn
            conn.start()
        threading.Thread(target=self.piece_selection_loop).start()

    def piece_selection_loop(self):
        while self.running:
            try:
                if self.peer_connections and any(conn and conn.peer_bitfield for conn in self.peer_connections):
                    piece_index = self.select_rarest_piece()
                    if piece_index is not None:
                        self.request_piece(piece_index)
                else:
                    time.sleep(1)
            except Exception as e:
                logging.error(f"Error in piece selection loop: {e}")
                time.sleep(1)

    def select_rarest_piece(self):
        piece_counts = defaultdict(int)
        for i in range(self.total_pieces):
            for conn in self.peer_connections:
                if conn and conn.peer_bitfield and conn.peer_bitfield.has_piece(i) and not self.bitfield.has_piece(i):
                    piece_counts[i] += 1
        if piece_counts:
            return min(piece_counts, key=piece_counts.get)
        return None

    def request_piece(self, piece_index):
        for conn in self.peer_connections.values():
            if conn.peer_bitfield.has_piece(piece_index):
                conn.request_piece(piece_index)
                break

    def handle_piece(self, piece_index, piece_data):
        if self.peer.torrents[self.file_info['info_hash']].verify_piece(piece_index, piece_data):
            self.pieces[piece_index] = piece_data
            self.bitfield.set_piece(piece_index)
            self.peer.update_tracker_bitfield(self.file_info['info_hash'])
            self.logger.info(f"Received and verified piece {piece_index}")
            if self.is_complete():
                self.complete_download()
        else:
            self.logger.warning(f"Received invalid piece {piece_index}")

    def is_complete(self):
        return self.bitfield.count_pieces() == self.bitfield.num_pieces

    def complete_download(self):
        file_path = os.path.join("downloads", self.file_info['filename'])
        with open(file_path, 'wb') as f:
            for i in range(self.bitfield.num_pieces):
                f.write(self.pieces[i])
        self.logger.info(f"Download completed: {file_path}")
        self.peer.torrents[self.file_info['info_hash']] = Torrent(file_path)

class UploadManager:
    def __init__(self, peer, torrent, requester_id, client_socket):
        self.peer = peer
        self.torrent = torrent
        self.requester_id = requester_id
        self.client_socket = client_socket
        self.logger = setup_logger('upload_manager')

    def start(self):
        threading.Thread(target=self.handle_requests).start()

    def handle_requests(self):
        while True:
            try:
                message = recv_msg(self.client_socket)
                if message['type'] == REQUEST:
                    self.handle_piece_request(message)
                elif message['type'] == CANCEL:
                    # Handle cancel request if implemented
                    pass
            except Exception as e:
                self.logger.error(f"Error handling upload request: {e}")
                break
        self.client_socket.close()

    def handle_piece_request(self, message):
        piece_index = message['piece_index']
        begin = message['begin']
        length = message['length']
        piece_data = self.torrent.get_piece(piece_index, begin, length)
        response = {
            'type': PIECE,
            'piece_index': piece_index,
            'begin': begin,
            'block': piece_data
        }
        send_msg(self.client_socket, response)
        self.logger.info(f"Sent piece {piece_index} to peer {self.requester_id}")

class PeerConnection:
    def __init__(self, peer, peer_id, ip, port, info_hash):
        self.peer = peer
        self.peer_id = peer_id
        self.ip = ip
        self.port = port
        self.info_hash = info_hash
        self.socket = None
        self.peer_bitfield = None
        self.am_choking = True
        self.am_interested = False
        self.peer_choking = True
        self.peer_interested = False
        self.logger = setup_logger('peer_connection')

    def start(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.ip, self.port))
            self.send_handshake()
            threading.Thread(target=self.message_loop).start()
        except Exception as e:
            self.logger.error(f"Failed to connect to peer {self.peer_id}: {e}")

    def send_handshake(self):
        message = {
            'type': HANDSHAKE,
            'info_hash': self.info_hash,
            'peer_id': self.peer.peer_id
        }
        send_msg(self.socket, message)

    def message_loop(self):
        while True:
            try:
                message = recv_msg(self.socket)
                self.handle_message(message)
            except Exception as e:
                self.logger.error(f"Error in message loop: {e}")
                break
        self.socket.close()

    def handle_message(self, message):
        if message['type'] == BITFIELD:
            self.peer_bitfield = BitField.from_bytes(message['bitfield'])
        elif message['type'] == HAVE:
            self.peer_bitfield.set_piece(message['piece_index'])
        elif message['type'] == CHOKE:
            self.peer_choking = True
        elif message['type'] == UNCHOKE:
            self.peer_choking = False
        elif message['type'] == INTERESTED:
            self.peer_interested = True
        elif message['type'] == NOT_INTERESTED:
            self.peer_interested = False
        elif message['type'] == PIECE:
            self.handle_piece(message)

    def handle_piece(self, message):
        piece_index = message['piece_index']
        begin = message['begin']
        block = message['block']
        download_manager = self.peer.downloads[self.info_hash]
        if piece_index not in download_manager.pieces:
            download_manager.pieces[piece_index] = bytearray(PIECE_SIZE)
        download_manager.pieces[piece_index][begin:begin+len(block)] = block
        if len(download_manager.pieces[piece_index]) == PIECE_SIZE:
            download_manager.handle_piece(piece_index, download_manager.pieces[piece_index])

    def request_piece(self, piece_index):
        if not self.peer_choking:
            message = {
                'type': REQUEST,
                'piece_index': piece_index,
                'begin': 0,
                'length': PIECE_SIZE
            }
            send_msg(self.socket, message)

    def send_have(self, piece_index):
        message = {
            'type': HAVE,
            'piece_index': piece_index
        }
        send_msg(self.socket, message)

    def send_interested(self):
        if not self.am_interested:
            message = {'type': INTERESTED}
            send_msg(self.socket, message)
            self.am_interested = True

    def send_not_interested(self):
        if self.am_interested:
            message = {'type': NOT_INTERESTED}
            send_msg(self.socket, message)
            self.am_interested = False