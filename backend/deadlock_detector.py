import networkx as nx
import psutil
from typing import List, Dict
import numpy as np
from collections import deque
import random  # For simulating risk in demo

class DeadlockDetector:
    def __init__(self):
        self.wait_for_graph = nx.DiGraph()
        self.history_buffer = deque(maxlen=100)  # Store last 100 measurements
        self.last_risk = 0.0  # Store last risk value for smoothing

    def update_wait_for_graph(self) -> None:
        """Update the wait-for graph based on current process relationships"""
        self.wait_for_graph.clear()
        
        # Get all running processes
        processes = psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent'])
        
        for proc in processes:
            try:
                # Add node for each process
                self.wait_for_graph.add_node(proc.pid)
                
                # Check for potential resource conflicts based on CPU and memory usage
                for other_proc in processes:
                    if proc.pid != other_proc.pid:
                        try:
                            # Simple heuristic: if both processes have high CPU/memory usage,
                            # assume there might be a resource conflict
                            if (proc.info['cpu_percent'] > 70 and other_proc.info['cpu_percent'] > 70) or \
                               (proc.info['memory_percent'] > 70 and other_proc.info['memory_percent'] > 70):
                                self.wait_for_graph.add_edge(proc.pid, other_proc.pid)
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    def detect_deadlocks(self) -> List[List[int]]:
        """Detect deadlocks using cycle detection in the wait-for graph"""
        try:
            cycles = list(nx.simple_cycles(self.wait_for_graph))
            return cycles
        except (nx.NetworkXNoCycle, nx.NetworkXError):
            return []

    def collect_system_metrics(self) -> Dict:
        """Collect current system metrics for deadlock prediction"""
        try:
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            process_count = len(psutil.pids())
            
            metrics = {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'process_count': process_count,
                'swap_percent': psutil.swap_memory().percent
            }
            
            self.history_buffer.append(metrics)
            return metrics
        except:
            return {
                'cpu_percent': 0,
                'memory_percent': 0,
                'process_count': 0,
                'swap_percent': 0
            }

    def predict_deadlock_risk(self) -> float:
        """Predict the probability of a deadlock occurring"""
        try:
            metrics = self.collect_system_metrics()
            
            # Calculate base risk from current system metrics
            cpu_risk = metrics['cpu_percent'] / 100.0
            memory_risk = metrics['memory_percent'] / 100.0
            
            # Check for cycles in the wait-for graph
            cycles = self.detect_deadlocks()
            cycle_risk = min(len(cycles) * 0.2, 0.6)  # Cap at 0.6
            
            # Combine risks with weights
            raw_risk = (
                0.4 * cpu_risk +
                0.3 * memory_risk +
                0.3 * cycle_risk
            )
            
            # Smooth the risk value to prevent sudden jumps
            smoothed_risk = 0.7 * raw_risk + 0.3 * self.last_risk
            self.last_risk = smoothed_risk
            
            return smoothed_risk
        except:
            return self.last_risk

    def suggest_resolution(self, deadlock_cycle: List[int]) -> List[Dict]:
        """Suggest resolution steps for a detected deadlock"""
        suggestions = []
        for pid in deadlock_cycle:
            try:
                process = psutil.Process(pid)
                cpu_percent = process.cpu_percent()
                memory_percent = process.memory_info().rss / psutil.virtual_memory().total * 100
                
                if cpu_percent > 80:
                    suggestions.append({
                        'pid': pid,
                        'action': 'kill',
                        'reason': 'High CPU usage',
                        'process_name': process.name()
                    })
                elif memory_percent > 80:
                    suggestions.append({
                        'pid': pid,
                        'action': 'restart',
                        'reason': 'High memory usage',
                        'process_name': process.name()
                    })
                else:
                    suggestions.append({
                        'pid': pid,
                        'action': 'monitor',
                        'reason': 'Part of deadlock cycle',
                        'process_name': process.name()
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
        return suggestions 