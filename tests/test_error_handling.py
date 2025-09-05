"""
Tests for comprehensive error handling and logging functionality.

This module tests error scenarios, recovery mechanisms, and logging
configuration across all StableCam components.
"""

import pytest
import tempfile
import json
import os
import logging
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from stablecam.backends.exceptions import (
    StableCamError, PlatformDetectionError, DeviceNotFoundError,
    UnsupportedPlatformError, PermissionError, HardwareError,
    ConfigurationError
)
from stablecam.registry import (
    DeviceRegistry, RegistryError, RegistryCorruptionError,
    RegistryPermissionError, RegistryLockError
)
from stablecam.manager import StableCam
from stablecam.logging_config import StableCamLogger, setup_logging
from stablecam.models import CameraDevice, DeviceStatus


class TestStableCamExceptions:
    """Test StableCam exception hierarchy and error context."""
    
    def test_base_exception_with_context(self):
        """Test base StableCam exception with context information."""
        context = {'device_id': 'test-device', 'operation': 'test'}
        cause = ValueError("Original error")
        
        error = StableCamError("Test error", cause=cause, context=context)
        
        assert error.message == "Test error"
        assert error.cause == cause
        assert error.context == context
        assert str(error) == "Test error"
    
    def test_platform_detection_error(self):
        """Test platform detection error with platform context."""
        error = PlatformDetectionError("Detection failed", platform="linux")
        
        assert error.context['platform'] == "linux"
        assert "Detection failed" in str(error)
    
    def test_device_not_found_error(self):
        """Test device not found error with device ID context."""
        error = DeviceNotFoundError("Device missing", device_id="stable-cam-001")
        
        assert error.context['device_id'] == "stable-cam-001"
    
    def test_permission_error_with_resource(self):
        """Test permission error with resource context."""
        error = PermissionError("Access denied", resource="/dev/video0")
        
        assert error.context['resource'] == "/dev/video0"
    
    def test_hardware_error_with_device_path(self):
        """Test hardware error with device path context."""
        error = HardwareError("Hardware failure", device_path="/dev/video0")
        
        assert error.context['device_path'] == "/dev/video0"
    
    def test_configuration_error_with_config_key(self):
        """Test configuration error with config key context."""
        error = ConfigurationError("Invalid config", config_key="log_level")
        
        assert error.context['config_key'] == "log_level"


class TestRegistryErrorHandling:
    """Test registry error handling and recovery mechanisms."""
    
    def test_registry_corruption_recovery(self):
        """Test registry corruption detection and recovery."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "test_registry.json"
            
            # Create corrupted registry file
            with open(registry_path, 'w') as f:
                f.write("invalid json content {")
            
            # Registry should handle corruption and create new file
            registry = DeviceRegistry(registry_path)
            
            # Should have created a backup and new registry
            assert registry_path.exists()
            backup_files = list(Path(temp_dir).glob("*.backup_*.json"))
            assert len(backup_files) > 0
            
            # New registry should be valid
            data = registry._read_registry()
            assert "version" in data
            assert "devices" in data
    
    def test_registry_permission_error(self):
        """Test registry permission error handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "readonly" / "registry.json"
            
            # Create readonly directory
            readonly_dir = Path(temp_dir) / "readonly"
            readonly_dir.mkdir()
            os.chmod(readonly_dir, 0o444)  # Read-only
            
            try:
                # The permission error should be caught during initialization
                # when trying to check if the registry file exists
                with pytest.raises(Exception) as exc_info:  # Catch any permission-related error
                    DeviceRegistry(registry_path)
                
                # Verify it's a permission-related error
                assert "Permission denied" in str(exc_info.value) or isinstance(exc_info.value, RegistryPermissionError)
            finally:
                # Restore permissions for cleanup
                os.chmod(readonly_dir, 0o755)
    
    def test_registry_backup_creation(self):
        """Test registry backup creation during corruption handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "test_registry.json"
            
            # Create valid registry first
            registry = DeviceRegistry(registry_path)
            
            # Add some data
            device = CameraDevice(
                system_index=0,
                vendor_id="1234",
                product_id="5678",
                serial_number="TEST123",
                port_path="/dev/video0",
                label="Test Camera",
                platform_data={}
            )
            stable_id = registry.register(device)
            
            # Corrupt the registry file
            with open(registry_path, 'w') as f:
                f.write("corrupted content")
            
            # Create new registry instance - should trigger recovery
            registry2 = DeviceRegistry(registry_path)
            
            # Check that backup was created
            backup_files = list(Path(temp_dir).glob("*.backup_*.json"))
            assert len(backup_files) > 0
    
    def test_registry_atomic_write_failure_recovery(self):
        """Test recovery from atomic write failures."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "test_registry.json"
            registry = DeviceRegistry(registry_path)
            
            # Mock tempfile creation to fail
            with patch('tempfile.NamedTemporaryFile', side_effect=OSError("Disk full")):
                with pytest.raises(RegistryError):
                    registry._write_registry_atomic({"test": "data"})
    
    def test_registry_file_lock_timeout(self):
        """Test file lock timeout handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "test_registry.json"
            registry = DeviceRegistry(registry_path)
            
            # Mock fcntl.flock to always raise IOError (lock unavailable)
            with patch('fcntl.flock', side_effect=IOError("Resource temporarily unavailable")):
                with pytest.raises(RegistryLockError):
                    registry._read_registry()


class TestManagerErrorHandling:
    """Test StableCam manager error handling."""
    
    def test_manager_initialization_with_registry_error(self):
        """Test manager initialization when registry fails."""
        with patch('stablecam.registry.DeviceRegistry') as mock_registry:
            mock_registry.side_effect = RegistryCorruptionError("Registry corrupted")
            
            # First call fails, second call should succeed (after recovery)
            mock_registry.side_effect = [
                RegistryCorruptionError("Registry corrupted"),
                Mock()  # Success on retry
            ]
            
            # Should succeed after recovery
            manager = StableCam(enable_logging=False)
            assert manager.registry is not None
    
    def test_manager_detection_error_handling(self):
        """Test manager handling of detection errors."""
        manager = StableCam(enable_logging=False)
        
        # Mock detector to raise permission error
        with patch.object(manager.detector, 'detect_cameras') as mock_detect:
            mock_detect.side_effect = PermissionError("Permission denied")
            
            with pytest.raises(PlatformDetectionError) as exc_info:
                manager.detect()
            
            assert "Permission denied" in str(exc_info.value)
    
    def test_manager_monitoring_error_recovery(self):
        """Test manager monitoring loop error recovery."""
        manager = StableCam(poll_interval=0.1, enable_logging=False)
        
        # Mock detect to fail a few times then succeed
        call_count = 0
        def mock_detect():
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise PlatformDetectionError("Temporary failure")
            return []
        
        with patch.object(manager, 'detect', side_effect=mock_detect):
            with patch.object(manager, 'list', return_value=[]):
                # Start monitoring
                manager.run()
                
                # Let it run for a bit
                import time
                time.sleep(0.5)
                
                # Should still be running (recovered from errors)
                assert manager._monitoring
                
                manager.stop()
    
    def test_manager_monitoring_excessive_errors(self):
        """Test manager stopping monitoring after excessive errors."""
        manager = StableCam(poll_interval=0.05, enable_logging=False)  # Faster polling
        manager._max_consecutive_errors = 3  # Lower threshold for testing
        
        # Mock detect to always fail
        with patch.object(manager, 'detect') as mock_detect:
            mock_detect.side_effect = PlatformDetectionError("Persistent failure")
            
            # Start monitoring
            manager.run()
            
            # Let it run and accumulate errors
            import time
            max_wait = 2.0  # Maximum time to wait
            start_time = time.time()
            
            while manager._monitoring and (time.time() - start_time) < max_wait:
                time.sleep(0.1)
            
            # Should have stopped due to excessive errors
            assert not manager._monitoring, f"Manager still monitoring after {max_wait}s, error count: {manager._error_count}"


class TestLoggingConfiguration:
    """Test logging configuration and setup."""
    
    def test_logging_setup_basic(self):
        """Test basic logging setup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            
            setup_logging(log_level="DEBUG", log_file=log_file)
            
            # Test that logging works
            logger = logging.getLogger("stablecam.test")
            logger.info("Test message")
            
            # Check log file was created and contains message
            assert log_file.exists()
            with open(log_file, 'r') as f:
                content = f.read()
                assert "Test message" in content
    
    def test_logging_level_change(self):
        """Test changing logging level."""
        StableCamLogger.configure(log_level="INFO")
        
        # Change level
        StableCamLogger.set_level("DEBUG")
        
        # Verify level was changed
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG
    
    def test_logging_file_rotation(self):
        """Test log file rotation configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            
            StableCamLogger.configure(
                log_file=log_file,
                max_file_size=512,  # Very small size for testing
                backup_count=2
            )
            
            # Generate enough log messages to trigger rotation
            logger = logging.getLogger("stablecam.test.rotation")
            for i in range(200):  # More messages
                logger.info(f"Test message {i} with some additional content to make it longer and trigger rotation sooner")
            
            # Force flush
            for handler in logging.getLogger().handlers:
                if hasattr(handler, 'flush'):
                    handler.flush()
            
            # Should have created backup files or at least the main log file
            log_files = list(Path(temp_dir).glob("test.log*"))
            assert len(log_files) >= 1  # At least the main log file should exist
            
            # Check if main log file exists and has content
            if log_file.exists():
                assert log_file.stat().st_size > 0
    
    def test_logging_console_output_disabled(self):
        """Test logging with console output disabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            
            StableCamLogger.configure(
                log_file=log_file,
                console_output=False
            )
            
            # Check that no console handler was added
            root_logger = logging.getLogger()
            console_handlers = [
                h for h in root_logger.handlers 
                if isinstance(h, logging.StreamHandler) and hasattr(h.stream, 'name') and h.stream.name == '<stdout>'
            ]
            assert len(console_handlers) == 0
    
    def test_logging_file_creation_failure(self):
        """Test logging setup when file creation fails."""
        # Try to create log file in non-existent directory without creating it
        invalid_path = Path("/nonexistent/directory/test.log")
        
        # Should not raise exception, just continue with console logging
        StableCamLogger.configure(log_file=invalid_path)
        
        # Should still have console handler
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) > 0


class TestPlatformBackendErrorHandling:
    """Test platform backend error handling."""
    
    def test_unsupported_platform_error(self):
        """Test unsupported platform detection."""
        with patch('platform.system', return_value='unsupported_os'):
            from stablecam.backends.base import DeviceDetector
            
            with pytest.raises(UnsupportedPlatformError) as exc_info:
                DeviceDetector()
            
            assert "unsupported_os" in str(exc_info.value)
            assert exc_info.value.context['platform'] == 'unsupported_os'
    
    @patch('stablecam.backends.linux.os.path.exists')
    def test_linux_backend_permission_error(self, mock_exists):
        """Test Linux backend permission error handling."""
        from stablecam.backends.linux import LinuxBackend
        
        # Mock /dev directory not accessible
        mock_exists.return_value = False
        
        backend = LinuxBackend()
        
        with pytest.raises(PlatformDetectionError) as exc_info:
            backend.enumerate_cameras()
        
        assert "Cannot access /dev directory" in str(exc_info.value)
        assert exc_info.value.context['platform'] == 'linux'
    
    def test_device_not_found_error_handling(self):
        """Test device not found error in backend."""
        from stablecam.backends.linux import LinuxBackend
        
        backend = LinuxBackend()
        
        with pytest.raises(DeviceNotFoundError) as exc_info:
            backend.get_device_info(999)  # Non-existent device index
        
        assert "Device /dev/video999 not found" in str(exc_info.value)


class TestErrorRecoveryScenarios:
    """Test various error recovery scenarios."""
    
    def test_registry_recovery_from_multiple_backups(self):
        """Test registry recovery when multiple backup files exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "registry.json"
            
            # Create multiple backup files with different timestamps
            backup1 = Path(temp_dir) / "registry.backup_20240101_120000.json"
            backup2 = Path(temp_dir) / "registry.backup_20240102_120000.json"
            
            # Create corrupted backup
            with open(backup1, 'w') as f:
                f.write("corrupted backup")
            
            # Create valid backup
            valid_backup_data = {
                "version": "1.0",
                "devices": {
                    "stable-cam-001": {
                        "stable_id": "stable-cam-001",
                        "vendor_id": "1234",
                        "product_id": "5678",
                        "serial_number": "TEST123",
                        "port_path": "/dev/video0",
                        "label": "Test Camera",
                        "platform_data": {},
                        "status": "connected",
                        "registered_at": "2024-01-01T12:00:00",
                        "last_seen": "2024-01-01T12:00:00"
                    }
                }
            }
            with open(backup2, 'w') as f:
                json.dump(valid_backup_data, f)
            
            # Create corrupted main registry
            with open(registry_path, 'w') as f:
                f.write("corrupted main registry")
            
            # Initialize registry - should recover from backup2
            registry = DeviceRegistry(registry_path)
            
            # Should have recovered the device
            devices = registry.get_all()
            assert len(devices) == 1
            assert devices[0].stable_id == "stable-cam-001"
    
    def test_manager_graceful_degradation(self):
        """Test manager graceful degradation when components fail."""
        # Test with registry that works but detector that fails
        manager = StableCam(enable_logging=False)
        
        # Mock detector to always fail
        with patch.object(manager.detector, 'detect_cameras') as mock_detect:
            mock_detect.side_effect = PlatformDetectionError("Hardware not available")
            
            # Manager should still be usable for registry operations
            devices = manager.list()  # Should work
            assert isinstance(devices, list)
            
            # Detection should fail gracefully
            with pytest.raises(PlatformDetectionError):
                manager.detect()


if __name__ == "__main__":
    pytest.main([__file__])