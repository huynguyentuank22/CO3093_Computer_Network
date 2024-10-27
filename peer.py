import socket
import threading
import sqlite3
import time
import json
import os
import hashlib
import maskpass
import pickle
from parameter import *
from helper import *
from torrent import *

SERVER_NAME = socket.gethostname()
SERVER = socket.gethostbyname(SERVER_NAME) # default ip of tracker for test
PORT = 5050


# function to ensure pwd hidden
def get_password():
    while True:
        password = maskpass.askpass(prompt="Enter your password: ", mask="*")
        confirm_password = maskpass.askpass(prompt="Confirm your password: ", mask="*")

        if password == confirm_password:
            print("Password confirmed.")
            return password
        else:
            print("Password does not match. Try again.")

# hash function to hash piece of file into hexa code
def sha1_hash(data):
    sha1 = hashlib.sha1()
    sha1.update(data)
    return sha1.hexdigest()

# split function to split file into equal piece and return list of their hash code
def split_file_into_piece(path,piece_size):
    pieces = []
    with open(path, 'rb') as f:
        while True:
            piece = f.read(piece_size)
            if not piece:
                break
            pieces.append(sha1_hash(piece))
            
    return pieces


class PeerClient:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.peer_socket.connect((SERVER, PORT))
        self.user_name = None
        self.peer_id = None
        self.files: Dict[str, MetaInfoFile] = {} # key: file name, value: MetaInfoFile
        self.pieces: Dict[str, Dict[int, bytes]] = {} # key: file name, value: dict of piece index and piece data
        self.magnet_links: Dict[str, str] = {} # key: file name, value: magnet link
        
        
    def connect_to_tracker(self):
        max_retries = 5
        for attempt in range(max_retries):
            try:
                self.peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.peer_socket.connect((SERVER, PORT))
                print(f"Connected to tracker at {SERVER}:{PORT}")
                return
            except Exception as e:
                print(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    print("Retrying in 5 seconds...")
                    time.sleep(5)
                else:
                    print("Failed to connect to tracker after multiple attempts.")
                    raise
                
    def register_account_with_tracker(self):
        user_name = input("Enter your username to register: ")
        pwd = get_password()
        
        message = {'type': REGISTER, 'username': user_name, 'password': pwd, 'ip': self.ip, 'port': self.port}
        try:
            print("Sending registration request...")
            message = pickle.dumps({'type': REGISTER, 'username': user_name, 'password': pwd, 'ip': self.ip, 'port': self.port})
            self.peer_socket.sendall(struct.pack('>I', len(message)) + message)
            print("Registration request sent. Waiting for response...")
            
            response_data = recv_msg(self.peer_socket)
            if response_data is None:
                raise ConnectionError("Connection closed while receiving data")
            
            print(f"Received {len(response_data)} bytes of data")
            response = pickle.loads(response_data)
            
            if response['type'] == REGISTER_SUCCESSFUL:
                print(f"Account {user_name} registered successfully")
                peer_id = response['peer_id']
                if not os.path.exists(f"repo_{user_name}"):
                    os.makedirs(f"repo_{user_name}")
                    print(f"Created directory for user {user_name}. All files will be stored in this directory.")
                self.user_name = user_name
                return peer_id
            else:
                print(f"Account {user_name} registration failed")
                print(response['message'])
                return None
        except ConnectionResetError:
            print("Connection was reset by the tracker. The tracker might have closed unexpectedly.")
            return None
        except Exception as e:
            print(f"An error occurred during registration: {e}")
            return None
        
    def login_account_with_tracker(self):
        user_name = input("Enter your username to login: ")
        pwd = get_password()
        self.user_name = user_name
        message = {'type': LOGIN, 'username': user_name, 'password': pwd, 'ip': self.ip, 'port': self.port}
        try:
            print('Sending login request ...')
            message = pickle.dumps({'type': LOGIN, 'username': user_name, 'password': pwd, 'ip': self.ip, 'port': self.port})
            self.peer_socket.sendall(struct.pack('>I', len(message)) + message)
            print("Login request sent. Waiting for response...")
            response_data = recv_msg(self.peer_socket)
            
            if response_data is None:
                raise ConnectionError("Connection closed while receiving data")
            
            print(f"Received {len(response_data)} bytes of data")
            response = pickle.loads(response_data)
            
            if response['type'] == LOGIN_SUCCESSFUL:
                print(f"Login successful for user {user_name}")
                return response['peer_id']
            else:
                print(f"Login failed for user {user_name}")
                print(response['message'])
                if response['type'] == LOGIN_WRONG_PASSWORD:
                    print("Wrong password")
                    print("Please try again.")
                    self.login_account_with_tracker()
                    return None
                elif response['type'] == LOGIN_ACC_NOT_EXIST:
                    print("Account does not exist. You need to register first.")
                    self.register_account_with_tracker()
                    return None
                else:
                    print("Internal server error")
                    return None
        except Exception as e:
            print(f"An error occurred during login: {e}")
        pass
    
    def create_torrent(self, file_path: str):
        print("Creating torrent...")
        if not os.path.exists(file_path):
            print(f"File {file_path} does not exist.")
            return

        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        info_hash = hashlib.sha1(file_name.encode()).hexdigest()
        pieces = split_file_into_piece(file_path, PIECE_SIZE)
        tracker_address = f"http://{SERVER}:{PORT}"
        metainfo = {
            'file_name': file_name,
            'file_size': file_size,
            'piece_length': PIECE_SIZE,
            'pieces_count': len(pieces),
            'announce': tracker_address
        }
        self.files[file_name] = metainfo
        self.pieces[file_name] = {i: piece for i, piece in enumerate(pieces)}
        # metainfo_path = os.path.join(f"repo_{self.user_name}", f"{file_name}.torrent")
        # with open(metainfo_path, 'wb') as f:
        #     pickle.dump(metainfo, f)
        return metainfo
    
    def register_file_with_tracker(self):
        if self.peer_id is None:
            print("You need to login first.")
            return
        file_path = str(input("Enter file name you want to register: "))
        file_path = 'repo_' + self.user_name + '/' + file_path
        metainfo = self.create_torrent(file_path)
        # print(metainfo.encode())
        try:
            print("Sending register file request...")
            
            message = pickle.dumps({'type': REGISTER_FILE, 'metainfo': metainfo, 'peer_id': self.peer_id})
            self.peer_socket.sendall(struct.pack('>I', len(message)) + message)
            
            print("Register file request sent. Waiting for response...")
            response_data = recv_msg(self.peer_socket)
            if response_data is None:
                raise ConnectionError("Connection closed while receiving data")
            print(f"Received {len(response_data)} bytes of data")
            response = pickle.loads(response_data)
            if response['type'] == REGISTER_FILE_SUCCESSFUL:
                print(f"File {file_path} registered successfully")
                magnet_link = response['magnet_link']
                print(f"Magnet link: {magnet_link}")
                with open(os.path.join(f"repo_{self.user_name}", f"{metainfo['file_name']}_magnet"), 'wb') as f:
                    f.write(magnet_link.encode())
            else:
                print(f"File {file_path} registration failed")
                print(response['message'])
        except Exception as e:
            print(f"An error occurred during register file: {e}")
        
        
    def logout_account_with_tracker(self):
        message = pickle.dumps({'type': LOGOUT, 'peer_id': self.peer_id})
        self.peer_socket.sendall(struct.pack('>I', len(message)) + message)
        print("Logout request sent. Waiting for response...")
        response_data = recv_msg(self.peer_socket)
        if response_data is None:
            raise ConnectionError("Connection closed while receiving data")
        response = pickle.loads(response_data)
        if response['type'] == LOGOUT_SUCCESSFUL:
            print("Logout successful")
        else:
            print("Logout failed")
            print(response['message'])
            
    def listen(self):
        pass
    def get_list_files_to_download(self):
        if not self.peer_id:
            print("You need to login first.")
            return
        message = pickle.dumps({'type': GET_LIST_FILES_TO_DOWNLOAD})
        self.peer_socket.sendall(struct.pack('>I', len(message)) + message)
        response_data = recv_msg(self.peer_socket)
        if response_data is None:
            raise ConnectionError("Connection closed while receiving data")
        response = pickle.loads(response_data)
        if response['type'] == GET_LIST_FILES_TO_DOWNLOAD and response['files']:
            print("Available files:")
            for file in response['files']:
                print(file)
        else:
            print("No available files")
    
    def handle_connection(self):
        pass
    
    def request_file(self):
        pass
    
    def download_file(self):
        self.get_list_files_to_download()
    
    def handle_magnet_link(self):
        pass
    
    def command_line_interface(self):
        while True:
            print("\n--- Peer Client Menu ---")
            print("1. Register a new account")
            print("2. Login")
            print("3. Register a file")
            print("4. Download a file")
            print("5. List registered files")
            print("6. Exit")
            
            choice = input("Enter your choice (1-6): ")
            
            if choice == '1':
                self.register_account_with_tracker()
            elif choice == '2':
                self.peer_id = self.login_account_with_tracker()
            elif choice == '3':
                self.register_file_with_tracker()
            elif choice == '4':
                self.download_file()
            # elif choice == '5':
            #     self.list_registered_files()
            elif choice == '6':
                if self.peer_socket:
                    self.peer_socket.close()
                print("Exiting...")
                break
            else:
                print("Invalid choice. Please try again.")
    
    
if __name__ == '__main__':
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)

    peer_port = int(input("Enter peer port: "))
    peer = None
    try:
        peer = PeerClient(local_ip, peer_port)
        peer.connect_to_tracker()
        peer.command_line_interface()
    except Exception as e:
        print(f"An error occurred: {e}")
    except KeyboardInterrupt:
        print("Program interrupted by user.")
    finally:
        if peer and peer.peer_socket:
            peer.peer_socket.close()
        print("Closing connection and exiting program.")
        input("Press Enter to exit...")
