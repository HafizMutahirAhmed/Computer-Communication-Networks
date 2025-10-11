import socket
import threading
from message_handler import handle_client
from logger_utility import Logger

logger = Logger()

class Server:
    def __init__(self, host='127.0.0.1', port=5557):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = {}  # key: socket, value: username

    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        logger.log_event(f"[SERVER STARTED] Listening on {self.host}:{self.port}")

        while True:
            try:
                conn, addr = self.server_socket.accept()
                # First message from client is the username
                username = conn.recv(1024).decode('utf-8')
                self.clients[conn] = username
                logger.log_event(f"[NEW CONNECTION] {username} ({addr})")

                thread = threading.Thread(
                    target=handle_client,
                    args=(conn, addr, self.clients)
                )
                thread.start()
            except Exception as e:
                logger.log_event(f"[ERROR] {e}")

    def stop(self):
        logger.log_event("[STOPPING SERVER...]")
        for conn in self.clients.keys():
            conn.close()
        self.server_socket.close()
        logger.log_event("[SERVER STOPPED]")


if __name__ == "__main__":
    chat_server = Server()
    try:
        chat_server.start()
    except KeyboardInterrupt:
        chat_server.stop()
