from parameter import *


class PeerUI:
    def __init__(self, peer):
        self.peer = peer

        # Create the main window
        self.root = tk.Tk()
        self.root.title("P2P File Sharing")
        self.root.geometry("450x450")

        self.root.protocol("WM_DELETE_WINDOW", self.exit_application)
        self.setup_ui()

    def setup_ui(self):
        self.main_frame = ttk.Frame(self.root, padding="20")
        self.main_frame.grid(
            row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Create frames for different screens
        self.create_login_frame()
        self.create_register_frame()
        self.create_menu_frame()
        self.create_file_operations_frame()

        # Start with main menu
        self.show_menu_frame()

    def create_login_frame(self):
        self.login_frame = ttk.Frame(self.main_frame)
        ttk.Label(self.login_frame, text="Username:").grid(
            row=0, column=0, pady=5)
        self.login_username = ttk.Entry(self.login_frame)
        self.login_username.grid(row=0, column=1, pady=5)

        ttk.Label(self.login_frame, text="Password:").grid(
            row=1, column=0, pady=5)
        self.login_password = ttk.Entry(self.login_frame, show="*")
        self.login_password.grid(row=1, column=1, pady=5)

        ttk.Button(self.login_frame, text="Login", command=self.peer.handle_login).grid(
            row=2, column=0, columnspan=2, pady=10)
        ttk.Button(self.login_frame, text="Back", command=self.show_menu_frame).grid(
            row=3, column=0, columnspan=2)

    def create_register_frame(self):
        self.register_frame = ttk.Frame(self.main_frame)
        ttk.Label(self.register_frame, text="Username:").grid(
            row=0, column=0, pady=5)
        self.register_username = ttk.Entry(self.register_frame)
        self.register_username.grid(row=0, column=1, pady=5)

        ttk.Label(self.register_frame, text="Password:").grid(
            row=1, column=0, pady=5)
        self.register_password = ttk.Entry(self.register_frame, show="*")
        self.register_password.grid(row=1, column=1, pady=5)

        ttk.Label(self.register_frame, text="Confirm Password:").grid(
            row=2, column=0, pady=5)
        self.register_confirm = ttk.Entry(self.register_frame, show="*")
        self.register_confirm.grid(row=2, column=1, pady=5)

        ttk.Button(self.register_frame, text="Register", command=self.peer.handle_register).grid(
            row=3, column=0, columnspan=2, pady=10)
        ttk.Button(self.register_frame, text="Back", command=self.show_menu_frame).grid(
            row=4, column=0, columnspan=2)

    def create_menu_frame(self):
        self.menu_frame = ttk.Frame(self.main_frame)
        ttk.Button(self.menu_frame, text="Login", command=self.show_login_frame).grid(
            row=0, column=0, pady=10, padx=20)
        ttk.Button(self.menu_frame, text="Register", command=self.show_register_frame).grid(
            row=1, column=0, pady=10, padx=20)
        ttk.Button(self.menu_frame, text="Exit", command=self.exit_application).grid(
            row=2, column=0, pady=10, padx=20)

    def create_file_operations_frame(self):
        self.file_operations_frame = ttk.Frame(self.main_frame)

        # Welcome message
        self.welcome_label = ttk.Label(
            self.file_operations_frame, text="Welcome!", font=('Helvetica', 12, 'bold'))
        self.welcome_label.grid(row=0, column=0, columnspan=2, pady=20)

        # Buttons frame (Publish and Fetch in a single row)
        buttons_frame = ttk.Frame(self.file_operations_frame)
        buttons_frame.grid(row=1, column=0, columnspan=2, pady=10)

        # Publish single file button
        self.publish_file_button = ttk.Button(
            buttons_frame, text="Publish Select File", command=self.publish_file)
        self.publish_file_button.grid(row=0, column=0, padx=10)

        # Publish folder button
        self.publish_folder_button = ttk.Button(
            buttons_frame, text="Publish Whole Folder", command=self.publish_folder)
        self.publish_folder_button.grid(row=0, column=1, padx=10)


        # Fetch multiple files button
        self.fetch_multiple_files_button = ttk.Button(
            buttons_frame, text="Fetch Selected Files", command=self.download_selected_files)
        self.fetch_multiple_files_button.grid(row=0, column=2, padx=10)

        # Create frames for file lists
        left_files_frame = ttk.LabelFrame(
            self.file_operations_frame, text="All Published Files")
        left_files_frame.grid(row=2, column=0, padx=5,
                            pady=(20, 5), sticky='nsew')

        right_files_frame = ttk.LabelFrame(
            self.file_operations_frame, text="Available Files")
        right_files_frame.grid(row=2, column=1, padx=5,
                            pady=(20, 5), sticky='nsew')

        # Reload button
        ttk.Button(self.file_operations_frame, text="🔄 Reload", command=self.reload_files).grid(
            row=3, column=0, columnspan=2, pady=5)

        # Left listbox (Published files)
        self.published_files_listbox = tk.Listbox(
            left_files_frame, height=10, width=30)
        self.published_files_listbox.pack(
            side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Left scrollbar
        left_scrollbar = ttk.Scrollbar(
            left_files_frame, orient=tk.VERTICAL, command=self.published_files_listbox.yview)
        left_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.published_files_listbox.configure(
            yscrollcommand=left_scrollbar.set)

        # Right listbox (Available files)
        self.available_files_listbox = tk.Listbox(
            right_files_frame, height=10, width=30, selectmode=tk.MULTIPLE)
        self.available_files_listbox.pack(
            side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Right scrollbar
        right_scrollbar = ttk.Scrollbar(
            right_files_frame, orient=tk.VERTICAL, command=self.available_files_listbox.yview)
        right_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.available_files_listbox.configure(
            yscrollcommand=right_scrollbar.set)

    # Logout button at bottom
        ttk.Button(self.file_operations_frame, text="Exit", command=self.exit_application).grid(
        row=4, column=0, columnspan=2, pady=20)
        
    def load_published_files(self):
        """Load published files from the user's repository folder."""
        repo_path = os.path.join(f"repo_{self.peer.username}")
        published_files = []
        
        if os.path.exists(repo_path):
            for root, _, files in os.walk(repo_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_name = os.path.basename(file_path)
                    if (file_name != 'peer_activity.log'):
                        file_size = os.path.getsize(file_path)  # Get the file size
                        published_files.append({"filename": file, "size": file_size})
        
        return published_files

    def update_published_files_list(self, published_files):
        """Update the 'Published Files' listbox with the user's local repository files."""
        self.published_files_listbox.delete(0, tk.END)  # Clear the current list
        
        for file in published_files:
            size_kb = file['size'] / 1024  # Convert size to KB
            file_entry = f"{file['filename']} ({size_kb:.2f} KB)"
            self.published_files_listbox.insert(tk.END, file_entry)

    def reload_files(self):
        """Reload the available files list"""
        self.peer.get_available_files()

    def show_login_frame(self):
        self.menu_frame.grid_remove()
        self.register_frame.grid_remove()
        self.login_frame.grid(row=0, column=0)

    def show_register_frame(self):
        self.menu_frame.grid_remove()
        self.login_frame.grid_remove()
        self.register_frame.grid(row=0, column=0)

    def show_menu_frame(self):
        self.login_frame.grid_remove()
        self.register_frame.grid_remove()
        self.file_operations_frame.grid_remove()
        self.menu_frame.grid(row=0, column=0)

    def exit_application(self):
        self.peer.handle_logout()
        if self.peer.peer_socket:
            self.peer.peer_socket.close()
        self.root.quit()

    def run(self):
        self.peer.connect_to_tracker()
        self.root.mainloop()
        
    def publish_folder(self):
        """Handle folder upload."""
        folder_path = filedialog.askdirectory()
        if folder_path:
            for root, _, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    self.peer.publish_file(file_path)
            messagebox.showinfo("Success", f"Published all files in {folder_path}.")
            
    def publish_file(self):
        file_paths = tk.filedialog.askopenfilenames()
        if file_paths:
            for file_path in file_paths:
                self.peer.publish_file(file_path)
                 # Store the file in the user's repository
                repo_path = os.path.join(f"repo_{self.peer.username}", os.path.basename(file_path))
                if os.path.exists(repo_path):
                    continue  # Skip if file already exists
                shutil.copy(file_path, repo_path) 
            messagebox.showinfo("Success", f"Published {len(file_paths)} file(s).")

    def fetch_file(self):
        selected = self.available_files_listbox.curselection()
        if selected:
            index = selected[0]
            self.peer.fetch_file(index)
        else:
            messagebox.showwarning("Warning", "Please select a file to fetch")
            
    def download_selected_files(self):
        selected_indices = self.available_files_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Warning", "Please select files to download")
            return

        # Get the selected files
        # selected_files = [self.available_files_listbox.get(i) for i in selected_indices]
        # print(selected_indices)
        # Start a thread for each file download
        # print(selected_indices)
        for index in selected_indices:
            # print(index)
            # print(self.peer.available_files[index])
            self.peer.fetch_file(index)
            # fetch_file_thread = threading.Thread(target=self.peer.fetch_file, args=(index,))
            # fetch_file_thread.daemon = True
            # fetch_file_thread.start()
        
            

    # def logout(self):
    #     self.peer.handle_logout()
    #     self.show_menu_frame()
    #     self.welcome_label.config(text="Welcome!")
    #     self.files_listbox.delete(0, tk.END)

    def show_file_operations_frame(self, username):
        self.login_frame.grid_remove()
        self.register_frame.grid_remove()
        self.menu_frame.grid_remove()
        self.file_operations_frame.grid(row=0, column=0)
        self.welcome_label.config(text=f"Welcome, {username}!")
        
        # # Load and display files from the user's repository
        # published_files = self.load_published_files()
        # self.update_published_files_list(published_files)
        
        
        self.peer.get_available_files()  # Get file list when showing frame

    def update_files_list(self, published_files, available_files):
        """Update both listboxes with available files"""
        self.published_files_listbox.delete(0, tk.END)  # Clear current lists
        self.available_files_listbox.delete(0, tk.END)
    
        for file in published_files:
            size_mb = file['size'] / 1024  # Convert to MB
            file_entry = f"{file['filename']} ({size_mb:.2f} KB)"
            self.published_files_listbox.insert(tk.END, file_entry)

        for file in available_files:
            size_mb = file['size'] / 1024  # Convert to MB
            file_entry = f"{file['filename']} ({size_mb:.2f} KB)"
            self.available_files_listbox.insert(tk.END, file_entry)
