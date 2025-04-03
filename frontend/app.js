// Constants
const API_URL = 'http://localhost:8002/api';
const POLLING_INTERVAL = 1000; // Poll every second

// Chart configuration
const chartConfig = {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            label: 'Deadlock Risk',
            data: [],
            borderColor: '#3b82f6',
            tension: 0.3,
            fill: false
        }]
    },
    options: {
        responsive: true,
        scales: {
            y: {
                beginAtZero: true,
                max: 1
            }
        }
    }
};

// Initialize Chart
const ctx = document.getElementById('deadlockChart').getContext('2d');
const deadlockChart = new Chart(ctx, chartConfig);

// Polling state
let isPolling = false;
let pollTimer = null;

async function startPolling() {
    if (isPolling) return;
    
    isPolling = true;
    showNotification('Connected to server', 'info');
    
    async function poll() {
        try {
            const response = await fetch(`${API_URL}/system/status`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            updateDashboard(data);
            
            // Schedule next poll
            pollTimer = setTimeout(poll, POLLING_INTERVAL);
        } catch (error) {
            console.error('Polling error:', error);
            showNotification('Connection error. Retrying...', 'error');
            isPolling = false;
            pollTimer = setTimeout(startPolling, POLLING_INTERVAL);
        }
    }
    
    // Start polling
    await poll();
}

function stopPolling() {
    isPolling = false;
    if (pollTimer) {
        clearTimeout(pollTimer);
        pollTimer = null;
    }
}

// Update Dashboard
function updateDashboard(data) {
    if (!data || !data.stats) return;
    
    updateSystemStats(data.stats);
    updateDeadlockRisk(data.stats.deadlock_risk);
    if (data.stats.processes) {
        updateProcessList(data.stats.processes);
    }
    if (data.deadlocks) {
        updateDeadlockAlerts(data.deadlocks);
    }
    updateChart(data.stats.deadlock_risk);
}

function updateSystemStats(stats) {
    if (!stats || !stats.cpu || !stats.memory || !stats.disk) return;
    
    document.getElementById('cpu-usage').textContent = `${stats.cpu.percent.toFixed(1)}%`;
    document.getElementById('memory-usage').textContent = `${stats.memory.percent.toFixed(1)}%`;
    document.getElementById('disk-usage').textContent = `${stats.disk.percent.toFixed(1)}%`;
    document.getElementById('process-count').textContent = stats.process_count || '0';
}

function updateDeadlockRisk(risk) {
    if (typeof risk !== 'number') return;
    
    const riskElement = document.getElementById('risk-indicator');
    const riskValue = document.getElementById('current-risk');
    const riskPercentage = (risk * 100).toFixed(1);
    
    riskValue.textContent = `${riskPercentage}%`;
    riskElement.className = 'inline-block px-4 py-2 rounded-full';
    
    if (risk < 0.3) {
        riskElement.classList.add('low');
    } else if (risk < 0.7) {
        riskElement.classList.add('medium');
    } else {
        riskElement.classList.add('high');
    }
}

function updateProcessList(processes) {
    if (!Array.isArray(processes)) return;
    
    const tbody = document.getElementById('process-list');
    tbody.innerHTML = '';

    processes.forEach(process => {
        if (!process || !process.pid) return;
        
        const row = document.createElement('tr');
        row.className = 'process-row';
        row.innerHTML = `
            <td class="px-4 py-2">${process.pid}</td>
            <td class="px-4 py-2">${process.name || 'Unknown'}</td>
            <td class="px-4 py-2">${(process.cpu_percent || 0).toFixed(1)}%</td>
            <td class="px-4 py-2">${(process.memory_percent || 0).toFixed(1)}%</td>
            <td class="px-4 py-2">${process.status || 'Unknown'}</td>
            <td class="px-4 py-2">
                <button class="btn btn-kill mr-2" onclick="killProcess(${process.pid})">Kill</button>
                <button class="btn btn-restart" onclick="restartProcess(${process.pid})">Restart</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

function updateDeadlockAlerts(deadlocks) {
    if (!deadlocks) return;
    
    const alertsContainer = document.getElementById('deadlock-alerts');
    alertsContainer.innerHTML = '';

    if (deadlocks.deadlocks_found) {
        deadlocks.deadlock_cycles.forEach(cycle => {
            if (!cycle || !cycle.processes) return;
            
            const alert = document.createElement('div');
            alert.className = 'deadlock-alert critical';
            alert.innerHTML = `
                <h3 class="font-semibold">Deadlock Detected</h3>
                <p>Processes involved: ${cycle.processes.map(p => `${p.name} (${p.pid})`).join(' → ')}</p>
                <div class="mt-2">
                    <strong>Suggested actions:</strong>
                    <ul class="list-disc ml-4">
                        ${cycle.suggestions.map(s => `<li>${s.action} ${s.process_name} (${s.pid}) - ${s.reason}</li>`).join('')}
                    </ul>
                </div>
            `;
            alertsContainer.appendChild(alert);
        });
    } else {
        const noAlert = document.createElement('div');
        noAlert.className = 'text-gray-500 text-center';
        noAlert.textContent = 'No deadlocks detected';
        alertsContainer.appendChild(noAlert);
    }
}

function updateChart(risk) {
    if (typeof risk !== 'number') return;
    
    const timestamp = new Date().toLocaleTimeString();
    
    if (deadlockChart.data.labels.length > 20) {
        deadlockChart.data.labels.shift();
        deadlockChart.data.datasets[0].data.shift();
    }
    
    deadlockChart.data.labels.push(timestamp);
    deadlockChart.data.datasets[0].data.push(risk);
    deadlockChart.update();
}

// Process Management Functions
async function killProcess(pid) {
    if (!pid) return;
    
    try {
        const response = await fetch(`${API_URL}/system/process/${pid}/kill`, {
            method: 'POST'
        });
        const result = await response.json();
        showNotification(result.message, result.success ? 'info' : 'error');
    } catch (error) {
        console.error('Error killing process:', error);
        showNotification('Failed to kill process', 'error');
    }
}

async function restartProcess(pid) {
    if (!pid) return;
    
    try {
        const response = await fetch(`${API_URL}/system/process/${pid}/restart`, {
            method: 'POST'
        });
        const result = await response.json();
        showNotification(result.message, result.success ? 'info' : 'error');
    } catch (error) {
        console.error('Error restarting process:', error);
        showNotification('Failed to restart process', 'error');
    }
}

// Notification System
function showNotification(message, type = 'info') {
    if (!message) return;
    
    const container = document.getElementById('notification-container');
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    container.appendChild(notification);
    
    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => {
            if (notification.parentNode === container) {
                container.removeChild(notification);
            }
        }, 300);
    }, 5000);
}

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    startPolling();
    
    // Handle visibility change
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible') {
            if (!isPolling) {
                startPolling();
            }
        } else {
            stopPolling();
        }
    });
}); 