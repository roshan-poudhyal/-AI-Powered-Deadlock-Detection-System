from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import psutil
import json
from typing import List, Dict
import asyncio
from datetime import datetime
import networkx as nx
import os
import sys

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.deadlock_detector import DeadlockDetector
from backend.process_manager import ProcessManager

app = FastAPI(title="AI Deadlock Detection System")

# Enable CORS with specific origins
origins = [
    "http://localhost",
    "http://localhost:8002",
    "http://127.0.0.1",
    "http://127.0.0.1:8002",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SystemState:
    def __init__(self):
        self.logs = []
        self.max_logs = 1000  # Maximum number of logs to keep in memory
        self.deadlock_detector = DeadlockDetector()
        self.process_manager = ProcessManager()
        self.last_update = None

system_state = SystemState()

@app.get("/api")
async def root():
    return {"message": "AI Deadlock Detection System API"}

@app.get("/api/system/status")
async def get_system_status():
    """Get complete system status including stats and deadlocks"""
    # Update deadlock detection
    system_state.deadlock_detector.update_wait_for_graph()
    deadlocks = system_state.deadlock_detector.detect_deadlocks()
    
    # Get system stats
    resources = system_state.process_manager.get_system_resources()
    deadlock_risk = system_state.deadlock_detector.predict_deadlock_risk()
    processes = system_state.process_manager.list_processes()
    
    # Prepare deadlock response
    deadlock_response = []
    for cycle in deadlocks:
        deadlock_response.append({
            "cycle": cycle,
            "processes": [system_state.process_manager.get_process_info(pid) for pid in cycle if system_state.process_manager.get_process_info(pid)],
            "suggestions": system_state.deadlock_detector.suggest_resolution(cycle)
        })
    
    # Create complete status update
    status_update = {
        "stats": {
            **resources,
            "deadlock_risk": deadlock_risk,
            "process_count": len(psutil.pids()),
            "processes": processes
        },
        "deadlocks": {
            "deadlocks_found": len(deadlocks) > 0,
            "deadlock_cycles": deadlock_response,
            "deadlock_risk": deadlock_risk
        },
        "timestamp": datetime.now().isoformat()
    }
    
    # Store in logs
    system_state.logs.append(status_update)
    if len(system_state.logs) > system_state.max_logs:
        system_state.logs.pop(0)
    
    system_state.last_update = status_update
    return status_update

@app.get("/api/system/processes")
async def get_processes():
    """Get list of running processes"""
    return system_state.process_manager.list_processes()

@app.get("/api/system/process/{pid}")
async def get_process_info(pid: int):
    """Get detailed information about a specific process"""
    info = system_state.process_manager.get_process_info(pid)
    if info is None:
        raise HTTPException(status_code=404, detail="Process not found")
    return info

@app.post("/api/system/process/{pid}/kill")
async def kill_process(pid: int):
    """Kill a specific process"""
    result = system_state.process_manager.kill_process(pid)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@app.post("/api/system/process/{pid}/restart")
async def restart_process(pid: int):
    """Restart a specific process"""
    result = system_state.process_manager.restart_process(pid)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002) 