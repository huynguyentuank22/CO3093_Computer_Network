from parameter import *

class BitField:
    def __init__(self, num_pieces):
        self.bitfield = bytearray([0] * ((num_pieces + 7) // 8))
        self.num_pieces = num_pieces

    def set_piece(self, piece_index):
        if 0 <= piece_index < self.num_pieces:
            byte_index = piece_index // 8
            bit_offset = 7 - (piece_index % 8)
            self.bitfield[byte_index] |= (1 << bit_offset)

    def has_piece(self, piece_index):
        if 0 <= piece_index < self.num_pieces:
            byte_index = piece_index // 8
            bit_offset = 7 - (piece_index % 8)
            return bool(self.bitfield[byte_index] & (1 << bit_offset))

    def count_pieces(self):
        return sum(bin(byte).count('1') for byte in self.bitfield)

    def to_bytes(self):
        return bytes(self.bitfield)

    @staticmethod
    def from_bytes(data, num_pieces):
        bf = BitField(num_pieces)
        bf.bitfield = bytearray(data)
        return bf

def recvall(sock, n):
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data.extend(packet)
    return data

def send_msg(sock, msg):
    try:
        data = pickle.dumps(msg)
        length = struct.pack('>I', len(data))
        sock.sendall(length + data)
    except Exception as e:
        logging.error(f"Error sending message: {e}")
        raise

def recv_msg(sock):
    try:
        length_data = recvall(sock, 4)
        if not length_data:
            return None
        length = struct.unpack('>I', length_data)[0]
        return pickle.loads(recvall(sock, length))
    except Exception as e:
        logging.error(f"Error receiving message: {e}")
        raise

def sha1_hash(data):
    return hashlib.sha1(data).hexdigest()

def calculate_num_pieces(file_size):
    return (file_size + PIECE_SIZE - 1) // PIECE_SIZE

def calculate_piece_size(file_size, piece_index, num_pieces):
    if piece_index < num_pieces - 1:
        return PIECE_SIZE
    return file_size - (num_pieces - 1) * PIECE_SIZE

def setup_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(f"{name}.log")
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    return logger