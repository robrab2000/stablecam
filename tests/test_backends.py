"""
Unit tests for platform detection backend interfaces.

Tests the abstract backend interface, device detector, and platform selection
logic using mock backends for cross-platform compatibility.
"""

import platform
import pytest
import os
import json
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


class TestWindowsBackend:
    """Test the Windows camera detection backend."""
    
    def setup_method(self):
        """Set up test fixtures."""
        from stablecam.backends.windows import WindowsBackend
        self.backend = WindowsBackend()
    
    def test_platform_name(self):
        """Test that platform name is correctly set."""
        assert self.backend.platform_name == "windows"
    
    @patch('subprocess.run')
    def test_check_wmi_availability_success(self, mock_run):
        """Test WMI availability check when WMI is available."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        result = self.backend._check_wmi_availability()
        assert result is True
        
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == 'wmic'
    
    @patch('subprocess.run')
    def test_check_wmi_availability_failure(self, mock_run):
        """Test WMI availability check when WMI is not available."""
        mock_run.side_effect = Exception("Command not found")
        
        result = self.backend._check_wmi_availability()
        assert result is False
    
    @patch('subprocess.run')
    def test_check_powershell_availability_success(self, mock_run):
        """Test PowerShell availability check when PowerShell is available."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        result = self.backend._check_powershell_availability()
        assert result is True
        
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == 'powershell'
    
    @patch('subprocess.run')
    def test_check_powershell_availability_failure(self, mock_run):
        """Test PowerShell availability check when PowerShell is not available."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result
        
        result = self.backend._check_powershell_availability()
        assert result is False
    
    def test_enumerate_cameras_basic(self):
        """Test basic camera enumeration."""
        with patch.object(self.backend, '_get_wmi_camera_devices') as mock_get_devices:
            mock_devices = [
                {
                    'Name': 'USB Camera',
                    'DeviceID': 'USB\\VID_046D&PID_085B\\ABC123',
                    'VendorID': '046d',
                    'ProductID': '085b',
                    'SerialNumber': 'ABC123',
                    'Status': 'OK'
                }
            ]
            mock_get_devices.return_value = mock_devices
            
            with patch.object(self.backend, '_create_camera_device') as mock_create:
                mock_camera = CameraDevice(
                    system_index=0,
                    vendor_id='046d',
                    product_id='085b',
                    serial_number='ABC123',
                    port_path='USB\\VID_046D&PID_085B\\ABC123',
                    label='USB Camera',
                    platform_data={}
                )
                mock_create.return_value = mock_camera
                
                cameras = self.backend.enumerate_cameras()
                
                assert len(cameras) == 1
                assert cameras[0].vendor_id == '046d'
                assert cameras[0].product_id == '085b'
                assert cameras[0].serial_number == 'ABC123'
    
    def test_enumerate_cameras_no_devices(self):
        """Test enumeration when no camera devices are found."""
        with patch.object(self.backend, '_get_wmi_camera_devices') as mock_get_devices:
            mock_get_devices.return_value = []
            
            cameras = self.backend.enumerate_cameras()
            assert cameras == []
    
    def test_enumerate_cameras_with_error(self):
        """Test enumeration handles device processing errors gracefully."""
        with patch.object(self.backend, '_get_wmi_camera_devices') as mock_get_devices:
            mock_devices = [
                {'Name': 'Camera 1', 'DeviceID': 'USB\\VID_046D&PID_085B\\ABC123'},
                {'Name': 'Camera 2', 'DeviceID': 'USB\\VID_046D&PID_085C\\DEF456'}
            ]
            mock_get_devices.return_value = mock_devices
            
            with patch.object(self.backend, '_create_camera_device') as mock_create:
                mock_camera = CameraDevice(
                    system_index=0,
                    vendor_id='046d',
                    product_id='085b',
                    serial_number='ABC123',
                    port_path='USB\\VID_046D&PID_085B\\ABC123',
                    label='Camera 1',
                    platform_data={}
                )
                # First device succeeds, second fails
                mock_create.side_effect = [mock_camera, Exception("Device error")]
                
                cameras = self.backend.enumerate_cameras()
                
                # Should return the successful device and continue
                assert len(cameras) == 1
                assert cameras[0].system_index == 0
    
    def test_get_device_info_success(self):
        """Test getting device info for existing device."""
        with patch.object(self.backend, '_get_wmi_camera_devices') as mock_get_devices:
            mock_devices = [
                {
                    'Name': 'USB Camera',
                    'DeviceID': 'USB\\VID_046D&PID_085B\\ABC123',
                    'VendorID': '046d',
                    'ProductID': '085b',
                    'SerialNumber': 'ABC123'
                }
            ]
            mock_get_devices.return_value = mock_devices
            
            with patch.object(self.backend, '_create_camera_device') as mock_create:
                mock_camera = CameraDevice(
                    system_index=0,
                    vendor_id='046d',
                    product_id='085b',
                    serial_number='ABC123',
                    port_path='USB\\VID_046D&PID_085B\\ABC123',
                    label='USB Camera',
                    platform_data={}
                )
                mock_create.return_value = mock_camera
                
                device = self.backend.get_device_info(0)
                
                assert device.system_index == 0
                assert device.vendor_id == '046d'
                assert device.product_id == '085b'
    
    def test_get_device_info_not_found(self):
        """Test getting device info for non-existent device."""
        with patch.object(self.backend, '_get_wmi_camera_devices') as mock_get_devices:
            mock_get_devices.return_value = []
            
            with pytest.raises(DeviceNotFoundError) as exc_info:
                self.backend.get_device_info(0)
            
            assert "Camera device at index 0 not found" in str(exc_info.value)
    
    def test_get_device_info_creation_fails(self):
        """Test getting device info when device creation fails."""
        with patch.object(self.backend, '_get_wmi_camera_devices') as mock_get_devices:
            mock_devices = [{'Name': 'USB Camera', 'DeviceID': 'USB\\VID_046D&PID_085B\\ABC123'}]
            mock_get_devices.return_value = mock_devices
            
            with patch.object(self.backend, '_create_camera_device') as mock_create:
                mock_create.return_value = None
                
                with pytest.raises(DeviceNotFoundError) as exc_info:
                    self.backend.get_device_info(0)
                
                assert "Could not get info for device at index 0" in str(exc_info.value)
    
    @patch('subprocess.run')
    def test_get_devices_via_powershell_success(self, mock_run):
        """Test device enumeration via PowerShell."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = '''[
            {
                "Name": "USB Camera",
                "DeviceID": "USB\\\\VID_046D&PID_085B\\\\ABC123",
                "VendorID": "046D",
                "ProductID": "085B",
                "SerialNumber": "ABC123",
                "Status": "OK"
            }
        ]'''
        mock_run.return_value = mock_result
        
        devices = self.backend._get_devices_via_powershell()
        
        assert len(devices) == 1
        assert devices[0]['Name'] == 'USB Camera'
        assert devices[0]['VendorID'] == '046d'
        assert devices[0]['ProductID'] == '085b'
        assert devices[0]['SerialNumber'] == 'ABC123'
    
    @patch('subprocess.run')
    def test_get_devices_via_powershell_single_device(self, mock_run):
        """Test PowerShell enumeration with single device (object instead of array)."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = '''{
            "Name": "USB Camera",
            "DeviceID": "USB\\\\VID_046D&PID_085B\\\\ABC123",
            "VendorID": "046D",
            "ProductID": "085B"
        }'''
        mock_run.return_value = mock_result
        
        devices = self.backend._get_devices_via_powershell()
        
        assert len(devices) == 1
        assert devices[0]['Name'] == 'USB Camera'
    
    @patch('subprocess.run')
    def test_get_devices_via_powershell_failure(self, mock_run):
        """Test PowerShell enumeration failure."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = 'PowerShell error'
        mock_result.stdout = ''
        mock_run.return_value = mock_result
        
        devices = self.backend._get_devices_via_powershell()
        assert devices == []
    
    @patch('subprocess.run')
    def test_get_devices_via_powershell_json_error(self, mock_run):
        """Test PowerShell enumeration with invalid JSON."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = 'invalid json'
        mock_run.return_value = mock_result
        
        devices = self.backend._get_devices_via_powershell()
        assert devices == []
    
    @patch('subprocess.run')
    def test_get_devices_via_wmic_success(self, mock_run):
        """Test device enumeration via WMIC."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = '''Node,ClassGuid,DeviceID,Name,PNPDeviceID,Service,Status
COMPUTER,{6BDD1FC6-810F-11D0-BEC7-08002BE2092F},USB\\VID_046D&PID_085B\\ABC123,USB Camera,USB\\VID_046D&PID_085B\\ABC123,usbvideo,OK
'''
        mock_run.return_value = mock_result
        
        with patch.object(self.backend, '_is_camera_device_name') as mock_is_camera:
            mock_is_camera.return_value = True
            
            devices = self.backend._get_devices_via_wmic()
            
            assert len(devices) == 1
            assert devices[0]['Name'] == 'USB Camera'
            assert devices[0]['VendorID'] == '046d'
            assert devices[0]['ProductID'] == '085b'
    
    @patch('subprocess.run')
    def test_get_devices_via_wmic_failure(self, mock_run):
        """Test WMIC enumeration failure."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = 'WMIC error'
        mock_run.return_value = mock_result
        
        devices = self.backend._get_devices_via_wmic()
        assert devices == []
    
    def test_get_devices_fallback(self):
        """Test fallback device enumeration."""
        devices = self.backend._get_devices_fallback()
        
        # Should return at least one basic device for testing
        assert len(devices) >= 1
        assert 'Name' in devices[0]
        assert 'DeviceID' in devices[0]
        assert 'VendorID' in devices[0]
        assert 'ProductID' in devices[0]
    
    def test_is_camera_device_name_positive_cases(self):
        """Test camera device name detection for positive cases."""
        camera_names = [
            'USB Camera',
            'Logitech Webcam',
            'Microsoft LifeCam',
            'Integrated Camera',
            'USB Video Device',
            'HD Pro Webcam C920'
        ]
        
        for name in camera_names:
            assert self.backend._is_camera_device_name(name) is True
    
    def test_is_camera_device_name_negative_cases(self):
        """Test camera device name detection for negative cases."""
        non_camera_names = [
            'USB Mass Storage',
            'Bluetooth Device',
            'Network Adapter',
            'Audio Device',
            '',
            None
        ]
        
        for name in non_camera_names:
            assert self.backend._is_camera_device_name(name) is False
    
    def test_parse_wmic_device_info_success(self):
        """Test parsing WMIC CSV device information."""
        csv_parts = [
            'COMPUTER',
            '{6BDD1FC6-810F-11D0-BEC7-08002BE2092F}',
            'USB\\VID_046D&PID_085B\\ABC123',
            'USB Camera',
            'USB\\VID_046D&PID_085B\\ABC123',
            'usbvideo',
            'OK'
        ]
        
        device_info = self.backend._parse_wmic_device_info(csv_parts)
        
        assert device_info is not None
        assert device_info['Name'] == 'USB Camera'
        assert device_info['VendorID'] == '046d'
        assert device_info['ProductID'] == '085b'
        assert device_info['SerialNumber'] == 'ABC123'
        assert device_info['Status'] == 'OK'
    
    def test_parse_wmic_device_info_insufficient_parts(self):
        """Test parsing WMIC CSV with insufficient parts."""
        csv_parts = ['COMPUTER', 'ClassGuid']  # Too few parts
        
        device_info = self.backend._parse_wmic_device_info(csv_parts)
        assert device_info is None
    
    def test_parse_usb_device_id_full_info(self):
        """Test USB device ID parsing with full information."""
        device_id = 'USB\\VID_046D&PID_085B\\ABC123456'
        
        vendor_id, product_id, serial_number = self.backend._parse_usb_device_id(device_id)
        
        assert vendor_id == '046d'
        assert product_id == '085b'
        assert serial_number == 'ABC123456'
    
    def test_parse_usb_device_id_no_serial(self):
        """Test USB device ID parsing without serial number."""
        device_id = 'USB\\VID_046D&PID_085B\\12345'  # Numeric instance ID
        
        vendor_id, product_id, serial_number = self.backend._parse_usb_device_id(device_id)
        
        assert vendor_id == '046d'
        assert product_id == '085b'
        assert serial_number is None  # Numeric instance IDs are not serial numbers
    
    def test_parse_usb_device_id_case_insensitive(self):
        """Test USB device ID parsing is case insensitive."""
        device_id = 'usb\\vid_046d&pid_085b\\abc123'
        
        vendor_id, product_id, serial_number = self.backend._parse_usb_device_id(device_id)
        
        assert vendor_id == '046d'
        assert product_id == '085b'
        assert serial_number == 'abc123'
    
    def test_parse_usb_device_id_malformed(self):
        """Test USB device ID parsing with malformed input."""
        device_id = 'NOT_A_USB_DEVICE_ID'
        
        vendor_id, product_id, serial_number = self.backend._parse_usb_device_id(device_id)
        
        assert vendor_id == 'unknown'
        assert product_id == 'unknown'
        assert serial_number is None
    
    def test_create_camera_device_success(self):
        """Test successful camera device creation."""
        device_info = {
            'Name': 'USB Camera',
            'DeviceID': 'USB\\VID_046D&PID_085B\\ABC123',
            'VendorID': '046d',
            'ProductID': '085b',
            'SerialNumber': 'ABC123',
            'Status': 'OK',
            'PNPDeviceID': 'USB\\VID_046D&PID_085B\\ABC123',
            'Service': 'usbvideo',
            'ClassGuid': '{6BDD1FC6-810F-11D0-BEC7-08002BE2092F}'
        }
        
        camera = self.backend._create_camera_device(0, device_info)
        
        assert camera is not None
        assert camera.system_index == 0
        assert camera.vendor_id == '046d'
        assert camera.product_id == '085b'
        assert camera.serial_number == 'ABC123'
        assert camera.label == 'USB Camera'
        assert camera.port_path == 'USB\\VID_046D&PID_085B\\ABC123'
        
        # Check platform data
        assert camera.platform_data['device_id'] == 'USB\\VID_046D&PID_085B\\ABC123'
        assert camera.platform_data['status'] == 'OK'
        assert camera.platform_data['service'] == 'usbvideo'
    
    def test_create_camera_device_minimal_info(self):
        """Test camera device creation with minimal information."""
        device_info = {
            'Name': 'Unknown Camera'
        }
        
        camera = self.backend._create_camera_device(1, device_info)
        
        assert camera is not None
        assert camera.system_index == 1
        assert camera.vendor_id == 'unknown'
        assert camera.product_id == 'unknown'
        assert camera.serial_number is None
        assert camera.label == 'Unknown Camera'
    
    def test_create_camera_device_exception(self):
        """Test camera device creation handles exceptions."""
        # Pass invalid device info that will cause an exception
        device_info = None
        
        camera = self.backend._create_camera_device(0, device_info)
        assert camera is None


class TestWindowsBackendIntegration:
    """Integration tests for Windows backend with mocked WMI responses."""
    
    def setup_method(self):
        """Set up test fixtures."""
        from stablecam.backends.windows import WindowsBackend
        self.backend = WindowsBackend()
    
    @patch('subprocess.run')
    def test_full_enumeration_workflow_powershell(self, mock_run):
        """Test complete enumeration workflow using PowerShell."""
        # Mock subprocess calls
        def mock_subprocess_run(cmd, *args, **kwargs):
            result = Mock()
            if cmd[0] == 'powershell':
                if len(cmd) == 2 and cmd[1] == '-Command' and cmd[1] == 'Get-Host':
                    # PowerShell availability check
                    result.returncode = 0
                else:
                    # PowerShell device enumeration
                    result.returncode = 0
                    result.stdout = '''[
                        {
                            "Name": "Logitech HD Pro Webcam C920",
                            "DeviceID": "USB\\\\VID_046D&PID_085B\\\\ABC123456",
                            "VendorID": "046D",
                            "ProductID": "085B", 
                            "SerialNumber": "ABC123456",
                            "Status": "OK"
                        },
                        {
                            "Name": "Microsoft LifeCam HD-3000",
                            "DeviceID": "USB\\\\VID_045E&PID_0779\\\\DEF789012",
                            "VendorID": "045E",
                            "ProductID": "0779",
                            "SerialNumber": "DEF789012",
                            "Status": "OK"
                        }
                    ]'''
            elif cmd[0] == 'wmic':
                # WMI availability check
                result.returncode = 0
            else:
                result.returncode = 0
            
            return result
        
        mock_run.side_effect = mock_subprocess_run
        
        # Create new backend instance with mocked availability
        from stablecam.backends.windows import WindowsBackend
        backend = WindowsBackend()
        
        cameras = backend.enumerate_cameras()
        
        assert len(cameras) == 2
        
        # Check first camera
        camera1 = cameras[0]
        assert camera1.system_index == 0
        assert camera1.vendor_id == '046d'
        assert camera1.product_id == '085b'
        assert camera1.serial_number == 'ABC123456'
        assert camera1.label == 'Logitech HD Pro Webcam C920'
        
        # Check second camera
        camera2 = cameras[1]
        assert camera2.system_index == 1
        assert camera2.vendor_id == '045e'
        assert camera2.product_id == '0779'
        assert camera2.serial_number == 'DEF789012'
        assert camera2.label == 'Microsoft LifeCam HD-3000'
    
    @patch('subprocess.run')
    def test_full_enumeration_workflow_wmic(self, mock_run):
        """Test complete enumeration workflow using WMIC."""
        # Mock availability checks - PowerShell fails, WMIC succeeds
        wmic_result = Mock()
        wmic_result.returncode = 0
        wmic_result.stdout = '''Node,ClassGuid,DeviceID,Name,PNPDeviceID,Service,Status
COMPUTER,{6BDD1FC6-810F-11D0-BEC7-08002BE2092F},USB\\VID_046D&PID_085B\\ABC123,Logitech HD Pro Webcam C920,USB\\VID_046D&PID_085B\\ABC123,usbvideo,OK
'''
        
        mock_run.side_effect = [
            Mock(returncode=1),  # PowerShell availability check fails
            Mock(returncode=0),  # WMI availability check succeeds
            wmic_result  # WMIC device enumeration
        ]
        
        # Create new backend instance with mocked availability
        from stablecam.backends.windows import WindowsBackend
        backend = WindowsBackend()
        
        cameras = backend.enumerate_cameras()
        
        assert len(cameras) == 1
        
        camera = cameras[0]
        assert camera.system_index == 0
        assert camera.vendor_id == '046d'
        assert camera.product_id == '085b'
        assert camera.serial_number == 'ABC123'
        assert camera.label == 'Logitech HD Pro Webcam C920'
    
    @patch('subprocess.run')
    def test_fallback_enumeration_workflow(self, mock_run):
        """Test enumeration workflow when both PowerShell and WMIC fail."""
        # Mock both availability checks to fail
        mock_run.side_effect = [
            Mock(returncode=1),  # PowerShell availability check fails
            Mock(returncode=1),  # WMI availability check fails
        ]
        
        # Create new backend instance with mocked availability
        from stablecam.backends.windows import WindowsBackend
        backend = WindowsBackend()
        
        cameras = backend.enumerate_cameras()
        
        # Should still return fallback devices
        assert len(cameras) >= 1
        
        camera = cameras[0]
        assert camera.system_index == 0
        assert camera.vendor_id == '0000'  # Fallback values
        assert camera.product_id == '0000'
        assert 'USB Camera' in camera.label


if __name__ == "__main__":
    pytest.main([__file__])


class TestMacOSBackend:
    """Test the macOS camera detection backend."""
    
    def setup_method(self):
        """Set up test fixtures."""
        from stablecam.backends.macos import MacOSBackend
        self.backend = MacOSBackend()
    
    def test_platform_name(self):
        """Test that platform name is correctly set."""
        assert self.backend.platform_name == "darwin"
    
    @patch('subprocess.run')
    def test_check_system_profiler_availability_success(self, mock_run):
        """Test system_profiler availability check when available."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        result = self.backend._check_system_profiler_availability()
        assert result is True
        
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == 'system_profiler'
    
    @patch('subprocess.run')
    def test_check_system_profiler_availability_failure(self, mock_run):
        """Test system_profiler availability check when not available."""
        mock_run.side_effect = Exception("Command not found")
        
        result = self.backend._check_system_profiler_availability()
        assert result is False
    
    @patch('subprocess.run')
    def test_check_ioreg_availability_success(self, mock_run):
        """Test ioreg availability check when available."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        result = self.backend._check_ioreg_availability()
        assert result is True
        
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == 'ioreg'
    
    @patch('subprocess.run')
    def test_check_ioreg_availability_failure(self, mock_run):
        """Test ioreg availability check when not available."""
        mock_run.side_effect = Exception("Command not found")
        
        result = self.backend._check_ioreg_availability()
        assert result is False
    
    def test_enumerate_cameras_basic(self):
        """Test basic camera enumeration."""
        with patch.object(self.backend, '_get_camera_devices') as mock_get_devices:
            mock_device_info = {
                '_name': 'FaceTime HD Camera',
                'vendor_id': '05ac',
                'product_id': '8600',
                'serial_number': None,
                'location_id': 'builtin',
                'device_path': 'AVFoundation:builtin',
                'manufacturer': 'Apple Inc.',
                'built_in': True
            }
            mock_get_devices.return_value = [mock_device_info]
            
            cameras = self.backend.enumerate_cameras()
            
            assert len(cameras) == 1
            assert cameras[0].system_index == 0
            assert cameras[0].vendor_id == '05ac'
            assert cameras[0].label == 'FaceTime HD Camera'
    
    def test_enumerate_cameras_no_devices(self):
        """Test enumeration when no camera devices are found."""
        with patch.object(self.backend, '_get_camera_devices') as mock_get_devices:
            mock_get_devices.return_value = []
            
            cameras = self.backend.enumerate_cameras()
            assert cameras == []
    
    def test_enumerate_cameras_with_error(self):
        """Test enumeration handles device processing errors gracefully."""
        with patch.object(self.backend, '_get_camera_devices') as mock_get_devices:
            mock_device_info = {
                '_name': 'Test Camera',
                'vendor_id': '046d',
                'product_id': '085b'
            }
            mock_get_devices.return_value = [mock_device_info]
            
            with patch.object(self.backend, '_create_camera_device') as mock_create:
                mock_create.side_effect = Exception("Device error")
                
                cameras = self.backend.enumerate_cameras()
                
                # Should handle error gracefully and return empty list
                assert cameras == []
    
    def test_get_device_info_success(self):
        """Test getting device info for existing device."""
        with patch.object(self.backend, '_get_camera_devices') as mock_get_devices:
            mock_device_info = {
                '_name': 'Test Camera',
                'vendor_id': '046d',
                'product_id': '085b',
                'serial_number': 'ABC123',
                'location_id': '0x14100000',
                'device_path': 'USB:0x14100000'
            }
            mock_get_devices.return_value = [mock_device_info]
            
            device = self.backend.get_device_info(0)
            
            assert device.system_index == 0
            assert device.vendor_id == '046d'
            assert device.product_id == '085b'
            assert device.serial_number == 'ABC123'
    
    def test_get_device_info_not_found(self):
        """Test getting device info for non-existent device."""
        with patch.object(self.backend, '_get_camera_devices') as mock_get_devices:
            mock_get_devices.return_value = []
            
            with pytest.raises(DeviceNotFoundError) as exc_info:
                self.backend.get_device_info(0)
            
            assert "Camera device at index 0 not found" in str(exc_info.value)
    
    def test_get_device_info_creation_fails(self):
        """Test getting device info when device creation fails."""
        with patch.object(self.backend, '_get_camera_devices') as mock_get_devices:
            mock_device_info = {'_name': 'Test Camera'}
            mock_get_devices.return_value = [mock_device_info]
            
            with patch.object(self.backend, '_create_camera_device') as mock_create:
                mock_create.return_value = None
                
                with pytest.raises(DeviceNotFoundError) as exc_info:
                    self.backend.get_device_info(0)
                
                assert "Could not get info for device at index 0" in str(exc_info.value)
    
    @patch('subprocess.run')
    def test_get_devices_via_system_profiler_success(self, mock_run):
        """Test device enumeration via system_profiler."""
        # Mock system_profiler JSON output
        mock_json_output = {
            "SPUSBDataType": [
                {
                    "_name": "USB Hub",
                    "_items": [
                        {
                            "_name": "FaceTime HD Camera",
                            "vendor_id": "0x05ac",
                            "product_id": "0x8600",
                            "serial_num": "CCGB7K042WDDJRLX",
                            "location_id": "0x14100000",
                            "manufacturer": "Apple Inc."
                        }
                    ]
                }
            ]
        }
        
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(mock_json_output)
        mock_run.return_value = mock_result
        
        devices = self.backend._get_devices_via_system_profiler()
        
        assert len(devices) == 1
        assert devices[0]['_name'] == 'FaceTime HD Camera'
        assert devices[0]['vendor_id'] == '05ac'
        assert devices[0]['product_id'] == '8600'
        assert devices[0]['serial_number'] == 'CCGB7K042WDDJRLX'
    
    @patch('subprocess.run')
    def test_get_devices_via_system_profiler_failure(self, mock_run):
        """Test system_profiler failure handling."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Command failed"
        mock_run.return_value = mock_result
        
        devices = self.backend._get_devices_via_system_profiler()
        assert devices == []
    
    @patch('subprocess.run')
    def test_get_devices_via_system_profiler_invalid_json(self, mock_run):
        """Test system_profiler with invalid JSON output."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "invalid json"
        mock_run.return_value = mock_result
        
        devices = self.backend._get_devices_via_system_profiler()
        assert devices == []
    
    def test_is_camera_device_by_name(self):
        """Test camera device detection by name."""
        test_cases = [
            ({'_name': 'FaceTime HD Camera'}, True),
            ({'_name': 'Built-in iSight'}, True),
            ({'_name': 'Logitech Webcam'}, True),
            ({'_name': 'USB Video Device'}, True),
            ({'_name': 'Microsoft LifeCam'}, True),
            ({'_name': 'USB Hub'}, False),
            ({'_name': 'Keyboard'}, False),
            ({'_name': 'Mouse'}, False)
        ]
        
        for device_info, expected in test_cases:
            result = self.backend._is_camera_device(device_info)
            assert result == expected, f"Failed for device: {device_info['_name']}"
    
    def test_is_camera_device_by_manufacturer(self):
        """Test camera device detection by manufacturer."""
        device_info = {
            '_name': 'Unknown Device',
            'manufacturer': 'Video Technology Inc.'
        }
        
        result = self.backend._is_camera_device(device_info)
        assert result is True
    
    def test_parse_system_profiler_device_success(self):
        """Test parsing system_profiler device information."""
        device_info = {
            '_name': 'FaceTime HD Camera',
            'vendor_id': '0x05ac',
            'product_id': '0x8600',
            'serial_num': 'CCGB7K042WDDJRLX',
            'location_id': '0x14100000',
            'manufacturer': 'Apple Inc.',
            'bcd_device': '1.0',
            'device_speed': 'Up to 480 Mb/sec'
        }
        
        parsed = self.backend._parse_system_profiler_device(device_info, '')
        
        assert parsed is not None
        assert parsed['_name'] == 'FaceTime HD Camera'
        assert parsed['vendor_id'] == '05ac'
        assert parsed['product_id'] == '8600'
        assert parsed['serial_number'] == 'CCGB7K042WDDJRLX'
        assert parsed['device_path'] == 'USB:0x14100000'
        assert parsed['manufacturer'] == 'Apple Inc.'
    
    def test_parse_system_profiler_device_hex_conversion(self):
        """Test hex ID conversion in system_profiler parsing."""
        test_cases = [
            ('0x046d', '046d'),
            ('1133', '046d'),  # 1133 in decimal = 0x046d
            ('0x05AC', '05ac'),
            (1133, '046d'),  # 0x046d in decimal
            ('invalid', 'inva')  # Should be truncated/padded to 4 chars
        ]
        
        for input_id, expected in test_cases:
            device_info = {
                '_name': 'Test Camera',
                'vendor_id': input_id,
                'product_id': '0x085b'
            }
            
            parsed = self.backend._parse_system_profiler_device(device_info, '')
            
            if expected == 'inva':
                # Special case for invalid input - should be truncated to 4 chars
                assert len(parsed['vendor_id']) == 4
                assert parsed['vendor_id'] == 'inva'
            else:
                assert parsed['vendor_id'] == expected
    
    def test_parse_system_profiler_device_no_serial(self):
        """Test parsing device with no serial number."""
        device_info = {
            '_name': 'Test Camera',
            'vendor_id': '0x046d',
            'product_id': '0x085b',
            'serial_num': '0'  # Should be treated as None
        }
        
        parsed = self.backend._parse_system_profiler_device(device_info, '')
        
        assert parsed['serial_number'] is None
    
    @patch('subprocess.run')
    def test_get_devices_via_ioreg_success(self, mock_run):
        """Test device enumeration via ioreg."""
        # Mock ioreg output
        ioreg_output = '''
+-o USB2.0 Hub@14100000  <class IOUSBHostDevice, id 0x100000abc>
  |   "idVendor" = 1452
  |   "idProduct" = 34816
  |   "USB Serial Number" = "CCGB7K042WDDJRLX"
  |   "USB Vendor Name" = "Apple Inc."
  |   "USB Product Name" = "FaceTime HD Camera"
  |   "locationID" = 0x14100000
  |   "bInterfaceClass" = 14
+-o Keyboard@14200000  <class IOUSBHostDevice, id 0x100000def>
  |   "idVendor" = 1452
  |   "idProduct" = 123
        '''
        
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ioreg_output
        mock_run.return_value = mock_result
        
        devices = self.backend._get_devices_via_ioreg()
        
        # Should find the camera device (has bInterfaceClass = 14)
        assert len(devices) == 1
        assert devices[0]['_name'] == 'USB2.0 Hub'
        assert devices[0]['vendor_id'] == '05ac'  # 1452 in hex
        assert devices[0]['product_id'] == '8800'  # 34816 in hex
        assert devices[0]['serial_number'] == 'CCGB7K042WDDJRLX'
    
    @patch('subprocess.run')
    def test_get_devices_via_ioreg_failure(self, mock_run):
        """Test ioreg failure handling."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Command failed"
        mock_run.return_value = mock_result
        
        devices = self.backend._get_devices_via_ioreg()
        assert devices == []
    
    def test_extract_device_name_from_ioreg_line(self):
        """Test device name extraction from ioreg line."""
        test_cases = [
            ('+-o FaceTime HD Camera@14100000  <class IOUSBHostDevice>', 'FaceTime HD Camera'),
            ('  +-o USB Hub@14200000  <class IOUSBHostDevice>', 'USB Hub'),
            ('+-o Device Name With Spaces@address  <class>', 'Device Name With Spaces'),
            ('invalid line', 'Unknown Device')
        ]
        
        for line, expected in test_cases:
            result = self.backend._extract_device_name_from_ioreg_line(line)
            assert result == expected
    
    def test_is_ioreg_camera_device(self):
        """Test ioreg camera device detection."""
        test_cases = [
            ({'_name': 'FaceTime HD Camera'}, True),
            ({'_name': 'USB Hub', 'bInterfaceClass': '14'}, True),
            ({'_name': 'USB Hub', 'bInterfaceClass': '0xe'}, True),
            ({'_name': 'Keyboard'}, False),
            ({'_name': 'USB Hub', 'bInterfaceClass': '3'}, False)
        ]
        
        for device_info, expected in test_cases:
            result = self.backend._is_ioreg_camera_device(device_info)
            assert result == expected
    
    def test_parse_ioreg_device_success(self):
        """Test parsing ioreg device information."""
        device_info = {
            '_name': 'FaceTime HD Camera',
            'idVendor': '1452',
            'idProduct': '34816',
            'USB Serial Number': 'CCGB7K042WDDJRLX',
            'locationID': '0x14100000',
            'USB Vendor Name': 'Apple Inc.',
            'USB Product Name': 'FaceTime HD Camera',
            'Device Speed': 'Up to 480 Mb/sec'
        }
        
        parsed = self.backend._parse_ioreg_device(device_info)
        
        assert parsed is not None
        assert parsed['_name'] == 'FaceTime HD Camera'
        assert parsed['vendor_id'] == '05ac'  # 1452 in hex
        assert parsed['product_id'] == '8800'  # 34816 in hex
        assert parsed['serial_number'] == 'CCGB7K042WDDJRLX'
        assert parsed['device_path'] == 'IOKit:0x14100000'
        assert parsed['manufacturer'] == 'Apple Inc.'
    
    def test_parse_ioreg_device_no_serial(self):
        """Test parsing ioreg device with no serial number."""
        device_info = {
            '_name': 'Test Camera',
            'idVendor': '1452',
            'idProduct': '34816',
            'USB Serial Number': '0'  # Should be treated as None
        }
        
        parsed = self.backend._parse_ioreg_device(device_info)
        
        assert parsed['serial_number'] is None
    
    @patch('os.path.exists')
    def test_get_devices_fallback_with_avfoundation(self, mock_exists):
        """Test fallback device enumeration when AVFoundation is available."""
        mock_exists.return_value = True
        
        devices = self.backend._get_devices_fallback()
        
        assert len(devices) == 1
        assert devices[0]['_name'] == 'Built-in Camera'
        assert devices[0]['vendor_id'] == '05ac'
        assert devices[0]['built_in'] is True
    
    @patch('os.path.exists')
    def test_get_devices_fallback_no_avfoundation(self, mock_exists):
        """Test fallback device enumeration when AVFoundation is not available."""
        mock_exists.return_value = False
        
        devices = self.backend._get_devices_fallback()
        
        # Should still return empty list gracefully
        assert devices == []
    
    def test_create_camera_device_success(self):
        """Test successful camera device creation."""
        device_info = {
            '_name': 'FaceTime HD Camera',
            'vendor_id': '05ac',
            'product_id': '8600',
            'serial_number': 'CCGB7K042WDDJRLX',
            'device_path': 'USB:0x14100000',
            'location_id': '0x14100000',
            'manufacturer': 'Apple Inc.',
            'product_name': 'FaceTime HD Camera',
            'device_speed': 'Up to 480 Mb/sec',
            'built_in': True
        }
        
        camera = self.backend._create_camera_device(0, device_info)
        
        assert camera is not None
        assert camera.system_index == 0
        assert camera.vendor_id == '05ac'
        assert camera.product_id == '8600'
        assert camera.serial_number == 'CCGB7K042WDDJRLX'
        assert camera.port_path == 'USB:0x14100000'
        assert camera.label == 'FaceTime HD Camera'
        assert camera.platform_data['built_in'] is True
        assert camera.platform_data['manufacturer'] == 'Apple Inc.'
    
    def test_create_camera_device_minimal_info(self):
        """Test camera device creation with minimal information."""
        device_info = {
            '_name': 'Unknown Camera'
        }
        
        camera = self.backend._create_camera_device(0, device_info)
        
        assert camera is not None
        assert camera.system_index == 0
        assert camera.vendor_id == '0000'
        assert camera.product_id == '0000'
        assert camera.serial_number is None
        assert camera.label == 'Unknown Camera'
    
    def test_create_camera_device_failure(self):
        """Test camera device creation failure handling."""
        # Pass invalid device info that will cause an exception
        device_info = None
        
        camera = self.backend._create_camera_device(0, device_info)
        
        assert camera is None
    
    def test_get_camera_devices_system_profiler_priority(self):
        """Test that system_profiler is used when available."""
        self.backend._system_profiler_available = True
        self.backend._ioreg_available = True
        
        with patch.object(self.backend, '_get_devices_via_system_profiler') as mock_sp, \
             patch.object(self.backend, '_get_devices_via_ioreg') as mock_ioreg:
            
            mock_sp.return_value = [{'_name': 'Test Camera'}]
            
            devices = self.backend._get_camera_devices()
            
            mock_sp.assert_called_once()
            mock_ioreg.assert_not_called()
            assert len(devices) == 1
    
    def test_get_camera_devices_ioreg_fallback(self):
        """Test that ioreg is used when system_profiler fails."""
        self.backend._system_profiler_available = True
        self.backend._ioreg_available = True
        
        with patch.object(self.backend, '_get_devices_via_system_profiler') as mock_sp, \
             patch.object(self.backend, '_get_devices_via_ioreg') as mock_ioreg:
            
            mock_sp.side_effect = Exception("system_profiler failed")
            mock_ioreg.return_value = [{'_name': 'Test Camera'}]
            
            devices = self.backend._get_camera_devices()
            
            mock_sp.assert_called_once()
            mock_ioreg.assert_called_once()
            assert len(devices) == 1
    
    def test_get_camera_devices_final_fallback(self):
        """Test that fallback method is used when both tools fail."""
        self.backend._system_profiler_available = False
        self.backend._ioreg_available = False
        
        with patch.object(self.backend, '_get_devices_fallback') as mock_fallback:
            mock_fallback.return_value = [{'_name': 'Fallback Camera'}]
            
            devices = self.backend._get_camera_devices()
            
            mock_fallback.assert_called_once()
            assert len(devices) == 1
    
    def test_extract_cameras_from_usb_tree_recursive(self):
        """Test recursive camera extraction from USB device tree."""
        usb_tree = [
            {
                '_name': 'USB Hub',
                'location_id': '0x14000000',
                '_items': [
                    {
                        '_name': 'FaceTime HD Camera',
                        'vendor_id': '0x05ac',
                        'product_id': '0x8600'
                    },
                    {
                        '_name': 'Keyboard',
                        'vendor_id': '0x05ac',
                        'product_id': '0x0123'
                    }
                ]
            }
        ]
        
        cameras = []
        
        with patch.object(self.backend, '_is_camera_device') as mock_is_camera, \
             patch.object(self.backend, '_parse_system_profiler_device') as mock_parse:
            
            # Only the camera device should be detected
            def is_camera_side_effect(device):
                return 'Camera' in device.get('_name', '')
            
            mock_is_camera.side_effect = is_camera_side_effect
            mock_parse.return_value = {'_name': 'FaceTime HD Camera'}
            
            self.backend._extract_cameras_from_usb_tree(usb_tree, cameras)
            
            assert len(cameras) == 1
            assert cameras[0]['_name'] == 'FaceTime HD Camera'
            
            # Should have called is_camera_device for both devices
            assert mock_is_camera.call_count == 3  # Hub + Camera + Keyboard
    
    def test_lazy_property_evaluation(self):
        """Test that availability properties are evaluated lazily."""
        # Initially None
        assert self.backend._system_profiler_available is None
        assert self.backend._ioreg_available is None
        
        with patch.object(self.backend, '_check_system_profiler_availability') as mock_sp, \
             patch.object(self.backend, '_check_ioreg_availability') as mock_ioreg:
            
            mock_sp.return_value = True
            mock_ioreg.return_value = False
            
            # First access should call the check method
            result1 = self.backend.system_profiler_available
            assert result1 is True
            mock_sp.assert_called_once()
            
            # Second access should use cached value
            result2 = self.backend.system_profiler_available
            assert result2 is True
            mock_sp.assert_called_once()  # Still only called once
            
            # Same for ioreg
            result3 = self.backend.ioreg_available
            assert result3 is False
            mock_ioreg.assert_called_once()