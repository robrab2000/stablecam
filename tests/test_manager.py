"""
Integration tests for StableCam manager class.

Tests the main StableCam manager functionality including device detection,
registration, event handling, and monitoring loop integration.
"""

import pytest
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from stablecam.manager import StableCam
from stablecam.models import CameraDevice, RegisteredDevice, DeviceStatus
from stablecam.registry import RegistryError
from stablecam.backends import PlatformDetectionError
from stablecam.events import EventType


class TestStableCamManager:
    """Test suite for StableCam manager class."""
    
    @pytest.fixture
    def temp_registry(self):
        """Create a temporary registry file for testing."""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            registry_path = Path(f.name)
        # Remove the empty file so DeviceRegistry can create it properly
        registry_path.unlink()
        yield registry_path
        # Cleanup
        if registry_path.exists():
            registry_path.unlink()
    
    @pytest.fixture
    def sample_camera(self):
        """Create a sample camera device for testing."""
        return CameraDevice(
            system_index=0,
            vendor_id="046d",
            product_id="085b",
            serial_number="ABC123456",
            port_path="/dev/video0",
            label="Test Camera",
            platform_data={"test": "data"}
        )
    
    @pytest.fixture
    def sample_camera_no_serial(self):
        """Create a sample camera device without serial number."""
        return CameraDevice(
            system_index=1,
            vendor_id="1234",
            product_id="5678",
            serial_number=None,
            port_path="/dev/video1",
            label="Test Camera No Serial",
            platform_data={"test": "data"}
        )
    
    @pytest.fixture
    def stablecam(self, temp_registry):
        """Create StableCam instance with temporary registry."""
        return StableCam(registry_path=temp_registry, poll_interval=0.1)
    
    def test_init(self, temp_registry):
        """Test StableCam initialization."""
        manager = StableCam(registry_path=temp_registry, poll_interval=1.0)
        
        assert manager.registry is not None
        assert manager.detector is not None
        assert manager.events is not None
        assert manager.poll_interval == 1.0
        assert not manager._monitoring
        assert manager._monitor_thread is None
    
    def test_init_default_registry(self):
        """Test StableCam initialization with default registry path."""
        manager = StableCam()
        
        assert manager.registry is not None
        assert manager.detector is not None
        assert manager.events is not None
        assert manager.poll_interval == 2.0
    
    @patch('stablecam.manager.DeviceDetector')
    def test_detect_success(self, mock_detector_class, stablecam, sample_camera):
        """Test successful camera detection."""
        # Setup mock
        mock_detector = Mock()
        mock_detector.detect_cameras.return_value = [sample_camera]
        mock_detector_class.return_value = mock_detector
        
        # Create new instance to use mocked detector
        manager = StableCam(poll_interval=0.1)
        manager.detector = mock_detector
        
        # Test detection
        devices = manager.detect()
        
        assert len(devices) == 1
        assert devices[0] == sample_camera
        mock_detector.detect_cameras.assert_called_once()
    
    @patch('stablecam.manager.DeviceDetector')
    def test_detect_failure(self, mock_detector_class, stablecam):
        """Test camera detection failure."""
        # Setup mock to raise exception
        mock_detector = Mock()
        mock_detector.detect_cameras.side_effect = Exception("Detection failed")
        mock_detector_class.return_value = mock_detector
        
        # Create new instance to use mocked detector
        manager = StableCam(poll_interval=0.1)
        manager.detector = mock_detector
        
        # Test detection failure
        with pytest.raises(PlatformDetectionError):
            manager.detect()
    
    def test_register_new_device(self, stablecam, sample_camera):
        """Test registering a new device."""
        # Mock detector to return empty list (no devices detected)
        with patch.object(stablecam.detector, 'detect_cameras', return_value=[]):
            stable_id = stablecam.register(sample_camera)
        
        assert stable_id == "stable-cam-001"
        
        # Verify device is in registry
        registered_device = stablecam.get_by_id(stable_id)
        assert registered_device is not None
        assert registered_device.stable_id == stable_id
        assert registered_device.status == DeviceStatus.CONNECTED
    
    def test_register_existing_device(self, stablecam, sample_camera):
        """Test registering an already registered device."""
        # Register device first time
        with patch.object(stablecam.detector, 'detect_cameras', return_value=[]):
            stable_id1 = stablecam.register(sample_camera)
        
        # Register same device again
        with patch.object(stablecam.detector, 'detect_cameras', return_value=[]):
            stable_id2 = stablecam.register(sample_camera)
        
        # Should return same stable ID
        assert stable_id1 == stable_id2
        
        # Should only have one device in registry
        devices = stablecam.list()
        assert len(devices) == 1
    
    def test_register_with_events(self, stablecam, sample_camera):
        """Test that registration emits appropriate events."""
        connect_callback = Mock()
        status_callback = Mock()
        
        stablecam.on(EventType.ON_CONNECT.value, connect_callback)
        stablecam.on(EventType.ON_STATUS_CHANGE.value, status_callback)
        
        # Register device
        with patch.object(stablecam.detector, 'detect_cameras', return_value=[]):
            stable_id = stablecam.register(sample_camera)
        
        # Verify events were emitted
        connect_callback.assert_called_once()
        status_callback.assert_called_once()
        
        # Verify event data
        registered_device = connect_callback.call_args[0][0]
        assert registered_device.stable_id == stable_id
    
    def test_list_devices(self, stablecam, sample_camera, sample_camera_no_serial):
        """Test listing all registered devices."""
        # Initially empty
        devices = stablecam.list()
        assert len(devices) == 0
        
        # Register devices
        with patch.object(stablecam.detector, 'detect_cameras', return_value=[]):
            stablecam.register(sample_camera)
            stablecam.register(sample_camera_no_serial)
        
        # List devices
        devices = stablecam.list()
        assert len(devices) == 2
        
        stable_ids = [device.stable_id for device in devices]
        assert "stable-cam-001" in stable_ids
        assert "stable-cam-002" in stable_ids
    
    def test_get_by_id_existing(self, stablecam, sample_camera):
        """Test getting device by existing stable ID."""
        # Register device
        with patch.object(stablecam.detector, 'detect_cameras', return_value=[]):
            stable_id = stablecam.register(sample_camera)
        
        # Get by ID
        device = stablecam.get_by_id(stable_id)
        
        assert device is not None
        assert device.stable_id == stable_id
        assert device.device_info.vendor_id == sample_camera.vendor_id
    
    def test_get_by_id_nonexistent(self, stablecam):
        """Test getting device by non-existent stable ID."""
        device = stablecam.get_by_id("nonexistent-id")
        assert device is None
    
    def test_event_subscription(self, stablecam):
        """Test event subscription functionality."""
        callback = Mock()
        
        # Subscribe to event
        stablecam.on(EventType.ON_CONNECT.value, callback)
        
        # Verify subscription
        count = stablecam.events.get_subscriber_count(EventType.ON_CONNECT.value)
        assert count == 1
    
    def test_event_subscription_invalid_type(self, stablecam):
        """Test event subscription with invalid event type."""
        callback = Mock()
        
        with pytest.raises(ValueError):
            stablecam.on("invalid_event", callback)
    
    def test_event_subscription_invalid_callback(self, stablecam):
        """Test event subscription with invalid callback."""
        with pytest.raises(TypeError):
            stablecam.on(EventType.ON_CONNECT.value, "not_callable")
    
    def test_monitoring_start_stop(self, stablecam):
        """Test starting and stopping device monitoring."""
        assert not stablecam._monitoring
        
        # Start monitoring
        stablecam.run()
        assert stablecam._monitoring
        assert stablecam._monitor_thread is not None
        
        # Stop monitoring
        stablecam.stop()
        assert not stablecam._monitoring
    
    def test_monitoring_double_start(self, stablecam):
        """Test starting monitoring when already running."""
        stablecam.run()
        assert stablecam._monitoring
        
        # Try to start again - should not crash
        stablecam.run()
        assert stablecam._monitoring
        
        stablecam.stop()
    
    def test_monitoring_double_stop(self, stablecam):
        """Test stopping monitoring when not running."""
        assert not stablecam._monitoring
        
        # Try to stop when not running - should not crash
        stablecam.stop()
        assert not stablecam._monitoring
    
    def test_monitoring_device_connection(self, stablecam, sample_camera):
        """Test monitoring detects device connections."""
        connect_callback = Mock()
        status_callback = Mock()
        
        stablecam.on(EventType.ON_CONNECT.value, connect_callback)
        stablecam.on(EventType.ON_STATUS_CHANGE.value, status_callback)
        
        # Register device as disconnected
        with patch.object(stablecam.detector, 'detect_cameras', return_value=[]):
            stable_id = stablecam.register(sample_camera)
        
        # Set device as disconnected
        stablecam.registry.update_status(stable_id, DeviceStatus.DISCONNECTED)
        
        # Clear previous event calls
        connect_callback.reset_mock()
        status_callback.reset_mock()
        
        # Start monitoring with device detected
        with patch.object(stablecam.detector, 'detect_cameras', return_value=[sample_camera]):
            stablecam.run()
            
            # Wait for monitoring loop to run
            time.sleep(0.2)
            
            stablecam.stop()
        
        # Verify connection events were emitted
        assert connect_callback.called
        assert status_callback.called
    
    def test_monitoring_device_disconnection(self, stablecam, sample_camera):
        """Test monitoring detects device disconnections."""
        disconnect_callback = Mock()
        status_callback = Mock()
        
        stablecam.on(EventType.ON_DISCONNECT.value, disconnect_callback)
        stablecam.on(EventType.ON_STATUS_CHANGE.value, status_callback)
        
        # Register device as connected
        with patch.object(stablecam.detector, 'detect_cameras', return_value=[sample_camera]):
            stable_id = stablecam.register(sample_camera)
        
        # Clear previous event calls
        disconnect_callback.reset_mock()
        status_callback.reset_mock()
        
        # Start monitoring with no devices detected
        with patch.object(stablecam.detector, 'detect_cameras', return_value=[]):
            stablecam.run()
            
            # Wait for monitoring loop to run
            time.sleep(0.2)
            
            stablecam.stop()
        
        # Verify disconnection events were emitted
        assert disconnect_callback.called
        assert status_callback.called
    
    def test_monitoring_error_handling(self, stablecam):
        """Test monitoring handles detection errors gracefully."""
        # Mock detector to raise exception
        with patch.object(stablecam.detector, 'detect_cameras', side_effect=Exception("Detection error")):
            stablecam.run()
            
            # Wait for monitoring loop to run and handle error
            time.sleep(0.2)
            
            # Should still be monitoring despite error
            assert stablecam._monitoring
            
            stablecam.stop()
    
    def test_context_manager(self, temp_registry):
        """Test StableCam as context manager."""
        with StableCam(registry_path=temp_registry) as manager:
            assert manager is not None
            manager.run()
            assert manager._monitoring
        
        # Should automatically stop monitoring on exit
        assert not manager._monitoring
    
    def test_system_index_update_on_reconnection(self, stablecam, sample_camera):
        """Test that system index is updated when device reconnects to different port."""
        # Register device
        with patch.object(stablecam.detector, 'detect_cameras', return_value=[sample_camera]):
            stable_id = stablecam.register(sample_camera)
        
        # Create same device with different system index
        reconnected_camera = CameraDevice(
            system_index=5,  # Different system index
            vendor_id=sample_camera.vendor_id,
            product_id=sample_camera.product_id,
            serial_number=sample_camera.serial_number,
            port_path=sample_camera.port_path,
            label=sample_camera.label,
            platform_data=sample_camera.platform_data
        )
        
        # Simulate disconnection then reconnection
        stablecam.registry.update_status(stable_id, DeviceStatus.DISCONNECTED)
        
        with patch.object(stablecam.detector, 'detect_cameras', return_value=[reconnected_camera]):
            stablecam.run()
            time.sleep(0.2)
            stablecam.stop()
        
        # Verify system index was updated
        registered_device = stablecam.get_by_id(stable_id)
        assert registered_device.device_info.system_index == 5
        assert registered_device.status == DeviceStatus.CONNECTED


class TestStableCamIntegration:
    """Integration tests for StableCam with real components."""
    
    @pytest.fixture
    def temp_registry(self):
        """Create a temporary registry file for testing."""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            registry_path = Path(f.name)
        # Remove the empty file so DeviceRegistry can create it properly
        registry_path.unlink()
        yield registry_path
        # Cleanup
        if registry_path.exists():
            registry_path.unlink()
    
    def test_full_workflow_integration(self, temp_registry):
        """Test complete workflow from detection to monitoring."""
        # Create sample devices
        camera1 = CameraDevice(
            system_index=0,
            vendor_id="046d",
            product_id="085b",
            serial_number="ABC123",
            port_path="/dev/video0",
            label="Camera 1",
            platform_data={}
        )
        
        camera2 = CameraDevice(
            system_index=1,
            vendor_id="1234",
            product_id="5678",
            serial_number=None,
            port_path="/dev/video1",
            label="Camera 2",
            platform_data={}
        )
        
        # Event tracking
        events_received = []
        
        def track_events(device):
            events_received.append(device.stable_id)
        
        with StableCam(registry_path=temp_registry, poll_interval=0.1) as manager:
            # Subscribe to events
            manager.on(EventType.ON_CONNECT.value, track_events)
            manager.on(EventType.ON_DISCONNECT.value, track_events)
            
            # Mock detection to return both cameras
            with patch.object(manager.detector, 'detect_cameras', return_value=[camera1, camera2]):
                # Register devices
                id1 = manager.register(camera1)
                id2 = manager.register(camera2)
                
                assert id1 == "stable-cam-001"
                assert id2 == "stable-cam-002"
                
                # Verify both devices are listed
                devices = manager.list()
                assert len(devices) == 2
                
                # Start monitoring
                manager.run()
                time.sleep(0.2)
            
            # Simulate camera1 disconnection
            with patch.object(manager.detector, 'detect_cameras', return_value=[camera2]):
                time.sleep(0.2)
            
            # Simulate both cameras disconnection
            with patch.object(manager.detector, 'detect_cameras', return_value=[]):
                time.sleep(0.2)
        
        # Verify events were received
        assert len(events_received) >= 2  # At least connect events for registration
        
        # Verify final state
        final_devices = manager.list()
        assert len(final_devices) == 2
        
        # At least one device should be disconnected
        statuses = [device.status for device in final_devices]
        assert DeviceStatus.DISCONNECTED in statuses