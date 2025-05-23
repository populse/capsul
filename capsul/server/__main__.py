import os
import socket
import uvicorn

def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))  # Port 0 = demander un port libre
        return s.getsockname()[1]

port = find_free_port()
os.environ["BASE_URL"] = f"http://127.0.0.1:{port}"

uvicorn.run(
    "capsul.server.asgi:application",
    host="127.0.0.1",
    port=port,
)
