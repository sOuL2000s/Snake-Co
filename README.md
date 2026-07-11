## 🎮 Snake & Co. Game Live Demo

[Play Snake & Co. Now!](https://snakeandco.netlify.app/)





# Remote Screen Recorder MVP for Exam Monitoring

This project implements a Minimum Viable Product (MVP) for a remote screen recording system, primarily intended for proof-of-concept for exam monitoring scenarios. The core idea is to allow a remote administrator to initiate and stop screen recordings on client machines, with the recordings being uploaded to a central server. Students/users on the client machines have no control over the recording process.

**IMPORTANT DISCLAIMER:** This MVP is a basic proof-of-concept and **lacks critical features required for an actual "industry-grade" or production exam monitoring system**. Specifically, it has **NO TAMPER-PROOFING** on the client side, meaning a user can easily stop the client process. It also lacks robust security, scalability, and error handling. It should **NOT** be used in any real-world scenario where exam integrity or data security is paramount.

## Features (MVP)

*   **Client-Server Architecture:** Clients connect to a central server via WebSockets for commands and HTTP for video uploads.
*   **Remote Control:** Admin can send "start recording" and "stop recording" commands to individual connected clients.
*   **Silent Client Operation:** The client runs without a visible GUI, capturing the screen in the background.
*   **Video Recording:** Captures the primary screen, encodes it into an MP4 file, and uploads it to the server upon stopping.
*   **Admin Dashboard:** A simple web-based interface (Flask) to view connected clients, trigger commands, and browse uploaded recordings.
*   **Basic Authentication:** Simple username/password login for the admin dashboard.

## Missing Key Features (for Production Use)

*   **Tamper-Proofing (CRITICAL for exams):** The client can easily be stopped by the user. A real system requires deep OS integration, process protection, and anti-detection mechanisms.
*   **Multi-OS Client Support:** MVP primarily tested on Windows for `mss` screen capture.
*   **Audio/Webcam Capture:** Currently only captures the screen.
*   **Live Streaming:** Recordings are uploaded only after they are stopped.
*   **Robust Error Handling & Logging:** Minimal error handling.
*   **Advanced Authentication/Authorization:** Basic admin login only.
*   **Scalability & Performance:** Not designed for a large number of concurrent clients or high-volume data.
*   **Background Service/Daemon:** Runs as a standard Python script, not a persistent background service.
*   **Security:** Lacks end-to-end encryption (HTTPS/WSS recommended), client authentication, and robust data protection.
*   **Virtual Machine / Remote Desktop Detection:** No mechanisms to detect or prevent bypasses.

## Technology Stack

*   **Python 3.8+**
*   **Client (Recorder):** `mss`, `opencv-python`, `requests`, `websockets`, `asyncio`
*   **Server (Control & Storage):** `Flask`, `websockets`, `asyncio`

## Setup and Installation

### 1. Prerequisites

*   Python 3.8 or higher installed on both the server and client machines.

### 2. Project Structure

```
screen_recorder_mvp/
├── server.py
├── client.py
├── requirements.txt
├── README.md
├── recordings/             # Created by server, stores uploaded video files
└── templates/
    ├── admin.html
    └── recordings.html
```

### 3. Install Dependencies

It's recommended to use a virtual environment:

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Configuration

**Important:** If your client and server are running on different machines, you **MUST** update the IP addresses in both `server.py` and `client.py`.

*   **`server.py`:**
    *   `HOST = '0.0.0.0'` (listens on all available interfaces)
    *   `FLASK_PORT = 5000`
    *   `WEBSOCKET_PORT = 8765`
    *   `ADMIN_USERNAME = 'admin'`
    *   `ADMIN_PASSWORD = 'password'` (Change this for any real use!)
    *   `app.secret_key = 'supersecretkey_for_flask_session'` (Change this!)

*   **`client.py`:**
    *   `SERVER_WS_URL = "ws://localhost:8765"` -> Change `localhost` to your server's IP.
    *   `SERVER_HTTP_UPLOAD_URL = "http://localhost:5000/upload_video"` -> Change `localhost` to your server's IP.
    *   `RECORDING_FPS = 10` (adjust as needed for performance/quality)

## How to Run

### 1. Start the Server

Open a terminal/command prompt, navigate to the `screen_recorder_mvp` directory, activate your virtual environment, and run:

```bash
python server.py
```
You will see messages indicating that the Flask admin server and the WebSocket server have started.

### 2. Access the Admin Interface

Open a web browser and go to: `http://localhost:5000` (or `http://YOUR_SERVER_IP:5000`).
Log in using the configured `ADMIN_USERNAME` and `ADMIN_PASSWORD`.

### 3. Start Clients (on student machines)

On each "student" machine where you want to record the screen:

1.  Open a terminal/command prompt.
2.  Navigate to the `screen_recorder_mvp` directory.
3.  Activate your virtual environment.
4.  Run:
    ```bash
    python client.py
    ```
    The client script will run silently in the background of that terminal. No GUI will appear.

### 4. Control Recording from the Dashboard

*   Once clients connect, they will appear on the admin dashboard.
*   Use the "Start Recording" button next to a client to send a command to begin buffering screen frames.
*   Use the "Stop Recording" button to stop buffering, finalize the video file, and upload it to the server.
*   Click "View All Recordings" to browse and play the uploaded video files.

## Development Notes

*   The client uses `mss` for screen capture, which is cross-platform but may require `X` server on Linux or specific permissions on macOS.
*   `opencv-python` is used for video writing.
*   `asyncio` is used for concurrent handling of WebSocket connections on both client and server.
*   The Flask `/command/<client_id>/<action>` route uses `async` to send WebSocket messages, which requires a specific setup if integrating with Flask in a truly asynchronous way (for this MVP, it works but might not be fully non-blocking if you hammer it).

## Contributing

As this is an MVP, contributions are not actively sought for this specific repository. However, if you find issues or have suggestions, feel free to open an issue.

## License

This project is open-source under the MIT License. See the LICENSE file (not included here, but typically found in such projects) for details.
"# Snake-Co" 
"# Snake-Co" 
"# Snake-Co" 
"# Snake-Co" 
