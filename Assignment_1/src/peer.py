from parameter import *
from helper import *
from peer_UI import *
from torrent import *

class Peer:
    def __init__(self, ip, port):
        self.ip = ip
        self.tracker_port = port  # Port for connecting to tracker
        self.listen_port = None   # Port for listening to peer connections
        self.peer_socket = None   # Socket for tracker connection
        self.listen_socket = None # Socket for peer connections
        self.peer_id = None
        self.username = None
        self.torrents = {} # info_hash -> Torrent
        self.available_files = []
        self.ui = PeerUI(self)
        self.downloading_pieces = {} # info_hash -> {piece_index: piece_data}
        self._shutdown = False
        self.logging_initialized = False
        
    # def select_peers_for_upload(self, num_slots=4, forgiveness_rate=0.1):
    #     """Select peers to upload to based on tit-for-tat strategy."""
    #     # Sort peers by their received contributions (descending order)
    #     ranked_peers = sorted(self.peer_scores.items(), 
    #                         key=lambda x: x[1]['received'], 
    #                         reverse=True)
        
    #     # Select top peers for uploading
    #     selected_peers = [peer_id for peer_id, _ in ranked_peers[:num_slots]]

    # # Add occasional forgiveness
    #     if random.random() < forgiveness_rate:
    #         all_peers = list(self.peer_scores.keys())
    #         unselected_peers = [p for p in all_peers if p not in selected_peers]
    #         if unselected_peers:
    #             selected_peers.append(random.choice(unselected_peers))
        
    #     return selected_peers

    # def update_peer_scores(self, peer_id, sent=0, received=0):
    #     if peer_id not in self.peer_scores:
    #         self.peer_scores[peer_id] = {'sent': 0, 'received': 0}
    #     self.peer_scores[peer_id]['sent'] += sent
    #     self.peer_scores[peer_id]['received'] += received
    #     self.save_peer_scores()

    # def load_peer_scores(self):
    #        if os.path.exists('repo_'+str(self.username)+'/peer_scores.json'):
    #            with open('repo_'+str(self.username)+'/peer_scores.json', 'r') as f:
    #                return json.load(f)
    #        return {}  

    # def save_peer_scores(self):
    #        with open('repo_'+str(self.username)+'/peer_scores.json', 'w') as f:
    #            json.dump(self.peer_scores, f) 
    
    def handle_login(self):
        try:
            # Find an available port for listening
            if not self.listen_port:
                self.listen_port = generate_port()
            send_msg(self.peer_socket, {'type': HANDSHAKE, 'port': self.listen_port})
            response = pickle.loads(recv_msg(self.peer_socket))
            message = {
                'type': LOGIN,
                'username': self.ui.login_username.get(),
                'password': self.ui.login_password.get(),
                'ip': self.ip,
                'port': self.listen_port  # Use listen_port instead of tracker_port
            }
            send_msg(self.peer_socket, message)
            response = pickle.loads(recv_msg(self.peer_socket))

            if response['type'] == LOGIN_SUCCESS:
                self.peer_id = response['peer_id']
                self.username = self.ui.login_username.get()
                logging.basicConfig(
                        filename='repo_'+str(self.username)+'/peer_activity.log',
                        level=logging.INFO,
                        format='%(asctime)s - %(message)s',
                        filemode='a'
                )
                self.logging_initialized = True
                logging.info(f'Connected with tracker server at localhost:{self.tracker_port}')
                logging.info('Peer activity log started')
                logging.info(f"Peer initialized with IP: {self.ip} and Port: {self.listen_port}")
                # updated published file
                repo_path = os.path.join(f"repo_{self.username}")
                if os.path.exists(repo_path):
                    for root, _, files in os.walk(repo_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            file_name = os.path.basename(file_path)
                            if file_name != 'peer_activity.log' and file_name != 'peer_scores.json':
                                torrent = Torrent(file_path)
                                torrent.set_all_piceces() # set all pieces to 1
                                self.torrents[torrent.info_hash] = torrent
                            
                messagebox.showinfo("Success", response['message'])
                # Start peer server before showing file operations
                self.peer_server()
                self.ui.show_file_operations_frame(self.username)
            else:
                messagebox.showerror("Error", response['message'])
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def handle_register(self):
        if self.ui.register_password.get() != self.ui.register_confirm.get():
            messagebox.showerror("Error", "Passwords do not match!")
            return

        try:
            # self.connect_to_tracker()
            message = {
                'type': REGISTER,
                'username': self.ui.register_username.get(),
                'password': self.ui.register_password.get(),
                'ip': self.ip,
                'port': self.listen_port  # Use listen_port instead of tracker_port
            }
            send_msg(self.peer_socket, message)
            response = pickle.loads(recv_msg(self.peer_socket))

            if response['type'] == REGISTER_SUCCESS:
                if not os.path.exists(f"repo_{self.ui.register_username.get()}"):
                    os.makedirs(f"repo_{self.ui.register_username.get()}")
                    # with open(f"repo_{self.ui.register_username.get()}/peer_activity.log", 'w') as log_file:
                    #     log_file.write("")
                    # with open(f"repo_{self.ui.register_username.get()}/peer_scores.json", 'w') as score_file:
                    #     score_file.write("{}")
                messagebox.showinfo("Success", response['message'])
                self.ui.show_login_frame()
            else:
                messagebox.showerror("Error", response['message'])
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def handle_logout(self):
        try:
            # self.connect_to_tracker()
            message = {
                'type': LOGOUT,
                'peer_id': self.peer_id
            }
            send_msg(self.peer_socket, message)
            response = pickle.loads(recv_msg(self.peer_socket))
            if response['type'] == LOGOUT_SUCCESS:
                logging.info('Peer activity log ended')
                messagebox.showinfo("Success", response['message'])
            else:
                messagebox.showerror("Error", response['message'])
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def connect_to_tracker(self, SERVER='localhost', PORT=5050):
        """Connect to tracker server"""
        if not self.peer_socket:
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    self.peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.peer_socket.connect((SERVER, PORT))
                    return
                except Exception as e:
                    if attempt < max_retries - 1:
                        time.sleep(1)
                    else:
                        raise

    def connect_to_peer(self, ip, port):
        try:
            self.peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.peer_socket.connect((ip, port))
        except Exception as e:
            print(f"Error connecting to peer {ip}:{port}: {e}")
            traceback.print_exc()

    def get_available_files(self):
        """Request list of available files from tracker"""
        try:
            message = {
                'type': GET_FILES,
                'peer_id': self.peer_id
            }
            send_msg(self.peer_socket, message)
            response = pickle.loads(recv_msg(self.peer_socket))

            if response['type'] == GET_FILES_SUCCESS:
                all_files = response['files']
                print(all_files)
                published_files = [
                    {'filename': torrent.file_name, 'size': torrent.file_size} 
                    for torrent in self.torrents.values()
                ]
                
                self.available_files = (
                    [file for file in all_files 
                     if file['info_hash'] not in [torrent.info_hash for torrent in self.torrents.values()]]
                    if all_files else []
                )
                
                self.ui.update_files_list(published_files, self.available_files)
                logging.info(f'Received list of available files from tracker: {self.available_files}')
            else:
                logging.error('Failed to get file list')
                messagebox.showerror("Error", "Failed to get file list")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def publish_file(self, file_path):
        torrent = Torrent(file_path)

        torrent.set_all_piceces() # set all pieces to 1
        self.torrents[torrent.info_hash] = torrent
        
        torrent.print_torrent()
        try:
            message = {
                'type': PUBLISH,
                'peer_id': self.peer_id,
                'info_hash': torrent.info_hash,
                'filename': torrent.file_name,
                'filesize': torrent.file_size,
                'bitfield': torrent.bitfield
            }
            send_msg(self.peer_socket, message)
            response = pickle.loads(recv_msg(self.peer_socket))
            if response['type'] == PUBLISH_SUCCESS:
                messagebox.showinfo("Success", response['message'])
                logging.info(f"Published file: {torrent.file_name}, {torrent.file_size} bytes, {torrent.info_hash}")
                repo_path = os.path.join(f"repo_{self.username}", os.path.basename(file_path))
                if not os.path.exists(repo_path):
                    shutil.copy(file_path, repo_path)
                self.torrents[torrent.info_hash].set_file_path(repo_path)
                self.get_available_files()  # Refresh file list after publishing
            else:
                messagebox.showerror("Error", response['message'])
                logging.error(f'Failed to publish file because of {response["message"]}')
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def fetch_file(self, index):
        """Client-side file download with multiple threads"""
        try:
            # Request peer list from tracker
            message = {
                'type': FETCH,
                'peer_id': self.peer_id,
                'info_hash': self.available_files[index]['info_hash']
            }
            send_msg(self.peer_socket, message)
            response = pickle.loads(recv_msg(self.peer_socket))
            
            if response['type'] == FETCH_SUCCESS:
                peers = response['peers']
                pieces_point = response['pieces_point']  # for rarest first
                if not peers:
                    logging.error('No peers available')
                    messagebox.showerror("Error", "No peers available")
                    return
                logging.info(f'Fetched peer list: {peers}')
                # Calculate pieces needed
                file_size = self.available_files[index]['size']
                num_pieces = (file_size + PIECE_SIZE - 1) // PIECE_SIZE
                logging.info(f'Initiating download file name: {self.available_files[index]["filename"]}, file size: {file_size} bytes, number of pieces: {num_pieces}')
                file_path = os.path.join(f"repo_{self.username}", self.available_files[index]["filename"])
                with open(file_path, 'wb') as f:
                    f.seek(file_size - 1)
                    f.write(b'\0')
                
                torrent = Torrent(file_path)
                torrent.file_path = file_path
                torrent.info_hash = self.available_files[index]['info_hash']
                torrent.file_name = self.available_files[index]['filename']
                torrent.file_size = self.available_files[index]['size']
                torrent.num_pieces = num_pieces
                torrent.bitfield = '0' * num_pieces
                self.torrents[torrent.info_hash] = torrent
                # # Create download manager thread
                # self.manage_download(peers, self.available_files[index], num_pieces)
                download_thread = threading.Thread(
                    target=self.manage_download,
                    args=(peers, self.available_files[index], num_pieces, pieces_point)
                )
                download_thread.daemon = True
                download_thread.start()
                
            else:
                messagebox.showerror("Error", "Failed to fetch peer list")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error initiating download: {str(e)}")

    def manage_download(self, peers, file_info, num_pieces, pieces_point):
        """Manage the download process using multiple threads"""
        try:
            pieces = {}
            download_threads = []
            info_hash = file_info['info_hash']
            
            # Create threads for each piece-peer assignment
            logging.info(f'Piece available: {peers}')
            piece_lock = threading.Lock()
            downloaded_pieces = set()
            piece_rarity = {}
            for piece_index in range(num_pieces):
                piece_rarity[piece_index] = pieces_point[piece_index]
            pieces_rarity = sorted(piece_rarity.items(), key=lambda x: x[1])
            
            # Group pieces by rarity
            grouped_pieces = {rarity: [] for _, rarity in pieces_rarity}
            for piece_index, rarity in pieces_rarity:
                grouped_pieces[rarity].append(piece_index)

            # Shuffle each group
            shuffled_pieces = {}
            for rarity, indices in grouped_pieces.items():
                random.shuffle(indices)  
                for index in indices:
                    shuffled_pieces[index] = rarity 
            pieces_rarity = list(shuffled_pieces.items())
            logging.info(f'Pieces rarity: {pieces_rarity} of file {info_hash}')
            for piece_index, _ in pieces_rarity:
                if self.torrents[info_hash].has_piece(piece_index):
                    continue
                
                with piece_lock:
                    if piece_index in downloaded_pieces:
                        continue
                    downloaded_pieces.add(piece_index)
                # for peer in peers:
                peer = random.choice(peers)
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((peer[1], peer[2]))
                    send_msg(s, {'type':HANDSHAKE})
                    response = pickle.loads(recv_msg(s))
                    logging.info(f"Handshake response from {peer[1]}:{peer[2]}: {response['message']}")
                    thread = threading.Thread(
                    target=self.download_piece,
                    args=(peer[0], peer[1], peer[2], file_info['info_hash'], piece_index, pieces, piece_lock, downloaded_pieces)
                )
                download_threads.append(thread)
                thread.start()
                    
                if len(download_threads) >= len(peers) * 2:
                    for t in download_threads:
                        t.join()
                    download_threads = []
            # for peer in peers:
            #     thread = threading.Thread(
            #         target=self.download_piece,
            #         args=(peer[0], peer[1], peer[2], file_info['info_hash'], [i for i in range(num_pieces)], pieces)
            #     )
            #     download_threads.append(thread)
            #     thread.start()
                
            #     if len(download_threads) >= len(peers) * 2:
            #         for t in download_threads:
            #             t.join()
            #         download_threads = []
                
                
            for thread in download_threads:
                thread.join()
            # for peer, piece_index in piece_assignments.items():
            #     print(f"Downloading piece {piece_index} from {peer}")
            #     thread = threading.Thread(
            #         target=self.download_piece,
            #         args=(peer[0], peer[1], peer[2], file_info['info_hash'], piece_index, pieces)
            #     )
            #     download_threads.append(thread)
            #     thread.start()
                    
            #         # Limit concurrent threads
            #     if len(download_threads) >= len(peers) * 2:  # 2 threads per peer
            #         for t in download_threads:
            #             t.join()
            #         download_threads = []
                
            #     # Wait for remaining threads
            # for thread in download_threads:
            #     thread.join()
                    
                # Save the complete file
                
            # handle missing piece 
            
            retry_attemps = 3
            while retry_attemps > 0:
                missing_pieces = [i for i in range(num_pieces) if i not in pieces]
                if not missing_pieces:
                    break
                logging.info(f"Attemping: {retry_attemps}")
                logging.info(f"Missing pieces: {missing_pieces}")
                download_threads = []
                downloaded_pieces.clear()
                for piece_index in missing_pieces:
                # Try each peer for each missing piece
                    for peer in peers:
                        if piece_index in pieces:  # Skip if piece was downloaded by another thread
                            continue
                            
                        with piece_lock:
                            if piece_index in downloaded_pieces:
                                continue
                            downloaded_pieces.add(piece_index)
                        
                        thread = threading.Thread(
                            target=self.download_piece,
                            args=(peer[0], peer[1], peer[2], info_hash, piece_index, pieces, piece_lock, downloaded_pieces)
                        )
                        download_threads.append(thread)
                        thread.start()
                        
                        if len(download_threads) >= len(peers):
                            for t in download_threads:
                                t.join()
                            download_threads = []
                
                    # Wait for remaining retry threads
                for thread in download_threads:
                    thread.join()
            retry_attemps -= 1
                
            self.save_complete_file(file_info['filename'], pieces, num_pieces)
            messagebox.showinfo("Success", f"File downloaded successfully: {file_info['filename']}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Download failed: {str(e)}")

    def download_piece(self, peer_id, ip, port, info_hash, piece_index, pieces, piece_lock, downloaded_pieces):
        if self.torrents[info_hash].has_piece(piece_index):
            with piece_lock:
                downloaded_pieces.discard(piece_index)
            return
        """Download a single piece from a specific peer"""

        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Create new connection for each piece
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    
                    print(f"Connecting to {ip}:{port}")
                    s.connect((ip, port))
                    message = {
                        'type': GET_PIECE,
                        'info_hash': info_hash,
                        'piece_index': piece_index,
                        'peer_id': self.peer_id
                    }
                    logging.info(f'Requesting piece {piece_index} to {ip}:{port}')
                    send_msg(s, message)
                    response = pickle.loads(recv_msg(s))
                    
                    if response['type'] == GET_PIECE_SUCCESS:
                        # data return is dictionary with key as index piece and value as piece data
                        pieces.update(response['data']) # update pieces with the received data
                        with piece_lock:
                            if info_hash not in self.downloading_pieces:
                                self.downloading_pieces[info_hash] = {}
                            self.downloading_pieces[info_hash][piece_index] = response['data'][piece_index]
                        self.torrents[info_hash].set_piece(piece_index)
                        self.notify_tracker_for_piece_downloaded(info_hash, piece_index)
                        print(f"Successfully downloaded piece {piece_index} from {ip}:{port}")
                        logging.info(f"Successfully downloaded piece {piece_index} from peer_id {response['peer_id']} {ip}:{port}")
                        return
                    else:
                        logging.error(f"Failed to download piece {piece_index} from {ip}:{port} because of {response['message']}")
                        
            except Exception as e:
                logging.error(f"Error downloading piece {piece_index} from {ip}:{port}: {e}")
                if attempt == max_retries - 1:
                    traceback.print_exc()
                else:
                    time.sleep(1)  # Wait before retry
            finally:
                with piece_lock:
                    downloaded_pieces.discard(piece_index)
                
                
    def notify_tracker_for_piece_downloaded(self, info_hash, piece_index):
        try:
            message = {
                'type': UPDATE_PIECE_POINT,
                'peer_id': self.peer_id,
                'info_hash': info_hash,
                'piece_index': piece_index
            }
            send_msg(self.peer_socket, message)
        except:
            logging.error(f"Error updating piece point for piece {piece_index} of {info_hash}")
            traceback.print_exc()
            
    def save_complete_file(self, filename, pieces, num_pieces):
        """Reassemble and save the complete file"""
        try:
            save_path = f"repo_{self.username}/{filename}"
            with open(save_path, 'wb') as f:
                for i in range(num_pieces):
                    if i in pieces:
                        f.write(pieces[i])
                    else:
                        raise Exception(f"Missing piece {i}")
            logging.info(f'File {filename} saved successfully')
        except Exception as e:
            logging.error(f"Error saving file {filename}: {e}")
            traceback.print_exc()
            raise

    def peer_server(self):
        try:
            # Close existing listen socket if it exists
            if self.listen_socket:
                try:
                    self.listen_socket.close()
                except:
                    pass

            # Create new socket for peer connections
            self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    self.listen_socket.bind((self.ip, self.listen_port))
                    self.listen_socket.listen(4)
                    logging.info(f"Listening for peer connections on {self.ip}:{self.listen_port}")
                    
                    # Start the listening thread
                    listen_thread = threading.Thread(target=self.listen_for_connections)
                    listen_thread.daemon = True
                    listen_thread.start()
                    return
                    
                except OSError as bind_error:
                    if attempt < max_retries - 1:
                        logging.error(f"Port {self.listen_port} is in use, trying another port...")
                        self.listen_port = generate_port()  # Try a new port
                    else:
                        raise bind_error
                        
        except Exception as e:
            print(f"Error in peer_server: {e}")
            traceback.print_exc()

    def listen_for_connections(self):
        """Thread that accepts new connections"""
        while True:
            try:
                client_socket, addr = self.listen_socket.accept()
                logging.info(f"New connection from {addr}")
                # Create new thread for each client connection
                client_thread = threading.Thread(
                    target=self.handle_client_connection,
                    args=(client_socket, addr)
                )
                client_thread.daemon = True
                client_thread.start()
            except Exception as e:
                print(f"Error accepting connection: {e}")
                traceback.print_exc()

    def handle_client_connection(self, client_socket, addr):
        """Handle individual client connections"""
        logging.info(f"Handling connection from {addr}")
        try:
            while True:
                data = recv_msg(client_socket)
                if not data:
                    break
                
                request = pickle.loads(data)
                logging.info(f"Received request from {addr}: {request['type']}")
                
                if request['type'] == GET_PIECE:
                    # Create new thread for file transfer
                    transfer_thread = threading.Thread(
                        target=self.handle_piece_transfer,
                        args=(client_socket, request)
                    )
                    transfer_thread.start()
                    transfer_thread.join()  # Wait for transfer to complete
                elif request['type'] == HANDSHAKE:
                    send_msg(client_socket, {'type':HANDSHAKE, 'message': 'Handshake successful'})
                else:
                    logging.error(f"Unknown request type: {request['type']}")
                    
        except Exception as e:
            print(f"Error handling client {addr}: {e}")
            traceback.print_exc()
        finally:
            print(f"Closing connection from {addr}")
            client_socket.close()

    def handle_piece_transfer(self, client_socket, request):
        """Handle the actual file piece transfer"""
        try:
            info_hash = request['info_hash']
            piece_index = request['piece_index']
            peer_id = request['peer_id']
            piece_data = {}
            # Find the torrent
            # if len(self.peer_scores) > 5:
            #     allowed_peers = self.select_peers_for_upload()
            
            #     if peer_id not in allowed_peers:
            #         send_msg(client_socket, {
            #             'type': GET_PIECE_FAIL,
            #             'message': 'Bandwidth currently unavailable for this peer'
            #         })
            #         logging.info(f"Peer {peer_id} not allowed to download piece {piece_index} because of bandwidth limit")
            #         return
            torrent = self.torrents.get(info_hash)
            if not torrent:
                send_msg(client_socket, {
                    'type': GET_PIECE_FAIL,
                    'message': 'File not found'
                    })
                logging.info(f'Peer {peer_id} requested piece {piece_index} for unknown file {info_hash}')
                return
            
            if self.torrents[info_hash].bitfield == '1' * self.torrents[info_hash].num_pieces:
                with open(torrent.file_path, 'rb') as f:
                    f.seek(piece_index * PIECE_SIZE)
                    piece = f.read(PIECE_SIZE)
                    piece_data[piece_index] = piece
            # Read and send the requested piece
            elif self.torrents[info_hash].has_piece(piece_index):
                if piece_index in self.downloading_pieces[info_hash]:
                    piece_data[piece_index] = self.downloading_pieces[info_hash][piece_index]
                else:
                    send_msg(client_socket, {
                        'type': GET_PIECE_FAIL,
                        'message': 'Piece not available'
                    })
                    logging.info(f'Peer {peer_id} requested piece {piece_index} for file {torrent.file_path} not available')
                    return
                
            send_msg(client_socket, {
                'type': GET_PIECE_SUCCESS,
                'data': piece_data,
                'peer_id': self.peer_id
            })
            logging.info(f"Sent piece {piece_index} of {torrent.file_path} to peer {peer_id}")
        except Exception as e:
            print(f"Error in piece transfer: {e}")
            traceback.print_exc()
            send_msg(client_socket, {
                'type': GET_PIECE_FAIL,
                'message': str(e)
            })
            logging.error(f"Error sending piece {piece_index} of {torrent.file_path} to peer {peer_id}: {e}")

    def download_from_peer(self, ip, info):
        pass

    def cleanup(self):
        """Clean up resources before shutdown"""
        self._shutdown = True
        self.logging_initialized = False
        if self.peer_socket:
            try:
                self.peer_socket.close()
            except:
                pass
        if self.listen_socket:
            try:
                self.listen_socket.close()
            except:
                pass

if __name__ == '__main__':
    try:
        peer = Peer('localhost', 5050)  # Port 5050 is for tracker connection
        peer.ui.run()
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print("Closing application...")
