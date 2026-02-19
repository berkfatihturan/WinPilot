from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv # Added dotenv
from backend.ssh_manager import ssh_manager
import os

# Load env vars explicitly
load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*", # Allow any origin via regex
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ActionRequest(BaseModel):
    type: str # 'move', 'click', 'none'
    x: int = 0
    y: int = 0


from fastapi.staticfiles import StaticFiles

os.makedirs("screenshots", exist_ok=True)
app.mount("/screenshots", StaticFiles(directory="screenshots"), name="screenshots")

@app.get("/")
def read_root():
    return FileResponse("frontend/index.html")

@app.get("/status")
def get_status():
    return {"Status": "Active", "Host": os.getenv("REMOTE_HOST")}

@app.post("/start")

def start_session():
    success, msg = ssh_manager.launch_overlay()
    if not success:
        raise HTTPException(status_code=500, detail=msg)
    return {"status": "started", "message": msg}

@app.post("/action")
def do_action(req: ActionRequest):
    # Perform action and get screenshot
    filename, error = ssh_manager.perform_action(req.type, req.x, req.y)
    if error:
        raise HTTPException(status_code=500, detail=error)
    
    # Return the screenshot URL 
    return {"status": "success", "screenshot_url": f"/screenshots/{filename}"}

@app.post("/stop")
def stop_session():
    ssh_manager.close()
    return {"status": "stopped"}
