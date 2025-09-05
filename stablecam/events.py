"""
Event management system for StableCam.

This module provides a thread-safe event system that allows components to
subscribe to and emit events related to camera device state changes.
"""

import threading
from typing import Any, Callable, Dict, List
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Enumeration of supported event types."""
    ON_CONNECT = "on_connect"
    ON_DISCONNECT = "on_disconnect"
    ON_STATUS_CHANGE = "on_status_change"


class EventManager:
    """
    Thread-safe event manager for handling camera device events.
    
    Provides subscription-based event handling with support for multiple
    callbacks per event type and thread-safe event emission.
    """
    
    def __init__(self):
        """Initialize the event manager with empty subscriber lists."""
        self._subscribers: Dict[str, List[Callable]] = {
            EventType.ON_CONNECT.value: [],
            EventType.ON_DISCONNECT.value: [],
            EventType.ON_STATUS_CHANGE.value: []
        }
        self._lock = threading.RLock()
    
    def subscribe(self, event_type: str, callback: Callable) -> None:
        """
        Subscribe a callback function to an event type.
        
        Args:
            event_type: The type of event to subscribe to (must be a valid EventType)
            callback: The function to call when the event is emitted
            
        Raises:
            ValueError: If event_type is not a valid EventType
            TypeError: If callback is not callable
        """
        if not callable(callback):
            raise TypeError("Callback must be callable")
        
        # Validate event type
        valid_types = [e.value for e in EventType]
        if event_type not in valid_types:
            raise ValueError(f"Invalid event type '{event_type}'. Must be one of: {valid_types}")
        
        with self._lock:
            if callback not in self._subscribers[event_type]:
                self._subscribers[event_type].append(callback)
                logger.debug(f"Subscribed callback to {event_type}")
    
    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        """
        Unsubscribe a callback function from an event type.
        
        Args:
            event_type: The type of event to unsubscribe from
            callback: The callback function to remove
            
        Raises:
            ValueError: If event_type is not a valid EventType
        """
        # Validate event type
        valid_types = [e.value for e in EventType]
        if event_type not in valid_types:
            raise ValueError(f"Invalid event type '{event_type}'. Must be one of: {valid_types}")
        
        with self._lock:
            if callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)
                logger.debug(f"Unsubscribed callback from {event_type}")
    
    def emit(self, event_type: str, data: Any = None) -> None:
        """
        Emit an event to all subscribed callbacks.
        
        Executes all callbacks for the given event type in a thread-safe manner.
        If a callback raises an exception, it is logged but does not prevent
        other callbacks from executing.
        
        Args:
            event_type: The type of event to emit
            data: Optional data to pass to the callbacks
            
        Raises:
            ValueError: If event_type is not a valid EventType
        """
        # Validate event type
        valid_types = [e.value for e in EventType]
        if event_type not in valid_types:
            raise ValueError(f"Invalid event type '{event_type}'. Must be one of: {valid_types}")
        
        # Get a copy of subscribers to avoid holding the lock during callback execution
        with self._lock:
            callbacks = self._subscribers[event_type].copy()
        
        logger.debug(f"Emitting {event_type} event to {len(callbacks)} subscribers")
        
        # Execute callbacks outside the lock to prevent deadlocks
        for callback in callbacks:
            try:
                if data is not None:
                    callback(data)
                else:
                    callback()
            except Exception as e:
                logger.error(f"Error in event callback for {event_type}: {e}")
    
    def get_subscriber_count(self, event_type: str) -> int:
        """
        Get the number of subscribers for a given event type.
        
        Args:
            event_type: The event type to check
            
        Returns:
            int: Number of subscribers for the event type
            
        Raises:
            ValueError: If event_type is not a valid EventType
        """
        # Validate event type
        valid_types = [e.value for e in EventType]
        if event_type not in valid_types:
            raise ValueError(f"Invalid event type '{event_type}'. Must be one of: {valid_types}")
        
        with self._lock:
            return len(self._subscribers[event_type])
    
    def clear_subscribers(self, event_type: str = None) -> None:
        """
        Clear all subscribers for a specific event type or all event types.
        
        Args:
            event_type: The event type to clear. If None, clears all event types.
            
        Raises:
            ValueError: If event_type is provided but not a valid EventType
        """
        if event_type is not None:
            # Validate event type
            valid_types = [e.value for e in EventType]
            if event_type not in valid_types:
                raise ValueError(f"Invalid event type '{event_type}'. Must be one of: {valid_types}")
            
            with self._lock:
                self._subscribers[event_type].clear()
                logger.debug(f"Cleared all subscribers for {event_type}")
        else:
            with self._lock:
                for event_list in self._subscribers.values():
                    event_list.clear()
                logger.debug("Cleared all subscribers for all event types")