# 💬 Python Chat Application

A simple **client–server chat app** built using **Python sockets** and **Tkinter GUI**.  
It allows multiple users to chat in real time — either **on one computer** or **across devices on the same Wi-Fi network**.

---

## ⚙️ Features
- Multiple users chatting at once  
- Public and private messages  
- View who’s online  
- GUI client for desktop  
- CLI client for Termux or terminal  
- Works locally or on LAN  

---

## 🧩 Files Overview

| File | Description |
|------|--------------|
| `connection_manager.py` | Starts the chat server and accepts new connections |
| `message_handler.py` | Handles all messages (broadcasts, private, system) |
| `client_handler.py` | Receives and displays messages on client side |
| `chat_gui.py` | Tkinter-based graphical chat client |
| `client_cli.py` | Command-line client (for Termux or testing) |
| `logger_utility.py` | Logs server events like connections or errors |

---

## 🧠 How It Works
- The **server** listens for connections.  
- Each **client** connects to it and can chat publicly or privately.  
- All messages go through the server.

---

## 🚀 How to Run

### 💻 Option 1 – Run on a Single Computer (Local Mode)

1. **Start the Server**
   ```bash
   python3 connection_manager.py --host 127.0.0.1 --port 5557
   ```

2. **Open one or more clients (on the same PC)**
   ```bash
   python3 chat_gui.py --host 127.0.0.1 --port 5557
   ```

3. Each client window will ask for a username.  
   Type messages and they’ll appear across all open clients.

---

### 🌐 Option 2 – Run Across Multiple Devices on the Same Wi-Fi

1. **Find your computer’s Wi-Fi IP**
   Run this on the server laptop:
   ```bash
   ifconfig
   ```
   Look for something like `inet 192.168.1.16` under your Wi-Fi interface.

2. **Start the Server**
   ```bash
   python3 connection_manager.py --host 0.0.0.0 --port 5557
   ```

3. **Allow the port through the firewall (if needed)**
   ```bash
   sudo ufw allow 5557/tcp
   ```

4. **Connect from other devices (same Wi-Fi)**
   On another laptop or PC:
   ```bash
   python3 chat_gui.py --host 192.168.1.16 --port 5557
   ```

5. You can also use Termux (CLI client on Android):
   ```bash
   python client_cli.py 192.168.1.16 5557 ali
   ```

✅ All devices on the same Wi-Fi can now chat together.

---

## 💬 Chat Commands

| Command | Description |
|----------|-------------|
| `/pm <username> <message>` | Send private message |
| `/list` | Show all online users |
| `/quit` | Disconnect from server |

---

## 🧱 Example Setup
```
Server Laptop IP: 192.168.1.16
Client Laptop:    192.168.1.6
Client Phone:     192.168.1.8 (Termux)

All connected to the same Wi-Fi.
```

---

## 👨‍💻 Created By
**Mutahir Ahmed**  
Python Socket Programming Project – 2025
