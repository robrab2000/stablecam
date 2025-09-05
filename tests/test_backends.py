"""
Unit tests for platform detection backend interfaces.

Tests the abstract backend interface, device detector, and platform selection
logic using mock backends for cross-platform compatibility.
"""

import platform
import pytest
import os
from unittest.mock import Mock, patch, MagicMock, mock_open

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


class TestLinuxBackend:
    """Test the Linux camera detection backend."""
    
    def setup_method(self):
        """Set up test fixtures."""
        from stablecam.backends.linux import LinuxBackend
        self.backend = LinuxBackend()
    
    def test_platform_name(self):
        """Test that platform name is correctly set."""
        assert self.backend.platform_name == "linux"
    
    @patch('glob.glob')
    @patch('os.path.exists')
    @patch('os.access')
    def test_enumerate_cameras_basic(self, mock_access, mock_exists, mock_glob):
        """Test basic camera enumeration without external libraries."""
        # Mock video device discovery
        mock_glob.return_value = ['/dev/video0', '/dev/video1']
        mock_exists.return_value = True
        mock_access.return_value = True
        
        # Mock the backend to not use external libraries
        self.backend._pyudev = None
        self.backend._v4l2 = None
        
        with patch.object(self.backend, '_create_camera_device') as mock_create:
            mock_camera = CameraDevice(
                system_index=0,
                vendor_id='046d',
                product_id='085b',
                serial_number='ABC123',
                port_path='/dev/video0',
                label='Test Camera',
                platform_data={}
            )
            mock_create.return_value = mock_camera
            
            cameras = self.backend.enumerate_cameras()
            
            assert len(cameras) == 2
            assert mock_create.call_count == 2
    
    @patch('glob.glob')
    def test_enumerate_cameras_no_devices(self, mock_glob):
        """Test enumeration when no video devices are found."""
        mock_glob.return_value = []
        
        cameras = self.backend.enumerate_cameras()
        assert cameras == []
    
    @patch('glob.glob')
    @patch('os.path.exists')
    @patch('os.access')
    def test_enumerate_cameras_with_error(self, mock_access, mock_exists, mock_glob):
        """Test enumeration handles device processing errors gracefully."""
        mock_glob.return_value = ['/dev/video0', '/dev/video1']
        mock_exists.return_value = True
        mock_access.return_value = True
        
        with patch.object(self.backend, '_create_camera_device') as mock_create:
            # First device succeeds, second fails
            mock_camera = CameraDevice(
                system_index=0,
                vendor_id='046d',
                product_id='085b',
                serial_number='ABC123',
                port_path='/dev/video0',
                label='Test Camera',
                platform_data={}
            )
            mock_create.side_effect = [mock_camera, Exception("Device error")]
            
            cameras = self.backend.enumerate_cameras()
            
            # Should return the successful device and continue
            assert len(cameras) == 1
            assert cameras[0].system_index == 0
    
    @patch('os.path.exists')
    def test_get_device_info_success(self, mock_exists):
        """Test getting device info for existing device."""
        mock_exists.return_value = True
        
        with patch.object(self.backend, '_create_camera_device') as mock_create:
            mock_camera = CameraDevice(
                system_index=0,
                vendor_id='046d',
                product_id='085b',
                serial_number='ABC123',
                port_path='/dev/video0',
                label='Test Camera',
                platform_data={}
            )
            mock_create.return_value = mock_camera
            
            device = self.backend.get_device_info(0)
            
            assert device.system_index == 0
            assert device.vendor_id == '046d'
            mock_create.assert_called_once_with('/dev/video0')
    
    @patch('os.path.exists')
    def test_get_device_info_not_found(self, mock_exists):
        """Test getting device info for non-existent device."""
        mock_exists.return_value = False
        
        with pytest.raises(DeviceNotFoundError) as exc_info:
            self.backend.get_device_info(99)
        
        assert "Device /dev/video99 not found" in str(exc_info.value)
    
    @patch('os.path.exists')
    def test_get_device_info_creation_fails(self, mock_exists):
        """Test getting device info when device creation fails."""
        mock_exists.return_value = True
        
        with patch.object(self.backend, '_create_camera_device') as mock_create:
            mock_create.return_value = None
            
            with pytest.raises(DeviceNotFoundError) as exc_info:
                self.backend.get_device_info(0)
            
            assert "Could not get info for device 0" in str(exc_info.value)
    
    def test_find_video_devices_filtering(self):
        """Test that video device finding filters correctly."""
        with patch('glob.glob') as mock_glob:
            # Include various device types
            mock_glob.return_value = [
                '/dev/video0',
                '/dev/video1', 
                '/dev/video-codec0',  # Should be filtered out
                '/dev/video10',
                '/dev/videodev'       # Should be filtered out
            ]
            
            with patch.object(self.backend, '_is_camera_device') as mock_is_camera:
                mock_is_camera.return_value = True
                
                devices = self.backend._find_video_devices()
                
                # Should only include numeric video devices
                expected = ['/dev/video0', '/dev/video1', '/dev/video10']
                assert devices == expected
    
    @patch('os.access')
    def test_is_camera_device_no_access(self, mock_access):
        """Test camera device check when device is not accessible."""
        mock_access.return_value = False
        
        result = self.backend._is_camera_device('/dev/video0')
        assert result is False
    
    @patch('os.access')
    def test_is_camera_device_fallback(self, mock_access):
        """Test camera device check fallback when v4l2 not available."""
        mock_access.return_value = True
        self.backend._v4l2 = None
        
        result = self.backend._is_camera_device('/dev/video0')
        assert result is True
    
    def test_create_camera_device_invalid_path(self):
        """Test camera device creation with invalid device path."""
        result = self.backend._create_camera_device('/dev/invalid')
        assert result is None
    
    @patch('os.path.exists')
    def test_create_camera_device_success(self, mock_exists):
        """Test successful camera device creation."""
        mock_exists.return_value = True
        self.backend._pyudev = None  # Use fallback method
        
        with patch.object(self.backend, '_get_fallback_info') as mock_fallback, \
             patch.object(self.backend, '_get_device_label') as mock_label:
            
            mock_fallback.return_value = {
                'vendor_id': '046d',
                'product_id': '085b',
                'serial_number': 'ABC123',
                'port_path': '/dev/video0',
                'subsystem': 'video4linux',
                'driver': 'uvcvideo'
            }
            mock_label.return_value = 'Test Camera'
            
            device = self.backend._create_camera_device('/dev/video0')
            
            assert device is not None
            assert device.system_index == 0
            assert device.vendor_id == '046d'
            assert device.product_id == '085b'
            assert device.serial_number == 'ABC123'
            assert device.label == 'Test Camera'
    
    def test_get_fallback_info_basic(self):
        """Test fallback hardware info extraction."""
        info = self.backend._get_fallback_info('/dev/video0')
        
        # Should return basic structure
        assert 'vendor_id' in info
        assert 'product_id' in info
        assert 'serial_number' in info
        assert 'port_path' in info
        assert info['port_path'] == '/dev/video0'
        assert info['subsystem'] == 'video4linux'
    
    @patch('os.path.exists')
    @patch('os.path.islink')
    @patch('os.path.realpath')
    def test_get_fallback_info_with_sysfs(self, mock_realpath, mock_islink, mock_exists):
        """Test fallback info extraction using sysfs."""
        mock_exists.return_value = True
        mock_islink.return_value = True
        mock_realpath.return_value = '/sys/devices/usb1/1-1/video4linux/video0'
        
        with patch.object(self.backend, '_extract_usb_info_from_path') as mock_extract:
            mock_extract.return_value = {
                'vendor_id': '046d',
                'product_id': '085b',
                'serial_number': 'ABC123'
            }
            
            info = self.backend._get_fallback_info('/dev/video0')
            
            assert info['vendor_id'] == '046d'
            assert info['product_id'] == '085b'
            assert info['serial_number'] == 'ABC123'
    
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_extract_usb_info_from_path(self, mock_file, mock_exists):
        """Test USB info extraction from sysfs path."""
        # Mock file existence and content
        def exists_side_effect(path):
            return path.endswith(('idVendor', 'idProduct', 'serial'))
        
        mock_exists.side_effect = exists_side_effect
        
        # Mock file contents
        file_contents = {
            'idVendor': '046d\n',
            'idProduct': '085b\n', 
            'serial': 'ABC123456\n'
        }
        
        def open_side_effect(path, mode='r'):
            filename = os.path.basename(path)
            if filename in file_contents:
                return mock_open(read_data=file_contents[filename]).return_value
            raise FileNotFoundError()
        
        mock_file.side_effect = open_side_effect
        
        usb_path = '/sys/devices/usb1/1-1'
        info = self.backend._extract_usb_info_from_path(usb_path)
        
        assert info['vendor_id'] == '046d'
        assert info['product_id'] == '085b'
        assert info['serial_number'] == 'ABC123456'
        assert info['port_path'] == usb_path
    
    def test_get_device_label_fallback(self):
        """Test device label generation fallback."""
        hardware_info = {
            'vendor_id': '046d',
            'product_id': '085b'
        }
        
        # Mock v4l2 not available
        self.backend._v4l2 = None
        
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = False
            
            label = self.backend._get_device_label('/dev/video0', hardware_info)
            
            assert label == 'USB Camera 046d:085b'
    
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='Test Camera Name\n')
    def test_get_device_label_from_sysfs(self, mock_file, mock_exists):
        """Test device label extraction from sysfs."""
        mock_exists.return_value = True
        
        label = self.backend._get_device_label('/dev/video0', {})
        
        assert label == 'Test Camera Name'
        mock_exists.assert_called_with('/sys/class/video4linux/video0/name')
    
    def test_get_device_label_unknown_hardware(self):
        """Test device label with unknown hardware info."""
        hardware_info = {
            'vendor_id': 'unknown',
            'product_id': 'unknown'
        }
        
        self.backend._v4l2 = None
        
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = False
            
            label = self.backend._get_device_label('/dev/video0', hardware_info)
            
            assert label == 'Camera video0'


class TestLinuxBackendWithMockedLibraries:
    """Test Linux backend with mocked external libraries."""
    
    def setup_method(self):
        """Set up test fixtures with mocked libraries."""
        from stablecam.backends.linux import LinuxBackend
        
        # Create mock libraries
        self.mock_pyudev = Mock()
        self.mock_v4l2 = Mock()
        self.mock_fcntl = Mock()
        self.mock_struct = Mock()
        
        # Create backend and inject mocks
        self.backend = LinuxBackend()
        self.backend._pyudev = self.mock_pyudev
        self.backend._v4l2 = self.mock_v4l2
        self.backend._fcntl = self.mock_fcntl
        self.backend._struct = self.mock_struct
    
    def test_check_v4l2_capabilities_success(self):
        """Test v4l2 capability checking."""
        # Mock v4l2 constants
        self.mock_v4l2.VIDIOC_QUERYCAP = 0x80685600
        
        # Mock struct packing/unpacking
        self.mock_struct.pack.return_value = b'\x00' * 64
        
        # Mock capability response - set video capture bit
        caps_data = b'\x00' * 16 + b'test_card' + b'\x00' * 16 + b'test_bus' + b'\x00' * 16 + b'\x01\x00\x00\x00\x01\x00\x00\x00'
        self.mock_struct.unpack.return_value = (b'driver', b'test_card', b'test_bus', 1, 0x00000001)
        
        # Mock fcntl ioctl
        self.mock_fcntl.ioctl.return_value = caps_data
        
        with patch('builtins.open', mock_open()) as mock_file:
            result = self.backend._check_v4l2_capabilities('/dev/video0')
            
            assert result is True
            mock_file.assert_called_once_with('/dev/video0', 'rb')
    
    def test_get_udev_info_success(self):
        """Test udev info extraction."""
        # Mock udev context and device
        mock_context = Mock()
        mock_device = Mock()
        mock_usb_device = Mock()
        
        self.mock_pyudev.Context.return_value = mock_context
        self.mock_pyudev.Devices.from_device_file.return_value = mock_device
        
        # Set up device hierarchy
        mock_device.subsystem = 'video4linux'
        mock_device.parent = mock_usb_device
        
        # Mock device.get() calls
        def device_get(key, default=None):
            device_values = {
                'ID_V4L_DRIVER': 'uvcvideo',
                'DRIVER': 'uvcvideo'
            }
            return device_values.get(key, default)
        
        mock_device.get.side_effect = device_get
        
        mock_usb_device.subsystem = 'usb'
        mock_usb_device.device_type = 'usb_device'
        mock_usb_device.parent = None
        
        # Mock usb_device.get() calls
        def usb_get(key, default=None):
            usb_values = {
                'ID_VENDOR_ID': '046d',
                'ID_MODEL_ID': '085b',
                'ID_SERIAL_SHORT': 'ABC123',
                'DEVPATH': '/devices/usb1/1-1'
            }
            return usb_values.get(key, default)
        
        mock_usb_device.get.side_effect = usb_get
        
        info = self.backend._get_udev_info('/dev/video0')
        
        assert info['vendor_id'] == '046d'
        assert info['product_id'] == '085b'
        assert info['serial_number'] == 'ABC123'
        assert info['port_path'] == '/devices/usb1/1-1'
        assert info['driver'] == 'uvcvideo'
    
    def test_get_udev_info_no_usb_parent(self):
        """Test udev info when no USB parent device is found."""
        mock_context = Mock()
        mock_device = Mock()
        
        self.mock_pyudev.Context.return_value = mock_context
        self.mock_pyudev.Devices.from_device_file.return_value = mock_device
        
        # Device with no USB parent
        mock_device.subsystem = 'video4linux'
        mock_device.parent = None
        
        # Mock device.get() calls
        def device_get(key, default=None):
            device_values = {
                'ID_V4L_DRIVER': 'uvcvideo',
                'DRIVER': 'uvcvideo'
            }
            return device_values.get(key, default)
        
        mock_device.get.side_effect = device_get
        
        info = self.backend._get_udev_info('/dev/video0')
        
        # Should return partial info when no USB device found
        assert info['driver'] == 'uvcvideo'
        # USB-specific fields should not be present or be None
        assert info.get('vendor_id') is None
        assert info.get('product_id') is None
    
    def test_get_udev_info_exception_fallback(self):
        """Test udev info falls back when exception occurs."""
        # Mock exception during udev operations
        self.mock_pyudev.Context.side_effect = Exception("udev error")
        
        with patch.object(self.backend, '_get_fallback_info') as mock_fallback:
            mock_fallback.return_value = {'vendor_id': 'unknown', 'driver': None}
            
            info = self.backend._get_udev_info('/dev/video0')
            
            # Should call fallback when exception occurs
            mock_fallback.assert_called_once_with('/dev/video0')
            assert info['vendor_id'] == 'unknown'
    
    def test_get_v4l2_device_name_success(self):
        """Test v4l2 device name extraction."""
        self.mock_v4l2.VIDIOC_QUERYCAP = 0x80685600
        
        # Mock struct operations
        self.mock_struct.pack.return_value = b'\x00' * 64
        
        # Create mock response with card name at offset 16
        card_name = b'Test Camera Device\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        caps_data = b'\x00' * 16 + card_name + b'\x00' * 16
        
        self.mock_fcntl.ioctl.return_value = caps_data
        
        with patch('builtins.open', mock_open()) as mock_file:
            name = self.backend._get_v4l2_device_name('/dev/video0')
            
            assert name == 'Test Camera Device'
    
    def test_get_v4l2_device_name_failure(self):
        """Test v4l2 device name extraction failure."""
        self.mock_fcntl.ioctl.side_effect = Exception("ioctl failed")
        
        with patch('builtins.open', mock_open()):
            name = self.backend._get_v4l2_device_name('/dev/video0')
            
            assert name is None


if __name__ == "__main__":
    pytest.main([__file__])