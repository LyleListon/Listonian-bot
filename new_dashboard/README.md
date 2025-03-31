# Listonian Arbitrage Bot - Dashboard

This dashboard provides real-time monitoring and visualization of the Listonian Arbitrage Bot's performance, trade history, and market data.

## Features

- Real-time metrics display
- Trade history tracking
- Performance analytics
- WebSocket-based updates
- Mock data generation for testing

## Getting Started

### Prerequisites

- Python 3.12+
- FastAPI
- Uvicorn
- WebSockets support

### Installation

1. Make sure you have all dependencies installed:

```bash
pip install fastapi uvicorn websockets
```

2. Navigate to the project directory:

```bash
cd new_dashboard
```

### Running the Test Server

To run the test server with mock data:

```bash
# Using PowerShell
.\run_test_server.ps1

# Or using Python directly
python run_test_server.py
```

The test server will start on port 9050. You can access the dashboard at:

```
http://localhost:9050/test
```

### Running the Production Server

To run the production server connected to the actual bot:

```bash
# Using Python
python -m uvicorn dashboard.app:app --host 0.0.0.0 --port 9051
```

The production server will start on port 9051. You can access the dashboard at:

```
http://localhost:9051
```

## Architecture

The dashboard consists of the following components:

1. **FastAPI Backend**: Handles WebSocket connections and serves the dashboard UI
2. **WebSocket Server**: Provides real-time updates to connected clients
3. **Data Processing Layer**: Processes and formats data from the bot
4. **UI Layer**: Visualizes the data in an intuitive interface

## Development

### Test Environment

The test environment uses mock data to simulate the bot's behavior. This is useful for UI development and testing without needing to run the actual bot.

### Directory Structure

```
new_dashboard/
├── README.md
├── run_test_server.ps1
├── run_test_server.py
├── tests/
│   └── dashboard/
│       ├── app.py
│       └── templates/
│           └── test.html
└── dashboard/
    ├── app.py
    ├── static/
    └── templates/
```

## Integration with the Bot

The dashboard integrates with the Listonian Arbitrage Bot through a shared memory interface. The bot updates the shared memory with its current state, and the dashboard reads this data to display it to the user.

## Contributing

When contributing to the dashboard, please follow these guidelines:

1. Use async/await patterns for all I/O operations
2. Implement proper error handling
3. Add appropriate logging
4. Follow the project's coding standards

## License

This project is licensed under the terms of the license included with the Listonian Arbitrage Bot.