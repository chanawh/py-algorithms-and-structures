# chat_client.py
import socket
import threading
import sys

HOST = "127.0.0.1"
PORT = 5000

def reader(sock: socket.socket):
    while True:
        data = sock.recv(4096)
        if not data:
            print("Disconnected from server")
            break
        for line in data.decode("utf-8", errors="ignore").splitlines():
            print(f"<< {line}")

def main():
    username = input("Choose a username: ").strip() or "anon"
    room = input("Room to join (e.g. lobby): ").strip() or "lobby"

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))

    t = threading.Thread(target=reader, args=(sock,), daemon=True)
    t.start()

    # send JOIN
    sock.sendall(f"JOIN {room} {username}\n".encode("utf-8"))

    print("Type messages. Commands:")
    print("  /join <room>")
    print("  /leave <room>")
    print("  /quit")

    current_room = room
    try:
        for line in sys.stdin:
            line = line.rstrip("\n")
            if not line:
                continue

            if line.startswith("/join "):
                room = line.split(" ", 1)[1]
                sock.sendall(f"JOIN {room} {username}\n".encode("utf-8"))
                current_room = room
            elif line.startswith("/leave "):
                room = line.split(" ", 1)[1]
                sock.sendall(f"LEAVE {room}\n".encode("utf-8"))
            elif line == "/quit":
                sock.sendall(b"QUIT\n")
                break
            else:
                # normal message to current room
                sock.sendall(f"MSG {current_room} {line}\n".encode("utf-8"))
    finally:
        sock.close()


if __name__ == "__main__":
    main()
