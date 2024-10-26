import tkinter as tk
from tkinter import messagebox

# # Hàm hiển thị hộp thoại lỗi
# def show_error():
#     messagebox.showinfo("Error", "Đã xảy ra lỗi!")

# # Tạo cửa sổ Tkinter
# root = tk.Tk()

# # Tạo một button và gắn hàm show_error vào command
# button = tk.Button(root, text="Nhấn để hiện lỗi", command=show_error)
# button.pack(pady=20)

# # Khởi chạy ứng dụng Tkinter
# root.mainloop()

import socket
import threading

hostname = socket.gethostname()
local_IP = socket.gethostbyname(hostname)

print('Hostname:', hostname) # TABLET-GA927AEQ
print('Local IP:', local_IP) # 192.168.1.163

HOST = local_IP

class TCPserver(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.HOST = HOST
        self.PORT = 3000
        self.server_socket = None
        self.running = 1
    
    def run(self):
        while 1:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.bind((self.HOST, self.PORT))
            self.server_socket.listen()
            self.conn, self.addr = self.server_socket.accept()
            msg = self.conn.recv(1024).decode()
            print(msg)
            if msg == b'':
                self.running = 0

if __name__ == '__main__':
    tcpThread = TCPserver()
    tcpThread.start()
    if tcpThread.running == 0:
        tcpThread.join()
