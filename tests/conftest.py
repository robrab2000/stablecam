"""
Pytest configuration and shared fixtures for StableCam tests.

This module provides common test fixtures, configuration, and utilities
used across all test modules for consistent testing setup.
"""

import pytest
import tempfile
import threading
import time
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch
from typing import List, Generator, Dict, Any

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from stablecam import CameraDevice, RegisteredDevice, DeviceStatus, StableCam
from stablecam.registry import DeviceRegistry


# Test markers configuration
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "slow: marks tests as slow running tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "linux: marks tests that require Linux platform")
    config.addinivalue_line("markers", "windows: marks tests that require Windows platform")
    config.addinivalue_line("markers", "macos: marks tests that require macOS platform")
    config.addinivalue_line("markers", "performance: marks tests as performance tests")
    config.addinivalue_line("markers", "tui: marks tests that require TUI components")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names and paths."""
    for item in items:
        # Add integration marker to integration test files
        if "test_integration" in item.fspath.basename:
            item.add_marker(pytest.mark.integration)
        
        # Add performance marker to performance test files
        if "test_performance" in item.fspath.basename:
            item.add_marker(pytest.mark.performance)
        
        # Add slow marker to tests with 'slow' in name
        if "slow" in item.name.lower():
            item.add_marker(pytest.mark.slow)
        
        # Add TUI marker to TUI-related tests
        if "tui" in item.name.lower() or "test_tui" in item.fspath.basename:
            item.add_marker(pytest.mark.tui)


# Shared fixtures
@pytest.fixture(scope="session")
def temp_dir():
    """Create a temporary directory for the test session."""
    with tempfile.TemporaryDirectory(prefix="stablecam_test_") as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def temp_registry_path(temp_dir):
    """Create a temporary registry file path."""
    registry_path = temp_dir / "test_registry.json"
    yield registry_path
    # Cleanup
    if registry_path.exists():
        registry_path.unlink()


@pytest.fixture
def clean_registry(temp_registry_path):
    """Create a clean DeviceRegistry instance for testing."""
    registry = DeviceRegistry(temp_registry_path)
    yield registry
    # Cleanup is handled by temp_registry_path fixture


@pytest.fixture
def sample_camera_device():
    """Create a sample CameraDevice for testing."""
    return CameraDevice(
        system_index=0,
        vendor_id="046d",
        product_id="085b",
        serial_number="ABC123456",
        port_path="/dev/video0",
        label="Test Camera Device",
        platform_data={"test": True, "mock": True}
    )


@pytest.fixture
def sample_camera_no_serial():
    """Create a sample CameraDevice without serial number."""
    return CameraDevice(
        system_index=1,
        vendor_id="1234",
        product_id="5678",
        serial_number=None,
        port_path="/dev/video1",
        label="Test Camera No Serial",
        platform_data={"test": True, "no_serial": True}
    )


@pytest.fixture
def multiple_camera_devices():
    """Create multiple CameraDevice instances for testing."""
    return [
        CameraDevice(
            system_index=i,
            vendor_id=f"{(0x1000 + i):04x}",
            product_id=f"{(0x2000 + i):04x}",
            serial_number=f"SERIAL{i:03d}" if i % 2 == 0 else None,
            port_path=f"/dev/video{i}",
            label=f"Test Camera {i}",
            platform_data={"test": True, "index": i}
        )
        for i in range(5)
    ]


@pytest.fixture
def sample_registered_device(sample_camera_device):
    """Create a sample RegisteredDevice for testing."""
    from datetime import datetime
    return RegisteredDevice(
        stable_id="stable-cam-001",
        device_info=sample_camera_device,
        status=DeviceStatus.CONNECTED,
        registered_at=datetime.now(),
        last_seen=datetime.now()
    )


@pytest.fixture
def mock_stablecam_manager(temp_registry_path):
    """Create a mock StableCam manager for testing."""
    manager = Mock(spec=StableCam)
    manager.registry_path = temp_registry_path
    manager.poll_interval = 0.1
    manager._monitoring = False
    manager._monitor_thread = None
    
    # Mock methods with reasonable defaults
    manager.detect.return_value = []
    manager.list.return_value = []
    manager.register.return_value = "stable-cam-001"
    manager.get_by_id.return_value = None
    manager.run.return_value = None
    manager.stop.return_value = None
    manager.on.return_value = None
    
    return manager


@pytest.fixture
def stablecam_instance(temp_registry_path):
    """Create a real StableCam instance for integration testing."""
    manager = StableCam(registry_path=temp_registry_path, poll_interval=0.1, enable_logging=False)
    yield manager
    # Cleanup
    if manager._monitoring:
        manager.stop()


class MockPlatformBackend:
    """Mock platform backend for testing."""
    
    def __init__(self, platform_name="test", devices=None):
        self.platform_name = platform_name
        self._devices = devices or []
    
    def enumerate_cameras(self):
        """Return mock camera devices."""
        return self._devices.copy()
    
    def get_device_info(self, system_index):
        """Get device info by system index."""
        for device in self._devices:
            if device.system_index == system_index:
                return device
        return None
    
    def set_devices(self, devices):
        """Set the devices to return from enumeration."""
        self._devices = devices.copy()


@pytest.fixture
def mock_platform_backend():
    """Create a mock platform backend."""
    return MockPlatformBackend()


@pytest.fixture
def patch_detector_with_mock_backend(mock_platform_backend):
    """Patch DeviceDetector to use mock backend."""
    with patch('stablecam.backends.DeviceDetector') as mock_detector_class:
        mock_detector = Mock()
        mock_detector.detect_cameras.return_value = []
        mock_detector.get_platform_backend.return_value = mock_platform_backend
        mock_detector_class.return_value = mock_detector
        yield mock_detector


class EventTracker:
    """Utility class for tracking events in tests."""
    
    def __init__(self):
        self.events = []
        self.event_counts = {}
        self.lock = threading.Lock()
    
    def track_event(self, event_type):
        """Create an event handler that tracks events."""
        def handler(device):
            with self.lock:
                event_data = {
                    'type': event_type,
                    'stable_id': device.stable_id,
                    'status': device.status,
                    'timestamp': time.time()
                }
                self.events.append(event_data)
                self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1
        return handler
    
    def get_events(self, event_type=None):
        """Get tracked events, optionally filtered by type."""
        with self.lock:
            if event_type:
                return [e for e in self.events if e['type'] == event_type]
            return self.events.copy()
    
    def get_count(self, event_type):
        """Get count of events by type."""
        with self.lock:
            return self.event_counts.get(event_type, 0)
    
    def clear(self):
        """Clear all tracked events."""
        with self.lock:
            self.events.clear()
            self.event_counts.clear()


@pytest.fixture
def event_tracker():
    """Create an EventTracker instance for testing."""
    return EventTracker()


class PerformanceTimer:
    """Utility class for timing operations in tests."""
    
    def __init__(self):
        self.times = {}
        self.start_times = {}
    
    def start(self, operation_name):
        """Start timing an operation."""
        self.start_times[operation_name] = time.perf_counter()
    
    def stop(self, operation_name):
        """Stop timing an operation and record the duration."""
        if operation_name in self.start_times:
            duration = time.perf_counter() - self.start_times[operation_name]
            self.times[operation_name] = duration
            del self.start_times[operation_name]
            return duration
        return None
    
    def get_time(self, operation_name):
        """Get the recorded time for an operation."""
        return self.times.get(operation_name)
    
    def get_all_times(self):
        """Get all recorded times."""
        return self.times.copy()


@pytest.fixture
def performance_timer():
    """Create a PerformanceTimer instance for testing."""
    return PerformanceTimer()


# Test utilities
def create_test_cameras(count: int, prefix: str = "TEST") -> List[CameraDevice]:
    """Create a list of test camera devices."""
    return [
        CameraDevice(
            system_index=i,
            vendor_id=f"{(0x1000 + i):04x}",
            product_id=f"{(0x2000 + i):04x}",
            serial_number=f"{prefix}{i:06d}" if i % 3 != 0 else None,  # Some without serial
            port_path=f"/dev/video{i}",
            label=f"{prefix} Camera {i}",
            platform_data={"test": True, "prefix": prefix, "index": i}
        )
        for i in range(count)
    ]


def wait_for_condition(condition_func, timeout=5.0, interval=0.1):
    """Wait for a condition to become true with timeout."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if condition_func():
            return True
        time.sleep(interval)
    return False


# Platform detection utilities
def get_current_platform():
    """Get the current platform name."""
    import platform
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    return system


def skip_if_not_platform(platform_name):
    """Skip test if not running on specified platform."""
    current = get_current_platform()
    return pytest.mark.skipif(
        current != platform_name,
        reason=f"Test requires {platform_name}, running on {current}"
    )


# TUI testing utilities
def check_textual_available():
    """Check if Textual is available for TUI testing."""
    try:
        import textual
        return True
    except ImportError:
        return False


skip_if_no_textual = pytest.mark.skipif(
    not check_textual_available(),
    reason="Textual not available for TUI testing"
)


# Environment setup for tests
@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment variables and cleanup."""
    # Set test environment variables
    original_env = os.environ.copy()
    os.environ["STABLECAM_TEST_MODE"] = "1"
    os.environ["STABLECAM_LOG_LEVEL"] = "WARNING"  # Reduce log noise in tests
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


# Memory and resource monitoring
@pytest.fixture
def memory_monitor():
    """Monitor memory usage during tests."""
    try:
        import psutil
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        yield {
            'initial': initial_memory,
            'process': process
        }
        
        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory
        
        # Warn if memory growth is excessive (>100MB)
        if memory_growth > 100 * 1024 * 1024:
            pytest.warns(UserWarning, f"Test caused significant memory growth: {memory_growth / 1024 / 1024:.1f} MB")
            
    except ImportError:
        # psutil not available, provide dummy monitor
        yield {'initial': 0, 'process': None}


# Cleanup utilities
@pytest.fixture(autouse=True)
def cleanup_threads():
    """Ensure no threads are left running after tests."""
    initial_thread_count = threading.active_count()
    
    yield
    
    # Wait a bit for threads to clean up
    time.sleep(0.1)
    
    final_thread_count = threading.active_count()
    if final_thread_count > initial_thread_count:
        # Give threads more time to clean up
        time.sleep(0.5)
        final_thread_count = threading.active_count()
        
        if final_thread_count > initial_thread_count:
            pytest.warns(
                UserWarning,
                f"Test left {final_thread_count - initial_thread_count} threads running"
            )


# Test data generators
@pytest.fixture
def camera_factory():
    """Factory function for creating test cameras."""
    def _create_cameras(count=1, **kwargs):
        defaults = {
            'vendor_id': '046d',
            'product_id': '085b',
            'label': 'Factory Test Camera',
            'platform_data': {'factory': True}
        }
        defaults.update(kwargs)
        
        cameras = []
        for i in range(count):
            camera_kwargs = defaults.copy()
            camera_kwargs.update({
                'system_index': i,
                'serial_number': f"FACTORY{i:06d}" if 'serial_number' not in kwargs else kwargs['serial_number'],
                'port_path': f"/dev/video{i}" if 'port_path' not in kwargs else kwargs['port_path'],
            })
            cameras.append(CameraDevice(**camera_kwargs))
        
        return cameras if count > 1 else cameras[0]
    
    return _create_cameras