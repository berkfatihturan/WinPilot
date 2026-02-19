
# Validated user command for launching the overlay
OVERLAY_CMD_TEMPLATE = (
    "psexec -accepteula -i {session_id} -s powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -Command "
    "\"Add-Type -AssemblyName System.Windows.Forms; Add-Type -AssemblyName System.Drawing; "
    "$f=New-Object System.Windows.Forms.Form; $f.FormBorderStyle='None'; $f.ShowInTaskbar=$false; "
    "$f.TopMost=$true; $f.BackColor=[System.Drawing.Color]::Black; $f.Opacity=0.75; "
    "$f.StartPosition='Manual'; $f.Width=170; $f.Height=30; "
    "$l=New-Object System.Windows.Forms.Label; $l.Dock='Fill'; $l.ForeColor=[System.Drawing.Color]::Lime; "
    "$l.BackColor=[System.Drawing.Color]::Black; "
    "$l.Font=New-Object System.Drawing.Font('Consolas',12,[System.Drawing.FontStyle]::Bold); "
    "$l.TextAlign='MiddleCenter'; $f.Controls.Add($l); $f.KeyPreview=$true; "
    "$f.Add_KeyDown({{ if($_.KeyCode -eq 'Escape'){{ $f.Close() }} }}); "
    "$t=New-Object System.Windows.Forms.Timer; $t.Interval=30; "
    "$t.Add_Tick({{ $p=[System.Windows.Forms.Cursor]::Position; "
    "$l.Text=('X={{0}} Y={{1}}' -f $p.X,$p.Y); "
    "$f.Location=New-Object System.Drawing.Point($p.X+18,$p.Y+18) }}); "
    "$t.Start(); $f.Add_FormClosed({{ $t.Stop() }}); $f.Show(); "
    "while($f.Visible){{ [System.Windows.Forms.Application]::DoEvents(); Start-Sleep -Milliseconds 30 }}\""
)

# Script to take a full screenshot and save it to a temp path
SCREENSHOT_SCRIPT = """
try {
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    $screen = [System.Windows.Forms.Screen]::PrimaryScreen
    $bitmap = New-Object System.Drawing.Bitmap $screen.Bounds.Width, $screen.Bounds.Height
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.CopyFromScreen($screen.Bounds.X, $screen.Bounds.Y, 0, 0, $bitmap.Size)
    $bitmap.Save('C:\\Windows\\Temp\\screenshot.png', [System.Drawing.Imaging.ImageFormat]::Png)
    $graphics.Dispose()
    $bitmap.Dispose()
} catch {
    Write-Error $_
    exit 1
}
"""

# Helper to move mouse (using P/Invoke SetCursorPos)
def generate_mouse_move_script(x, y):
    return (
        "Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; "
        "public class C { [DllImport(\"user32.dll\")] public static extern bool SetCursorPos(int X,int Y); }'; "
        f"[C]::SetCursorPos({x},{y})|Out-Null"
    )

# Helper to click (using user32.dll for proper simulation and focus)
# Helper to click (using user32.dll for proper simulation)
CLICK_SCRIPT = """
$code = @'
    using System;
    using System.Runtime.InteropServices;
    public class MouseUtils {
        [DllImport("user32.dll")] public static extern void mouse_event(int dwFlags, int dx, int dy, int cButtons, int dwExtraInfo);
    }
'@
$mouse = Add-Type -MemberDefinition $code -Name "MouseUtils" -Namespace Win32 -PassThru

# Click
$mouse::mouse_event(0x0001, 0, 0, 0, 0) # Move (Wakeup)
$mouse::mouse_event(0x0002, 0, 0, 0, 0) # LeftDown
Start-Sleep -Milliseconds 50
$mouse::mouse_event(0x0004, 0, 0, 0, 0) # LeftUp
"""

DOUBLE_CLICK_SCRIPT = """
$code = @'
    using System;
    using System.Runtime.InteropServices;
    public class MouseUtils {
        [DllImport("user32.dll")] public static extern void mouse_event(int dwFlags, int dx, int dy, int cButtons, int dwExtraInfo);
    }
'@
$mouse = Add-Type -MemberDefinition $code -Name "MouseUtils" -Namespace Win32 -PassThru

# Double Click
$mouse::mouse_event(0x0001, 0, 0, 0, 0) # Move (Wakeup)
$mouse::mouse_event(0x0002, 0, 0, 0, 0) # LeftDown
Start-Sleep -Milliseconds 50
$mouse::mouse_event(0x0004, 0, 0, 0, 0) # LeftUp
Start-Sleep -Milliseconds 100
$mouse::mouse_event(0x0002, 0, 0, 0, 0) # LeftDown
Start-Sleep -Milliseconds 50
$mouse::mouse_event(0x0004, 0, 0, 0, 0) # LeftUp
"""
