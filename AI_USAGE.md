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

## 2. Strict AI Operating Procedure

To successfully control this system, you **MUST** follow these steps in order:

### Step 1: Initialization
-   **Always** begin your session by calling `POST /start`. If this returns an error, do not proceed.

### Step 2: The Action Loop (Observe & Act)
This loop repeats until your overarching goal is achieved.

1.  **OBSERVE (Get Context)**
    -   Call `POST /action` with payload `{"type": "screenshot", "grid": true}`.
    -   **CRITICAL RULE**: ALWAYS use `grid: true`. It divides the screen into a 100x100 grid (Cyan lines). Each cell is exactly 1% of the screen.
    -   **Analyze the Result**: The API returns a `screenshot_url` (e.g., `/screenshots/screenshot_1701234567.png`). This URL contains a Unix timestamp. If you have made multiple actions, **always analyze the highest timestamped URL**.
    -   **Identify the Red Dot**: The image contains a small red dot. This shows your *last* clicked position to help you verify success.

2.  **ACT (Execute Command)**
    -   Locate your target on the grid (e.g., Row 45, Column 10).
    -   Send a `POST /action` request.
    -   **CRITICAL RULE**: Always use `grid_x` and `grid_y` (values between 0 and 100). Do NOT use raw pixel `x` and `y`.
    -   *Example Click*: `{"type": "click", "grid_x": 10.5, "grid_y": 45.0}`
    -   *Example Text*: `{"type": "type", "text": "Hello{ENTER}"}` (System automatically focuses the window under your cursor first).

### Step 3: Termination
-   Once your goal is complete, **always** call `POST /stop` to clean up SSH resources.

---

## 3. Deep UI Extraction Mode (AI Eyes)

Standard operation provides a screenshot (raw pixels). For exact, mathematical precision, you can use the **UI Extraction Mode**.

This mode uses the **AI Image Helper API** to perform deep UI tree extraction via `uiautomation` and generates a strict JSON layout map of the screen, resolving issues like occluded (hidden) windows, Z-index overlapping, and invisible background elements.

### How to Use

Instead of calling `POST /action`, call `POST /action_with_ui_map`.

The payload is the exact same, but the response will include a `ui_map_data` array alongside the `screenshot_url`.

```json
// Example Response from POST /action_with_ui_map
{
  "status": "success",
  "screenshot_url": "/screenshots/screenshot_1701234567.png",
  "ui_map_data": [
    {
      "pencere": "Google Chrome",
      "z_index": 10,
      "kutu": [0, 0, 1920, 1080],
      "elmanlar": [
        {
          "tip": "Button",
          "isim": "Submit",
          "merkez_koordinat": { "x": 550, "y": 320 }
        }
      ]
    }
  ]
}
```

### Best Practices for Deep Extraction
1. **Analyze `tip` (Type)**: Look for `Button`, `Edit`, `MenuItem`, etc.
2. **Find the Exact Pixel**: Read the `merkez_koordinat` (e.g., `x: 550, y: 320`).
3. **Execute**: On your *next* action, use those exact pixels (e.g., `{"type": "click", "x": 550, "y": 320}`).

---

## 4. Python Client Example

```python
import requests

BASE_URL = "http://localhost:8001"

def perform_action(action_type, grid_x=0, grid_y=0, text="", grid=True):
    print(f"Executing {action_type}...")
    payload = {"type": action_type, "grid_x": grid_x, "grid_y": grid_y, "text": text, "grid": grid}
    resp = requests.post(f"{BASE_URL}/action", json=payload)
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"Success! Screenshot: {data['screenshot_url']}")
        print(f"Original Resolution: {data.get('width')}x{data.get('height')}")
        return data['screenshot_url']
    return None

# Workflow
# 1. Start Session MUST be called first
requests.post(f"{BASE_URL}/start")

# 2. Get Initial View (ALWAYS request grid)
payload = {"type": "screenshot", "grid": True}
resp = requests.post(f"{BASE_URL}/action", json=payload)
print("Analyze image at:", resp.json()["screenshot_url"])

# 3. Click visible element (e.g. Center of screen)
# ALWAYS use grid_x and grid_y (0-100 scale)
perform_action("click", grid_x=50, grid_y=50, grid=True)

# 4. Type Text
perform_action("type", text="Hello AI{ENTER}", grid=True)

# 5. Stop Session MUST be called to clean up
requests.post(f"{BASE_URL}/stop")
```

