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

        # Buttons frame
        buttons_frame = ttk.Frame(self.file_operations_frame)
        buttons_frame.grid(row=1, column=0, columnspan=2, pady=10)

        # Publish button
        self.publish_button = ttk.Button(
            buttons_frame, text="Publish File", command=self.publish_file)
        self.publish_button.grid(row=0, column=0, padx=10)

        # Fetch button
        self.fetch_button = ttk.Button(
            buttons_frame, text="Fetch File", command=self.fetch_file)
        self.fetch_button.grid(row=0, column=1, padx=10)

        # Create two frames for file lists
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
            right_files_frame, height=10, width=30)
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

    def publish_file(self):
        file_path = tk.filedialog.askopenfilename()
        if file_path:
            self.peer.publish_file(file_path)

    def fetch_file(self):
        selected = self.available_files_listbox.curselection()
        if selected:
            index = selected[0]
            self.peer.fetch_file(index)
        else:
            messagebox.showwarning("Warning", "Please select a file to fetch")

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