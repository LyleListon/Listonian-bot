# Arbitrage Bot Dashboard

A lightweight, modern dashboard for monitoring the arbitrage bot system. This implementation uses FastAPI and minimizes dependencies for improved reliability.

## Features

- **Real-time Monitoring**: View system status, wallet balance, network information and more
- **Gas Price Tracking**: Visual chart of gas prices over time
- **DEX Integration Status**: Monitor which DEXes are active
- **Dynamic Allocation Settings**: View current balance allocation settings
- **Responsive Design**: Works on desktop and mobile devices
- **Fast & Reliable**: Minimal dependencies for improved stability
- **Modern UI**: Clean, intuitive interface built with Bootstrap 5

## Setup & Installation

### Prerequisites

- Python 3.10+ installed
- Virtual environment (recommended)
- Access to Ethereum RPC endpoint (for Base network)

### Installation

1. The dashboard dependencies will be automatically installed when you run the start script for the first time, or you can install them manually:

```bash
pip install -r new_dashboard/dashboard_requirements.txt
```

### Configuration

The dashboard requires an RPC endpoint to connect to the blockchain. You can configure this in two ways:

1. **Environment Variables** (recommended):
   - `BASE_RPC_URL`: Your RPC endpoint URL
   - `WALLET_ADDRESS`: Your wallet address to monitor

2. **Config Files**:
   - The dashboard will check `configs/production.json` and `configs/config.json`
   - It will use the first available file it finds

### Starting the Dashboard

#### Windows Command Prompt:

```
new_dashboard\start_dashboard.bat
```

#### PowerShell:

```
.\new_dashboard\start_dashboard.ps1
```

#### Manual Start:

```
cd new_dashboard
python app.py --host localhost --port 8080
```

The dashboard will be available at: http://localhost:8080

## Usage

The dashboard displays several key metrics:

- **Status Cards**: System status, wallet balance, uptime, and total profit
- **Network Information**: Network name, block number, gas price, and wallet address
- **Dynamic Allocation**: View current allocation settings
- **DEX Status**: Active DEXes and their priorities
- **Gas Price Chart**: Visual representation of gas prices

Debug information can be toggled by clicking the "Debug" button in the upper right corner.

## Troubleshooting

### Common Issues

1. **Dashboard shows "Not Connected"**:
   - Check your RPC URL is correct
   - Ensure you have internet connectivity
   - Verify your RPC provider is operational

2. **Wallet Balance shows "Not Available"**:
   - Verify your wallet address is correctly configured
   - Ensure the address is in the proper format (0x...)

3. **Missing DEXes or Configuration**:
   - Check that your config.json file is properly formatted
   - Ensure the DEXes section is configured correctly

### Logs

Dashboard logs are stored in:
- `logs/new_dashboard.log`

## Differences from the Old Dashboard

This new dashboard offers several improvements over the previous implementation:

1. **Reliability**: Fewer dependencies and simpler architecture
2. **Speed**: Faster loading and more responsive UI
3. **Modern Interface**: Improved design and usability
4. **Simplified Code**: Easier to maintain and extend
5. **Better Error Handling**: More robust error reporting and recovery

## Development

The dashboard code is organized as follows:

- `app.py`: Main FastAPI application
- `templates/`: HTML templates (Jinja2)
- `static/`: CSS, JavaScript, and other static assets
- `dashboard_requirements.txt`: Required Python packages
- `start_dashboard.bat` & `start_dashboard.ps1`: Startup scripts

To customize the dashboard:

1. Modify `templates/index.html` for UI changes
2. Update `static/css/styles.css` for styling
3. Extend `app.py` to add new data or API endpoints