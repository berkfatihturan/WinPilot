import paramiko
import os
import time
import re
import base64
from backend.utils import OVERLAY_CMD_TEMPLATE, generate_screenshot_script, GET_RESOLUTION_SCRIPT, generate_mouse_move_script, CLICK_SCRIPT, DOUBLE_CLICK_SCRIPT, generate_type_script

class SSHManager:
    def __init__(self):
        self.client = None
        self.sftp = None
        self.host = None
        self.user = None
        self.password = None
        self.pstools_path = None
        self.session_id = None
        self.logical_width = 0
        self.logical_height = 0

    def _update_resolution(self):
        if not self.connect() or not self.session_id:
            return

        # Run resolution script
        encoded_bytes = base64.b64encode(GET_RESOLUTION_SCRIPT.encode('utf-16le'))
        encoded_str = encoded_bytes.decode('utf-8')
        cmd = f'psexec -accepteula -i {self.session_id} -s powershell -WindowStyle Hidden -ExecutionPolicy Bypass -NoProfile -EncodedCommand {encoded_str}'
        
        out, err = self.execute_command(cmd)
        # Parse LOGICAL_RESOLUTION:1920x1080
        match = re.search(r"LOGICAL_RESOLUTION:(\d+)x(\d+)", out)
        if match:
            self.logical_width = int(match.group(1))
            self.logical_height = int(match.group(2))
            print(f"Detected Logical Resolution: {self.logical_width}x{self.logical_height}")
        else:
            print(f"Failed to detect resolution: {out} {err}")

    def connect(self):
        # Load config lazy to ensure env vars are loaded
        self.host = os.getenv("REMOTE_HOST")
        self.user = os.getenv("REMOTE_USER")
        self.password = os.getenv("REMOTE_PASS")
        self.pstools_path = os.getenv("PSTOOLS_PATH", "C:\\PSTools")

        try:
            # Check if existing connection is valid
            if self.client and self.client.get_transport() and self.client.get_transport().is_active():
                return True
            
            # Reconnect
            self.close() 
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            print(f"Connecting to {self.host}...")
            self.client.connect(self.host, username=self.user, password=self.password, timeout=10)
            self.sftp = self.client.open_sftp()
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            self.client = None
            return False

    def close(self):
        try:
            if self.sftp:
                self.sftp.close()
            if self.client:
                self.client.close()
        except:
            pass
        self.client = None
        self.sftp = None

    def execute_command(self, command):
        if not self.connect(): # Ensure connected
            return None, "Not connected"
        
        full_command = f"cmd.exe /c set PATH=%PATH%;{self.pstools_path} && {command}"
        print(f"Executing: {full_command}")
        
        try:
            stdin, stdout, stderr = self.client.exec_command(full_command)
            out = stdout.read().decode().strip()
            err = stderr.read().decode().strip()
            return out, err
        except Exception as e:
            print(f"Command execution failed ({e}), retrying connection...")
            # Force reconnect and retry once
            self.close()
            if self.connect():
                 try:
                    stdin, stdout, stderr = self.client.exec_command(full_command)
                    out = stdout.read().decode().strip()
                    err = stderr.read().decode().strip()
                    return out, err
                 except Exception as final_e:
                    return None, f"Command failed after reconnect: {final_e}"
            else:
                return None, "Reconnection failed"

    def get_active_session_id(self):
        # Run query session
        out, err = self.execute_command("query session")
        if err and "No session" not in err:
            print(f"Query session error: {err}")
        
        # Parse output looking for Active session or Console
        # Output format usually:
        # SESSIONNAME       USERNAME                 ID  STATE   TYPE        DEVICE
        # services                                    0  Disc
        # console           koyun                     1  Active
        # rdp-tcp#0         koyun                     2  Active
        
        print(f"Sessions:\n{out}")
        
        lines = out.splitlines()
        for line in lines:
            # Check for Active (Eng), Etkin (Tr), or console
            if "Active" in line or "Etkin" in line or "console" in line: 
                parts = line.split()
                # ID is usually the 3rd or 2nd regex group, let's logic it out
                # If parsed correctly, ID is a digit.
                for part in parts:
                    if part.isdigit():
                        return part
        return None

    def launch_overlay(self):
        if not self.connect():
            return False, "Connection failed"
            
        self.session_id = self.get_active_session_id()
        if not self.session_id:
            return False, "Could not find active session ID"
            
        print(f"Found Session ID: {self.session_id}")
        
        cmd = OVERLAY_CMD_TEMPLATE.format(session_id=self.session_id)
        
        # We run this asynchronously or check if it blocks. 
        # psexec without -d waits for process termination. 
        # User wants a loop afterwards, so maybe we want to run this in background?
        # But user said "bu ilk açılış... sonra hareket komutu olacak". 
        # If the Powershell script blocks (while($f.Visible)), psexec will block.
        # We should probably run psexec with -d (detached) OR assume the user wants us to start it and then send other commands via OTHER SSH channels/exec calls.
        # Since we use paramiko exec_command, each call is a new channel. 
        # So blocking one channel for the overlay is fine, we can just not wait for it to finish?
        # IMPORTANT: Paramiko exec_command returns immediately, but reading stdout blocks. 
        # We will NOT wait for stdout here if we think it blocks. 
        # However, psexec might output immediate text. 
        # Let's add -d to psexec to be safe, so it returns immediately after launch.
        
        # Adding -d to psexec arguments (detached)
        cmd = cmd.replace("psexec -accepteula", "psexec -d -accepteula")
        
        out, err = self.execute_command(cmd)
        return True, f"Overlay launched on session {self.session_id}. Output: {out}"

    def perform_action(self, action_type, x=0, y=0, text="", grid=False):
        if not self.connect():
            return None, "Not connected", 0, 0
            
        if not self.session_id:
            # Try to recover session ID if missing (e.g. restart)
            self.session_id = self.get_active_session_id()
            if not self.session_id: 
                 return None, "No active session known. Please calling /start first.", 0, 0

        # Update resolution info if missing
        if self.logical_width == 0:
            self._update_resolution()

        # Calculate Scaling
        # We assume X,Y provided are based on the Physical (Screenshot) pixels.
        # We need to translate them to Logical (System) pixels for SetCursorPos.
        target_x = x
        target_y = y
        
        # We need physical dims to calculate scale. If we processed a screenshot before, we have them.
        # If not, we might be flying blind on the very first click if it's high DPI.
        # But usually users "Observe" (get screenshot) then "Act".
        # If we have tracked physical dimensions:
        if hasattr(self, 'physical_width') and self.physical_width > 0 and self.logical_width > 0:
            scale_x = self.logical_width / self.physical_width
            scale_y = self.logical_height / self.physical_height
            target_x = int(x * scale_x)
            target_y = int(y * scale_y)
            # print(f"Scaling: {x},{y} -> {target_x},{target_y} (Scale: {scale_x:.2f})")

        # 1. Provide Input
        ps_script = ""
        if action_type == "move":
            ps_script = generate_mouse_move_script(target_x, target_y)
        elif action_type == "click":
            if target_x != 0 or target_y!= 0:
                 ps_script = generate_mouse_move_script(target_x, target_y) + "\n" + CLICK_SCRIPT
            else:
                 ps_script = CLICK_SCRIPT
        elif action_type == "double_click":
             if target_x != 0 or target_y!= 0:
                 ps_script = generate_mouse_move_script(target_x, target_y) + "\n" + DOUBLE_CLICK_SCRIPT
             else:
                 ps_script = DOUBLE_CLICK_SCRIPT
        elif action_type == "type":
            ps_script = generate_type_script(text)
        elif action_type == "none":
            # Just screenshot
            pass
        
        if ps_script:
            # Run PowerShell command inside the session via psexec using Base64
            encoded_bytes = base64.b64encode(ps_script.encode('utf-16le'))
            encoded_str = encoded_bytes.decode('utf-8')
            
            cmd = f'psexec -accepteula -i {self.session_id} -s powershell -WindowStyle Hidden -ExecutionPolicy Bypass -NoProfile -EncodedCommand {encoded_str}'
            # print(f"DEBUG INPUT CMD: {cmd}") 
            self.execute_command(cmd)

        # 2. Capture Screenshot
        self.execute_command("del C:\\Windows\\Temp\\screenshot.png")
        
        # Run Screenshot script with Base64
        # NEW: Use dynamic generation with grid option
        scr_script = generate_screenshot_script(draw_grid=grid, draw_cursor=True)
        
        encoded_bytes = base64.b64encode(scr_script.encode('utf-16le'))
        encoded_str = encoded_bytes.decode('utf-8')
        
        cmd = f'psexec -accepteula -i {self.session_id} -s powershell -WindowStyle Hidden -ExecutionPolicy Bypass -NoProfile -EncodedCommand {encoded_str}'
        # print(f"DEBUG SCREENSHOT CMD: {cmd}")
        out, err = self.execute_command(cmd)
        
        # Parse Dimensions from output
        # Expecting: SCREEN_DIMENSIONS:1920x1080
        width = 0
        height = 0
        # Check both out and err because psexec/powershell sometimes streams differently
        combined_output = out + "\n" + err
        match = re.search(r"SCREEN_DIMENSIONS:(\d+)x(\d+)", combined_output)
        if match:
            width = int(match.group(1))
            height = int(match.group(2))
            # Store for next time scaling
            self.physical_width = width
            self.physical_height = height
        
        # Check if screenshot exists remotely
        check_out, _ = self.execute_command("if exist C:\\Windows\\Temp\\screenshot.png (echo YES) else (echo NO)")
        if "NO" in check_out:
             return None, f"Screenshot not created on remote. SCR_OUT: {out} SCR_ERR: {err}", 0, 0
        
        # 3. Download Screenshot with Timestamp
        timestamp = int(time.time())
        filename = f"screenshot_{timestamp}.png"
        screenshots_dir = os.path.join(os.getcwd(), "screenshots")
        os.makedirs(screenshots_dir, exist_ok=True)
        local_path = os.path.join(screenshots_dir, filename)
        
        try:
            self.sftp.get('C:\\Windows\\Temp\\screenshot.png', local_path)
            return filename, None, width, height
        except Exception as e:
            return None, f"Failed to retrieve screenshot: {e} | Remote Out: {out} Remote Err: {err}", 0, 0

ssh_manager = SSHManager()
