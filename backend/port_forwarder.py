"""Lightweight port forwarder: forwards connections on 0.0.0.0:8001 -> 127.0.0.1:8000.
Allows test_api.ps1 and docs links referencing port 8001 to work without Docker.
"""
import socket
import threading
import sys

def forward(src, dst):
    try:
        while True:
            data = src.recv(4096)
            if not data:
                break
            dst.sendall(data)
    except Exception:
        pass
    finally:
        try: src.close()
        except Exception: pass
        try: dst.close()
        except Exception: pass

def handle_client(client_sock):
    try:
        remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote.connect(('127.0.0.1', 8000))
        t1 = threading.Thread(target=forward, args=(client_sock, remote), daemon=True)
        t2 = threading.Thread(target=forward, args=(remote, client_sock), daemon=True)
        t1.start()
        t2.start()
    except Exception as e:
        client_sock.close()

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind(('0.0.0.0', 8001))
    except Exception as e:
        print(f"Port 8001 bind error: {e}", file=sys.stderr)
        return
    server.listen(100)
    print("Port forwarder listening on 0.0.0.0:8001 -> 127.0.0.1:8000")
    while True:
        try:
            client, _ = server.accept()
            threading.Thread(target=handle_client, args=(client,), daemon=True).start()
        except Exception:
            break

if __name__ == '__main__':
    main()
