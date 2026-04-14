// Configuration
const API_BASE_URL = 'http://localhost:8000/api';
const REFRESH_INTERVAL = 10000; // 10 seconds

// State
let dashboardRefreshInterval;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('Dashboard initialized');
    loadDashboard();
    dashboardRefreshInterval = setInterval(loadDashboard, REFRESH_INTERVAL);
    updateClock();
    setInterval(updateClock, 1000);
});

// Update clock
function updateClock() {
    const now = new Date();
    document.getElementById('current-time').textContent = 
        now.toLocaleString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit', 
            second: '2-digit',
            month: 'short',
            day: '2-digit',
            year: 'numeric'
        });
}

// Load dashboard data
async function loadDashboard() {
    try {
        showLoading(true);

        // Fetch all required data in parallel
        const [dashboardData, sessionsData] = await Promise.all([
            fetch(`${API_BASE_URL}/dashboard`).then(r => r.json()),
            fetch(`${API_BASE_URL}/sessions`).then(r => r.json()).catch(() => ({}))
        ]);

        // Update dashboard
        updateDashboard(dashboardData, sessionsData);
        showLoading(false);

    } catch (error) {
        console.error('Error loading dashboard:', error);
        showLoading(false);
    }
}

// Update dashboard with data
function updateDashboard(dashboardData, sessionsData) {
    // Update summary cards
    const status = dashboardData.system_status;
    
    document.getElementById('total-machines').textContent = status.total_machines;
    document.getElementById('healthy-machines').textContent = `Healthy: ${status.healthy_machines}`;
    
    const totalAlerts = status.critical_alerts + status.warning_alerts;
    document.getElementById('total-alerts').textContent = totalAlerts;
    document.getElementById('critical-alerts').textContent = `Critical: ${status.critical_alerts}`;
    document.getElementById('warning-alerts').textContent = `Warning: ${status.warning_alerts}`;
    
    // Update system status
    const systemStatus = status.critical_alerts > 0 ? 'critical' : 
                         status.warning_alerts > 0 ? 'warning' : 'healthy';
    const statusBadge = document.getElementById('system-status');
    statusBadge.className = `status-badge ${systemStatus}`;
    statusBadge.textContent = systemStatus === 'healthy' ? 'System Healthy' : 
                             systemStatus === 'warning' ? 'System Warning' : 'System Critical';
    
    // Update sessions
    if (sessionsData && sessionsData.total_sessions) {
        document.getElementById('total-sessions').textContent = sessionsData.total_sessions;
        document.getElementById('available-sessions').textContent = sessionsData.total_available;
        document.getElementById('unavailable-sessions').textContent = sessionsData.total_unavailable;
    }
    
    // Update database status
    document.getElementById('db-status').textContent = status.database_connected ? '✅ Connected' : '❌ Disconnected';
    
    if (status.last_collection) {
        const lastTime = new Date(status.last_collection);
        document.getElementById('last-update').textContent = lastTime.toLocaleTimeString();
    }
    
    // Update alerts
    updateAlerts(dashboardData.active_alerts);
    
    // Update machines
    updateMachines(dashboardData.machines);
}

// Update alerts display
function updateAlerts(alerts) {
    const alertsList = document.getElementById('alerts-list');
    const alertBadge = document.getElementById('alert-badge');
    
    alertBadge.textContent = alerts.length;
    
    if (alerts.length === 0) {
        alertsList.innerHTML = '<div class="no-data">✅ No active alerts</div>';
        return;
    }
    
    // Sort by severity (critical first)
    const sortedAlerts = alerts.sort((a, b) => {
        const severityOrder = { critical: 0, warning: 1, info: 2 };
        return severityOrder[a.severity] - severityOrder[b.severity];
    });
    
    alertsList.innerHTML = sortedAlerts.map(alert => `
        <div class="alert-item ${alert.severity}">
            <div class="alert-header">
                <div>
                    <div class="alert-title">${escapeHtml(alert.title)}</div>
                    <div class="alert-machine">Machine: ${escapeHtml(alert.machine_name)}</div>
                </div>
                <span class="alert-severity ${alert.severity}">${alert.severity}</span>
            </div>
            
            <div class="alert-description">${escapeHtml(alert.description)}</div>
            
            ${alert.root_cause ? `
                <div class="alert-root-cause">
                    <strong>🔍 Root Cause:</strong> ${escapeHtml(alert.root_cause)}
                </div>
            ` : ''}
            
            ${alert.suggested_fix ? `
                <div class="alert-fix">
                    <strong>✅ Suggested Fix:</strong> ${escapeHtml(alert.suggested_fix)}
                </div>
            ` : ''}
            
            <div style="display: flex; gap: 8px;">
                <button class="button" onclick="resolveAlert(${alert.id})">
                    Mark as Resolved
                </button>
                <div style="font-size: 12px; color: #999; display: flex; align-items: center;">
                    Created: ${new Date(alert.created_at).toLocaleTimeString()}
                </div>
            </div>
        </div>
    `).join('');
}

// Update machines display
function updateMachines(machines) {
    const machinesGrid = document.getElementById('machines-grid');
    
    if (machines.length === 0) {
        machinesGrid.innerHTML = '<div class="no-data">No machines found</div>';
        return;
    }
    
    machinesGrid.innerHTML = machines.map(machine => {
        const cpuPercent = Math.min(machine.cpu_usage, 100);
        const memPercent = Math.min(machine.memory_usage, 100);
        const diskPercent = Math.min(machine.disk_usage || 0, 100);
        const cpuClass = cpuPercent > 85 ? 'high' : cpuPercent > 70 ? 'medium' : '';
        const memClass = memPercent > 85 ? 'high' : memPercent > 70 ? 'medium' : '';
        const diskClass = diskPercent > 90 ? 'high' : diskPercent > 70 ? 'medium' : '';
        
        return `
            <div class="machine-card">
                <div class="machine-name">${escapeHtml(machine.machine_name)}</div>
                
                <div>
                    <span class="state-badge ${machine.state.toLowerCase()}">
                        ${escapeHtml(machine.state)}
                    </span>
                    <span class="state-badge ${machine.power_state.toLowerCase()}">
                        Power: ${escapeHtml(machine.power_state)}
                    </span>
                    ${machine.is_in_maintenance ? '<span class="state-badge maintenance">🔧 Maintenance</span>' : ''}
                </div>
                
                <div class="metric-item">
                    <div class="metric-label">CPU Usage</div>
                    <div class="metric-value">${cpuPercent.toFixed(1)}%</div>
                    <div class="progress-bar">
                        <div class="progress-fill ${cpuClass}" style="width: ${cpuPercent}%"></div>
                    </div>
                </div>
                
                <div class="metric-item">
                    <div class="metric-label">Memory Usage</div>
                    <div class="metric-value">${memPercent.toFixed(1)}%</div>
                    <div class="progress-bar">
                        <div class="progress-fill ${memClass}" style="width: ${memPercent}%"></div>
                    </div>
                </div>

                <div class="metric-item">
                    <div class="metric-label">Disk Usage</div>
                    <div class="metric-value">${diskPercent.toFixed(1)}%</div>
                    <div class="progress-bar">
                        <div class="progress-fill ${diskClass}" style="width: ${diskPercent}%"></div>
                    </div>
                </div>
                
                <div class="metric-item">
                    <div class="metric-label">Sessions</div>
                    <div class="metric-value">${machine.session_count}</div>
                    <div style="font-size: 12px; color: #666;">
                        Available: ${machine.available_sessions} | 
                        Unavailable: ${machine.unavailable_sessions}
                    </div>
                    ${machine.ghost_sessions > 0 ? `<div style="font-size: 12px; color: #d32f2f; font-weight: bold;">👻 Ghost Sessions: ${machine.ghost_sessions}</div>` : ''}
                </div>

                <div class="metric-item">
                    <div class="metric-label">HDX Latency</div>
                    <div class="metric-value">${(machine.hdx_latency || 0).toFixed(1)}ms</div>
                    ${(machine.hdx_latency || 0) > 100 ? '<div style="font-size: 12px; color: #d32f2f;">⚠️ High latency detected</div>' : ''}
                </div>

                <div class="metric-item">
                    <div class="metric-label">Disconnect Rate</div>
                    <div class="metric-value">${machine.disconnect_rate.toFixed(1)}%</div>
                    <div class="progress-bar">
                        <div class="progress-fill ${machine.disconnect_rate > 20 ? 'high' : ''}" 
                             style="width: ${Math.min(machine.disconnect_rate, 100)}%"></div>
                    </div>
                </div>

                <div class="metric-item">
                    <div class="metric-label">Uptime</div>
                    <div class="metric-value">${(machine.uptime_percentage || 100).toFixed(1)}%</div>
                </div>

                ${machine.failed_logins > 0 ? `<div style="font-size: 12px; color: #ff9800; padding: 6px; background: #fff3e0; border-radius: 4px;">🔒 Failed Logins: ${machine.failed_logins}</div>` : ''}
                
                <div style="font-size: 12px; color: #999; margin-top: 8px;">
                    Last updated: ${new Date(machine.last_updated).toLocaleTimeString()}
                </div>
            </div>
        `;
    }).join('');
}

// Resolve alert
async function resolveAlert(alertId) {
    try {
        const response = await fetch(`${API_BASE_URL}/alerts/${alertId}/resolve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (response.ok) {
            console.log(`Alert ${alertId} resolved`);
            loadDashboard();
        }
    } catch (error) {
        console.error('Error resolving alert:', error);
    }
}

// Show/hide loading indicator
function showLoading(show) {
    const loading = document.getElementById('loading');
    const content = document.getElementById('dashboard-content');
    
    loading.style.display = show ? 'block' : 'none';
    content.style.display = show ? 'none' : 'block';
}

// Utility function to escape HTML
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return String(text).replace(/[&<>"']/g, m => map[m]);
}

// Log that dashboard is ready
console.log('Citrix DaaS AI Monitoring Dashboard Ready');
