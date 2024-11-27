import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from peer import Peer

class PeerUI:
    def __init__(self, peer):
        self.peer = peer
        self.root = tk.Tk()
        self.root.title("P2P File Sharing")
        self.root.geometry("600x400")
        self.setup_ui()

    def setup_ui(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill='both')

        self.login_frame = ttk.Frame(self.notebook)
        self.files_frame = ttk.Frame(self.notebook)

        self.notebook.add(self.login_frame, text='Login')
        self.notebook.add(self.files_frame, text='Files')

        self.setup_login_frame()
        self.setup_files_frame()

    def setup_login_frame(self):
        ttk.Label(self.login_frame, text="Username:").grid(row=0, column=0, padx=5, pady=5)
        self.username_entry = ttk.Entry(self.login_frame)
        self.username_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(self.login_frame, text="Password:").grid(row=1, column=0, padx=5, pady=5)
        self.password_entry = ttk.Entry(self.login_frame, show="*")
        self.password_entry.grid(row=1, column=1, padx=5, pady=5)

        ttk.Button(self.login_frame, text="Login", command=self.login).grid(row=2, column=0, padx=5, pady=5)
        ttk.Button(self.login_frame, text="Register", command=self.register).grid(row=2, column=1, padx=5, pady=5)

    def setup_files_frame(self):
        self.files_tree = ttk.Treeview(self.files_frame, columns=('Size', 'Status'), show='headings')
        self.files_tree.heading('Size', text='Size')
        self.files_tree.heading('Status', text='Status')
        self.files_tree.pack(expand=True, fill='both')

        button_frame = ttk.Frame(self.files_frame)
        button_frame.pack(fill='x')

        ttk.Button(button_frame, text="Refresh", command=self.refresh_files).pack(side='left', padx=5, pady=5)
        ttk.Button(button_frame, text="Publish", command=self.publish_file).pack(side='left', padx=5, pady=5)
        ttk.Button(button_frame, text="Download", command=self.download_file).pack(side='left', padx=5, pady=5)

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        if self.peer.login(username, password):
            messagebox.showinfo("Success", "Logged in successfully")
            self.notebook.select(1)  # Switch to Files tab
            self.refresh_files()
        else:
            messagebox.showerror("Error", "Login failed")

    def register(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        if self.peer.register(username, password):
            messagebox.showinfo("Success", "Registered successfully")
        else:
            messagebox.showerror("Error", "Registration failed")

    def refresh_files(self):
        self.files_tree.delete(*self.files_tree.get_children())
        files = self.peer.get_available_files()
        for file in files:
            self.files_tree.insert('', 'end', values=(file['filename'], f"{file['size']} bytes", "Available"))

    def publish_file(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            if self.peer.publish_file(file_path):
                messagebox.showinfo("Success", f"Published {file_path}")
                self.refresh_files()
            else:
                messagebox.showerror("Error", "Failed to publish file")

    def download_file(self):
        selected_item = self.files_tree.selection()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select a file to download")
            return
        file_index = self.files_tree.index(selected_item[0])
        if self.peer.start_download(file_index):
            messagebox.showinfo("Success", "Download started")
        else:
            messagebox.showerror("Error", "Failed to start download")

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    port = int(input("Enter port number: "))
    peer = Peer("localhost", port=port)  # Example IP and port
    peer.connect_to_tracker("localhost", 5050)  # Example tracker IP and port
    ui = PeerUI(peer)
    ui.run()