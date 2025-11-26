# chat_server.py
import socket
import threading

HOST = "0.0.0.0"
PORT = 5000

# room_name -> set of ClientHandler
rooms = {}
rooms_lock = threading.Lock()


class ClientHandler(threading.Thread):
    def __init__(self, conn, addr):
        super().__init__(daemon=True)
        self.conn = conn
        self.addr = addr
        self.username = None
        self.joined_rooms = set()
        self.alive = True

    def send_line(self, line: str):
        try:
            self.conn.sendall((line + "\n").encode("utf-8"))
        except OSError:
            self.alive = False

    def broadcast_to_room(self, room: str, line: str):
        with rooms_lock:
            clients = list(rooms.get(room, set()))
        for client in clients:
            if client is not self and client.alive:
                client.send_line(line)

    def join_room(self, room: str):
        with rooms_lock:
            if room not in rooms:
                rooms[room] = set()
            rooms[room].add(self)
        self.joined_rooms.add(room)
        self.send_line(f"INFO joined room {room}")
        self.broadcast_to_room(room, f"INFO {self.username} joined {room}")

    def leave_room(self, room: str):
        with rooms_lock:
            if room in rooms and self in rooms[room]:
                rooms[room].remove(self)
                if not rooms[room]:
                    del rooms[room]
        if room in self.joined_rooms:
            self.joined_rooms.remove(room)
        self.broadcast_to_room(room, f"INFO {self.username} left {room}")

    def cleanup(self):
        for room in list(self.joined_rooms):
            self.leave_room(room)
        self.alive = False
        try:
            self.conn.close()
        except OSError:
            pass

    def handle_command(self, line: str):
        parts = line.strip().split(" ", 2)
        if not parts:
            return

        cmd = parts[0].upper()

        if cmd == "JOIN" and len(parts) >= 3:
            room = parts[1]
            username = parts[2]
            if self.username is None:
                self.username = username
            self.join_room(room)

        elif cmd == "MSG" and len(parts) >= 3:
            room = parts[1]
            text = parts[2]
            if room not in self.joined_rooms:
                self.send_line(f"ERROR not in room {room}")
            else:
                # echo to sender + broadcast
                msg_line = f"MSG {room} {self.username} {text}"
                self.send_line(msg_line)
                self.broadcast_to_room(room, msg_line)

        elif cmd == "LEAVE" and len(parts) >= 2:
            room = parts[1]
            if room in self.joined_rooms:
                self.leave_room(room)
            else:
                self.send_line(f"ERROR not in room {room}")

        elif cmd == "QUIT":
            self.send_line("INFO bye")
            self.cleanup()

        else:
            self.send_line("ERROR unknown command or wrong args")

    def run(self):
        self.send_line("INFO welcome to tinychat")
        try:
            with self.conn:
                buf = b""
                while self.alive:
                    data = self.conn.recv(4096)
                    if not data:
                        break
                    buf += data
                    while b"\n" in buf:
                        line, buf = buf.split(b"\n", 1)
                        line = line.decode("utf-8", errors="ignore")
                        if line.strip():
                            self.handle_command(line)
        finally:
            self.cleanup()
            print(f"[INFO] Connection closed {self.addr}")


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        print(f"[INFO] chat server listening on {HOST}:{PORT}")
        while True:
            conn, addr = s.accept()
            print(f"[INFO] new connection from {addr}")
            handler = ClientHandler(conn, addr)
            handler.start()


if __name__ == "__main__":
    main()
