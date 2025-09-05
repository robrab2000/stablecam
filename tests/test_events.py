"""
Unit tests for the EventManager class.

Tests cover event subscription, unsubscription, emission, thread safety,
and error handling scenarios.
"""

import pytest
import threading
import time
from unittest.mock import Mock, patch
from stablecam.events import EventManager, EventType


class TestEventManager:
    """Test cases for the EventManager class."""
    
    def setup_method(self):
        """Set up a fresh EventManager for each test."""
        self.event_manager = EventManager()
    
    def test_initialization(self):
        """Test that EventManager initializes with empty subscriber lists."""
        for event_type in EventType:
            assert self.event_manager.get_subscriber_count(event_type.value) == 0
    
    def test_subscribe_valid_event_type(self):
        """Test subscribing to valid event types."""
        callback = Mock()
        
        # Test all valid event types
        for event_type in EventType:
            self.event_manager.subscribe(event_type.value, callback)
            assert self.event_manager.get_subscriber_count(event_type.value) == 1
    
    def test_subscribe_invalid_event_type(self):
        """Test that subscribing to invalid event type raises ValueError."""
        callback = Mock()
        
        with pytest.raises(ValueError, match="Invalid event type 'invalid_event'"):
            self.event_manager.subscribe("invalid_event", callback)
    
    def test_subscribe_non_callable(self):
        """Test that subscribing non-callable raises TypeError."""
        with pytest.raises(TypeError, match="Callback must be callable"):
            self.event_manager.subscribe(EventType.ON_CONNECT.value, "not_callable")
    
    def test_subscribe_duplicate_callback(self):
        """Test that subscribing the same callback twice doesn't create duplicates."""
        callback = Mock()
        event_type = EventType.ON_CONNECT.value
        
        self.event_manager.subscribe(event_type, callback)
        self.event_manager.subscribe(event_type, callback)
        
        assert self.event_manager.get_subscriber_count(event_type) == 1
    
    def test_unsubscribe_existing_callback(self):
        """Test unsubscribing an existing callback."""
        callback = Mock()
        event_type = EventType.ON_CONNECT.value
        
        self.event_manager.subscribe(event_type, callback)
        assert self.event_manager.get_subscriber_count(event_type) == 1
        
        self.event_manager.unsubscribe(event_type, callback)
        assert self.event_manager.get_subscriber_count(event_type) == 0
    
    def test_unsubscribe_non_existing_callback(self):
        """Test unsubscribing a callback that wasn't subscribed."""
        callback = Mock()
        event_type = EventType.ON_CONNECT.value
        
        # Should not raise an error
        self.event_manager.unsubscribe(event_type, callback)
        assert self.event_manager.get_subscriber_count(event_type) == 0
    
    def test_unsubscribe_invalid_event_type(self):
        """Test that unsubscribing from invalid event type raises ValueError."""
        callback = Mock()
        
        with pytest.raises(ValueError, match="Invalid event type 'invalid_event'"):
            self.event_manager.unsubscribe("invalid_event", callback)
    
    def test_emit_without_data(self):
        """Test emitting events without data."""
        callback1 = Mock()
        callback2 = Mock()
        event_type = EventType.ON_CONNECT.value
        
        self.event_manager.subscribe(event_type, callback1)
        self.event_manager.subscribe(event_type, callback2)
        
        self.event_manager.emit(event_type)
        
        callback1.assert_called_once_with()
        callback2.assert_called_once_with()
    
    def test_emit_with_data(self):
        """Test emitting events with data."""
        callback = Mock()
        event_type = EventType.ON_STATUS_CHANGE.value
        test_data = {"device_id": "stable-cam-001", "status": "connected"}
        
        self.event_manager.subscribe(event_type, callback)
        self.event_manager.emit(event_type, test_data)
        
        callback.assert_called_once_with(test_data)
    
    def test_emit_invalid_event_type(self):
        """Test that emitting invalid event type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid event type 'invalid_event'"):
            self.event_manager.emit("invalid_event")
    
    def test_emit_with_callback_exception(self):
        """Test that callback exceptions don't prevent other callbacks from executing."""
        callback1 = Mock(side_effect=Exception("Test exception"))
        callback2 = Mock()
        event_type = EventType.ON_DISCONNECT.value
        
        self.event_manager.subscribe(event_type, callback1)
        self.event_manager.subscribe(event_type, callback2)
        
        # Should not raise exception
        self.event_manager.emit(event_type)
        
        callback1.assert_called_once()
        callback2.assert_called_once()
    
    def test_multiple_event_types(self):
        """Test subscribing to multiple event types with different callbacks."""
        connect_callback = Mock()
        disconnect_callback = Mock()
        status_callback = Mock()
        
        self.event_manager.subscribe(EventType.ON_CONNECT.value, connect_callback)
        self.event_manager.subscribe(EventType.ON_DISCONNECT.value, disconnect_callback)
        self.event_manager.subscribe(EventType.ON_STATUS_CHANGE.value, status_callback)
        
        # Emit each event type
        self.event_manager.emit(EventType.ON_CONNECT.value)
        self.event_manager.emit(EventType.ON_DISCONNECT.value)
        self.event_manager.emit(EventType.ON_STATUS_CHANGE.value)
        
        connect_callback.assert_called_once()
        disconnect_callback.assert_called_once()
        status_callback.assert_called_once()
    
    def test_get_subscriber_count_invalid_event_type(self):
        """Test that getting subscriber count for invalid event type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid event type 'invalid_event'"):
            self.event_manager.get_subscriber_count("invalid_event")
    
    def test_clear_subscribers_specific_event(self):
        """Test clearing subscribers for a specific event type."""
        callback1 = Mock()
        callback2 = Mock()
        
        self.event_manager.subscribe(EventType.ON_CONNECT.value, callback1)
        self.event_manager.subscribe(EventType.ON_DISCONNECT.value, callback2)
        
        assert self.event_manager.get_subscriber_count(EventType.ON_CONNECT.value) == 1
        assert self.event_manager.get_subscriber_count(EventType.ON_DISCONNECT.value) == 1
        
        self.event_manager.clear_subscribers(EventType.ON_CONNECT.value)
        
        assert self.event_manager.get_subscriber_count(EventType.ON_CONNECT.value) == 0
        assert self.event_manager.get_subscriber_count(EventType.ON_DISCONNECT.value) == 1
    
    def test_clear_subscribers_all_events(self):
        """Test clearing subscribers for all event types."""
        callback = Mock()
        
        for event_type in EventType:
            self.event_manager.subscribe(event_type.value, callback)
        
        # Verify all have subscribers
        for event_type in EventType:
            assert self.event_manager.get_subscriber_count(event_type.value) == 1
        
        self.event_manager.clear_subscribers()
        
        # Verify all are cleared
        for event_type in EventType:
            assert self.event_manager.get_subscriber_count(event_type.value) == 0
    
    def test_clear_subscribers_invalid_event_type(self):
        """Test that clearing subscribers for invalid event type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid event type 'invalid_event'"):
            self.event_manager.clear_subscribers("invalid_event")


class TestEventManagerThreadSafety:
    """Test cases for thread safety of EventManager."""
    
    def setup_method(self):
        """Set up a fresh EventManager for each test."""
        self.event_manager = EventManager()
        self.results = []
        self.lock = threading.Lock()
    
    def callback_with_delay(self, data=None):
        """Test callback that adds to results with a small delay."""
        time.sleep(0.01)  # Small delay to increase chance of race conditions
        with self.lock:
            self.results.append(data or "called")
    
    def test_concurrent_subscribe_unsubscribe(self):
        """Test concurrent subscription and unsubscription operations."""
        event_type = EventType.ON_CONNECT.value
        callbacks = [Mock() for _ in range(10)]
        
        def subscribe_callbacks():
            for callback in callbacks:
                self.event_manager.subscribe(event_type, callback)
        
        def unsubscribe_callbacks():
            for callback in callbacks:
                self.event_manager.unsubscribe(event_type, callback)
        
        # Run subscribe and unsubscribe concurrently
        threads = [
            threading.Thread(target=subscribe_callbacks),
            threading.Thread(target=unsubscribe_callbacks)
        ]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Should not crash and final count should be consistent
        count = self.event_manager.get_subscriber_count(event_type)
        assert 0 <= count <= 10
    
    def test_concurrent_emit_operations(self):
        """Test concurrent event emission operations."""
        event_type = EventType.ON_STATUS_CHANGE.value
        num_threads = 5
        emissions_per_thread = 10
        
        self.event_manager.subscribe(event_type, self.callback_with_delay)
        
        def emit_events():
            for i in range(emissions_per_thread):
                self.event_manager.emit(event_type, f"thread_data_{i}")
        
        threads = [threading.Thread(target=emit_events) for _ in range(num_threads)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All emissions should have been processed
        assert len(self.results) == num_threads * emissions_per_thread
    
    def test_subscribe_during_emit(self):
        """Test subscribing new callbacks while events are being emitted."""
        event_type = EventType.ON_CONNECT.value
        initial_callback = Mock()
        
        self.event_manager.subscribe(event_type, initial_callback)
        
        def continuous_emit():
            for _ in range(50):
                self.event_manager.emit(event_type)
                time.sleep(0.001)
        
        def add_callbacks():
            time.sleep(0.01)  # Let some emissions happen first
            for i in range(5):
                new_callback = Mock()
                self.event_manager.subscribe(event_type, new_callback)
                time.sleep(0.005)
        
        emit_thread = threading.Thread(target=continuous_emit)
        subscribe_thread = threading.Thread(target=add_callbacks)
        
        emit_thread.start()
        subscribe_thread.start()
        
        emit_thread.join()
        subscribe_thread.join()
        
        # Should not crash and initial callback should have been called
        assert initial_callback.call_count > 0
        # Final subscriber count should include the new callbacks
        assert self.event_manager.get_subscriber_count(event_type) == 6


class TestEventType:
    """Test cases for the EventType enum."""
    
    def test_event_type_values(self):
        """Test that EventType enum has the correct values."""
        assert EventType.ON_CONNECT.value == "on_connect"
        assert EventType.ON_DISCONNECT.value == "on_disconnect"
        assert EventType.ON_STATUS_CHANGE.value == "on_status_change"
    
    def test_event_type_completeness(self):
        """Test that all required event types are defined."""
        expected_events = {"on_connect", "on_disconnect", "on_status_change"}
        actual_events = {event.value for event in EventType}
        assert actual_events == expected_events