// Common JavaScript functionality for dashboard

// Initialize Socket.IO with both websocket and polling
const socket = io({
    path: '/socket.io/',
    transports: ['websocket', 'polling'],  // Try websocket first, fallback to polling
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 5000,
    reconnectionAttempts: Infinity,
    timeout: 20000,
    autoConnect: true,
    forceNew: true
});

// Export socket for use in other scripts
window.dashboardSocket = socket;

// Connection event handlers
socket.on('connect', () => {
    console.log('Connected to server');
    console.log('Transport:', socket.io.engine.transport.name);
    updateConnectionStatus('connected');
});

socket.on('disconnect', (reason) => {
    console.log('Disconnected from server:', reason);
    updateConnectionStatus('disconnected');
});

socket.on('connect_error', (error) => {
    console.error('Connection error:', error);
    updateConnectionStatus('error');
    
    // Try to reconnect with different transport
    if (socket.io.engine.transport.name === 'websocket') {
        console.log('Falling back to polling...');
        socket.io.engine.transport.name = 'polling';
    }
});

socket.on('error', (error) => {
    console.error('Socket error:', error);
    showError('Socket error: ' + error.message);
});

// Connection status management
function updateConnectionStatus(status) {
    const statusElement = document.getElementById('connection-status');
    if (statusElement) {
        statusElement.textContent = status.charAt(0).toUpperCase() + status.slice(1);
        statusElement.className = `px-3 py-1 rounded-full text-sm font-medium ${getStatusClass(status)}`;
    }
}

// Error handling
function showError(message) {
    const errorElement = document.getElementById('error-message');
    if (errorElement) {
        errorElement.textContent = message;
        errorElement.classList.remove('hidden');
        errorElement.classList.add('block');
        setTimeout(() => {
            errorElement.classList.remove('block');
            errorElement.classList.add('hidden');
        }, 5000);
    }
    console.error(message);
}

// Status class helper
function getStatusClass(status) {
    switch(status.toLowerCase()) {
        case 'connected':
            return 'bg-green-200 text-green-800';
        case 'disconnected':
        case 'failed':
            return 'bg-red-200 text-red-800';
        case 'connecting...':
        case 'error':
            return 'bg-yellow-200 text-yellow-800';
        default:
            return 'bg-gray-200 text-gray-800';
    }
}

// Connection monitoring
let lastActivityTime = Date.now();
const ACTIVITY_TIMEOUT = 30000; // 30 seconds

function updateLastActivity() {
    lastActivityTime = Date.now();
}

// Monitor for events that indicate activity
socket.on('market_update', updateLastActivity);
socket.on('metrics_update', updateLastActivity);
socket.on('state_update', updateLastActivity);
socket.on('system_update', updateLastActivity);

// Check connection health periodically
const healthCheck = setInterval(() => {
    const currentTime = Date.now();
    const timeSinceLastActivity = currentTime - lastActivityTime;
    
    if (timeSinceLastActivity > ACTIVITY_TIMEOUT) {
        console.warn('No activity detected for', timeSinceLastActivity, 'ms');
        if (!socket.connected) {
            console.log('Attempting to reconnect...');
            socket.connect();
        }
    }
}, 5000);

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    clearInterval(healthCheck);
    socket.close();
});
