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

        # ------------------ ADD HERE ------------------
        import pyaudio
        self.p_audio = pyaudio.PyAudio()
        self.voice_stream = self.p_audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=44100,
            output=True,
            frames_per_buffer=1024
        )
        # ----------------------------------------------

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
                msg = self.client_socket.recv(4096)  # use larger buffer for files/audio
                if not msg:
                    break

                # ---------------- FILE DATA ----------------
                if msg.startswith(b"[FILE]"):
                    # Notify user of incoming file
                    if self.gui_callback:
                        self.gui_callback(msg.decode('utf-8'))

                elif msg.startswith(b"[FILEDATA]"):
                    # Receive actual file bytes
                    file_data = msg[len(b"[FILEDATA]"):]
                    # Append to a temporary file (e.g., received_file)
                    with open("received_file", "ab") as f:
                        f.write(file_data)
                    if self.gui_callback:
                        self.gui_callback("[SYSTEM] Received a chunk of a file...")

                # ---------------- VOICE DATA ----------------
                elif msg.startswith(b"[VOICE]"):
                    audio_data = msg[len(b"[VOICE]"):]  # raw bytes
                    # You will need a running PyAudio stream to play
                    if hasattr(self, "voice_stream"):
                        self.voice_stream.write(audio_data)

                # ---------------- NORMAL MESSAGES ----------------
                else:
                    if self.gui_callback:
                        self.gui_callback(msg.decode('utf-8'))

            except Exception as e:
                print(f"[DISCONNECTED] {e}")
                self.running = False
                break

    def stop(self):
        self.running = False
        self.client_socket.close()
