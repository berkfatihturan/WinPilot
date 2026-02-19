# Remote Automation System - AI Agent Usage Guide

This system proivdes a robust API allowing an AI agent (like yourself) to control a remote Windows desktop. It abstracts SSH, PowerShell, and Screen Capture complexities into simple HTTP endpoints.

## 1. System Architecture
-   **Backend**: FastAPI server running locally (`http://localhost:8000`).
-   **Remote Host**: Windows machine controlled via SSH + PsExec.
-   **Capabilities**:
    -   Launch visual overlay for coordinate mapping.
    -   Move mouse (absolute coordinates).
    -   Click (Left Click).
    -   Double Click.
    -   Capture Screenshot.

## 2. API Workflow

### Phase 1: Initialization
1.  **POST /start**: Establishes the SSH tunnel.
    -   Identifies the active user session ID.
    -   Launches a coordinate overlay on the remote screen.

### Phase 2: The Loop (Observe -> Orient -> Decide -> Act)
1.  **POST /action (type="screenshot")**: Get the initial state.
2.  **Analyze Image**: Process the returned screenshot URL.
3.  **Decide Action**: Determine if you need to click a button or type.
4.  **POST /action**: Execute the improved `click` or `double_click`.
    -   **Important**: The system automatically waits (default 3s) after an action to allow UI updates before capturing the next screenshot.

### Phase 3: Cleanup
1.  **POST /stop**: Always close the session to free up SSH connections.

## 3. Python Client Example

Use this code snippet to interact with the system:

```python
import requests
import time

BASE_URL = "http://localhost:8000"

def start_session():
    print("Starting session...")
    resp = requests.post(f"{BASE_URL}/start")
    if resp.status_code == 200:
        print(f"Session Started: {resp.json()}")
        return True
    else:
        print(f"Failed to start: {resp.text}")
        return False

def perform_action(action_type, x=0, y=0):
    print(f"Executing {action_type} at ({x}, {y})...")
    payload = {"type": action_type, "x": x, "y": y}
    resp = requests.post(f"{BASE_URL}/action", json=payload)
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"Success! Screenshot saved at: {data['screenshot_url']}")
        return data['screenshot_url']
    else:
        print(f"Action Failed: {resp.text}")
        return None

def main():
    if not start_session():
        return

    try:
        # Step 1: Get initial screenshot
        perform_action("screenshot")

        # Step 2: Move mouse to (500, 300) and Click
        # Note: Coordinates are absolute screen pixels
        perform_action("click", x=500, y=300)

        # Step 3: Double Click on an icon at (100, 100)
        perform_action("double_click", x=100, y=100)
        
    finally:
        print("Stopping session...")
        requests.post(f"{BASE_URL}/stop")

if __name__ == "__main__":
    main()
```

## 4. Nuances & Tips
-   **Coordinate System**: The API expects absolute screen coordinates. If the remote machine uses scaling (e.g., 125%), ensure your visual analysis accounts for this or uses normalized coordinates mapped to the resolution.
-   **Delays**: The backend enforces a 3-second delay after input actions before taking the screenshot. Do not verify the state immediately in your code; trust the API to return the *post-action* state.
-   **Error Recovery**: If you receive a 500 error (e.g., SSH dropout), the system attempts to auto-reconnect. Retry the request once before failing.
