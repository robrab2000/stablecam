"""
Unit tests for platform detection backend interfaces.

Tests the abstract backend interface, device detector, and platform selection
logic using mock backends for cross-platform compatibility.
"""

import platform
import pytest
from unittest.mock import Mock, patch, MagicMock

from stablecam.models import CameraDevice, DeviceStatus
from stablecam.backends.base import PlatformBackend, DeviceDetector
from stablecam.backends.exceptions import (
    PlatformDetectionError, 
    DeviceNotFoundError, 
    UnsupportedPlatformError
)


class MockBackend(PlatformBackend):
    """Mock backend for testing purposes."""
    
    def __init__(self, platform_name: str = "mock", cameras: list = None):
        self._platform_name = platform_name
        self._cameras = cameras or []
    
    @property
    def platform_name(self) -> str:
        return self._platform_name
    
    def enumerate_cameras(self) -> list:
        return self._cameras.copy()
    
    def get_device_info(self, system_index: int) -> CameraDevice:
        for camera in self._cameras:
            if camera.system_index == system_index:
                return camera
        raise DeviceNotFoundError(f"Device with index {system_index} not found")


class TestPlatformBackend:
    """Test the abstract PlatformBackend interface."""
    
    def test_abstract_methods_must_be_implemented(self):
        """Test that PlatformBackend cannot be instantiated directly."""
        with pytest.raises(TypeError):
            PlatformBackend()
    
    def test_mock_backend_implements_interface(self):
        """Test that MockBackend properly implements the interface."""
        backend = MockBackend("test")
        
        assert backend.platform_name == "test"
        assert backend.enumerate_cameras() == []
        
        with pytest.raises(DeviceNotFoundError):
            backend.get_device_info(0)
    
    def test_mock_backend_with_cameras(self):
        """Test MockBackend with sample camera data."""
        camera1 = CameraDevice(
            system_index=0,
            vendor_id="046d",
            product_id="085b", 
            serial_number="ABC123",
            port_path="/dev/video0",
            label="Test Camera 1",
            platform_data={}
        )
        
        camera2 = CameraDevice(
            system_index=1,
            vendor_id="046d",
            product_id="085c",
            serial_number="DEF456", 
            port_path="/dev/video1",
            label="Test Camera 2",
            platform_data={}
        )
        
        backend = MockBackend("test", [camera1, camera2])
        
        cameras = backend.enumerate_cameras()
        assert len(cameras) == 2
        assert cameras[0].system_index == 0
        assert cameras[1].system_index == 1
        
        # Test get_device_info
        device = backend.get_device_info(0)
        assert device.system_index == 0
        assert device.serial_number == "ABC123"
        
        # Test device not found
        with pytest.raises(DeviceNotFoundError):
            backend.get_device_info(99)


class TestDeviceDetector:
    """Test the DeviceDetector class."""
    
    @patch('platform.system')
    def test_linux_backend_selection(self, mock_system):
        """Test that Linux backend is selected on Linux systems."""
        mock_system.return_value = "Linux"
        
        with patch('stablecam.backends.linux.LinuxBackend') as mock_linux:
            mock_instance = Mock()
            mock_linux.return_value = mock_instance
            
            detector = DeviceDetector()
            assert detector.get_platform_backend() == mock_instance
            mock_linux.assert_called_once()
    
    @patch('platform.system')
    def test_windows_backend_selection(self, mock_system):
        """Test that Windows backend is selected on Windows systems."""
        mock_system.return_value = "Windows"
        
        with patch('stablecam.backends.windows.WindowsBackend') as mock_windows:
            mock_instance = Mock()
            mock_windows.return_value = mock_instance
            
            detector = DeviceDetector()
            assert detector.get_platform_backend() == mock_instance
            mock_windows.assert_called_once()
    
    @patch('platform.system')
    def test_macos_backend_selection(self, mock_system):
        """Test that macOS backend is selected on Darwin systems."""
        mock_system.return_value = "Darwin"
        
        with patch('stablecam.backends.macos.MacOSBackend') as mock_macos:
            mock_instance = Mock()
            mock_macos.return_value = mock_instance
            
            detector = DeviceDetector()
            assert detector.get_platform_backend() == mock_instance
            mock_macos.assert_called_once()
    
    @patch('platform.system')
    def test_unsupported_platform_raises_error(self, mock_system):
        """Test that unsupported platforms raise UnsupportedPlatformError."""
        mock_system.return_value = "FreeBSD"
        
        with pytest.raises(UnsupportedPlatformError) as exc_info:
            DeviceDetector()
        
        assert "Unsupported platform: freebsd" in str(exc_info.value)
    
    def test_detect_cameras_delegates_to_backend(self):
        """Test that detect_cameras calls the backend's enumerate_cameras method."""
        camera = CameraDevice(
            system_index=0,
            vendor_id="046d",
            product_id="085b",
            serial_number="ABC123",
            port_path="/dev/video0", 
            label="Test Camera",
            platform_data={}
        )
        
        mock_backend = MockBackend("test", [camera])
        
        detector = DeviceDetector()
        detector._backend = mock_backend
        
        cameras = detector.detect_cameras()
        assert len(cameras) == 1
        assert cameras[0].system_index == 0
        assert cameras[0].serial_number == "ABC123"
    
    def test_get_platform_backend_returns_backend(self):
        """Test that get_platform_backend returns the current backend."""
        mock_backend = MockBackend("test")
        
        detector = DeviceDetector()
        detector._backend = mock_backend
        
        assert detector.get_platform_backend() == mock_backend
    
    def test_backend_error_propagation(self):
        """Test that backend errors are properly propagated."""
        mock_backend = Mock()
        mock_backend.enumerate_cameras.side_effect = PlatformDetectionError("Test error")
        
        detector = DeviceDetector()
        detector._backend = mock_backend
        
        with pytest.raises(PlatformDetectionError) as exc_info:
            detector.detect_cameras()
        
        assert "Test error" in str(exc_info.value)


class TestCrossPlatformCompatibility:
    """Test cross-platform compatibility using mock backends."""
    
    def test_multiple_platform_backends(self):
        """Test that different platform backends can coexist."""
        linux_backend = MockBackend("linux")
        windows_backend = MockBackend("windows") 
        macos_backend = MockBackend("macos")
        
        assert linux_backend.platform_name == "linux"
        assert windows_backend.platform_name == "windows"
        assert macos_backend.platform_name == "macos"
        
        # All should implement the same interface
        for backend in [linux_backend, windows_backend, macos_backend]:
            assert hasattr(backend, 'enumerate_cameras')
            assert hasattr(backend, 'get_device_info')
            assert hasattr(backend, 'platform_name')
    
    def test_consistent_camera_data_format(self):
        """Test that all backends return consistent CameraDevice format."""
        camera_data = [
            CameraDevice(
                system_index=0,
                vendor_id="046d",
                product_id="085b",
                serial_number="ABC123",
                port_path="/dev/video0",
                label="Test Camera",
                platform_data={"platform": "linux"}
            )
        ]
        
        backends = [
            MockBackend("linux", camera_data),
            MockBackend("windows", camera_data),
            MockBackend("macos", camera_data)
        ]
        
        for backend in backends:
            cameras = backend.enumerate_cameras()
            assert len(cameras) == 1
            
            camera = cameras[0]
            assert isinstance(camera, CameraDevice)
            assert camera.system_index == 0
            assert camera.vendor_id == "046d"
            assert camera.product_id == "085b"
            assert camera.serial_number == "ABC123"
    
    @patch('platform.system')
    def test_platform_detection_case_insensitive(self, mock_system):
        """Test that platform detection is case insensitive."""
        test_cases = [
            ("LINUX", "linux"),
            ("Linux", "linux"), 
            ("WINDOWS", "windows"),
            ("Windows", "windows"),
            ("DARWIN", "darwin"),
            ("Darwin", "darwin")
        ]
        
        for system_name, expected_lower in test_cases:
            mock_system.return_value = system_name
            
            # Mock the backend imports to avoid actual imports
            with patch('stablecam.backends.linux.LinuxBackend') as mock_linux, \
                 patch('stablecam.backends.windows.WindowsBackend') as mock_windows, \
                 patch('stablecam.backends.macos.MacOSBackend') as mock_macos:
                
                mock_linux.return_value = Mock()
                mock_windows.return_value = Mock()
                mock_macos.return_value = Mock()
                
                detector = DeviceDetector()
                
                # Verify the correct backend was called based on lowercase comparison
                if expected_lower == "linux":
                    mock_linux.assert_called_once()
                elif expected_lower == "windows":
                    mock_windows.assert_called_once()
                elif expected_lower == "darwin":
                    mock_macos.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])