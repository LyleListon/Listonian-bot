"""Event bus for the arbitrage bot."""

import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """Event class for the event bus."""
    
    type: str
    data: Dict[str, Any]
    timestamp: float = 0.0
    
    def __post_init__(self):
        """Initialize timestamp if not provided."""
        if not self.timestamp:
            self.timestamp = time.time()


class EventBus:
    """Event bus for publishing and subscribing to events."""
    
    def __init__(self):
        """Initialize the event bus."""
        self._subscribers: Dict[str, List[Callable[[Event], None]]] = {}
        self._event_history: List[Event] = []
        self._max_history_size = 1000
    
    def subscribe(self, event_type: str, callback: Callable[[Event], None]) -> None:
        """Subscribe to an event type.
        
        Args:
            event_type: The type of event to subscribe to.
            callback: The function to call when an event of this type is published.
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        self._subscribers[event_type].append(callback)
        logger.debug(f"Subscribed to event type: {event_type}")
    
    def unsubscribe(self, event_type: str, callback: Callable[[Event], None]) -> None:
        """Unsubscribe from an event type.
        
        Args:
            event_type: The type of event to unsubscribe from.
            callback: The function to remove from the subscribers.
        """
        if event_type in self._subscribers and callback in self._subscribers[event_type]:
            self._subscribers[event_type].remove(callback)
            logger.debug(f"Unsubscribed from event type: {event_type}")
    
    def publish(self, event: Event) -> None:
        """Publish an event to all subscribers.
        
        Args:
            event: The event to publish.
        """
        # Add to history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history_size:
            self._event_history.pop(0)
        
        # Notify subscribers
        if event.type in self._subscribers:
            for callback in self._subscribers[event.type]:
                try:
                    callback(event)
                except Exception as e:
                    logger.error(f"Error in event subscriber: {e}")
        
        logger.debug(f"Published event: {event.type}")
    
    def publish_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Create and publish an event.
        
        Args:
            event_type: The type of event to publish.
            data: The data to include in the event.
        """
        event = Event(type=event_type, data=data)
        self.publish(event)
    
    def get_history(
        self, event_type: Optional[str] = None, limit: int = 100
    ) -> List[Event]:
        """Get the event history.
        
        Args:
            event_type: The type of event to filter by. If None, all events are returned.
            limit: The maximum number of events to return.
            
        Returns:
            A list of events.
        """
        if event_type:
            filtered_history = [
                event for event in self._event_history if event.type == event_type
            ]
            return filtered_history[-limit:]
        
        return self._event_history[-limit:]
