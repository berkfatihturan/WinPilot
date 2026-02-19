# Remote Automation System - Setup Guide

This guide explains how to install, configure, and run the Remote Automation System.

## 1. Prerequisites (Remote Windows Machine)
Before running the agent, ensure the target Windows machine is prepared:
1.  **OpenSSH Server**: Must be installed and running.
    -   Settings > System > Optional Features > Add a feature > OpenSSH Server.
    -   Start the `OpenSSH SSH Server` service via `services.msc`.
2.  **PsExec**: Download **PSTools** from Sysinternals.
    -   Extract to a folder (e.g., `C:\PSTools`).
    -   Add `C:\PSTools` to the system **PATH** environment variable (optional, but recommended).
3.  **User Account**: Ensure you have a valid username and password. The account should be an Administrator or have permissions to run `psexec`.

## 2. Installation (Host Machine)
1.  **Python**: Ensure Python 3.9+ is installed.
2.  **Dependencies**: Install required packages using `pip`:
    ```bash
    pip install -r requirements.txt
    ```
    *Note: If `requirements.txt` is missing, install: `fastapi`, `uvicorn`, `paramiko`, `python-dotenv`, `requests`.*

## 3. Configuration
Create a `.env` file in the project root (`remote_automation/`) with the following credentials:

```ini
REMOTE_HOST=192.168.1.X      # IP Application of the Windows machine
REMOTE_USER=username         # Windows Username
REMOTE_PASS=password         # Windows Password
PSTOOLS_PATH=C:\PSTools      # Path to PsExec on the remote machine
```

## 4. Running the System
Start the backend server using `uvicorn`:

```bash
# Must be run from the 'remote_automation' directory
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8001
```

-   **Backend API**: `http://localhost:8001`
-   **Frontend Dashboard**: `http://localhost:8001/`

## 5. Usage (Dashboard)
1.  Open `http://localhost:8001/` in your browser.
2.  Click **START SESSION**.
    -   Wait for "Session Started" message.
    -   A green overlay (coordinates) should appear on the remote Windows screen.
3.  **To Interact**:
    -   Click anywhere on the black screenshot area in the browser.
    -   The system will move the mouse to that loction on the remote PC and click.
    -   A new screenshot will appear after a few seconds.
4.  **Double Click**:
    -   Select "Double Click" radio button to perform double clicks.
5.  **Send Text**:
    -   Enter text in the input box and click **SEND TEXT** to type on the remote machine.
6.  **Stop**: copy
    -   Always click **STOP SESSION** when finished to close SSH connections.

## Troubleshooting
-   **Resim Gelmiyor (No Image)**:
    -   Check if the SSH connection is active.
    -   Ensure `psexec` is working on the remote machine.
    -   Check the terminal logs for "DEBUG SCREENSHOT" output.
-   **Click Çalışmıyor (No Click)**:
    -   Ensure the remote machine is not on the Lock Screen (Ctrl+Alt+Del).
    -   Ensure the SSH user is the same as the desktop user.
