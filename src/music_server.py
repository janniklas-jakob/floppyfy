import http.server
import socketserver
import os

PORT = 8080
DIRECTORY = "/home/pi/music" # Adjust to actual music path or NAS mount

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

def run():
    # Ensure directory exists
    if not os.path.exists(DIRECTORY):
        os.makedirs(DIRECTORY, exist_ok=True)
        
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving music at port {PORT} from {DIRECTORY}")
        httpd.serve_forever()

if __name__ == "__main__":
    run()
