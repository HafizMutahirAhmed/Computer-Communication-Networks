import threading
from logger_utility import Logger

logger = Logger()

class MessageHandler:
    def __init__(self, client_socket, client_address, clients):
        """
        clients: dict {socket: username}
        """
        self.client_socket = client_socket
        self.client_address = client_address
        self.clients = clients
        self.running = True

        thread = threading.Thread(target=self.handle_client)
        thread.daemon = True
        thread.start()

    def handle_client(self):
        username = self.clients[self.client_socket]
        logger.log_event(f"[CONNECTED] {username} ({self.client_address})")
        while self.running:
            try:
                msg = self.client_socket.recv(1024).decode('utf-8')
                if not msg:
                    break
                full_msg = f"[{username}] ({self.client_address[0]}:{self.client_address[1]}): {msg}"
                logger.log_event(f"[RECEIVED] {full_msg}")
                self.broadcast(full_msg)
            except Exception as e:
                logger.log_event(f"[DISCONNECTED] {username} ({e})")
                break
        self.stop()

    def broadcast(self, message):
        for client in list(self.clients.keys()):
            if client != self.client_socket:
                try:
                    client.send(message.encode('utf-8'))
                except:
                    client.close()
                    del self.clients[client]

    def stop(self):
        self.running = False
        if self.client_socket in self.clients:
            del self.clients[self.client_socket]
        self.client_socket.close()
        logger.log_event(f"[DISCONNECTED] {self.client_address}")

def handle_client(client_socket, client_address, clients):
    MessageHandler(client_socket, client_address, clients)
