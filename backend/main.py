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
    type: str # 'move', 'click', 'double_click', 'type', 'none'
    x: int = 0
    y: int = 0
    text: str = ""
    grid: bool = False
    grid_x: float = None
    grid_y: float = None


from fastapi.staticfiles import StaticFiles

os.makedirs("screenshots", exist_ok=True)
app.mount("/screenshots", StaticFiles(directory="screenshots"), name="screenshots")

import queue
import threading
from concurrent.futures import Future

# Job Queue to serialize SSH operations
action_queue = queue.Queue()

def process_actions():
    """Worker thread to process actions sequentially."""
    print("Action Worker Started")
    while True:
        try:
            task, future = action_queue.get()
            if task is None:
                break
            
            # Execute the blocking SSH operation
            try:
                result = ssh_manager.perform_action(task.type, task.x, task.y, text=task.text, grid=task.grid, grid_x=task.grid_x, grid_y=task.grid_y)
                if not future.cancelled():
                    future.set_result(result)
            except Exception as e:
                if not future.cancelled():
                    future.set_exception(e)
            finally:
                action_queue.task_done()
        except Exception as e:
            print(f"Worker Error: {e}")

# Start worker thread
worker_thread = threading.Thread(target=process_actions, daemon=True)
worker_thread.start()

@app.get("/")
def read_root():
    return FileResponse("frontend/index.html")

@app.get("/status")
def get_status():
    return {"Status": "Active", "Host": os.getenv("REMOTE_HOST"), "QueueSize": action_queue.qsize()}

@app.post("/start")
def start_session():
    # Ideally start should also be queued or mutexed, but for now we assume start is called once.
    # We could check if a session is already active.
    success, msg = ssh_manager.launch_overlay()
    if not success:
        raise HTTPException(status_code=500, detail=msg)
    return {"status": "started", "message": msg}

@app.post("/action")
def do_action(req: ActionRequest):
    # Create a Future to track the result of this specific job
    future = Future()
    
    # Put the job in the queue
    action_queue.put((req, future))
    
    # Wait for the result (max 60 seconds to prevent indefinite hang)
    try:
        # Result is a tuple: (filename, error, width, height)
        filename, error, width, height = future.result(timeout=60)
        
        if error:
            raise HTTPException(status_code=500, detail=error)
        
        return {
            "status": "success", 
            "screenshot_url": f"/screenshots/{filename}",
            "width": width,
            "height": height
        }
        
    except TimeoutError:
        raise HTTPException(status_code=504, detail="Action timed out in queue")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stop")
def stop_session():
    ssh_manager.close()
    return {"status": "stopped"}
