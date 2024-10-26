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
    
    
    def register_file_with_tracker(self):
        pass
    
    
    def listen(self):
        pass
    
    def handle_connection(self):
        pass
    
    def request_file(self):
        pass
    
    def download_from_peer(self):
        pass
    
    def handle_magnet_link(self):
        pass
    
    
if __name__ == '__main__':
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)

    peer_port = int(input("Enter peer port: "))
    while True:
        try:
            peer = PeerClient(local_ip, peer_port)
            peer_id = peer.login_account_with_tracker()
            if peer_id:
                print(f"Login with peer_id: {peer_id}")
            else:
                print("Login failed.")
        except Exception as e:
            print(f"An error occurred: {e}")
        except KeyboardInterrupt:
            print("Exiting program.")
            break
    # finally:
        # if peer.peer_socket:
        #     peer.peer_socket.close()

    # input("Press Enter to exit...")
