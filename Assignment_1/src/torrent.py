from parameter import *
from helper import *

class Torrent:
    def __init__(self, file_path):
        if not os.path.exists(file_path):
            messagebox.showerror("Error", "File does not exist")
            return
        self.file_path = file_path
        self.file_name = os.path.basename(file_path)
        self.file_size = os.path.getsize(file_path)
        self.num_pieces = (self.file_size + PIECE_SIZE - 1) // PIECE_SIZE
        self.bitfield = '0' * self.num_pieces
        self.pieces = self.split_file_into_pieces()
        self.info_hash = self.calculate_file_hash()
    
    def set_file_path(self, file_path):
        self.file_path = file_path
    def set_all_piceces(self):
        for i in range(self.num_pieces):
            self.set_piece(i)
            
    def set_piece(self, piece_index):
        """Mark a piece as complete in the bitfield"""
        self.bitfield = self.bitfield[:piece_index] + '1' + self.bitfield[piece_index + 1:]

    def has_piece(self, piece_index):
        """Check if we have a specific piece"""
        return self.bitfield[piece_index] == '1'
    
    def split_file_into_pieces(self):
        """Split file into pieces and calculate hash for each piece"""
        pieces = []
        with open(self.file_path, 'rb') as f:
            while True:
                piece = f.read(PIECE_SIZE)
                if not piece:
                    break
                pieces.append(sha1_hash(piece))
        return pieces

    def calculate_file_hash(self):
        """Calculate a unique hash for the entire file"""
        sha1 = hashlib.sha1()
        with open(self.file_path, 'rb') as f:
            while True:
                data = f.read(8192)
                if not data:
                    break
                sha1.update(data)
        return sha1.hexdigest()
    
    def print_torrent(self):
        print(f"File Name: {self.file_name}")
        print(f"File Size: {self.file_size} bytes")
        print(f"Info Hash: {self.info_hash}")
        print(f"Number of Pieces: {len(self.pieces)}")
        print(f"Bitfield: {self.bitfield}")
    
    # def equals(self, other_torrent):
    #     """Compare if two torrents are the same file"""
    #     if not isinstance(other_torrent, Torrent):
    #         return False
        
    #     # Compare file size first (quick check)
    #     if self.file_size != other_torrent.file_size:
    #         return False
            
    #     # Compare file hash
    #     if self.file_hash != other_torrent.file_hash:
    #         return False
            
    #     # Compare pieces for extra verification
    #     if self.pieces != other_torrent.pieces:
    #         return False
            
    #     return True


