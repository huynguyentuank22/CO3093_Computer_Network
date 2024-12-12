from parameter import *

def recvall(sock, n):
    # Helper function to recv n bytes or return None if EOF is hit
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data.extend(packet)
    return data

def recv_msg(sock):
    # Receive the size of the message first
    raw_msglen = recvall(sock, 4)
    if not raw_msglen:
        return None
    msglen = struct.unpack('>I', raw_msglen)[0]
    # Now receive the message data
    return recvall(sock, msglen)

def send_msg(sock, msg):
    msg = pickle.dumps(msg)
    sock.sendall(struct.pack('>I', len(msg)) + msg)

def sha1_hash(data):
    return hashlib.sha1(data).hexdigest()

def generate_port():
    # global PORT_PEER
    # tmp = PORT_PEER
    # PORT_PEER += 1
    return random.randint(10000, 65535)
