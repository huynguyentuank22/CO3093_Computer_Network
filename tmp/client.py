import socket
import threading
import time
import os
import json
import hashlib
import random

class Peer:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.pieces = set()
        self.last_seen = time.time()

class Client:
    def __init__(self, file_path, listen_port, server_host='localhost', server_port=5000):
        self.file_path = file_path
        self.listen_port = listen_port
        self.server_host = server_host
        self.server_port = server_port
        self.peers = {}
        self.file_id = self.generate_file_id()
        self.metadata = self.get_or_create_metadata()
        self.pieces = [False] * len(self.metadata['pieces'])
        self.file = self.prepare_file()
        self.max_connections = 4  # Maximum number of unchoked peers
        self.interested_peers = {}  # Peers interested in our pieces
        self.piece_counts = {}  # Track how many peers have each piece
        self.unchoked_peers = set()  # Currently unchoked peers
        self.last_unchoke_time = time.time()
        self.upload_rates = {}  # Track upload rates for peers

    def generate_file_id(self):
        return hashlib.md5(self.file_path.encode()).hexdigest()

    def get_or_create_metadata(self):
        response = self.send_to_server({
            'type': 'get_file_info',
            'file_id': self.file_id
        })
        if response['status'] == 'success':
            return response['metadata']
        else:
            return self.create_metadata()

    def create_metadata(self):
        piece_size = 256 * 1024  # 256 KB
        metadata = {
            'file_name': os.path.basename(self.file_path),
            'file_size': os.path.getsize(self.file_path),
            'piece_size': piece_size,
            'pieces': []
        }
        
        with open(self.file_path, 'rb') as f:
            while True:
                piece = f.read(piece_size)
                if not piece:
                    break
                piece_hash = hashlib.sha256(piece).hexdigest()
                metadata['pieces'].append(piece_hash)
        
        self.send_to_server({
            'type': 'register_file',
            'file_id': self.file_id,
            'metadata': metadata
        })
        return metadata

    def prepare_file(self):
        if os.path.exists(self.file_path) and os.path.getsize(self.file_path) == self.metadata['file_size']:
            return open(self.file_path, 'rb+')
        else:
            file = open(self.file_path, 'wb+')
            file.seek(self.metadata['file_size'] - 1)
            file.write(b'\0')
            file.seek(0)
            return file

    def announce_to_server(self):
        self.send_to_server({
            'type': 'announce',
            'ip': '127.0.0.1',
            'port': self.listen_port,
            'file_id': self.file_id
        })
        print("Successfully announced to server")

    def get_peer_list(self):
        response = self.send_to_server({
            'type': 'get_peers',
            'file_id': self.file_id
        })
        if response['status'] == 'success':
            peer_list = response['peers']
            for peer in peer_list:
                if peer['port'] != self.listen_port:  # Don't add self as peer
                    self.peers[f"{peer['ip']}:{peer['port']}"] = Peer(peer['ip'], peer['port'])
            print(f"Got peer list: {self.peers.keys()}")

    def send_to_server(self, message):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.server_host, self.server_port))
            s.sendall(json.dumps(message).encode())
            return json.loads(s.recv(1024).decode())

    def update_piece_counts(self):
        # Reset piece counts
        self.piece_counts = {i: 0 for i in range(len(self.metadata['pieces']))}
        # Count how many peers have each piece
        for peer in self.peers.values():
            for piece_index in peer.pieces:
                self.piece_counts[piece_index] = self.piece_counts.get(piece_index, 0) + 1

    def select_next_piece(self):
        # Get pieces we don't have
        missing_pieces = [i for i, have in enumerate(self.pieces) if not have]
        if not missing_pieces:
            return None

        # Get available pieces from peers
        available_pieces = {}
        for piece_index in missing_pieces:
            peers_with_piece = [
                peer_id for peer_id, peer in self.peers.items()
                if piece_index in peer.pieces and peer_id in self.unchoked_peers
            ]
            if peers_with_piece:
                available_pieces[piece_index] = self.piece_counts[piece_index]

        if not available_pieces:
            return None

        # Select rarest piece
        rarest_count = min(available_pieces.values())
        rarest_pieces = [
            piece for piece, count in available_pieces.items()
            if count == rarest_count
        ]
        
        # Randomly select from among the rarest pieces
        return random.choice(rarest_pieces) if rarest_pieces else None

    def run_choking_algorithm(self):
        while True:
            try:
                current_time = time.time()
                if current_time - self.last_unchoke_time >= 10:  # Run every 10 seconds
                    self.update_choked_peers()
                    self.last_unchoke_time = current_time
                time.sleep(1)
            except Exception as e:
                print(f"Error in choking algorithm: {e}")

    def update_choked_peers(self):
        # Sort peers by upload rate
        sorted_peers = sorted(
            self.upload_rates.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Select top uploaders to unchoke
        new_unchoked = set()
        for peer_id, _ in sorted_peers[:self.max_connections-1]:
            if peer_id in self.interested_peers:
                new_unchoked.add(peer_id)

        # Optimistic unchoke: randomly select one additional peer
        remaining_peers = [
            peer_id for peer_id in self.interested_peers
            if peer_id not in new_unchoked
        ]
        if remaining_peers:
            new_unchoked.add(random.choice(remaining_peers))

        # Update unchoked peers
        newly_choked = self.unchoked_peers - new_unchoked
        newly_unchoked = new_unchoked - self.unchoked_peers

        # Send choke/unchoke messages
        for peer_id in newly_choked:
            self.send_choke_message(peer_id)
        for peer_id in newly_unchoked:
            self.send_unchoke_message(peer_id)

        self.unchoked_peers = new_unchoked

    def update_upload_rate(self, peer_id, bytes_uploaded):
        # Simple moving average of upload rate
        current_rate = self.upload_rates.get(peer_id, 0)
        new_rate = 0.7 * current_rate + 0.3 * bytes_uploaded
        self.upload_rates[peer_id] = new_rate

    def run(self):
        # Start listener thread for incoming peer connections
        listener_thread = threading.Thread(target=self.listen_for_peers)
        listener_thread.daemon = True
        listener_thread.start()

        # Start announcer thread to periodically announce to server
        announcer_thread = threading.Thread(target=self.periodic_announce)
        announcer_thread.daemon = True
        announcer_thread.start()

        # Start peer manager thread to update peer list and remove inactive peers
        peer_manager_thread = threading.Thread(target=self.manage_peers)
        peer_manager_thread.daemon = True
        peer_manager_thread.start()

        # Add choking algorithm thread
        choking_thread = threading.Thread(target=self.run_choking_algorithm)
        choking_thread.daemon = True
        choking_thread.start()

        # Add piece selection thread
        piece_selection_thread = threading.Thread(target=self.run_piece_selection)
        piece_selection_thread.daemon = True
        piece_selection_thread.start()

    def listen_for_peers(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind(('0.0.0.0', self.listen_port))
            server_socket.listen()
            while True:
                client_socket, address = server_socket.accept()
                peer_thread = threading.Thread(target=self.handle_peer_connection, args=(client_socket,))
                peer_thread.daemon = True
                peer_thread.start()

    def periodic_announce(self):
        while True:
            self.announce_to_server()
            self.get_peer_list()
            time.sleep(60)  # Announce every minute

    def manage_peers(self):
        while True:
            current_time = time.time()
            # Remove peers not seen in the last 5 minutes
            inactive_peers = [peer_id for peer_id, peer in self.peers.items() 
                             if current_time - peer.last_seen > 300]
            for peer_id in inactive_peers:
                del self.peers[peer_id]
            time.sleep(60)

    def run_piece_selection(self):
        while True:
            try:
                self.update_piece_counts()
                next_piece = self.select_next_piece()
                if next_piece is not None:
                    # Request the selected piece from an unchoked peer that has it
                    self.request_piece(next_piece)
                time.sleep(1)
            except Exception as e:
                print(f"Error in piece selection: {e}")

# Usage
client = Client('path/to/your/file.txt', 6881)
client.run()
