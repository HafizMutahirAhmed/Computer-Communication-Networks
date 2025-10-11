import socket
import tkinter as tk
from tkinter import simpledialog, scrolledtext
from client_handler import MessageHandler
from datetime import datetime


class ChatGUI:
    def __init__(self, host='127.0.0.1', port=5557):
        # ---------- Ask username ----------
        root = tk.Tk()
        root.withdraw()  # Hide main window temporarily
        self.username = simpledialog.askstring("Username", "Enter your username:", parent=root)
        if not self.username:
            self.username = "Anonymous"
        root.destroy()

        # ---------- Window Setup ----------
        self.window = tk.Tk()
        self.window.title(f"💬 Chat Application - {self.username}")
        self.window.geometry("750x650")
        self.window.configure(bg="#8FC1A9")
        self.window.resizable(False, False)

        # ---------- Chat Area ----------
        self.chat_area = scrolledtext.ScrolledText(
            self.window, wrap=tk.WORD, state='disabled',
            bg="#E8F5E9", fg="#2C3E50", font=("Segoe UI", 12)
        )
        self.chat_area.pack(fill=tk.BOTH, expand=True, padx=15, pady=(10, 5))

        # ---------- Entry ----------
        self.entry_frame = tk.Frame(self.window, bg="#8FC1A9")
        self.entry_frame.pack(fill=tk.X, pady=10, padx=15)
        self.msg_entry = tk.Entry(self.entry_frame, font=("Segoe UI", 13), bg="#E8F5E9")
        self.msg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), ipady=8)
        tk.Button(self.entry_frame, text="Send ➤", command=self.send_message,
                  bg="#4E7E5A", fg="white", font=("Segoe UI", 12, "bold")).pack(side=tk.RIGHT)

        # ---------- Connect to Server ----------
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((host, port))

        # Send username to server
        self.client_socket.send(self.username.encode('utf-8'))

        # ---------- Message Handler ----------
        self.handler = MessageHandler(self.client_socket, gui_callback=self.display_message)

        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---------- Display message ----------
    def display_message(self, message):
        self.chat_area.configure(state='normal')
        timestamp = datetime.now().strftime("%H:%M")
        self.chat_area.insert(tk.END, f"[{timestamp}] {message}\n")
        self.chat_area.configure(state='disabled')
        self.chat_area.see(tk.END)

    # ---------- Send message ----------
    def send_message(self):
        message = self.msg_entry.get().strip()
        if message:
            # Send to server
            self.handler.send_message(message)
            
            # Display locally in chat area
            timestamp = datetime.now().strftime("%H:%M")
            self.display_message(f"[You] ({self.handler.client_socket.getsockname()[0]}:{self.handler.client_socket.getsockname()[1]}): {message}")
            
            self.msg_entry.delete(0, tk.END)


    # ---------- Close ----------
    def on_close(self):
        self.handler.stop()
        self.client_socket.close()
        self.window.destroy()

    def run(self):
        self.window.mainloop()


if __name__ == "__main__":
    app = ChatGUI()
    app.run()
