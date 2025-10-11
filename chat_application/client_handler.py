import threading
from datetime import datetime

class MessageHandler:
    def __init__(self, client_socket, gui_callback=None):
        """
        client_socket: connected socket to server
        gui_callback: function to update GUI when a message is received
        """
        self.client_socket = client_socket
        self.gui_callback = gui_callback
        self.running = True

        thread = threading.Thread(target=self.receive_messages)
        thread.daemon = True
        thread.start()

    def send_message(self, message):
        try:
            self.client_socket.send(message.encode('utf-8'))
        except Exception as e:
            print(f"[ERROR] Failed to send message: {e}")

    def receive_messages(self):
        while self.running:
            try:
                msg = self.client_socket.recv(1024).decode('utf-8')
                if not msg:
                    break
                if self.gui_callback:
                    self.gui_callback(msg)
            except Exception as e:
                print(f"[DISCONNECTED] {e}")
                self.running = False
                break

    def stop(self):
        self.running = False
        self.client_socket.close()
