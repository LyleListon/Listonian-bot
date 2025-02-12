"""Flask application for arbitrage bot dashboard."""

import os
import json
import logging
import asyncio
import eventlet
eventlet.monkey_patch()  # Patch all blocking operations

from datetime import datetime
from flask import Flask, render_template, send_from_directory
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from ..core.memory import get_memory_bank
from ..core.storage.factory import create_storage_hub
from ..core.distribution import DistributionManager, DistributionConfig
from ..core.execution import ExecutionManager, ExecutionConfig
from ..core.web3.web3_manager import create_web3_manager
from decimal import Decimal

# Configure logging
logging.basicConfig(level=logging.INFO)
logging.getLogger('werkzeug').setLevel(logging.ERROR)
logging.getLogger('socketio').setLevel(logging.ERROR)
logging.getLogger('engineio').setLevel(logging.ERROR)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def create_app():
    """Create Flask application."""
    app = Flask(__name__, 
        template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
        static_folder=os.path.join(os.path.dirname(__file__), 'static')
    )
    app.config['SECRET_KEY'] = os.urandom(24)
    
    # Configure CORS for codespace access
    CORS(app, resources={
        r"/*": {"origins": "*"},
        r"/socket.io/*": {"origins": "*"}
    })

    # Load config
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'configs', 'config.json')
    with open(config_path) as f:
        config = json.load(f)

    # Load memory config
    memory_config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'configs', 'memory_config.json')
    logger.debug(f"Loading memory config from {memory_config_path}")
    with open(memory_config_path) as f:
        memory_config = json.load(f)

    # Initialize memory bank with config
    logger.debug("Initializing memory bank...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    memory_bank = loop.run_until_complete(get_memory_bank(memory_config))
    
    if not getattr(memory_bank, '_initialized', False):
        logger.error("Memory bank manager failed to initialize")
        raise RuntimeError("Memory bank manager initialization failed")

    if not getattr(memory_bank.memory_bank, 'initialized', False):
        logger.error("Memory bank failed to initialize")
        raise RuntimeError("Memory bank initialization failed")

    # Initialize storage hub
    storage_hub = create_storage_hub()

    # Initialize distribution manager with correct config parameters
    distribution_config = DistributionConfig(
        max_exposure_per_dex=Decimal('1.0'),
        max_exposure_per_pair=Decimal('0.5'),
        min_liquidity_threshold=Decimal('10000'),
        rebalance_threshold=Decimal('0.2'),
        gas_price_weight=0.3,
        liquidity_weight=0.3,
        volume_weight=0.2,
        success_rate_weight=0.2
    )
    distribution_manager = DistributionManager(distribution_config, memory_bank=memory_bank)
    
    execution_config = ExecutionConfig(
        max_slippage=Decimal("0.005"),
        gas_limit=300000,
        max_gas_price=Decimal("100"),
        retry_attempts=3,
        retry_delay=5,
        confirmation_blocks=2,
        timeout=60
    )

    # Initialize execution manager only if web3 is available
    execution_manager = None
    web3_manager = None
    try:
        web3_manager = loop.run_until_complete(create_web3_manager(config))
        if web3_manager:
            execution_manager = ExecutionManager(
                config=execution_config,
                web3=web3_manager.w3,
                distribution_manager=distribution_manager,
                memory_bank=memory_bank
            )
    except Exception as e:
        logger.error(f"Failed to initialize web3: {e}")
    
    # Configure SocketIO with eventlet
    socketio = SocketIO(
        app,
        cors_allowed_origins="*",
        logger=True,  # Enable logging for debugging
        engineio_logger=True,  # Enable engine.io logging
        async_mode='eventlet',
        ping_timeout=60,
        ping_interval=25,
        max_http_buffer_size=1000000,  # 1MB
        path='/socket.io/',  # Explicit path for codespace compatibility
        manage_session=True,  # Enable session management
        async_handlers=True
    )

    # Store last update times for rate limiting
    last_update = {
        'system': 0,
        'metrics': 0,
        'performance': 0,
        'memory': 0,
        'storage': 0,
        'distribution': 0,
        'execution': 0
    }

    # Update intervals (in seconds)
    update_intervals = {
        'system': 5,
        'metrics': 5,
        'performance': 10,
        'memory': 2,
        'storage': 5,
        'distribution': 2,
        'execution': 2
    }

    def should_emit(event_type: str) -> bool:
        """Check if event should be emitted based on rate limiting."""
        current_time = int(datetime.now().timestamp())
        if current_time - last_update[event_type] >= update_intervals[event_type]:
            last_update[event_type] = current_time
            return True
        return False

    async def broadcast_memory_stats():
        """Async function to broadcast memory statistics."""
        while True:
            if should_emit('memory'):
                try:
                    # Get memory stats
                    logger.debug("Fetching memory stats...")
                    mem_stats = await memory_bank.get_memory_stats()
                    logger.debug(f"Raw memory stats: {mem_stats}")
                    
                    # Convert NamedTuple to dict with actual values
                    stats_dict = {
                        'cache_size': mem_stats.cache_size,
                        'total_size': mem_stats.total_size_bytes,
                        'disk_size': mem_stats.total_size_bytes,
                        'total_entries': mem_stats.total_entries,
                        'categories': {
                            cat: {
                                'size': data.get('size', 0),
                                'items': data.get('items', [])
                            }
                            for cat, data in mem_stats.categories.items()
                        },
                        'cache_hits': mem_stats.cache_hits,
                        'cache_misses': mem_stats.cache_misses
                    }
                    
                    # Get compression stats
                    comp_stats = memory_bank.get_compression_stats()
                    
                    # Get category stats
                    category_stats = {}
                    for category in memory_bank._categories:
                        category_stats[category] = {
                            'files': [],
                            'size': 0
                        }
                    
                    # Emit stats in the format expected by frontend
                    socketio.emit('memory_stats', {
                        'stats': {
                            'memory': stats_dict,
                            'compression': comp_stats,
                            'categories': category_stats
                        }
                    }, namespace='/')
                    
                    logger.debug(f"Memory stats: {stats_dict}")
                    
                except Exception as e:
                    logger.error(f"Error broadcasting memory stats: {e}")
            
            await asyncio.sleep(update_intervals['memory'])

    async def broadcast_storage_stats():
        """Async function to broadcast storage statistics."""
        while True:
            if should_emit('storage'):
                try:
                    # Calculate storage stats
                    stats = {
                        'data_size': 0,
                        'backup_size': 0,
                        'metadata_size': 0,
                        'total_items': 0,
                        'categories': {}
                    }
                    
                    # Collect stats from each storage manager
                    for category, manager in [
                        ('trades', storage_hub.trades),
                        ('opportunities', storage_hub.opportunities),
                        ('market_data', storage_hub.market_data),
                        ('config', storage_hub.config),
                        ('performance', storage_hub.performance),
                        ('errors', storage_hub.errors),
                        ('health', storage_hub.health)
                    ]:
                        # Initialize stats for this category
                        stats['categories'][category] = {
                            'items': 0,
                            'size': 0
                        }
                    
                    # Collect recent activity
                    activities = []
                    for category, manager in [
                        ('trades', storage_hub.trades),
                        ('opportunities', storage_hub.opportunities),
                        ('market_data', storage_hub.market_data)
                    ]:
                        for key in manager.list_keys():
                            metadata = manager.get_metadata(key)
                            if metadata:
                                activities.append({
                                    'timestamp': metadata.updated_at,
                                    'category': category,
                                    'action': 'update',
                                    'key': key
                                })
                    
                    # Sort activities by timestamp (most recent first)
                    activities.sort(key=lambda x: x['timestamp'], reverse=True)
                    activities = activities[:10]  # Keep only 10 most recent
                    
                    # Collect backup status
                    backup_status = {}
                    for category, manager in [
                        ('trades', storage_hub.trades),
                        ('opportunities', storage_hub.opportunities),
                        ('market_data', storage_hub.market_data),
                        ('config', storage_hub.config)
                    ]:
                        backup_path = manager.base_path / "backups"
                        if backup_path.exists():
                            backups = list(backup_path.glob("*.json"))
                            if backups:
                                latest = max(backups, key=lambda p: p.stat().st_mtime)
                                backup_status[category] = {
                                    'items': len(backups),
                                    'last_backup': latest.stat().st_mtime,
                                    'size': sum(f.stat().st_size for f in backups)
                                }
                    
                    # Emit all stats
                    socketio.emit('storage_stats', {
                        'type': 'storage_stats',
                        'stats': stats
                    }, namespace='/')
                    
                    socketio.emit('storage_stats', {
                        'type': 'activity_log',
                        'activities': activities
                    }, namespace='/')
                    
                    socketio.emit('storage_stats', {
                        'type': 'backup_status',
                        'backups': backup_status
                    }, namespace='/')
                except Exception as e:
                    logger.error(f"Error broadcasting storage stats: {e}")
            
            await asyncio.sleep(update_intervals['storage'])

    async def broadcast_distribution_stats():
        """Async function to broadcast distribution statistics."""
        while True:
            if should_emit('distribution'):
                try:
                    # Get distribution stats
                    stats = distribution_manager.get_distribution_stats()
                    
                    # Get rebalancing trades if needed
                    rebalancing_actions = []
                    if stats['needs_rebalancing']:
                        trades = distribution_manager.get_rebalancing_trades()
                        rebalancing_actions = [
                            {
                                'from_dex': from_dex,
                                'to_dex': to_dex,
                                'pair': pair,
                                'amount': str(amount)
                            }
                            for from_dex, to_dex, pair, amount in trades
                        ]
                    
                    # Emit stats
                    socketio.emit('distribution_stats', {
                        'type': 'distribution_stats',
                        'stats': stats
                    }, namespace='/')
                    
                    socketio.emit('distribution_stats', {
                        'type': 'dex_scores',
                        'scores': stats['dex_scores']
                    }, namespace='/')
                    
                    socketio.emit('distribution_stats', {
                        'type': 'rebalancing_actions',
                        'actions': rebalancing_actions
                    }, namespace='/')
                except Exception as e:
                    logger.error(f"Error broadcasting distribution stats: {e}")
            
            await asyncio.sleep(update_intervals['distribution'])

    async def broadcast_execution_stats():
        """Async function to broadcast execution statistics."""
        while True:
            if should_emit('execution') and execution_manager:
                try:
                    # Get active executions
                    active_executions = execution_manager.get_active_executions()
                    
                    # Get recent transactions from storage
                    transactions = storage_hub.trades.retrieve_recent(10)
                    
                    # Get execution metrics
                    metrics = storage_hub.performance.retrieve("execution_metrics")
                    if metrics:
                        # Calculate gas metrics
                        gas_metrics = {
                            'avgGasUsed': metrics['average_gas_used'],
                            'avgGasPrice': metrics['average_gas_price'],
                            'totalGasCost': metrics['total_gas_cost'],
                            'history': [
                                {
                                    'timestamp': m['timestamp'],
                                    'gas_price': m['gas_price']
                                }
                                for m in metrics.get('gas_history', [])
                            ]
                        }
                        
                        # Calculate performance stats
                        performance_stats = {
                            'total_executions': metrics['total_executions'],
                            'successful_executions': metrics['successful_executions'],
                            'failed_executions': metrics['failed_executions'],
                            'average_confirmation_time': metrics['average_confirmation_time']
                        }
                        
                        # Emit stats
                        socketio.emit('execution_stats', {
                            'type': 'active_executions',
                            'executions': active_executions
                        }, namespace='/')
                        
                        socketio.emit('execution_stats', {
                            'type': 'transaction_history',
                            'transactions': transactions
                        }, namespace='/')
                        
                        socketio.emit('execution_stats', {
                            'type': 'gas_metrics',
                            'metrics': gas_metrics
                        }, namespace='/')
                        
                        socketio.emit('execution_stats', {
                            'type': 'performance_stats',
                            'stats': performance_stats
                        }, namespace='/')
                except Exception as e:
                    logger.error(f"Error broadcasting execution stats: {e}")
            
            await asyncio.sleep(update_intervals['execution'])

    # Start async broadcasters
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection."""
        logger.info("New client connection established")
        
        # Send initial performance stats
        try:
            initial_stats = {
                'type': 'performance_stats',
                'stats': {
                    'total_profit': 1234.56,
                    'active_opportunities': 5,
                    'successful_executions': 100,
                    'total_executions': 120,
                    'total_gas_cost': 0.5,
                    'profit_history': [
                        {
                            'timestamp': datetime.now().timestamp() - i * 3600,
                            'profit': float(1000 + i * 100)
                        }
                        for i in range(10)
                    ],
                    'gas_history': [
                        {
                            'timestamp': datetime.now().timestamp() - i * 3600,
                            'gas_price': float(50 - i * 2)
                        }
                        for i in range(10)
                    ]
                }
            }
            emit('execution_stats', initial_stats, namespace='/')
        except Exception as e:
            logger.error(f"Error sending initial stats: {e}")

        # Send initial activity log
        try:
            initial_activities = {
                'type': 'activity_log',
                'activities': [{
                    'timestamp': float(datetime.now().timestamp()),
                    'category': 'trades',
                    'action': 'Trade executed',
                    'key': 'ETH/USDC',
                    'profit': '0.25 ETH'
                }]
            }
            emit('storage_stats', initial_activities, namespace='/')
        except Exception as e:
            logger.error(f"Error sending initial activities: {e}")
            
        # Start broadcasters
        eventlet.spawn(broadcast_memory_stats)
        eventlet.spawn(broadcast_storage_stats)
        eventlet.spawn(broadcast_distribution_stats)
        eventlet.spawn(broadcast_execution_stats)
        emit('system_update', {'status': 'connected'}, namespace='/')

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection."""
        logger.info("Client disconnected")

    @socketio.on('system_update')
    def handle_system_update(data):
        """Handle system update event."""
        if should_emit('system'):
            emit('system_update', data, namespace='/')

    @socketio.on('metrics_update')
    def handle_metrics_update(data):
        """Handle metrics update event."""
        if should_emit('metrics'):
            emit('metrics_update', data, namespace='/')

    @socketio.on('performance_update')
    def handle_performance_update(data):
        """Handle performance update event."""
        if should_emit('performance'):
            emit('performance_update', data, namespace='/')

    @app.route('/')
    def index():
        """Render dashboard index page."""
        return render_template('index.html')

    @app.route('/opportunities')
    def opportunities():
        """Render opportunities page."""
        return render_template('opportunities.html')

    @app.route('/history')
    def history():
        """Render trade history page."""
        return render_template('history.html')

    @app.route('/analytics')
    def analytics():
        """Render analytics page."""
        return render_template('analytics.html')

    @app.route('/memory')
    def memory():
        """Render memory monitor page."""
        return render_template('memory.html')

    @app.route('/storage')
    def storage():
        """Render storage monitor page."""
        return render_template('storage.html')

    @app.route('/distribution')
    def distribution():
        """Render distribution monitor page."""
        return render_template('distribution.html')

    @app.route('/execution')
    def execution():
        """Render execution monitor page."""
        return render_template('execution.html')

    @app.route('/settings')
    def settings():
        """Render settings page."""
        return render_template('settings.html')

    @app.route('/static/<path:path>')
    def send_static(path):
        """Serve static files."""
        return send_from_directory('static', path)

    @socketio.on('get_settings')
    def handle_get_settings():
        """Handle settings request."""
        try:
            # Load settings from config files
            config_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'configs')
            trading_config_path = os.path.join(config_dir, 'trading_config.json')
            dex_config_path = os.path.join(config_dir, 'dex_config.json')

            settings = {}
            if os.path.exists(trading_config_path):
                with open(trading_config_path, 'r') as f:
                    settings['trading'] = json.load(f)
            if os.path.exists(dex_config_path):
                with open(dex_config_path, 'r') as f:
                    settings['dex'] = json.load(f)

            emit('settings_update', settings, namespace='/')
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            emit('settings_error', str(e), namespace='/')

    @socketio.on('save_settings')
    def handle_save_settings(data):
        """Handle settings save request."""
        try:
            config_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'configs')
            
            if 'trading' in data:
                trading_config_path = os.path.join(config_dir, 'trading_config.json')
                with open(trading_config_path, 'w') as f:
                    json.dump(data['trading'], f, indent=2)
            
            if 'dex' in data:
                dex_config_path = os.path.join(config_dir, 'dex_config.json')
                with open(dex_config_path, 'w') as f:
                    json.dump(data['dex'], f, indent=2)
            
            emit('settings_saved', namespace='/')
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            emit('settings_error', str(e), namespace='/')

    return app, socketio

# Create application instance
app, socketio = create_app()

# Configure port from environment or config
port = int(os.getenv('DASHBOARD_PORT', 5001))  # Use dashboard port from config
host = '0.0.0.0'  # Bind to all interfaces for codespace access

if __name__ == '__main__':
    logger.info(f"Starting dashboard on {host}:{port}")
    socketio.run(app, host=host, port=port, allow_unsafe_werkzeug=True)