// Establish WebSocket connection
const socket = io.connect('http://' + document.domain + ':' + location.port);

// Update connection status
socket.on('connect', function() {
    document.getElementById('connection-status').innerText = 'Connected';
});

// Handle system updates
socket.on('system_update', function(data) {
    // Update metrics based on received data
    document.getElementById('total-profit').innerText = data.total_profit || '$0.00';
    document.getElementById('active-opportunities').innerText = data.active_opportunities || '0';
    document.getElementById('success-rate').innerText = data.success_rate || '0%';
    document.getElementById('gas-used').innerText = data.gas_used || '0 ETH';
});

// Handle errors
socket.on('error', function(error) {
    const errorMessage = document.getElementById('error-message');
    errorMessage.innerText = error;
    errorMessage.classList.remove('hidden');
});

// Initialize charts after DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Initialize charts
    window.profitChart = new Chart(document.getElementById('profit-chart'), {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Profit (USD)',
                data: [],
                borderColor: 'rgb(75, 192, 192)',
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });

    window.gasChart = new Chart(document.getElementById('gas-chart'), {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Gas Price (Gwei)',
                data: [],
                borderColor: 'rgb(153, 102, 255)',
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
});