from datetime import datetime
import threading

class Logger:
    def __init__(self, log_file="server_log.txt"):
        self.log_file = log_file
        self.lock = threading.Lock()

    def log_event(self, event):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {event}"
        with self.lock:
            print(log_line)
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_line + "\n")

    def list_active_clients(self, clients):
        active = []
        for client in clients:
            try:
                active.append(client.getpeername())
            except:
                continue
        return active

    def log_client_list(self, clients):
        active_clients = self.list_active_clients(clients)
        self.log_event(f"[ACTIVE CLIENTS] {active_clients if active_clients else 'None'}")
