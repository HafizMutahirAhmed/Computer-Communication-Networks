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
                msg = self.client_socket.recv(4096)
                if not msg:
                    break

                # ---------------- FILE START ----------------
                if msg.startswith(b"[FILE]"):
                    # Extract filename
                    filename = msg[len(b"[FILE]"):].decode('utf-8').strip()
                    self.current_file_name = filename
                    self.current_file = open(filename, "wb")
                    if self.gui_callback:
                        self.gui_callback(f"[SYSTEM] Receiving file '{filename}'...")

                # ---------------- FILE DATA ----------------
                elif msg.startswith(b"[FILEDATA]"):
                    file_data = msg[len(b"[FILEDATA]"):]
                    if hasattr(self, "current_file") and self.current_file:
                        self.current_file.write(file_data)

                # ---------------- END OF FILE ----------------
                elif msg.startswith(b"[ENDFILE]"):
                    if hasattr(self, "current_file") and self.current_file:
                        self.current_file.close()
                        del self.current_file
                    if self.gui_callback:
                        self.gui_callback(f"[SYSTEM] File '{self.current_file_name}' received successfully!")

                # ---------------- VOICE DATA ----------------
                elif msg.startswith(b"[VOICE]"):
                    audio_data = msg[len(b"[VOICE]"):]
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
