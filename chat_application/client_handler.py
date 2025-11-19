# client_handler.py
import threading
import os
import pyaudio
from tkinter import messagebox

# -------------------- Audio Settings --------------------
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
p = pyaudio.PyAudio()


class MessageHandler:
    def __init__(self, client_socket, gui_callback=None, window=None, file_save_dir="received_files"):
        self.client_socket = client_socket
        self.gui_callback = gui_callback
        self.window = window
        self.running = True

        # ---- File Handling ----
        self.file_save_dir = file_save_dir
        self.buffer = b""

        if not os.path.exists(self.file_save_dir):
            os.makedirs(self.file_save_dir, exist_ok=True)

        # ---- Voice Call ----
        self.calling = False
        self.stream_out = None
        self.stream_in = None

        # Start receiving thread
        threading.Thread(target=self.receive_messages, daemon=True).start()

    # --------------------------------------------------------------
    # SEND TEXT MESSAGE
    # --------------------------------------------------------------
    def send_text_message(self, message):
        try:
            self.client_socket.sendall((message + "\n").encode('utf-8'))
        except Exception as e:
            print(f"[ERROR] Failed to send message: {e}")

    # --------------------------------------------------------------
    # SEND FILE
    # --------------------------------------------------------------
    def send_file(self, recipient, filepath, chunk_size=4096):
        if not os.path.isfile(filepath):
            raise FileNotFoundError(filepath)

        fname = os.path.basename(filepath)
        fsize = os.path.getsize(filepath)
        header = f"/file {recipient} {fname} {fsize}\n"

        try:
            self.client_socket.sendall(header.encode('utf-8'))
        except Exception as e:
            raise RuntimeError(f"Failed to send file header: {e}")

        try:
            with open(filepath, 'rb') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    self.client_socket.sendall(chunk)
        except Exception as e:
            raise RuntimeError(f"Failed to send file bytes: {e}")

    # --------------------------------------------------------------
    # EXACT BYTE RECEIVER (used for file download)
    # --------------------------------------------------------------
    def _recv_exact(self, num_bytes):
        data = b''
        remaining = num_bytes
        while remaining > 0:
            chunk = self.client_socket.recv(min(4096, remaining))
            if not chunk:
                raise ConnectionError("Connection lost while receiving file")
            data += chunk
            remaining -= len(chunk)
        return data

    # --------------------------------------------------------------
    # MAIN RECEIVER — handles: TEXT + FILE + VOICE STREAM
    # --------------------------------------------------------------
    def receive_messages(self):
        while self.running:
            try:
                chunk = self.client_socket.recv(4096)
                if not chunk:
                    break

                # -----------------------------------
                # VOICE CALL MODE → treat as audio
                # -----------------------------------
                if self.calling and isinstance(chunk, bytes):
                    if self.stream_out:
                        self.stream_out.write(chunk)
                    continue

                # -----------------------------------
                # TEXT / COMMAND MESSAGE
                # -----------------------------------
                try:
                    text = chunk.decode('utf-8', errors='ignore').strip()
                except:
                    continue

                # Incoming call request
                if text.startswith("/call_request:"):
                    caller = text.split(":")[1]
                    if self.window:
                        self.window.after(0, lambda: self.handle_incoming_call(caller))
                    continue

                # Call accepted → start audio
                if text.startswith("/call_accept:"):
                    self.start_voice_stream()
                    if self.gui_callback:
                        self.gui_callback("[SYSTEM] Voice call connected.")
                    continue

                # Call rejected
                if text.startswith("/call_reject:"):
                    if self.gui_callback:
                        self.gui_callback("[SYSTEM] Call rejected.")
                    continue

                # -----------------------------------
                # FILE HEADER
                # -----------------------------------
                if text.startswith("[FILE]"):
                    parts = text.split(" ", 3)
                    if len(parts) < 4:
                        if self.gui_callback:
                            self.gui_callback("[SYSTEM] Malformed file header.")
                        continue

                    _, sender, filename, filesize_str = parts
                    try:
                        filesize = int(filesize_str)
                    except:
                        if self.gui_callback:
                            self.gui_callback("[SYSTEM] Invalid file size.")
                        continue

                    if self.gui_callback:
                        self.gui_callback(f"[FILE] Incoming from {sender}: {filename} ({filesize} bytes)")

                    try:
                        file_bytes = self._recv_exact(filesize)
                    except Exception as e:
                        if self.gui_callback:
                            self.gui_callback(f"[SYSTEM] Failed receiving file: {e}")
                        continue

                    save_path = os.path.join(self.file_save_dir, filename)
                    base, ext = os.path.splitext(save_path)
                    i = 1
                    while os.path.exists(save_path):
                        save_path = f"{base}_{i}{ext}"
                        i += 1

                    try:
                        with open(save_path, 'wb') as f:
                            f.write(file_bytes)
                        if self.gui_callback:
                            self.gui_callback(f"[SYSTEM] File saved: {save_path}")
                    except Exception as e:
                        if self.gui_callback:
                            self.gui_callback(f"[SYSTEM] Error saving file: {e}")

                    continue

                # -----------------------------------
                # NORMAL TEXT MESSAGE
                # -----------------------------------
                if self.gui_callback:
                    self.gui_callback(text)

            except Exception as e:
                print(f"[DISCONNECTED] {e}")
                self.running = False
                break

    # --------------------------------------------------------------
    # INCOMING CALL POPUP
    # --------------------------------------------------------------
    def handle_incoming_call(self, caller):
        response = messagebox.askyesno("Incoming Voice Call", f"{caller} is calling. Accept?")
        if response:
            self.send_text_message(f"/call_accept:{caller}")
            self.start_voice_stream()
        else:
            self.send_text_message(f"/call_reject:{caller}")

    # --------------------------------------------------------------
    # START AUDIO STREAM
    # --------------------------------------------------------------
    def start_voice_stream(self):
        if self.calling:
            return

        self.calling = True
        self.stream_out = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True, frames_per_buffer=CHUNK)
        self.stream_in = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

        threading.Thread(target=self.send_audio, daemon=True).start()

    # --------------------------------------------------------------
    # SEND AUDIO DATA
    # --------------------------------------------------------------
    def send_audio(self):
        while self.calling:
            try:
                data = self.stream_in.read(CHUNK)
                self.client_socket.sendall(data)
            except:
                break

    # --------------------------------------------------------------
    # END CALL
    # --------------------------------------------------------------
    def stop_call(self):
        self.calling = False
        try:
            if self.stream_out:
                self.stream_out.stop_stream()
                self.stream_out.close()
            if self.stream_in:
                self.stream_in.stop_stream()
                self.stream_in.close()
        except:
            pass

    # --------------------------------------------------------------
    # CLOSE CONNECTION
    # --------------------------------------------------------------
    def stop(self):
        self.stop_call()
        self.running = False
        try:
            self.client_socket.close()
        except:
            pass