
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
def generate_screenshot_script(draw_grid=False, draw_cursor=True):
    grid_logic = ""
    if draw_grid:
        grid_logic = """
    # Draw Grid (20x20)
    $pen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(128, [System.Drawing.Color]::Cyan), 1)
    $width = $screen.Bounds.Width
    $height = $screen.Bounds.Height
    
    for ($i = 1; $i -lt 100; $i++) {
        $x = [int]($width * $i / 100)
        $y = [int]($height * $i / 100)
        
        # Vertical Line
        $graphics.DrawLine($pen, $x, 0, $x, $height)
        # Horizontal Line
        $graphics.DrawLine($pen, 0, $y, $width, $y)
    }
    $pen.Dispose()
"""

    cursor_logic = ""
    if draw_cursor:
        cursor_logic = """
    # Draw Red Cursor
    $cursor = [System.Windows.Forms.Cursor]::Position
    $relX = $cursor.X - $screen.Bounds.X
    $relY = $cursor.Y - $screen.Bounds.Y
    $brush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::Red)
    $graphics.FillEllipse($brush, $relX - 5, $relY - 5, 10, 10)
    $brush.Dispose()
"""

    return f"""
try {{
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    $screen = [System.Windows.Forms.Screen]::PrimaryScreen
    $bitmap = New-Object System.Drawing.Bitmap $screen.Bounds.Width, $screen.Bounds.Height
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.CopyFromScreen($screen.Bounds.X, $screen.Bounds.Y, 0, 0, $bitmap.Size)
    
    {grid_logic}
    {cursor_logic}

    $bitmap.Save('C:\\\\Windows\\\\Temp\\\\screenshot.png', [System.Drawing.Imaging.ImageFormat]::Png)
    [Console]::WriteLine("SCREEN_DIMENSIONS:$($bitmap.Width)x$($bitmap.Height)")
    $graphics.Dispose()
    $bitmap.Dispose()
}} catch {{
    Write-Error $_
    exit 1
}}
"""

GET_RESOLUTION_SCRIPT = """
try {
    Add-Type -AssemblyName System.Windows.Forms
    $screen = [System.Windows.Forms.Screen]::PrimaryScreen
    $res = "LOGICAL_RESOLUTION:$($screen.Bounds.Width)x$($screen.Bounds.Height)"
    $res | Out-File -FilePath "C:\\Windows\\Temp\\resolution.txt" -Encoding ASCII -Force
    [Console]::WriteLine($res)
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
# Helper to click (using user32.dll with robust definition)
CLICK_SCRIPT = """
$csharpSource = @'
using System;
using System.Runtime.InteropServices;

public class Win32Mouse {
    [DllImport("user32.dll", CharSet = CharSet.Auto, CallingConvention = CallingConvention.StdCall)]
    public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint cButtons, uint dwExtraInfo);
}
'@

try {
    Add-Type -TypeDefinition $csharpSource -Language CSharp
} catch {
    # If type already exists in session, ignore
}

# Mouse codes
# MOUSEEVENTF_LEFTDOWN = 0x0002
# MOUSEEVENTF_LEFTUP = 0x0004

[Win32Mouse]::mouse_event(0x0002, 0, 0, 0, 0)
Start-Sleep -Milliseconds 50
[Win32Mouse]::mouse_event(0x0004, 0, 0, 0, 0)
"""

DOUBLE_CLICK_SCRIPT = """
$csharpSource = @'
using System;
using System.Runtime.InteropServices;

public class Win32Mouse {
    [DllImport("user32.dll", CharSet = CharSet.Auto, CallingConvention = CallingConvention.StdCall)]
    public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint cButtons, uint dwExtraInfo);
}
'@

try {
    Add-Type -TypeDefinition $csharpSource -Language CSharp
} catch {
    # If type already exists in session, ignore
}

# Double Click Sequence
[Win32Mouse]::mouse_event(0x0002, 0, 0, 0, 0) # Down
Start-Sleep -Milliseconds 50
[Win32Mouse]::mouse_event(0x0004, 0, 0, 0, 0) # Up
Start-Sleep -Milliseconds 100
[Win32Mouse]::mouse_event(0x0002, 0, 0, 0, 0) # Down
Start-Sleep -Milliseconds 50
[Win32Mouse]::mouse_event(0x0004, 0, 0, 0, 0) # Up
"""

# Helper to type text (with Focus restoration)
def generate_type_script(text):
    # Escape single quotes for PowerShell
    safe_text = text.replace("'", "''")
    
    return f"""
$csharpSource = @'
using System;
using System.Runtime.InteropServices;

public class Win32Key {{
    [DllImport("user32.dll")] public static extern bool GetCursorPos(out POINT lpPoint);
    [DllImport("user32.dll")] public static extern IntPtr WindowFromPoint(POINT Point);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);

    [StructLayout(LayoutKind.Sequential)]
    public struct POINT {{ public int X; public int Y; }}
}}
'@

try {{
    Add-Type -TypeDefinition $csharpSource -Language CSharp
}} catch {{
    # Ignore if already added
}}

# 1. Get Mouse Position
$p = New-Object Win32Key+POINT
[Win32Key]::GetCursorPos([ref]$p) | Out-Null

# 2. Get Window at Mouse
$hWnd = [Win32Key]::WindowFromPoint($p)

# 3. Force Focus (Restore focus from terminal)
if ($hWnd -ne [IntPtr]::Zero) {{
    [Win32Key]::SetForegroundWindow($hWnd) | Out-Null
    Start-Sleep -Milliseconds 200
}}

# 4. Send Keys
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.SendKeys]::SendWait('{safe_text}')
"""
