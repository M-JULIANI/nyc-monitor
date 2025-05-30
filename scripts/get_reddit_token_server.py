#!/usr/bin/env python3
"""
Reddit OAuth2 token generator with local server
This version runs a temporary web server to handle the OAuth callback automatically.
"""
import os
import requests
import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time

try:
    from dotenv import load_dotenv
except ImportError:
    print("❌ Error: python-dotenv not found")
    print("Please install it with: pip install python-dotenv")
    print("Or if using poetry: cd backend && poetry install")
    exit(1)

# Load environment variables from .env file
load_dotenv()

# Get credentials from environment
CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:8080"

# Validate credentials
if not CLIENT_ID or not CLIENT_SECRET:
    print("❌ Error: Missing Reddit credentials in .env file")
    print("\nPlease add these to your .env file:")
    print("REDDIT_CLIENT_ID=your_client_id")
    print("REDDIT_CLIENT_SECRET=your_client_secret")
    print("\nGet these from: https://www.reddit.com/prefs/apps")
    exit(1)

print(f"📱 Using Reddit app: {CLIENT_ID}")
print()

# Global variable to store the authorization code
auth_code = None
server_running = True


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code, server_running

        # Parse the URL to get the code parameter
        parsed_url = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_url.query)

        if 'code' in query_params:
            auth_code = query_params['code'][0]
            # Send a success response
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'''
            <html>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h2 style="color: green;">Success!</h2>
                    <p>Authorization code received. You can close this window.</p>
                    <p>Return to your terminal to continue.</p>
                </body>
            </html>
            ''')
            server_running = False
        else:
            # Send an error response
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'''
            <html>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h2 style="color: red;">Error</h2>
                    <p>No authorization code found in the callback.</p>
                </body>
            </html>
            ''')

    def log_message(self, format, *args):
        # Suppress server log messages
        pass


def run_server():
    """Run the temporary web server"""
    server = HTTPServer(('localhost', 8080), CallbackHandler)
    while server_running:
        server.handle_request()
    server.server_close()


# Start the temporary web server
print("🚀 Starting temporary web server on http://localhost:8080")
server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()

# Give the server a moment to start
time.sleep(1)

# Generate the authorization URL
auth_url = f"https://www.reddit.com/api/v1/authorize?client_id={CLIENT_ID}&response_type=code&state=random_string&redirect_uri={REDIRECT_URI}&duration=permanent&scope=read"

print("🔗 Opening authorization URL in your browser...")
print(f"   {auth_url}")
print()
print("📋 After clicking 'Allow', the page should automatically show a success message.")
print("   If your browser doesn't open automatically, copy the URL above.")
print()

# Open the browser
try:
    webbrowser.open(auth_url)
except:
    print("❌ Could not open browser automatically. Please copy the URL above.")

# Wait for the authorization code
print("⏳ Waiting for authorization...")
timeout = 120  # 2 minutes timeout
start_time = time.time()

while auth_code is None and time.time() - start_time < timeout:
    time.sleep(1)

if auth_code is None:
    print("❌ Timeout: No authorization code received within 2 minutes.")
    print("   Please try again or use the manual method.")
    exit(1)

print(f"✅ Authorization code received: {auth_code[:10]}...")

# Exchange code for tokens
auth = requests.auth.HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET)
data = {
    'grant_type': 'authorization_code',
    'code': auth_code,
    'redirect_uri': REDIRECT_URI
}

headers = {'User-Agent': 'atlas-monitor/1.0'}
response = requests.post(
    'https://www.reddit.com/api/v1/access_token', auth=auth, data=data, headers=headers)

if response.status_code == 200:
    tokens = response.json()
    print()
    print("🎉 Success! Your refresh token has been generated.")
    print()
    print("📝 Add this to your .env file:")
    print(f"REDDIT_REFRESH_TOKEN={tokens['refresh_token']}")
    print()
    print("🔍 Token details:")
    print(f"  Refresh token: {tokens['refresh_token']}")
    print(f"  Access token: {tokens['access_token'][:20]}...")
    print(f"  Token type: {tokens['token_type']}")
    print(f"  Expires in: {tokens['expires_in']} seconds")
    print()
    print("⚠️  Keep this refresh token safe - it doesn't expire for script apps!")
else:
    print(f"❌ Error: {response.status_code}")
    print(response.text)
