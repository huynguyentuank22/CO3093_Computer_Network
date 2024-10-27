import struct
import pickle
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
