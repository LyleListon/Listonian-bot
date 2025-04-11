"""
Log Parser Bridge

Bridges the gap between log files and the dashboard's data stores by parsing logs
and updating the OpportunityTracker in near real-time.
"""

import asyncio
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Pattern, Any
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

from arbitrage_bot.core.opportunity_tracker import OpportunityTracker

logger = logging.getLogger(__name__)


class LogFileHandler(FileSystemEventHandler):
    """Handles file system events for log files."""

    def __init__(self, callback):
        """Initialize the handler with a callback function."""
        self.callback = callback

    def on_modified(self, event):
        """Handle file modification events."""
        if isinstance(event, FileModifiedEvent):
            self.callback(event.src_path)


class LogParserBridge:
    """
    Bridges log files to OpportunityTracker by parsing logs and updating the tracker.
    Uses file system events for efficient monitoring and updates.
    """

    def __init__(
        self,
        log_dir: Path,
        opportunity_tracker: OpportunityTracker,
        update_frequency: float = 1.0,
        max_batch_size: int = 1000,
    ):
        """
        Initialize the Log Parser Bridge.

        Args:
            log_dir: Directory containing log files
            opportunity_tracker: OpportunityTracker instance to update
            update_frequency: How often to check for updates (seconds)
            max_batch_size: Maximum number of entries to process in one batch
        """
        self.log_dir = Path(log_dir)
        self.opportunity_tracker = opportunity_tracker
        self.update_frequency = update_frequency
        self.max_batch_size = max_batch_size

        # File position tracking
        self.file_positions: Dict[str, int] = {}

        # Compile regex patterns for different log types
        self.patterns = {
            "opportunity": re.compile(
                r"Found opportunity.*DEX: (.*) -> (.*), Token: (.*), "
                r"Price diff: ([\d.]+)%, Amount: ([\d.]+) ETH, "
                r"Expected profit: \$([\d.]+)"
            ),
            "execution": re.compile(
                r"Trade execution.*Hash: (0x[a-fA-F0-9]+), "
                r"Status: (\w+), Profit: \$([\d.]+), "
                r"Gas cost: \$([\d.]+)"
            ),
        }

        # Initialize file watcher
        self.observer = Observer()
        self.event_handler = LogFileHandler(self._handle_file_update)

        # Track active status
        self.is_running = False
        self.update_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the log parser bridge."""
        if self.is_running:
            logger.warning("Log Parser Bridge is already running")
            return

        try:
            # Ensure log directory exists
            self.log_dir.mkdir(exist_ok=True)

            # Start file system observer
            self.observer.schedule(
                self.event_handler, str(self.log_dir), recursive=False
            )
            self.observer.start()

            # Initialize file positions
            await self._initialize_file_positions()

            # Start update loop
            self.is_running = True
            self.update_task = asyncio.create_task(self._update_loop())

            logger.info("Log Parser Bridge started successfully")

        except Exception as e:
            logger.error(f"Failed to start Log Parser Bridge: {e}")
            await self.stop()
            raise

    async def stop(self):
        """Stop the log parser bridge."""
        self.is_running = False

        if self.update_task:
            self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass
            self.update_task = None

        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join()

        logger.info("Log Parser Bridge stopped")

    async def _initialize_file_positions(self):
        """Initialize file positions for all existing log files."""
        for pattern in ["opportunities_*.log", "execution_*.log"]:
            for log_file in self.log_dir.glob(pattern):
                if log_file.is_file():
                    self.file_positions[str(log_file)] = log_file.stat().st_size

    def _handle_file_update(self, file_path: str):
        """Handle file update events from the file system observer."""
        if not self.is_running:
            return

        # File position will be checked in the update loop
        logger.debug(f"Received update notification for {file_path}")

    async def _update_loop(self):
        """Main update loop that processes log files periodically."""
        while self.is_running:
            try:
                await self._process_log_updates()
                await asyncio.sleep(self.update_frequency)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in update loop: {e}")
                await asyncio.sleep(self.update_frequency * 2)  # Back off on error

    async def _process_log_updates(self):
        """Process updates from all log files."""
        for pattern in ["opportunities_*.log", "execution_*.log"]:
            for log_file in self.log_dir.glob(pattern):
                await self._process_single_file(log_file)

    async def _process_single_file(self, file_path: Path):
        """Process updates from a single log file."""
        try:
            current_size = file_path.stat().st_size
            last_position = self.file_positions.get(str(file_path), 0)

            if current_size == last_position:
                return  # No new content

            if current_size < last_position:
                # File was truncated
                logger.warning(
                    f"Log file {file_path} was truncated, resetting position"
                )
                last_position = 0

            # Read new content
            with open(file_path, "r") as f:
                f.seek(last_position)
                new_lines = f.readlines(self.max_batch_size)

            # Process new lines
            for line in new_lines:
                await self._process_log_line(line.strip())

            # Update position
            self.file_positions[str(file_path)] = current_size

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")

    async def _process_log_line(self, line: str):
        """Process a single log line and update OpportunityTracker if relevant."""
        try:
            # Try opportunity pattern first
            match = self.patterns["opportunity"].search(line)
            if match:
                dex_from, dex_to, token, price_diff, amount, profit = match.groups()
                await self._handle_opportunity(
                    dex_from.strip(),
                    dex_to.strip(),
                    token.strip(),
                    float(price_diff),
                    float(amount),
                    float(profit),
                )
                return

            # Try execution pattern
            match = self.patterns["execution"].search(line)
            if match:
                tx_hash, status, profit, gas_cost = match.groups()
                await self._handle_execution(
                    tx_hash, status, float(profit), float(gas_cost)
                )

        except Exception as e:
            logger.error(f"Error processing log line: {e}\nLine: {line}")

    async def _handle_opportunity(
        self,
        dex_from: str,
        dex_to: str,
        token: str,
        price_diff: float,
        amount: float,
        profit: float,
    ):
        """Handle an opportunity log entry."""
        opportunity_data = {
            "timestamp": datetime.now().isoformat(),
            "source_dex": dex_from,
            "target_dex": dex_to,
            "token": token,
            "price_diff_pct": price_diff,
            "amount": amount,
            "profit_usd": profit,
            "executed": False,  # Will be updated if execution log is found
        }
        self.opportunity_tracker.add_opportunity(opportunity_data)

    async def _handle_execution(
        self, tx_hash: str, status: str, profit: float, gas_cost: float
    ):
        """Handle an execution log entry."""
        execution_data = {
            "timestamp": datetime.now().isoformat(),
            "tx_hash": tx_hash,
            "status": status,
            "profit_usd": profit,
            "gas_cost_usd": gas_cost,
            "net_profit_usd": profit - gas_cost,
            "executed": status.lower() == "success",
        }
        self.opportunity_tracker.add_opportunity(execution_data)
