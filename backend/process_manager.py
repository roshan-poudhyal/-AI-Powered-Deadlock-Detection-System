import psutil
from typing import Dict, List, Optional
import logging

class ProcessManager:
    @staticmethod
    def kill_process(pid: int) -> Dict:
        """Kill a process by PID"""
        try:
            process = psutil.Process(pid)
            process.kill()
            return {"success": True, "message": f"Process {pid} killed successfully"}
        except psutil.NoSuchProcess:
            return {"success": False, "message": f"Process {pid} not found"}
        except psutil.AccessDenied:
            return {"success": False, "message": f"Access denied to kill process {pid}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @staticmethod
    def restart_process(pid: int) -> Dict:
        """Restart a process by PID"""
        try:
            process = psutil.Process(pid)
            cmd = process.cmdline()
            process.kill()
            if cmd:
                import subprocess
                subprocess.Popen(cmd)
                return {"success": True, "message": f"Process {pid} restarted successfully"}
            return {"success": False, "message": "Could not determine process command line"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @staticmethod
    def get_process_info(pid: int) -> Optional[Dict]:
        """Get detailed information about a process"""
        try:
            process = psutil.Process(pid)
            with process.oneshot():
                return {
                    "pid": pid,
                    "name": process.name(),
                    "status": process.status(),
                    "cpu_percent": process.cpu_percent(),
                    "memory_percent": process.memory_percent(),
                    "create_time": process.create_time(),
                    "num_threads": process.num_threads(),
                    "username": process.username()
                }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None

    @staticmethod
    def list_processes() -> List[Dict]:
        """List all running processes with detailed information"""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'status', 'cpu_percent', 'memory_percent']):
            try:
                pinfo = proc.info
                processes.append({
                    "pid": pinfo['pid'],
                    "name": pinfo['name'],
                    "status": pinfo['status'],
                    "cpu_percent": pinfo['cpu_percent'] or 0.0,
                    "memory_percent": pinfo['memory_percent'] or 0.0
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return processes

    @staticmethod
    def get_system_resources() -> Dict:
        """Get current system resource usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "cpu": {
                    "percent": cpu_percent,
                    "count": psutil.cpu_count()
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent
                },
                "swap": {
                    "total": swap.total,
                    "used": swap.used,
                    "percent": swap.percent
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "percent": disk.percent
                }
            }
        except Exception as e:
            logging.error(f"Error getting system resources: {e}")
            return {
                "cpu": {"percent": 0, "count": 0},
                "memory": {"total": 0, "available": 0, "percent": 0},
                "swap": {"total": 0, "used": 0, "percent": 0},
                "disk": {"total": 0, "used": 0, "percent": 0}
            } 