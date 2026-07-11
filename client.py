import asyncio
import websockets
import json
import uuid
import mss
import numpy as np
import cv2
import time
import requests
import threading
import os

# --- Configuration ---
SERVER_WS_URL = "ws://localhost:8765" # Change localhost to your server's IP address
SERVER_HTTP_UPLOAD_URL = "http://localhost:5000/upload_video" # Change localhost to your server's IP address
RECORDING_FPS = 10 # Frames per second
CLIENT_ID = str(uuid.uuid4()) # Unique ID for this client instance
HEARTBEAT_INTERVAL = 5 # seconds
MAX_FRAME_BUFFER = RECORDING_FPS * 60 * 5 # Buffer up to 5 minutes of frames

# --- Global state for recording ---
recording_active = False
video_writer = None
current_frames = [] # Buffer for frames
current_video_filename = None
sct = mss.mss() # Screen capture object

print(f"Client ID: {CLIENT_ID}")

# --- Screen Capture Logic ---
def capture_and_buffer_frames():
    global recording_active, video_writer, current_frames, current_video_filename

    # Assuming primary monitor
    # You might need to adjust `sct.monitors[1]` based on your system setup.
    # `sct.monitors[0]` is usually metadata, `sct.monitors[1]` is the first actual screen.
    monitor = sct.monitors[1]
    width, height = monitor['width'], monitor['height']

    frame_count = 0
    start_time = time.time()

    while True:
        if recording_active:
            try:
                sct_img = sct.grab(monitor)
                # Convert to an OpenCV image
                img = np.array(sct_img)
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR) # Convert BGRA to BGR for OpenCV
                current_frames.append(img)
                frame_count += 1

                # Keep buffer size manageable, discard oldest frames if too large
                if len(current_frames) > MAX_FRAME_BUFFER:
                    current_frames.pop(0)

                # Maintain target FPS
                elapsed_time = time.time() - start_time
                expected_frames = elapsed_time * RECORDING_FPS
                if frame_count > expected_frames:
                    # We are capturing too fast, sleep a bit
                    time_to_sleep = (frame_count - expected_frames) / RECORDING_FPS
                    # print(f"Sleeping for {time_to_sleep:.3f}s to maintain FPS")
                    time.sleep(time_to_sleep)

            except Exception as e:
                print(f"Error capturing screen: {e}")
                recording_active = False # Stop recording on error
                current_frames = []
        else:
            # If not recording, clear frames to save memory
            if current_frames:
                current_frames = []
            time.sleep(0.1) # Sleep briefly to avoid busy-waiting

# Start screen capture in a separate thread
capture_thread = threading.Thread(target=capture_and_buffer_frames, daemon=True)
capture_thread.start()

# --- Recording Control Functions ---
def start_recording():
    global recording_active, video_writer, current_frames, current_video_filename

    if recording_active:
        print("Already recording.")
        return

    # Clear any previous frames
    current_frames = []
    recording_active = True
    current_video_filename = f"{CLIENT_ID}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    print(f"Recording started. Buffering frames...")

def stop_recording_and_upload():
    global recording_active, video_writer, current_frames, current_video_filename

    if not recording_active:
        print("Not currently recording.")
        return

    print(f"Stopping recording. Writing {len(current_frames)} frames to video...")
    recording_active = False # Stop adding new frames
    frames_to_write = list(current_frames) # Make a copy to write
    current_frames = [] # Clear buffer immediately

    if not frames_to_write:
        print("No frames captured to write.")
        current_video_filename = None
        return

    # Assuming primary monitor for dimensions
    monitor = sct.monitors[1]
    width, height = monitor['width'], monitor['height']

    temp_filepath = f"temp_recording_{os.getpid()}.mp4" # Use PID to make unique
    try:
        # Use MP4V codec which is generally supported
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video_writer = cv2.VideoWriter(temp_filepath, fourcc, RECORDING_FPS, (width, height))

        if not video_writer.isOpened():
            raise IOError(f"Could not open video writer at {temp_filepath}")

        for frame in frames_to_write:
            video_writer.write(frame)
        video_writer.release()
        print(f"Video saved locally to {temp_filepath}. Uploading...")

        # Upload the video file
        with open(temp_filepath, 'rb') as f:
            files = {'video': (current_video_filename, f, 'video/mp4')}
            data = {'client_id': CLIENT_ID}
            try:
                response = requests.post(SERVER_HTTP_UPLOAD_URL, files=files, data=data, timeout=600) # 10 min timeout
                if response.status_code == 200:
                    print(f"Video '{current_video_filename}' uploaded successfully.")
                else:
                    print(f"Failed to upload video: {response.status_code} - {response.text}")
            except requests.exceptions.RequestException as e:
                print(f"Network error during upload: {e}")
    except Exception as e:
        print(f"Error writing or uploading video: {e}")
    finally:
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath) # Clean up temporary file
        current_video_filename = None

# --- WebSocket Client Logic ---
async def send_heartbeat(websocket):
    while True:
        try:
            await websocket.send(json.dumps({"type": "heartbeat", "client_id": CLIENT_ID}))
            await asyncio.sleep(HEARTBEAT_INTERVAL)
        except websockets.exceptions.ConnectionClosed:
            print("Heartbeat failed, connection closed.")
            break
        except Exception as e:
            print(f"Heartbeat error: {e}")
            await asyncio.sleep(HEARTBEAT_INTERVAL) # Try again after some time

async def connect_and_listen():
    while True:
        try:
            async with websockets.connect(SERVER_WS_URL) as websocket:
                # Register with the server
                await websocket.send(json.dumps({"type": "register", "client_id": CLIENT_ID}))
                response = json.loads(await websocket.recv())
                if response.get("status") == "registered":
                    print(f"Successfully registered with server. Client ID: {response['client_id']}")
                else:
                    print(f"Registration failed: {response}")
                    await asyncio.sleep(5)
                    continue

                # Start heartbeat in background
                heartbeat_task = asyncio.create_task(send_heartbeat(websocket))

                # Listen for commands
                while True:
                    message = await websocket.recv()
                    data = json.loads(message)
                    command = data.get("command")

                    if command == "start":
                        start_recording()
                    elif command == "stop":
                        stop_recording_and_upload()
                    else:
                        print(f"Unknown command: {command}")

        except websockets.exceptions.ConnectionClosed as e:
            print(f"WebSocket connection closed: {e}. Reconnecting in 5 seconds...")
        except ConnectionRefusedError:
            print(f"Connection refused. Server might not be running. Retrying in 5 seconds...")
        except Exception as e:
            print(f"An unexpected error occurred: {e}. Retrying in 5 seconds...")
        finally:
            if 'heartbeat_task' in locals() and not heartbeat_task.done():
                heartbeat_task.cancel()
            await asyncio.sleep(5) # Wait before attempting to reconnect

if __name__ == '__main__':
    # Flask's `request.host` will default to localhost if not specified.
    # To use a different IP, ensure it's set in the server and here.
    # E.g., SERVER_WS_URL = "ws://192.168.1.100:8765"
    # E.g., SERVER_HTTP_UPLOAD_URL = "http://192.168.1.100:5000/upload_video"

    # For now, print instructions for changing IP:
    print("\n------------------------------------------------------------")
    print("  Remember to change 'localhost' in client.py and server.py")
    print("  to your server's actual IP address if running on different machines!")
    print("------------------------------------------------------------\n")

    asyncio.run(connect_and_listen())
