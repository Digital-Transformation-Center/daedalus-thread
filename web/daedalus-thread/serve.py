"""
Custom local HTTP server for Daedalus Thread preview.
Transparently maps '/daedalus-thread/*' and '/*' to the 'dist' directory.
"""
import http.server
import socketserver
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(SCRIPT_DIR, 'dist')

class DaedalusHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIST_DIR, **kwargs)

    def translate_path(self, path):
        # Strip '/daedalus-thread' prefix if present
        if path.startswith('/daedalus-thread'):
            path = path[len('/daedalus-thread'):]
            if not path:
                path = '/'
        return super().translate_path(path)

if __name__ == '__main__':
    port = 4321
    # Allow port reuse to avoid address already in use errors
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(('', port), DaedalusHandler) as httpd:
        print(f"Server ready at http://localhost:{port}/daedalus-thread/")
        sys.stdout.flush()
        httpd.serve_forever()
