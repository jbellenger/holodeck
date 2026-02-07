#!/usr/bin/env python3
"""Quiet HTTP server for presentation development."""

import http.server
import socketserver

PORT = 8000


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler that suppresses request logging."""

    def log_message(self, format, *args):
        pass


class QuietServer(socketserver.TCPServer):
    """TCP server that suppresses broken pipe errors."""

    def handle_error(self, request, client_address):
        # Suppress BrokenPipeError (browser cancelled request)
        pass


if __name__ == "__main__":
    with QuietServer(("", PORT), QuietHandler) as httpd:
        print(f"Serving at http://localhost:{PORT}")
        print("Press Ctrl+C to stop")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped")
