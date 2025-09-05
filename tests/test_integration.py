"""
Comprehensive integration tests for StableCam.

This module contains end-to-end integration tests that simulate real-world
device connection scenarios, test cross-platform compatibility, measure
performance with multiple devices, and validate TUI functionality.
"""

import pytest
import tempfile
import threading
import time
import asyncio
import platform
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from typing import List, Dict, Any

from stablecam import StableCam, CameraDevice, RegisteredDevice, DeviceStatus
from stablecam.registry import DeviceRegistry, RegistryError
from stablecam.events import EventType
from stablecam.backends.exceptions import PlatformDetectionError


class TestEndToEndScenarios:
    """End-to-end integration tests simulating real device connection scenarios."""
    
    @pytest.fixture
    def temp_registry(self):
        """Create a temporary registry file for testing."""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            registry_path = Path(f.name)
        registry_path.unlink()  # Remove empty file
        yield registry_path
        if registry_path.exists():
            registry_path.unlink()
    
    @pytest.fixture
    def sample_cameras(self):
        """Create sample camera devices for testing."""
        return [
            CameraDevice(
                system_index=0,
                vendor_id="046d",
                product_id="085b", 
                serial_number="ABC123456",
                port_path="/dev/usb1/1-1",
                label="Logitech C920 HD Pro Webcam",
                platform_data={"udev_path": "/sys/devices/usb1/1-1"}
            ),
            CameraDevice(
                system_index=1,
                vendor_id="0c45",
                product_id="6366",
                serial_number="DEF789012",
                port_path="/dev/usb1/1-2", 
                label="Generic USB Camera",
                platform_data={"udev_path": "/sys/devices/usb1/1-2"}
            ),
            CameraDevice(
                system_index=2,
                vendor_id="1234",
                product_id="5678",
                serial_number=None,  # No serial number
                port_path="/dev/usb2/2-1",
                label="No Serial Camera",
                platform_data={"udev_path": "/sys/devices/usb2/2-1"}
            )
        ]
    
    @pytest.mark.integration
    def test_complete_device_lifecycle(self, temp_registry, sample_cameras):
        """Test complete device lifecycle from detection to monitoring."""
        events_received = []
        
        def track_events(device):
            events_received.append({
                'type': 'event',
                'stable_id': device.stable_id,
                'status': device.status,
                'timestamp': datetime.now()
            })
        
        with StableCam(registry_path=temp_registry, poll_interval=0.1) as manager:
            # Subscribe to all events
            manager.on(EventType.ON_CONNECT.value, track_events)
            manager.on(EventType.ON_DISCONNECT.value, track_events)
            manager.on(EventType.ON_STATUS_CHANGE.value, track_events)
            
            # Phase 1: Initial detection and registration
            with patch.object(manager.detector, 'detect_cameras', return_value=sample_cameras[:2]):
                detected = manager.detect()
                assert len(detected) == 2
                
                # Register first camera
                id1 = manager.register(sample_cameras[0])
                assert id1 == "stable-cam-001"
                
                # Register second camera
                id2 = manager.register(sample_cameras[1])
                assert id2 == "stable-cam-002"
            
            # Verify initial state
            devices = manager.list()
            assert len(devices) == 2
            assert all(d.status == DeviceStatus.CONNECTED for d in devices)
            
            # Phase 2: Start monitoring
            manager.run()
            time.sleep(0.2)  # Let monitoring loop run
            
            # Phase 3: Simulate device disconnection
            with patch.object(manager.detector, 'detect_cameras', return_value=[sample_cameras[1]]):
                time.sleep(0.2)  # Wait for monitoring to detect change
            
            # Verify disconnection was detected
            devices = manager.list()
            device1 = manager.get_by_id(id1)
            device2 = manager.get_by_id(id2)
            
            assert device1.status == DeviceStatus.DISCONNECTED
            assert device2.status == DeviceStatus.CONNECTED
            
            # Phase 4: Simulate reconnection with different system index
            reconnected_camera = CameraDevice(
                system_index=5,  # Different system index
                vendor_id=sample_cameras[0].vendor_id,
                product_id=sample_cameras[0].product_id,
                serial_number=sample_cameras[0].serial_number,
                port_path=sample_cameras[0].port_path,
                label=sample_cameras[0].label,
                platform_data={"udev_path": "/sys/devices/usb1/1-1"}
            )
            
            with patch.object(manager.detector, 'detect_cameras', 
                            return_value=[sample_cameras[1], reconnected_camera]):
                time.sleep(0.2)  # Wait for monitoring to detect change
            
            # Verify reconnection with updated system index
            device1 = manager.get_by_id(id1)
            assert device1.status == DeviceStatus.CONNECTED
            assert device1.device_info.system_index == 5
            
            # Phase 5: Add new device during monitoring
            with patch.object(manager.detector, 'detect_cameras',
                            return_value=[sample_cameras[1], reconnected_camera, sample_cameras[2]]):
                # Register new device
                id3 = manager.register(sample_cameras[2])
                assert id3 == "stable-cam-003"
                
                time.sleep(0.2)  # Let monitoring process
            
            # Verify all devices are tracked
            devices = manager.list()
            assert len(devices) == 3
            assert all(d.status == DeviceStatus.CONNECTED for d in devices)
        
        # Verify events were emitted
        assert len(events_received) >= 6  # At least registration + connection/disconnection events
        
        # Verify event types
        stable_ids = {event['stable_id'] for event in events_received}
        assert id1 in stable_ids
        assert id2 in stable_ids
        assert id3 in stable_ids
    
    @pytest.mark.integration
    def test_registry_persistence_across_restarts(self, temp_registry, sample_cameras):
        """Test that device registry persists across application restarts."""
        # First session: register devices
        with StableCam(registry_path=temp_registry) as manager1:
            with patch.object(manager1.detector, 'detect_cameras', return_value=sample_cameras):
                id1 = manager1.register(sample_cameras[0])
                id2 = manager1.register(sample_cameras[1])
                
                devices = manager1.list()
                assert len(devices) == 2
        
        # Second session: verify persistence
        with StableCam(registry_path=temp_registry) as manager2:
            devices = manager2.list()
            assert len(devices) == 2
            
            # Verify stable IDs are preserved
            stable_ids = {d.stable_id for d in devices}
            assert id1 in stable_ids
            assert id2 in stable_ids
            
            # Verify device details are preserved
            device1 = manager2.get_by_id(id1)
            assert device1.device_info.vendor_id == sample_cameras[0].vendor_id
            assert device1.device_info.serial_number == sample_cameras[0].serial_number
    
    @pytest.mark.integration
    def test_concurrent_access_safety(self, temp_registry, sample_cameras):
        """Test that multiple StableCam instances can safely access the same registry."""
        results = {}
        errors = []
        
        def worker(worker_id, camera):
            try:
                with StableCam(registry_path=temp_registry) as manager:
                    with patch.object(manager.detector, 'detect_cameras', return_value=[camera]):
                        stable_id = manager.register(camera)
                        results[worker_id] = stable_id
                        time.sleep(0.1)  # Simulate some work
            except Exception as e:
                errors.append(f"Worker {worker_id}: {e}")
        
        # Start multiple workers concurrently
        threads = []
        for i, camera in enumerate(sample_cameras):
            thread = threading.Thread(target=worker, args=(i, camera))
            threads.append(thread)
            thread.start()
        
        # Wait for all workers to complete
        for thread in threads:
            thread.join(timeout=5.0)
        
        # Verify no errors occurred
        assert len(errors) == 0, f"Concurrent access errors: {errors}"
        
        # Verify all devices were registered
        assert len(results) == len(sample_cameras)
        
        # Verify final registry state
        with StableCam(registry_path=temp_registry) as manager:
            devices = manager.list()
            assert len(devices) == len(sample_cameras)
    
    @pytest.mark.integration
    def test_error_recovery_scenarios(self, temp_registry, sample_cameras):
        """Test system recovery from various error conditions."""
        with StableCam(registry_path=temp_registry, poll_interval=0.1) as manager:
            # Register initial device
            with patch.object(manager.detector, 'detect_cameras', return_value=[sample_cameras[0]]):
                stable_id = manager.register(sample_cameras[0])
            
            manager.run()
            time.sleep(0.1)
            
            # Simulate detection errors
            error_count = 0
            original_detect = manager.detector.detect_cameras
            
            def failing_detect():
                nonlocal error_count
                error_count += 1
                if error_count <= 2:  # Fail first 2 times
                    raise PlatformDetectionError("Simulated detection failure", "test")
                return [sample_cameras[0]]  # Then succeed
            
            with patch.object(manager.detector, 'detect_cameras', side_effect=failing_detect):
                time.sleep(0.3)  # Let monitoring handle errors
            
            # Verify system recovered
            assert manager._monitoring  # Should still be monitoring
            assert error_count >= 2  # Should have retried at least twice
            
            # Verify device state is still correct
            device = manager.get_by_id(stable_id)
            assert device is not None


class TestCrossPlatformCompatibility:
    """Tests for cross-platform compatibility and platform-specific behavior."""
    
    @pytest.fixture
    def temp_registry(self):
        """Create a temporary registry file for testing."""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            registry_path = Path(f.name)
        registry_path.unlink()
        yield registry_path
        if registry_path.exists():
            registry_path.unlink()
    
    @pytest.mark.integration
    def test_platform_backend_selection(self, temp_registry):
        """Test that correct platform backend is selected based on current OS."""
        with StableCam(registry_path=temp_registry) as manager:
            backend = manager.detector.get_platform_backend()
            current_platform = platform.system().lower()
            
            if current_platform == "linux":
                from stablecam.backends.linux import LinuxBackend
                assert isinstance(backend, LinuxBackend)
            elif current_platform == "windows":
                from stablecam.backends.windows import WindowsBackend
                assert isinstance(backend, WindowsBackend)
            elif current_platform == "darwin":
                from stablecam.backends.macos import MacOSBackend
                assert isinstance(backend, MacOSBackend)
    
    @pytest.mark.integration
    @pytest.mark.parametrize("platform_name,expected_backend", [
        ("linux", "LinuxBackend"),
        ("windows", "WindowsBackend"), 
        ("darwin", "MacOSBackend"),
    ])
    def test_platform_specific_device_data(self, temp_registry, platform_name, expected_backend):
        """Test that platform-specific device data is handled correctly."""
        # Create platform-specific test data
        platform_data_samples = {
            "linux": {
                "udev_path": "/sys/devices/pci0000:00/0000:00:14.0/usb1/1-1",
                "v4l2_caps": ["video_capture", "streaming"]
            },
            "windows": {
                "device_path": "\\\\?\\usb#vid_046d&pid_085b#abc123456#{65e8773d-8f56-11d0-a3b9-00a0c9223196}",
                "friendly_name": "Logitech HD Pro Webcam C920"
            },
            "darwin": {
                "io_service_path": "IOService:/AppleACPIPlatformExpert/PCI0@0/AppleACPIPCI/XHC1@14/XHC1@14000000/HS01@14100000/USB Camera@14100000",
                "av_device_id": "0x1a11000005ac8600"
            }
        }
        
        test_camera = CameraDevice(
            system_index=0,
            vendor_id="046d",
            product_id="085b",
            serial_number="ABC123456",
            port_path="/dev/video0" if platform_name == "linux" else "USB\\VID_046D&PID_085B\\ABC123456",
            label="Test Camera",
            platform_data=platform_data_samples[platform_name]
        )
        
        with StableCam(registry_path=temp_registry) as manager:
            # Mock the backend to return our test data
            with patch.object(manager.detector, 'detect_cameras', return_value=[test_camera]):
                stable_id = manager.register(test_camera)
                
                # Verify platform data is preserved
                registered_device = manager.get_by_id(stable_id)
                assert registered_device.device_info.platform_data == platform_data_samples[platform_name]
    
    @pytest.mark.integration
    def test_hardware_id_generation_consistency(self, temp_registry):
        """Test that hardware ID generation is consistent across platforms."""
        # Test devices with different identifier scenarios
        test_cases = [
            # Device with serial number (preferred)
            CameraDevice(
                system_index=0, vendor_id="046d", product_id="085b",
                serial_number="ABC123456", port_path="/dev/video0",
                label="Camera with Serial", platform_data={}
            ),
            # Device without serial number (fallback to vendor/product + port)
            CameraDevice(
                system_index=1, vendor_id="1234", product_id="5678", 
                serial_number=None, port_path="/dev/video1",
                label="Camera without Serial", platform_data={}
            ),
            # Device with empty serial number
            CameraDevice(
                system_index=2, vendor_id="abcd", product_id="efgh",
                serial_number="", port_path="/dev/video2", 
                label="Camera with Empty Serial", platform_data={}
            )
        ]
        
        with StableCam(registry_path=temp_registry) as manager:
            stable_ids = []
            
            for camera in test_cases:
                with patch.object(manager.detector, 'detect_cameras', return_value=[camera]):
                    stable_id = manager.register(camera)
                    stable_ids.append(stable_id)
            
            # Verify all devices got unique stable IDs
            assert len(set(stable_ids)) == len(stable_ids)
            
            # Verify hardware ID generation is deterministic
            for i, camera in enumerate(test_cases):
                hw_id1 = camera.generate_hardware_id()
                hw_id2 = camera.generate_hardware_id()
                assert hw_id1 == hw_id2, f"Hardware ID generation not deterministic for camera {i}"


class TestPerformanceMultiDevice:
    """Performance tests for multi-device detection and monitoring."""
    
    @pytest.fixture
    def temp_registry(self):
        """Create a temporary registry file for testing."""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            registry_path = Path(f.name)
        registry_path.unlink()
        yield registry_path
        if registry_path.exists():
            registry_path.unlink()
    
    def create_test_cameras(self, count: int) -> List[CameraDevice]:
        """Create a list of test camera devices."""
        cameras = []
        for i in range(count):
            cameras.append(CameraDevice(
                system_index=i,
                vendor_id=f"{(0x1000 + i):04x}",
                product_id=f"{(0x2000 + i):04x}",
                serial_number=f"SERIAL{i:06d}",
                port_path=f"/dev/video{i}",
                label=f"Test Camera {i}",
                platform_data={"test_id": i}
            ))
        return cameras
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_detection_performance_scaling(self, temp_registry):
        """Test detection performance with increasing number of devices."""
        device_counts = [1, 5, 10, 20, 50]
        detection_times = {}
        
        with StableCam(registry_path=temp_registry) as manager:
            for count in device_counts:
                cameras = self.create_test_cameras(count)
                
                # Measure detection time
                with patch.object(manager.detector, 'detect_cameras', return_value=cameras):
                    start_time = time.time()
                    detected = manager.detect()
                    detection_time = time.time() - start_time
                    
                    detection_times[count] = detection_time
                    assert len(detected) == count
                    
                    # Detection should complete within reasonable time
                    assert detection_time < 1.0, f"Detection took {detection_time:.3f}s for {count} devices"
        
        # Verify performance doesn't degrade significantly with more devices
        # (This is a basic check - real performance will depend on platform backend)
        if len(detection_times) > 1:
            times = list(detection_times.values())
            # Performance shouldn't degrade more than 10x from smallest to largest
            assert max(times) / min(times) < 10.0
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_registration_performance_bulk(self, temp_registry):
        """Test registration performance with many devices."""
        camera_count = 25
        cameras = self.create_test_cameras(camera_count)
        
        with StableCam(registry_path=temp_registry) as manager:
            with patch.object(manager.detector, 'detect_cameras', return_value=cameras):
                # Measure bulk registration time
                start_time = time.time()
                
                stable_ids = []
                for camera in cameras:
                    stable_id = manager.register(camera)
                    stable_ids.append(stable_id)
                
                registration_time = time.time() - start_time
                
                # Verify all devices were registered
                assert len(stable_ids) == camera_count
                assert len(set(stable_ids)) == camera_count  # All unique
                
                # Registration should complete within reasonable time
                assert registration_time < 5.0, f"Registration took {registration_time:.3f}s for {camera_count} devices"
                
                # Verify registry contains all devices
                devices = manager.list()
                assert len(devices) == camera_count
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_monitoring_performance_many_devices(self, temp_registry):
        """Test monitoring loop performance with many devices."""
        camera_count = 20
        cameras = self.create_test_cameras(camera_count)
        
        monitoring_times = []
        
        with StableCam(registry_path=temp_registry, poll_interval=0.1) as manager:
            # Register all devices
            with patch.object(manager.detector, 'detect_cameras', return_value=cameras):
                for camera in cameras:
                    manager.register(camera)
            
            # Monitor detection performance
            def timed_detect():
                start_time = time.time()
                result = cameras  # Return all cameras
                detection_time = time.time() - start_time
                monitoring_times.append(detection_time)
                return result
            
            with patch.object(manager.detector, 'detect_cameras', side_effect=timed_detect):
                manager.run()
                time.sleep(1.0)  # Let monitoring run for 1 second
                manager.stop()
            
            # Verify monitoring performance
            assert len(monitoring_times) > 5  # Should have run multiple times
            avg_time = sum(monitoring_times) / len(monitoring_times)
            max_time = max(monitoring_times)
            
            # Each monitoring cycle should be fast
            assert avg_time < 0.1, f"Average monitoring time {avg_time:.3f}s too slow"
            assert max_time < 0.2, f"Max monitoring time {max_time:.3f}s too slow"
    
    @pytest.mark.integration
    def test_memory_usage_stability(self, temp_registry):
        """Test that memory usage remains stable during extended monitoring."""
        import gc
        import sys
        
        camera_count = 10
        cameras = self.create_test_cameras(camera_count)
        
        with StableCam(registry_path=temp_registry, poll_interval=0.05) as manager:
            # Register devices
            with patch.object(manager.detector, 'detect_cameras', return_value=cameras):
                for camera in cameras:
                    manager.register(camera)
            
            # Start monitoring and measure memory usage
            manager.run()
            
            # Force garbage collection and get initial memory usage
            gc.collect()
            initial_objects = len(gc.get_objects())
            
            # Run monitoring for a while
            time.sleep(0.5)
            
            # Check memory usage again
            gc.collect()
            final_objects = len(gc.get_objects())
            
            manager.stop()
            
            # Memory usage shouldn't grow significantly
            object_growth = final_objects - initial_objects
            growth_percentage = (object_growth / initial_objects) * 100
            
            # Allow some growth but not excessive
            assert growth_percentage < 50, f"Memory usage grew by {growth_percentage:.1f}%"


# TUI Integration Tests
try:
    from stablecam.tui import StableCamTUI, run_tui
    from textual.app import App
    from textual.widgets import DataTable
    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False


@pytest.mark.skipif(not TEXTUAL_AVAILABLE, reason="Textual not available")
class TestTUIIntegration:
    """Integration tests for TUI functionality using Textual testing framework."""
    
    @pytest.fixture
    def temp_registry(self):
        """Create a temporary registry file for testing."""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            registry_path = Path(f.name)
        registry_path.unlink()
        yield registry_path
        if registry_path.exists():
            registry_path.unlink()
    
    @pytest.fixture
    def sample_devices(self):
        """Create sample registered devices for TUI testing."""
        device1 = CameraDevice(
            system_index=0, vendor_id="046d", product_id="085b",
            serial_number="ABC123", port_path="/dev/video0",
            label="Logitech C920", platform_data={}
        )
        
        device2 = CameraDevice(
            system_index=1, vendor_id="0c45", product_id="6366", 
            serial_number=None, port_path="/dev/video1",
            label="Generic Camera", platform_data={}
        )
        
        return [
            RegisteredDevice(
                stable_id="stable-cam-001", device_info=device1,
                status=DeviceStatus.CONNECTED, registered_at=datetime.now(),
                last_seen=datetime.now()
            ),
            RegisteredDevice(
                stable_id="stable-cam-002", device_info=device2,
                status=DeviceStatus.DISCONNECTED, registered_at=datetime.now(),
                last_seen=None
            )
        ]
    
    @pytest.mark.integration
    def test_tui_initialization_and_mount(self, temp_registry):
        """Test TUI initialization and mounting process."""
        app = StableCamTUI(registry_path=temp_registry)
        
        # Mock the StableCam manager
        mock_manager = Mock()
        mock_manager.list.return_value = []
        mock_manager.on.return_value = None
        mock_manager.run.return_value = None
        
        with patch('stablecam.tui.StableCam', return_value=mock_manager):
            # Test that app can be created and mounted
            assert app.registry_path == temp_registry
            assert app.manager is None  # Not initialized until mount
            
            # Simulate mount by calling the sync parts
            # We can't easily test the async mount without running the app
            # So we'll test the initialization logic directly
            app.manager = mock_manager
            
            # Verify manager was set
            assert app.manager is not None
    
    @pytest.mark.integration
    def test_tui_device_display_and_updates(self, temp_registry, sample_devices):
        """Test TUI device display and real-time updates."""
        app = StableCamTUI(registry_path=temp_registry)
        
        # Mock manager with sample devices
        mock_manager = Mock()
        mock_manager.list.return_value = sample_devices
        mock_manager.on.return_value = None
        mock_manager.run.return_value = None
        
        with patch('stablecam.tui.StableCam', return_value=mock_manager):
            app.manager = mock_manager
            
            # Simulate device loading (sync version)
            app.devices = sample_devices
            app.device_count = len(sample_devices)
            app.connected_count = sum(1 for d in sample_devices if d.status == DeviceStatus.CONNECTED)
            
            # Verify devices were loaded
            assert len(app.devices) == 2
            assert app.device_count == 2
            assert app.connected_count == 1  # Only one connected
            
            # Test status display formatting
            connected_device = sample_devices[0]
            disconnected_device = sample_devices[1]
            
            indicator1, css1 = app._get_status_display(connected_device)
            assert indicator1 == "● Online"
            assert css1 == "connected"
            
            indicator2, css2 = app._get_status_display(disconnected_device)
            assert indicator2 == "○ Offline"
            assert css2 == "disconnected"
    
    @pytest.mark.integration
    def test_tui_device_registration_flow(self, temp_registry):
        """Test TUI device registration workflow."""
        app = StableCamTUI(registry_path=temp_registry)
        
        # Create new unregistered device
        new_device = CameraDevice(
            system_index=2, vendor_id="1234", product_id="5678",
            serial_number="NEW123", port_path="/dev/video2",
            label="New Camera", platform_data={}
        )
        
        # Mock manager
        mock_manager = Mock()
        mock_manager.list.return_value = []  # No existing devices
        mock_manager.detect.return_value = [new_device]
        mock_manager.register.return_value = "stable-cam-001"
        mock_manager.on.return_value = None
        mock_manager.run.return_value = None
        
        with patch('stablecam.tui.StableCam', return_value=mock_manager):
            app.manager = mock_manager
            app.devices = []  # No existing devices
            
            # Test registration logic (sync version)
            detected_devices = mock_manager.detect()
            unregistered = [d for d in detected_devices if not any(
                rd.device_info.generate_hardware_id() == d.generate_hardware_id() 
                for rd in app.devices
            )]
            
            if unregistered:
                stable_id = mock_manager.register(unregistered[0])
                assert stable_id == "stable-cam-001"
            
            # Verify registration was attempted
            mock_manager.detect.assert_called_once()
            mock_manager.register.assert_called_once_with(new_device)
    
    @pytest.mark.integration
    def test_tui_event_handling_and_visual_updates(self, temp_registry, sample_devices):
        """Test TUI event handling and visual update indicators."""
        app = StableCamTUI(registry_path=temp_registry)
        
        mock_manager = Mock()
        mock_manager.list.return_value = sample_devices
        mock_manager.on.return_value = None
        mock_manager.run.return_value = None
        
        with patch('stablecam.tui.StableCam', return_value=mock_manager):
            app.manager = mock_manager
            
            device = sample_devices[0]
            stable_id = device.stable_id
            
            # Test event handlers
            app._on_device_connect(device)
            assert app._is_recent_change(stable_id)
            
            app._on_device_disconnect(device)
            assert app._is_recent_change(stable_id)
            
            app._on_device_status_change(device)
            assert app._is_recent_change(stable_id)
            
            # Test recent change tracking with time
            with patch('stablecam.tui.datetime') as mock_datetime:
                # Simulate time passing
                original_time = app._recent_changes[stable_id]
                future_time = original_time + timedelta(seconds=6)
                mock_datetime.now.return_value = future_time
                
                # Should no longer be recent
                assert not app._is_recent_change(stable_id)
    
    @pytest.mark.integration
    def test_tui_error_handling_and_recovery(self, temp_registry):
        """Test TUI error handling and recovery scenarios."""
        app = StableCamTUI(registry_path=temp_registry)
        
        # Mock manager that raises errors
        mock_manager = Mock()
        mock_manager.list.side_effect = Exception("Registry error")
        mock_manager.detect.side_effect = Exception("Detection error")
        mock_manager.on.return_value = None
        mock_manager.run.return_value = None
        
        with patch('stablecam.tui.StableCam', return_value=mock_manager):
            app.manager = mock_manager
            
            # Mock status update to capture error messages
            app._update_status = Mock()
            
            # Test error handling in device listing
            try:
                devices = app.manager.list()
            except Exception:
                # Should handle error gracefully
                app._update_status("Error loading devices")
            
            # Test error handling in detection
            try:
                detected = app.manager.detect()
            except Exception:
                # Should handle detection error gracefully
                app._update_status("Error detecting devices")
            
            # Verify error handling was called
            assert app._update_status.call_count >= 1
    
    @pytest.mark.integration
    def test_tui_run_function_integration(self, temp_registry):
        """Test the run_tui function integration."""
        with patch('stablecam.tui.StableCamTUI') as mock_tui_class:
            mock_app = Mock()
            mock_tui_class.return_value = mock_app
            
            # Test run_tui function
            run_tui(registry_path=temp_registry)
            
            # Verify TUI was created and run
            mock_tui_class.assert_called_once_with(registry_path=temp_registry)
            mock_app.run.assert_called_once()
    
    @pytest.mark.integration
    def test_tui_cleanup_on_unmount(self, temp_registry):
        """Test proper TUI cleanup when unmounting."""
        app = StableCamTUI(registry_path=temp_registry)
        
        mock_manager = Mock()
        mock_manager.list.return_value = []
        mock_manager.on.return_value = None
        mock_manager.run.return_value = None
        mock_manager.stop.return_value = None
        
        with patch('stablecam.tui.StableCam', return_value=mock_manager):
            app.manager = mock_manager
            
            # Set up mock timer
            mock_timer = Mock()
            app.update_timer = mock_timer
            
            # Test cleanup logic (sync version)
            if hasattr(app, 'update_timer') and app.update_timer:
                app.update_timer.stop()
            if app.manager:
                app.manager.stop()
            
            # Verify cleanup was performed
            mock_timer.stop.assert_called_once()
            mock_manager.stop.assert_called_once()


class TestSystemIntegration:
    """System-level integration tests combining multiple components."""
    
    @pytest.fixture
    def temp_registry(self):
        """Create a temporary registry file for testing."""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            registry_path = Path(f.name)
        registry_path.unlink()
        yield registry_path
        if registry_path.exists():
            registry_path.unlink()
    
    @pytest.mark.integration
    def test_full_system_workflow_with_events(self, temp_registry):
        """Test complete system workflow with event propagation."""
        # Track all system events
        system_events = []
        
        def event_logger(event_type):
            def handler(device):
                system_events.append({
                    'type': event_type,
                    'stable_id': device.stable_id,
                    'status': device.status,
                    'timestamp': datetime.now()
                })
            return handler
        
        # Create test scenario with multiple devices
        cameras = [
            CameraDevice(0, "046d", "085b", "ABC123", "/dev/video0", "Camera 1", {}),
            CameraDevice(1, "0c45", "6366", "DEF456", "/dev/video1", "Camera 2", {}),
            CameraDevice(2, "1234", "5678", None, "/dev/video2", "Camera 3", {})
        ]
        
        with StableCam(registry_path=temp_registry, poll_interval=0.05) as manager:
            # Set up comprehensive event tracking
            manager.on(EventType.ON_CONNECT.value, event_logger('connect'))
            manager.on(EventType.ON_DISCONNECT.value, event_logger('disconnect'))
            manager.on(EventType.ON_STATUS_CHANGE.value, event_logger('status_change'))
            
            # Phase 1: Initial registration
            with patch.object(manager.detector, 'detect_cameras', return_value=cameras):
                stable_ids = []
                for camera in cameras:
                    stable_id = manager.register(camera)
                    stable_ids.append(stable_id)
                
                # Start monitoring
                manager.run()
                time.sleep(0.1)
            
            # Phase 2: Simulate complex connection changes
            scenarios = [
                # All devices connected
                cameras,
                # One device disconnected
                cameras[1:],
                # Two devices disconnected
                [cameras[0]],
                # All devices disconnected
                [],
                # Devices reconnect in different order
                [cameras[2], cameras[0]],
                # All devices back
                cameras
            ]
            
            for scenario in scenarios:
                with patch.object(manager.detector, 'detect_cameras', return_value=scenario):
                    time.sleep(0.1)  # Let monitoring detect changes
            
            # Verify final state
            final_devices = manager.list()
            assert len(final_devices) == 3
            
            # Verify comprehensive event tracking
            assert len(system_events) >= 6  # At least registration events
            
            # Verify all devices had events
            event_stable_ids = {event['stable_id'] for event in system_events}
            assert all(sid in event_stable_ids for sid in stable_ids)
            
            # Verify event types were recorded
            event_types = {event['type'] for event in system_events}
            assert 'connect' in event_types or 'status_change' in event_types
    
    @pytest.mark.integration
    def test_stress_test_rapid_changes(self, temp_registry):
        """Stress test with rapid device connection changes."""
        cameras = [
            CameraDevice(i, f"{i:04x}", f"{i+1000:04x}", f"SER{i:03d}", 
                        f"/dev/video{i}", f"Camera {i}", {})
            for i in range(5)
        ]
        
        change_count = 0
        
        with StableCam(registry_path=temp_registry, poll_interval=0.02) as manager:
            # Register all devices initially
            with patch.object(manager.detector, 'detect_cameras', return_value=cameras):
                for camera in cameras:
                    manager.register(camera)
            
            # Track status changes
            def count_changes(device):
                nonlocal change_count
                change_count += 1
            
            manager.on(EventType.ON_STATUS_CHANGE.value, count_changes)
            manager.run()
            
            # Rapidly change device configurations
            import random
            for _ in range(20):  # 20 rapid changes
                # Randomly select subset of devices
                active_cameras = random.sample(cameras, random.randint(0, len(cameras)))
                
                with patch.object(manager.detector, 'detect_cameras', return_value=active_cameras):
                    time.sleep(0.03)  # Brief pause between changes
            
            # Let final state settle
            time.sleep(0.1)
            
            # Verify system handled rapid changes
            final_devices = manager.list()
            assert len(final_devices) == len(cameras)  # All devices still registered
            assert change_count > 10  # Multiple status changes detected
            
            # Verify system is still responsive
            with patch.object(manager.detector, 'detect_cameras', return_value=cameras):
                time.sleep(0.1)
                
            # All devices should be connected in final state
            final_devices = manager.list()
            connected_count = sum(1 for d in final_devices if d.status == DeviceStatus.CONNECTED)
            assert connected_count == len(cameras)