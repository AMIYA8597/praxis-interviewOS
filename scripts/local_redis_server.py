"""Local standalone FakeRedis RESP TCP server for local development without Docker.

Listens on 127.0.0.1:6379 to allow arq, FastAPI, and redis-py to operate seamlessly.
"""
from fakeredis import TcpFakeServer

def main():
    host = "127.0.0.1"
    port = 6379
    print(f"Starting standalone Redis server on {host}:{port}...", flush=True)
    server = TcpFakeServer((host, port))
    print(f"Standalone Redis server listening on {host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        print("Standalone Redis server stopped.", flush=True)

if __name__ == "__main__":
    main()
