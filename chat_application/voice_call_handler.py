import socket
import threading
import pyaudio

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

class VoiceCallHandler:
    def __init__(self, username, udp_port=6000):
        self.username = username
        self.udp_port = udp_port
        self.running = False

        # Create UDP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("", udp_port))

        # PyAudio setup
        self.p = pyaudio.PyAudio()
        self.stream = None

    def start_call(self, target_ip, target_port):
        self.running = True
        print(f"[CALL] Starting voice call with {target_ip}:{target_port}")

        # Input/output streams
        self.stream = self.p.open(format=FORMAT, channels=CHANNELS,
                                  rate=RATE, input=True, frames_per_buffer=CHUNK)
        play_stream = self.p.open(format=FORMAT, channels=CHANNELS,
                                  rate=RATE, output=True, frames_per_buffer=CHUNK)

        # Start threads
        threading.Thread(target=self._send_audio, args=(target_ip, target_port), daemon=True).start()
        threading.Thread(target=self._receive_audio, args=(play_stream,), daemon=True).start()

    def _send_audio(self, target_ip, target_port):
        while self.running:
            try:
                data = self.stream.read(CHUNK, exception_on_overflow=False)
                self.sock.sendto(data, (target_ip, target_port))
            except Exception as e:
                print(f"[SEND AUDIO ERROR] {e}")
                break

    def _receive_audio(self, play_stream):
        while self.running:
            try:
                data, _ = self.sock.recvfrom(4096)
                play_stream.write(data)
            except Exception as e:
                print(f"[RECV AUDIO ERROR] {e}")
                break

    def stop_call(self):
        print("[CALL ENDED]")
        self.running = False
        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            self.p.terminate()
            self.sock.close()
        except Exception as e:
            print(f"[STOP CALL ERROR] {e}")
