# message_handler.py
import threading
from logger_utility import Logger

logger = Logger()

# Shared active calls mapping (username -> partner_username)
# When A and B are in call:
#   active_calls['A'] == 'B' and active_calls['B'] == 'A'
active_calls = {}

class MessageHandler:
    def __init__(self, client_socket, client_address, clients, clients_lock):
        """
        merged message handler supporting:
          - text chat / broadcast
          - private messages (/pm)
          - user list (/list)
          - file send: header '/file <recipient> <filename> <size>\\n' followed by raw bytes
          - voice call signalling: /call_request:, /call_accept:, /call_reject:, /call_end
          - raw audio forwarding while in-call (server acts as relay)
        """
        self.client_socket = client_socket
        self.client_address = client_address
        self.clients = clients              # dict: socket -> username
        self.clients_lock = clients_lock
        self.running = True

        # buffer used for assembling text/file headers when not in-call
        self.buffer = b""

        # start thread
        t = threading.Thread(target=self.handle_client, daemon=True)
        t.start()

    # find socket by username (thread-safe with clients_lock)
    def find_socket_by_username(self, username):
        with self.clients_lock:
            for sock, user in self.clients.items():
                if user == username:
                    return sock
        return None

    # helper to send a text line (adds newline)
    def _send_to_client(self, client, message):
        try:
            client.send((message + "\n").encode('utf-8'))
        except Exception as e:
            logger.log_event(f"[SEND ERROR] {e}")

    # helper to send raw bytes (no encoding)
    def _send_bytes(self, client, data):
        try:
            client.sendall(data)
        except Exception as e:
            logger.log_event(f"[SEND BYTES ERROR] {e}")

    # remove call pairing for a username (cleanup both sides)
    def _end_call_for(self, username):
        partner = active_calls.pop(username, None)
        if partner:
            # remove partner mapping too
            active_calls.pop(partner, None)
            partner_sock = self.find_socket_by_username(partner)
            if partner_sock:
                try:
                    partner_sock.send(f"[SYSTEM] {username} ended the call.\n".encode('utf-8'))
                except:
                    pass

    # receive EXACT n bytes (used only when we already know how many bytes to read)
    def _recv_exact(self, n):
        data = b""
        remaining = n
        while remaining > 0:
            chunk = self.client_socket.recv(min(4096, remaining))
            if not chunk:
                raise ConnectionError("Connection lost while receiving data")
            data += chunk
            remaining -= len(chunk)
        return data

    def handle_client(self):
        # determine username
        with self.clients_lock:
            username = self.clients.get(self.client_socket, "Unknown")
        logger.log_event(f"[CONNECTED] {username} ({self.client_address})")

        while self.running:
            try:
                chunk = self.client_socket.recv(4096)
                if not chunk:
                    break

                # ---------- If this user is currently in a call, treat incoming bytes as audio and forward ----------
                # audio frames are sent as raw bytes (no newline), so active_calls presence decides audio forwarding
                if username in active_calls:
                    partner_name = active_calls.get(username)
                    if partner_name:
                        partner_sock = self.find_socket_by_username(partner_name)
                        if partner_sock:
                            try:
                                partner_sock.sendall(chunk)
                            except Exception as e:
                                logger.log_event(f"[CALL FORWARD ERROR] {e}")
                                # if forwarding fails, end call
                                self._end_call_for(username)
                        else:
                            # partner disconnected — end call
                            self._end_call_for(username)
                    continue  # done with this chunk

                # ---------- Not in-call: buffer chunk and process newline-terminated text/headers ----------
                self.buffer += chunk

                # process all complete lines in buffer
                while b"\n" in self.buffer:
                    line, self.buffer = self.buffer.split(b"\n", 1)
                    try:
                        text = line.decode('utf-8').strip()
                    except Exception as e:
                        logger.log_event(f"[DECODE ERROR] {e}")
                        continue

                    # ---- FILE TRANSFER header: /file <recipient> <filename> <size>
                    if text.startswith("/file "):
                        # safe split into 4 parts (cmd, recipient, filename, filesize)
                        parts = text.split(" ", 3)
                        if len(parts) < 4:
                            self._send_to_client(self.client_socket, "[SYSTEM] Malformed /file header.")
                            continue
                        _, recipient, filename, size_str = parts
                        try:
                            filesize = int(size_str)
                        except:
                            self._send_to_client(self.client_socket, "[SYSTEM] Invalid file size.")
                            continue

                        # ensure buffer has the file bytes; if not, read from socket until we have it
                        while len(self.buffer) < filesize:
                            more = self.client_socket.recv(4096)
                            if not more:
                                raise ConnectionError("Connection lost during file receive")
                            self.buffer += more

                        filebytes = self.buffer[:filesize]
                        self.buffer = self.buffer[filesize:]

                        # forward file to recipient(s)
                        self._forward_file(username, recipient, filename, filesize, filebytes)
                        continue

                    # ---- PRIVATE MESSAGE: /pm recipient message...
                    if text.startswith("/pm "):
                        parts = text.split(" ", 2)
                        if len(parts) < 3:
                            self._send_to_client(self.client_socket, "[SYSTEM] Usage: /pm <username> <message>")
                            continue
                        _, target_username, private_msg = parts
                        self._handle_private_message(username, target_username, private_msg)
                        continue

                    # ---- LIST USERS
                    if text == "/list":
                        self._send_user_list()
                        continue

                    # ---- QUIT
                    if text == "/quit":
                        self._send_to_client(self.client_socket, "[SYSTEM] Goodbye.")
                        self.running = False
                        break

                    # ---- Voice call signalling commands (textual) ----
                    if text.startswith("/call_request:"):
                        # incoming format: /call_request:target_username
                        try:
                            target_username = text.split(":", 1)[1]
                        except:
                            self._send_to_client(self.client_socket, "[SYSTEM] Malformed call request.")
                            continue

                        target_sock = self.find_socket_by_username(target_username)
                        if target_sock:
                            # forward request to target (so GUI can prompt)
                            try:
                                target_sock.send(f"/call_request:{username}\n".encode('utf-8'))
                            except Exception as e:
                                logger.log_event(f"[CALL REQUEST FORWARD ERROR] {e}")
                                self._send_to_client(self.client_socket, f"[SYSTEM] Could not reach {target_username}.")
                        else:
                            self._send_to_client(self.client_socket, f"[SYSTEM] User '{target_username}' not found.")
                        continue

                    if text.startswith("/call_accept:"):
                        # format: /call_accept:caller_username  (sent by callee)
                        try:
                            caller_username = text.split(":", 1)[1]
                        except:
                            continue
                        caller_sock = self.find_socket_by_username(caller_username)
                        if caller_sock:
                            # notify caller that call was accepted; caller will start sending/receiving audio
                            try:
                                caller_sock.send(f"/call_accept:{username}\n".encode('utf-8'))
                            except Exception as e:
                                logger.log_event(f"[CALL ACCEPT FORWARD ERROR] {e}")
                                continue
                            # mark both as in-call
                            active_calls[username] = caller_username
                            active_calls[caller_username] = username
                            # inform callee too (optional)
                            self._send_to_client(self.client_socket, f"[SYSTEM] Call connected with {caller_username}.")
                        continue

                    if text.startswith("/call_reject:"):
                        # format: /call_reject:caller_username
                        try:
                            caller_username = text.split(":", 1)[1]
                        except:
                            continue
                        caller_sock = self.find_socket_by_username(caller_username)
                        if caller_sock:
                            try:
                                caller_sock.send(f"/call_reject:{username}\n".encode('utf-8'))
                            except Exception as e:
                                logger.log_event(f"[CALL REJECT FORWARD ERROR] {e}")
                        continue

                    if text == "/call_end":
                        # end call for this user (if any)
                        self._end_call_for(username)
                        continue

                    # ---- Otherwise treat as broadcast chat message ----
                    with self.clients_lock:
                        uname = self.clients.get(self.client_socket, "Unknown")
                    full_msg = f"[{uname}] ({self.client_address[0]}:{self.client_address[1]}): {text}"
                    logger.log_event(f"[BROADCAST] {full_msg}")
                    self._broadcast(full_msg)

            except Exception as e:
                logger.log_event(f"[DISCONNECTED] {self.clients.get(self.client_socket,'Unknown')} ({e})")
                break

        # cleanup and stop
        self.stop()

    # helper: forward file to recipient or broadcast to all
    def _forward_file(self, sender, recipient, filename, filesize, filebytes):
        meta = f"[FILE] {sender} {filename} {filesize}\n".encode('utf-8')

        if recipient.lower() == "all":
            with self.clients_lock:
                for sock in list(self.clients.keys()):
                    if sock == self.client_socket:
                        continue
                    try:
                        sock.sendall(meta)
                        sock.sendall(filebytes)
                    except Exception as e:
                        logger.log_event(f"[FILE BROADCAST ERROR] {e}")
            self._send_to_client(self.client_socket, f"[SYSTEM] File broadcasted: {filename}")
            return

        target_sock = self.find_socket_by_username(recipient)
        if not target_sock:
            self._send_to_client(self.client_socket, f"[SYSTEM] User '{recipient}' not found.")
            return

        try:
            target_sock.sendall(meta)
            target_sock.sendall(filebytes)
            self._send_to_client(self.client_socket, f"[SYSTEM] File sent to {recipient}: {filename}")
        except Exception as e:
            logger.log_event(f"[FILE SEND ERROR] {e}")
            self._send_to_client(self.client_socket, f"[SYSTEM] Failed to send file: {e}")

    # helper: private message
    def _handle_private_message(self, sender, target, msg):
        target_sock = self.find_socket_by_username(target)
        if not target_sock:
            self._send_to_client(self.client_socket, f"[SYSTEM] User '{target}' not found.")
            return
        try:
            target_sock.send(f"[PRIVATE] {sender}: {msg}\n".encode('utf-8'))
            self._send_to_client(self.client_socket, f"[SYSTEM] Private message sent to {target}.")
            logger.log_event(f"[PRIVATE] {sender} -> {target}: {msg}")
        except Exception as e:
            logger.log_event(f"[PRIVATE ERROR] {e}")
            self._send_to_client(self.client_socket, f"[SYSTEM] Failed to deliver private message: {e}")

    # helper: broadcast to everyone (except sender)
    def _broadcast(self, message):
        with self.clients_lock:
            for sock in list(self.clients.keys()):
                if sock != self.client_socket:
                    try:
                        sock.send((message + "\n").encode('utf-8'))
                    except Exception as e:
                        logger.log_event(f"[BROADCAST ERROR] {e}")
                        try:
                            sock.close()
                        except:
                            pass
                        if sock in self.clients:
                            del self.clients[sock]

    # helper: send user list back to this client
    def _send_user_list(self):
        with self.clients_lock:
            users = list(self.clients.values())
        msg = "[SYSTEM] Users online: " + ", ".join(users)
        self._send_to_client(self.client_socket, msg)

    def stop(self):
        # cleanup: if user was in-call, end the call for both
        with self.clients_lock:
            username = self.clients.get(self.client_socket)
        if username:
            # end any active call
            if username in active_calls:
                self._end_call_for(username)

            logger.log_event(f"[DISCONNECTED] {username} {self.client_address}")
            with self.clients_lock:
                self.clients.pop(self.client_socket, None)

        try:
            self.client_socket.close()
        except:
            pass


# convenience function used by server code to start handler
def handle_client(client_socket, client_address, clients, clients_lock):
    MessageHandler(client_socket, client_address, clients, clients_lock)