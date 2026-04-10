#!/usr/bin/env python3
"""Quiet HTTP server for presentation development."""

import http.server
import os
import socketserver

PORT = 8000


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler that suppresses request logging."""

    def log_message(self, format, *args):
        pass


class QuietServer(socketserver.TCPServer):
    """TCP server that suppresses broken pipe errors."""

    allow_reuse_address = True

    def handle_error(self, request, client_address):
        # Suppress BrokenPipeError (browser cancelled request)
        pass


if __name__ == "__main__":
    # Change to the directory containing this script
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    with QuietServer(("", PORT), QuietHandler) as httpd:
        print(f"Serving at http://localhost:{PORT}")
        print("Press Ctrl+C to stop")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped")
