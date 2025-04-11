import asyncio
import logging
import signal
import sys
from typing import Optional, Dict, Any, Callable, Awaitable

logger = logging.getLogger(__name__)


class SignalHandler:
    def __init__(self, loop: Optional[asyncio.AbstractEventLoop] = None):
        self._loop = loop or asyncio.get_event_loop()
        self._windows_signals: Dict[signal.Signals, Any] = {}
        self._cleanup_handler: Optional[Callable[[], Awaitable[None]]] = None

    def register_cleanup(self, handler: Callable[[], Awaitable[None]]) -> None:
        self._cleanup_handler = handler

    async def _handle_signal(self, sig: signal.Signals) -> None:
        logger.info(f"Received signal {sig.name}")
        if self._cleanup_handler:
            try:
                await self._cleanup_handler()
            except Exception as e:
                logger.error(f"Error in cleanup handler: {e}", exc_info=True)
        self._loop.stop()

    def setup(self) -> None:
        def windows_handler(signum: int, frame: Any) -> None:
            self._loop.create_task(self._handle_signal(signal.Signals(signum)))

        if sys.platform == "win32":
            for sig in (signal.SIGINT, signal.SIGTERM):
                old_handler = signal.signal(sig, windows_handler)
                self._windows_signals[sig] = old_handler
        else:
            for sig in (signal.SIGINT, signal.SIGTERM):
                try:
                    self._loop.add_signal_handler(
                        sig,
                        lambda s=sig: self._loop.create_task(self._handle_signal(s)),
                    )
                except NotImplementedError:
                    old_handler = signal.signal(sig, windows_handler)
                    self._windows_signals[sig] = old_handler

    def cleanup(self) -> None:
        if sys.platform == "win32" or self._windows_signals:
            for sig, original_handler in self._windows_signals.items():
                signal.signal(sig, original_handler)
            self._windows_signals.clear()
        else:
            for sig in (signal.SIGINT, signal.SIGTERM):
                try:
                    self._loop.remove_signal_handler(sig)
                except NotImplementedError:
                    pass
