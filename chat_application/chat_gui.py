import socket
import tkinter as tk
from tkinter import simpledialog, scrolledtext, messagebox
from client_handler import MessageHandler
from datetime import datetime
from voice_call_handler import VoiceCallHandler


class ChatGUI:
    def __init__(self, host='127.0.0.1', port=5557):
        # ---------- Username ----------
        root = tk.Tk()
        root.withdraw()
        self.username = simpledialog.askstring("Login", "Enter your username:")
        self.voice_handler = VoiceCallHandler(self.username)
        if not self.username:
            self.username = "Anonymous"
        root.destroy()

        # ---------- Main Window ----------
        self.window = tk.Tk()
        self.window.title(f"💬 Chat - {self.username}")
        self.window.geometry("1100x750")
        self.window.configure(bg="#e3f2e1")  # soft green-gray

        # ---------- Chat Display ----------
        self.chat_display = scrolledtext.ScrolledText(
            self.window, state='disabled', wrap=tk.WORD,
            bg="#ffffff", fg="#1b4332", font=("Segoe UI", 13)
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Define colors for different message types
        self.chat_display.tag_config("self", foreground="#1b5e20", font=("Segoe UI", 13, "bold"))
        self.chat_display.tag_config("other", foreground="#1565c0")
        self.chat_display.tag_config("system", foreground="#555555", font=("Segoe UI", 12, "italic"))
        self.chat_display.tag_config("private", foreground="#6a1b9a")

        # ---------- Entry + Send ----------
        entry_frame = tk.Frame(self.window, bg="#e3f2e1")
        entry_frame.pack(fill=tk.X, padx=20, pady=(5, 10))

        self.msg_entry = tk.Entry(entry_frame, font=("Segoe UI", 13), bg="#f0f0f0", fg="#1b4332")
        self.msg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), ipady=8)
        self.msg_entry.bind("<Return>", lambda e: self.send_message())

        send_btn = tk.Button(entry_frame, text="Send ➤", command=self.send_message,
                             bg="#2e7d32", fg="white", activebackground="#4caf50",
                             activeforeground="white", font=("Segoe UI", 12, "bold"),
                             width=12, height=1, relief="flat")
        send_btn.pack(side=tk.RIGHT)

        # ---------- Control Buttons ----------
        btn_frame = tk.Frame(self.window, bg="#c8e6c9")
        btn_frame.pack(fill=tk.X, pady=(0, 15), padx=20)

        self.btn_list = tk.Button(
            btn_frame, text="👥 Online Users", command=self.request_user_list,
            bg="#2e7d32", fg="white", font=("Segoe UI", 12, "bold"),
            relief="flat", width=20, height=2, activebackground="#388e3c", activeforeground="white"
        )
        self.btn_list.pack(side=tk.LEFT, expand=True, padx=10)

        self.btn_pm = tk.Button(
            btn_frame, text="📩 Private Message", command=self.send_private_message,
            bg="#2e7d32", fg="white", font=("Segoe UI", 12, "bold"),
            relief="flat", width=20, height=2, activebackground="#388e3c", activeforeground="white"
        )
        self.btn_pm.pack(side=tk.LEFT, expand=True, padx=10)
        

        self.btn_call = tk.Button(
    btn_frame, text="📞 Voice Call", command=self.start_voice_call,
    bg="#2e7d32", fg="white", font=("Segoe UI", 12, "bold"),
    relief="flat", width=20, height=2, activebackground="#388e3c", activeforeground="white"
)
        self.btn_call.pack(side=tk.LEFT, expand=True, padx=10)



        


        self.btn_quit = tk.Button(
            btn_frame, text="❌ Quit", command=self.on_close,
            bg="#c62828", fg="white", font=("Segoe UI", 12, "bold"),
            relief="flat", width=12, height=2, activebackground="#e53935", activeforeground="white"
        )
        self.btn_quit.pack(side=tk.RIGHT, expand=True, padx=10)

        # ---------- Connect to Server ----------
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((host, port))
            self.client_socket.send(self.username.encode('utf-8'))
        except Exception as e:
            messagebox.showerror("Connection Error", f"Could not connect to server:\n{e}")
            self.window.destroy()
            return

        # ---------- Message Handler ----------
        self.handler = MessageHandler(self.client_socket, gui_callback=self.display_message)

        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

        # Initial connection message
        self.display_message(f"[SYSTEM] Connected to {host}:{port} as {self.username}", tag="system")

    # ---------- Display Messages ----------
    def display_message(self, message, tag="other"):
        self.chat_display.configure(state='normal')
        timestamp = datetime.now().strftime("%H:%M")

        # Auto-tag messages
        if message.startswith("[SYSTEM]"):
            tag = "system"
        elif message.startswith("[PRIVATE]"):
            tag = "private"
        elif message.startswith("[You]"):
            tag = "self"

        self.chat_display.insert(tk.END, f"[{timestamp}] {message}\n", tag)
        self.chat_display.configure(state='disabled')
        self.chat_display.yview(tk.END)

    # ---------- Send Normal Message ----------
    def send_message(self):
        msg = self.msg_entry.get().strip()
        if not msg:
            return
        self.handler.send_message(msg)
        self.display_message(f"[You]: {msg}", tag="self")
        self.msg_entry.delete(0, tk.END)

    def start_voice_call(self):
        target = simpledialog.askstring("Voice Call", "Enter username to call:")
        if not target:
            return
        # Send call request command to server
        self.handler.send_message(f"/call {target}")

    # ---------- Send Private Message ----------
    def send_private_message(self):
        recipient = simpledialog.askstring("Private Message", "Recipient username:")
        if not recipient:
            return
        pm = simpledialog.askstring("Private Message", f"Message to {recipient}:")
        if not pm:
            return
        self.handler.send_message(f"/pm {recipient} {pm}")
        self.display_message(f"[You → {recipient}] {pm}", tag="private")

    # ---------- Request User List ----------
    def request_user_list(self):
        self.handler.send_message("/list")

    # ---------- Quit ----------
    def on_close(self):
        try:
            self.handler.send_message("/quit")
            self.handler.stop()
            self.client_socket.close()
        except:
            pass
        self.window.destroy()

    # ---------- Run ----------
    def run(self):
        self.window.mainloop()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1", help="Server host (use LAN/public IP for demo)")
    parser.add_argument("--port", type=int, default=5557, help="Server port")
    args = parser.parse_args()

    app = ChatGUI(host=args.host, port=args.port)
    app.run()
