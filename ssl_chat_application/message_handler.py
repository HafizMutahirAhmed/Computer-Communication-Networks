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

                # ---------------- COMMANDS ----------------
                if msg.startswith("/pm "):
                    # existing private message code
                    parts = msg.split(" ", 2)
                    if len(parts) < 3:
                        self._send_to_client(self.client_socket, "[SYSTEM] Usage: /pm <username> <message>")
                        continue
                    _, target_username, private_msg = parts
                    self.handle_private_message(username, target_username, private_msg)

                # ----------- FILE TRANSFER -----------
                elif msg.startswith("/file "):
                    # Format: /file recipient_username filename
                    parts = msg.split(" ", 2)
                    if len(parts) < 3:
                        self._send_to_client(self.client_socket, "[SYSTEM] Usage: /file <username> <filename>")
                        continue
                    _, target_username, filename = parts
                    self.handle_file_transfer(username, target_username, filename)

                # ----------- VOICE CALL -----------
                elif msg.startswith("/voice "):
                    # Format: /voice recipient_username <audio_bytes>
                    parts = msg.split(" ", 2)
                    if len(parts) < 3:
                        continue
                    _, target_username, audio_data = parts
                    self.handle_voice_data(username, target_username, audio_data)

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

    # inside MessageHandler class
    def send_message_bytes(self, data_bytes):
        try:
            self.client_socket.send(data_bytes)
        except Exception as e:
            print(f"[ERROR] Failed to send bytes: {e}")
    def handle_voice_data(self, sender_username, target_username, audio_data):
        target_sock = self.find_socket_by_username(target_username)
        if target_sock is None:
            self._send_to_client(self.client_socket, f"[SYSTEM] User '{target_username}' not found.")
            return
        try:
            # Forward raw audio bytes with prefix
            target_sock.send(b"[VOICE]" + audio_data)
        except Exception as e:
            self._send_to_client(self.client_socket, f"[SYSTEM] Failed to send voice: {e}")

    def handle_file_transfer(self, sender_username, target_username, filename):
        target_sock = self.find_socket_by_username(target_username)
        if target_sock is None:
            self._send_to_client(self.client_socket, f"[SYSTEM] User '{target_username}' not found.")
            return
        try:
            # Notify target user
            self._send_to_client(target_sock, f"[FILE] Incoming file from {sender_username}: {filename}")
            # Send actual file in chunks
            with open(filename, "rb") as f:
                data = f.read(4096)
                while data:
                    target_sock.send(b"[FILEDATA]" + data)
                    data = f.read(4096)
            self._send_to_client(self.client_socket, f"[SYSTEM] File '{filename}' sent to {target_username}.")
            logger.log_event(f"[FILE] {sender_username} sent {filename} to {target_username}")
        except Exception as e:
            self._send_to_client(self.client_socket, f"[SYSTEM] Failed to send file: {e}")



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
