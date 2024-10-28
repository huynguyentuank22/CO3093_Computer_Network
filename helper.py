import struct
import pickle
import bencodepy
def recv_msg(sock):
    # Receive the size of the message first
    raw_msglen = recvall(sock, 4)
    if not raw_msglen:
        return None
    msglen = struct.unpack('>I', raw_msglen)[0]
    # Now receive the message data
    return recvall(sock, msglen)

def recvall(sock, n):
    # Helper function to recv n bytes or return None if EOF is hit
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data.extend(packet)
    return data

def send_msg(sock, msg):
    msg = pickle.dumps(msg)
    sock.sendall(struct.pack('>I', len(msg)) + msg)
    
def command_line_interface():
    print("Welcome to the command line interface")
    while True:
        command = input(">>> ")
        if command == "exit":
            break
        else:
            print(f"Unknown command: {command}")

def create_magnet_link(metainfo, HOST, PORT):
        info_hash = bencodepy.encode(metainfo).hex()
        file_name = metainfo['file_name']
        file_size = metainfo['file_size']
        
        
        magnet_link = f"magnet:?xt=urn:btih:{info_hash}&dn={file_name}&xl={file_size}"
        
        # Add tracker URL to the magnet link
        tracker_url = f"http://{HOST}:{PORT}/announce"
        magnet_link += f"&tr={tracker_url}" 
        
        return magnet_link