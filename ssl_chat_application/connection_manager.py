import socket
import threading
import ssl
from message_handler import handle_client
from logger_utility import Logger

logger = Logger()

class Server:
    def __init__(self, host='127.0.0.1', port=5557):
        """
        Secure Chat Server using TLS Encryption.
        """
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # SSL context setup
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.context.load_cert_chain(certfile="server.crt", keyfile="server.key")

        self.clients = {}  # key: socket, value: username
        self.clients_lock = threading.Lock()

    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        logger.log_event(f"[SECURE SERVER STARTED] Listening on {self.host}:{self.port}")

        while True:
            try:
                conn, addr = self.server_socket.accept()

                # Wrap socket for SSL
                secure_conn = self.context.wrap_socket(conn, server_side=True)
                logger.log_event(f"[SECURE CONNECTION] TLS handshake successful with {addr}")

                # First message from client is username
                username = secure_conn.recv(1024).decode('utf-8').strip()
                if not username:
                    secure_conn.close()
                    continue

                with self.clients_lock:
                    # Avoid duplicate usernames
                    existing_usernames = set(self.clients.values())
                    original_name = username
                    i = 1
                    while username in existing_usernames:
                        username = f"{original_name}_{i}"
                        i += 1
                    self.clients[secure_conn] = username

                logger.log_event(f"[NEW CONNECTION] {username} ({addr})")

                # Start thread for this client
                thread = threading.Thread(
                    target=handle_client,
                    args=(secure_conn, addr, self.clients, self.clients_lock)
                )
                thread.daemon = True
                thread.start()

            except Exception as e:
                logger.log_event(f"[ERROR] {e}")

    def stop(self):
        logger.log_event("[STOPPING SERVER...]")
        with self.clients_lock:
            for conn in list(self.clients.keys()):
                try:
                    conn.close()
                except:
                    pass
            self.clients.clear()
        try:
            self.server_socket.close()
        except:
            pass
        logger.log_event("[SERVER STOPPED]")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind (use 0.0.0.0 for public)")
    parser.add_argument("--port", type=int, default=5557)
    args = parser.parse_args()

    chat_server = Server(host=args.host, port=args.port)
    try:
        chat_server.start()
    except KeyboardInterrupt:
        chat_server.stop()
