import socket
import json
import threading
import time

class Server:
    def __init__(self, host='localhost', port=5000):
        self.host = host
        self.port = port
        self.files = {}  # {file_id: {metadata, peers}}
        self.peers = {}  # {peer_id: {ip, port, last_seen}}

    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, self.port))
            s.listen()
            print(f"Server listening on {self.host}:{self.port}")
            while True:
                conn, addr = s.accept()
                threading.Thread(target=self.handle_client, args=(conn, addr)).start()

    def handle_client(self, conn, addr):
        with conn:
            print(f"Connected by {addr}")
            while True:
                data = conn.recv(1024).decode()
                if not data:
                    break
                message = json.loads(data)
                response = self.process_message(message, addr)
                conn.sendall(json.dumps(response).encode())

    def process_message(self, message, addr):
        if message['type'] == 'register_file':
            return self.register_file(message['file_id'], message['metadata'])
        elif message['type'] == 'get_file_info':
            return self.get_file_info(message['file_id'])
        elif message['type'] == 'announce':
            return self.announce(message['ip'], message['port'], message.get('file_id'))
        elif message['type'] == 'get_peers':
            return self.get_peers(message['file_id'])
        else:
            return {"status": "error", "message": "Unknown message type"}

    def register_file(self, file_id, metadata):
        self.files[file_id] = {
            'metadata': metadata,
            'peers': set()
        }
        return {"status": "success", "file_id": file_id}

    def get_file_info(self, file_id):
        if file_id in self.files:
            return {
                "status": "success",
                "metadata": self.files[file_id]['metadata'],
                "peers": list(self.files[file_id]['peers'])
            }
        return {"status": "error", "message": "File not found"}

    def announce(self, ip, port, file_id=None):
        peer_id = f"{ip}:{port}"
        self.peers[peer_id] = {
            'ip': ip,
            'port': port,
            'last_seen': time.time()
        }
        if file_id:
            self.files[file_id]['peers'].add(peer_id)
        return {"status": "success"}

    def get_peers(self, file_id):
        if file_id in self.files:
            active_peers = [peer for peer in self.files[file_id]['peers'] if time.time() - self.peers[peer]['last_seen'] < 300]
            self.files[file_id]['peers'] = set(active_peers)
            return {
                "status": "success",
                "peers": [self.peers[peer] for peer in active_peers]
            }
        return {"status": "error", "message": "File not found"}

if __name__ == '__main__':
    server = Server()
    server.start()