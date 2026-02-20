# Remote Automation System - AI Agent Usage Guide

This system proivdes a robust API allowing an AI agent (like yourself) to control a remote Windows desktop.

**Core Principle**: You simply look at the screenshot, decide where to click, and send those exact pixel coordinates. The system handles all SSH connections, resolution scaling, and input simulation automatically.

## 1. System Capabilities
-   **API URL**: `http://localhost:8001`
-   **Actions**:
    -   `click` (x, y): Left click.
    -   `double_click` (x, y): Double left click.
    -   `type` (text): Type text or send special keys.
        -   **Special Keys**: Use `{KEY}` format.
        -   Examples: `{ENTER}`, `{TAB}`, `{ESC}`, `{BACKSPACE}`, `{UP}`, `{DOWN}`, `{LEFT}`, `{RIGHT}`.
        -   Composite: `Hello World{ENTER}` or `{DOWN}{DOWN}{ENTER}`.
    -   `screenshot`: Just capture the screen.

## 2. The AI Workflow (Loop)

1.  **OBSERVE**: Call `POST /action` to get a screenshot.
    -   **Grid Overlay (Recommended)**: Send `grid=True`.
        -   Draws a **100x100** Cyan grid on the image.
        -   Each cell represents **1%** of the screen width/height.
        -   Use this to pinpoint exact coordinates (e.g., "Row 5, Column 90").
    -   **Red Dot**: The image contains a small red dot indicating the *last* known mouse position. Use this to verify your previous move worked.

2.  **DECIDE**: Analyze the image to find your target (e.g., "Start Button").
    -   Get the coordinates of the target (e.g., `x=50, y=1050`).

3.  **ACT**: Send those coordinates to `POST /action`.
    -   **Do not scale them**. The backend automatically adjusts for specific Windows DPI or resolution differences.
    -   Send: `{"type": "click", "x": 50, "y": 1050}`.

4.  **WAIT**: The system enforces a delay (default 3s) for UI animations before returning the next screenshot.

## 3. Python Client Example

```python
import requests

BASE_URL = "http://localhost:8001"

def perform_action(action_type, x=0, y=0, text=""):
    print(f"Executing {action_type}...")
    payload = {"type": action_type, "x": x, "y": y, "text": text}
    resp = requests.post(f"{BASE_URL}/action", json=payload)
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"Success! Screenshot: {data['screenshot_url']}")
        print(f"Original Resolution: {data.get('width')}x{data.get('height')}")
        return data['screenshot_url']
    return None

# Workflow
# 1. Start Session
requests.post(f"{BASE_URL}/start")

# 2. Get Initial View
perform_action("screenshot")

# 3. Click visible element (e.g. Icon at 500, 300)
# INFO: Backend will map 500,300 to the correct location even if screen is scaled.
perform_action("click", x=500, y=300)

# 4. Type Text (System focuses window under cursor first)
perform_action("type", text="Hello AI")

# 5. Stop
requests.post(f"{BASE_URL}/stop")
```

