# server.py
import socket
import threading
import ssl
from message_handler import handle_client
from logger_utility import Logger

logger = Logger()

class Server:
    def __init__(self, host='127.0.0.1', port=5557):  # ✅ double underscores
        self.host = host
        self.port = port

        # TCP socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # SSL setup
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.context.load_cert_chain(certfile="server.crt", keyfile="server.key")

        # Clients
        self.clients = {}
        self.clients_lock = threading.Lock()

    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()

        logger.log_event(f"[SECURE SERVER STARTED] Listening on {self.host}:{self.port}")

        # Accept loop
        while True:
            try:
                conn, addr = self.server_socket.accept()

                # Wrap with TLS
                secure_conn = self.context.wrap_socket(conn, server_side=True)
                logger.log_event(f"[TLS OK] Handshake completed with {addr}")

                # First message = username
                username = secure_conn.recv(1024).decode("utf-8").strip()
                if not username:
                    secure_conn.close()
                    continue

                # Ensure username uniqueness
                with self.clients_lock:
                    existing = set(self.clients.values())
                    original = username
                    i = 1
                    while username in existing:
                        username = f"{original}_{i}"
                        i += 1

                    self.clients[secure_conn] = username

                logger.log_event(f"[NEW USER] {username} ({addr}) connected.")

                # Start handler thread
                thread = threading.Thread(
                    target=handle_client,
                    args=(secure_conn, addr, self.clients, self.clients_lock),
                    daemon=True
                )
                thread.start()

            except Exception as e:
                logger.log_event(f"[SERVER ERROR] {e}")

    def stop(self):
        logger.log_event("[SERVER STOPPING] Closing all connections...")

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
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5557)
    args = parser.parse_args()

    server = Server(host=args.host, port=args.port)
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()