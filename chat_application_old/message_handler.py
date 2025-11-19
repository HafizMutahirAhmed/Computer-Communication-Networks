# message_handler.py
import threading
from logger_utility import Logger

logger = Logger()

class MessageHandler:
    def __init__(self, client_socket, client_address, clients, clients_lock):
        """
        clients: dict {socket: username}
        clients_lock: threading.Lock instance guarding clients
        """
        self.client_socket = client_socket
        self.client_address = client_address
        self.clients = clients
        self.clients_lock = clients_lock
        self.running = True

        thread = threading.Thread(target=self.handle_client)
        thread.daemon = True
        thread.start()

    def handle_client(self):
        username = None
        with self.clients_lock:
            username = self.clients.get(self.client_socket, "Unknown")
        logger.log_event(f"[CONNECTED] {username} ({self.client_address})")

        while self.running:
            try:
                msg = self.client_socket.recv(4096).decode('utf-8')
                if not msg:
                    break
                msg = msg.strip()
                logger.log_event(f"[RECEIVED RAW] {username}: {msg}")

                # Commands
                if msg.startswith("/pm "):
                    # Format: /pm recipient_username message...
                    parts = msg.split(" ", 2)
                    if len(parts) < 3:
                        self._send_to_client(self.client_socket, "[SYSTEM] Usage: /pm <username> <message>")
                        continue
                    _, target_username, private_msg = parts
                    self.handle_private_message(username, target_username, private_msg)
                elif msg == "/list":
                    self.send_user_list()
                elif msg == "/quit":
                    self._send_to_client(self.client_socket, "[SYSTEM] Goodbye.")
                    break
                else:
                    full_msg = f"[{username}] ({self.client_address[0]}:{self.client_address[1]}): {msg}"
                    logger.log_event(f"[BROADCAST] {full_msg}")
                    self.broadcast(full_msg)
            except Exception as e:
                logger.log_event(f"[DISCONNECTED] {username} ({e})")
                break
        self.stop()

    def find_socket_by_username(self, username):
        with self.clients_lock:
            for sock, user in self.clients.items():
                if user == username:
                    return sock
        return None

    def handle_private_message(self, sender_username, target_username, message):
        target_sock = self.find_socket_by_username(target_username)
        if target_sock is None:
            self._send_to_client(self.client_socket, f"[SYSTEM] User '{target_username}' not found.")
            return

        composed = f"[PRIVATE] {sender_username} -> {target_username}: {message}"
        # send to target
        try:
            target_sock.send(composed.encode('utf-8'))
            # ack sender
            self._send_to_client(self.client_socket, f"[SYSTEM] Private message sent to {target_username}.")
            logger.log_event(f"[PRIVATE] {composed}")
        except Exception as e:
            self._send_to_client(self.client_socket, f"[SYSTEM] Failed to deliver to {target_username}: {e}")
            logger.log_event(f"[PRIVATE ERROR] {e}")

    def send_user_list(self):
        with self.clients_lock:
            users = list(self.clients.values())
        user_list_msg = "[SYSTEM] Users online: " + ", ".join(users)
        self._send_to_client(self.client_socket, user_list_msg)

    def broadcast(self, message):
        with self.clients_lock:
            for client in list(self.clients.keys()):
                if client != self.client_socket:
                    try:
                        client.send(message.encode('utf-8'))
                    except Exception as e:
                        logger.log_event(f"[BROADCAST ERROR] {e}")
                        try:
                            client.close()
                        except:
                            pass
                        if client in self.clients:
                            del self.clients[client]

    def _send_to_client(self, client, message):
        try:
            client.send(message.encode('utf-8'))
        except Exception as e:
            logger.log_event(f"[SEND ERROR] {e}")

    def stop(self):
        self.running = False
        with self.clients_lock:
            if self.client_socket in self.clients:
                username = self.clients[self.client_socket]
                del self.clients[self.client_socket]
                logger.log_event(f"[DISCONNECTED] {username} {self.client_address}")
        try:
            self.client_socket.close()
        except:
            pass


def handle_client(client_socket, client_address, clients, clients_lock):
    MessageHandler(client_socket, client_address, clients, clients_lock)
