from parameter import *
from helper import *

class Torrent:
    def __init__(self, file_path):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        self.file_path = file_path
        self.file_name = os.path.basename(file_path)
        self.file_size = os.path.getsize(file_path)
        self.num_pieces = calculate_num_pieces(self.file_size)
        self.bitfield = BitField(self.num_pieces)
        self.pieces = []
        self.piece_hashes = []
        self.info_hash = None
        self.initialize_pieces()

    def initialize_pieces(self):
        """Calculate piece hashes and initialize bitfield"""
        with open(self.file_path, 'rb') as f:
            for piece_index in range(self.num_pieces):
                piece_size = calculate_piece_size(
                    self.file_size, piece_index, self.num_pieces)
                piece_data = f.read(piece_size)
                piece_hash = sha1_hash(piece_data)
                self.piece_hashes.append(piece_hash)
                self.bitfield.set_piece(piece_index)

        # Calculate info hash from piece hashes
        info_string = json.dumps({
            'file_name': self.file_name,
            'file_size': self.file_size,
            'piece_hashes': self.piece_hashes
        }).encode()
        self.info_hash = sha1_hash(info_string)

    def get_piece(self, piece_index, offset=0, length=None):
        """Read a specific piece from the file"""
        if not self.bitfield.has_piece(piece_index):
            raise ValueError(f"Piece {piece_index} not available")

        piece_size = calculate_piece_size(
            self.file_size, piece_index, self.num_pieces)
        if length is None:
            length = piece_size - offset

        with open(self.file_path, 'rb') as f:
            f.seek(piece_index * PIECE_SIZE + offset)
            return f.read(length)

    def verify_piece(self, piece_index, piece_data):
        """Verify if a piece matches its hash"""
        if piece_index >= len(self.piece_hashes):
            return False
        return sha1_hash(piece_data) == self.piece_hashes[piece_index]

    def to_dict(self):
        """Convert torrent information to dictionary"""
        return {
            'info_hash': self.info_hash,
            'file_name': self.file_name,
            'file_size': self.file_size,
            'num_pieces': self.num_pieces,
            'piece_hashes': self.piece_hashes
        }