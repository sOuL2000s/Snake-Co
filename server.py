import asyncio
import websockets
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
import os
import threading
import time
from datetime import datetime
from functools import wraps

# --- Configuration ---
HOST = '0.0.0.0'
FLASK_PORT = 5000
WEBSOCKET_PORT = 8765
UPLOAD_FOLDER = 'recordings'
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'password' # !!!!!!!!!!!! NEVER USE THIS IN PRODUCTION !!!!!!!!!!!!

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.secret_key = 'supersecretkey_for_flask_session' # !!!!!!!!!!!! CHANGE THIS !!!!!!!!!!!!
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- Global state for clients ---
# Store WebSocket connection objects, keyed by client_id
connected_clients = {}
# Store client details (e.g., last seen, recording status if we add it)
client_info = {} # {client_id: {"last_seen": time.time(), "recording_status": False, "ip": "..."}}

# --- Flask Admin UI ---

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or not session['logged_in']:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        return "Invalid credentials. <a href='/login'>Try again</a>"
    return """
        <!DOCTYPE html>
        <html>
        <head><title>Admin Login</title>
        <style>
            body { font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; background-color: #f4f4f4; }
            .login-container { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            input[type="text"], input[type="password"] { width: 100%; padding: 10px; margin-bottom: 10px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
            input[type="submit"] { width: 100%; padding: 10px; background-color: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
            input[type="submit"]:hover { background-color: #0056b3; }
        </style>
        </head>
        <body>
            <div class="login-container">
                <h2>Admin Login</h2>
                <form method="post">
                    <input type="text" name="username" placeholder="Username" required><br>
                    <input type="password" name="password" placeholder="Password" required><br>
                    <input type="submit" value="Login">
                </form>
            </div>
        </body>
        </html>
    """

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    # Update client_info with current connected_clients
    current_clients_display = {}
    for client_id, ws_obj in connected_clients.items():
        # ws_obj.remote_address contains (ip, port)
        current_clients_display[client_id] = {
            "ip": client_info.get(client_id, {}).get("ip", "N/A"),
            "last_seen": client_info.get(client_id, {}).get("last_seen", 0)
        }
    return render_template('admin.html', clients=current_clients_display, ws_port=WEBSOCKET_PORT, flask_port=FLASK_PORT)

@app.route('/command/<client_id>/<action>')
@login_required
async def send_command(client_id, action):
    if client_id in connected_clients:
        message = json.dumps({"command": action})
        await connected_clients[client_id].send(message)
        print(f"Sent {action} command to {client_id}")
        return f"Command '{action}' sent to {client_id}."
    return f"Client {client_id} not found or not connected.", 404

@app.route('/recordings')
@login_required
def list_recordings():
    videos = []
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        if filename.endswith(('.mp4', '.avi', '.mov')): # Add other video formats if needed
            videos.append(filename)
    return render_template('recordings.html', videos=videos)

@app.route('/recordings/<filename>')
@login_required
def serve_recording(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/upload_video', methods=['POST'])
def upload_video():
    # This endpoint is NOT login_required because clients don't log in
    if 'video' not in request.files:
        print("No video file part in request")
        return 'No video file part', 400
    file = request.files['video']
    if file.filename == '':
        print("No selected file for upload")
        return 'No selected file', 400
    if file:
        filename = f"{request.form.get('client_id', 'unknown_client')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        print(f"File uploaded successfully: {filename}")
        return 'File uploaded successfully', 200
    print("Upload failed for unknown reason")
    return 'Upload failed', 500

# --- WebSocket Server for Client Communication ---
import json

async def websocket_handler(websocket, path):
    client_id = None
    try:
        # Client registers itself upon connection
        registration_message = await websocket.recv()
        data = json.loads(registration_message)
        if data.get("type") == "register":
            client_id = data["client_id"]
            connected_clients[client_id] = websocket
            client_info[client_id] = {
                "last_seen": time.time(),
                "ip": websocket.remote_address[0],
                "recording_status": False # Placeholder
            }
            print(f"Client {client_id} connected from {websocket.remote_address[0]}. Total clients: {len(connected_clients)}")
            await websocket.send(json.dumps({"status": "registered", "client_id": client_id}))
        else:
            print(f"Unknown initial message from {websocket.remote_address}: {registration_message}")
            return # Terminate connection if not registered properly

        # Keep connection alive, listen for heartbeats or other client messages
        while True:
            try:
                message = await websocket.recv()
                client_data = json.loads(message)
                if client_data.get("type") == "heartbeat":
                    client_info[client_id]["last_seen"] = time.time()
                    # print(f"Heartbeat from {client_id}")
                # You could add other client-to-server messages here if needed
                # e.g., "recording_started", "recording_stopped", "error_occurred"
            except websockets.exceptions.ConnectionClosedOK:
                print(f"Client {client_id} disconnected cleanly.")
                break
            except Exception as e:
                print(f"Error receiving message from {client_id}: {e}")
                break

    except websockets.exceptions.ConnectionClosedError as e:
        print(f"Client {client_id if client_id else 'unknown'} connection closed with error: {e}")
    except Exception as e:
        print(f"Unhandled error in websocket_handler for client {client_id if client_id else 'unknown'}: {e}")
    finally:
        if client_id in connected_clients:
            del connected_clients[client_id]
            print(f"Client {client_id} removed. Total clients: {len(connected_clients)}")

# --- Run Servers Concurrently ---

def run_flask():
    print(f"Starting Flask admin server on http://{HOST}:{FLASK_PORT}")
    app.run(host=HOST, port=FLASK_PORT, debug=False) # debug=False for production use

async def run_websocket_server():
    print(f"Starting WebSocket server on ws://{HOST}:{WEBSOCKET_PORT}")
    async with websockets.serve(websocket_handler, HOST, WEBSOCKET_PORT):
        await asyncio.Future() # Run forever

if __name__ == '__main__':
    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True # Allow main program to exit even if thread is running
    flask_thread.start()

    # Start WebSocket server in the main thread (using asyncio)
    # Note: Flask's route handlers for /command/... are async now, requiring a loop
    # For this simple setup, we use `asyncio.run` directly.
    # In a more complex app, you might use a shared event loop or `quart` for Flask.
    # For this MVP, if you click command buttons quickly, you might see issues.
    asyncio.run(run_websocket_server())
