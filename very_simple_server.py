#!/usr/bin/env python
"""Very simple HTTP server for testing."""

import os
import sys
import http.server
import socketserver

# Change to the static directory
os.chdir("arbitrage_bot/dashboard/frontend/static")

# Create server
PORT = 8082
Handler = http.server.SimpleHTTPRequestHandler
httpd = socketserver.TCPServer(("", PORT), Handler)

print(f"Serving at port {PORT}")
print(f"Current directory: {os.getcwd()}")
print(f"Directory contents: {os.listdir('.')}")

# Start server
httpd.serve_forever()
