"""
Tests for StableCam CLI interface.

This module contains unit tests for the CLI commands including register
and list commands, testing both success and error scenarios.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner
from datetime import datetime

from stablecam.cli import cli, register, list as list_cmd
from stablecam.models import CameraDevice, RegisteredDevice, DeviceStatus
from stablecam.backends import PlatformDetectionError
from stablecam.registry import RegistryError


class TestCLI:
    """Test cases for CLI functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        
        # Create mock camera device
        self.mock_device = CameraDevice(
            system_index=0,
            vendor_id="046d",
            product_id="085b",
            serial_number="ABC123456",
            port_path="/dev/usb1/1-1",
            label="Logitech C920 HD Pro Webcam",
            platform_data={}
        )
        
        # Create mock registered device
        self.mock_registered_device = RegisteredDevice(
            stable_id="stable-cam-001",
            device_info=self.mock_device,
            status=DeviceStatus.CONNECTED,
            registered_at=datetime(2024, 1, 15, 10, 30, 0),
            last_seen=datetime(2024, 1, 15, 14, 22, 0)
        )
    
    def test_cli_version(self):
        """Test CLI version command."""
        result = self.runner.invoke(cli, ['--version'])
        assert result.exit_code == 0
        assert "0.1.0" in result.output
    
    def test_cli_help(self):
        """Test CLI help command."""
        result = self.runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert "StableCam" in result.output
        assert "register" in result.output
        assert "list" in result.output


class TestRegisterCommand:
    """Test cases for the register command."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        
        # Create mock camera device
        self.mock_device = CameraDevice(
            system_index=0,
            vendor_id="046d",
            product_id="085b",
            serial_number="ABC123456",
            port_path="/dev/usb1/1-1",
            label="Logitech C920 HD Pro Webcam",
            platform_data={}
        )
    
    @patch('stablecam.cli.StableCam')
    def test_register_success(self, mock_stablecam_class):
        """Test successful camera registration."""
        # Setup mock
        mock_manager = Mock()
        mock_stablecam_class.return_value = mock_manager
        mock_manager.detect.return_value = [self.mock_device]
        mock_manager.register.return_value = "stable-cam-001"
        
        # Run command
        result = self.runner.invoke(register)
        
        # Verify results
        assert result.exit_code == 0
        assert "Detecting USB cameras..." in result.output
        assert "Found camera: Logitech C920 HD Pro Webcam" in result.output
        assert "Camera registered with stable ID: stable-cam-001" in result.output
        assert "Device details:" in result.output
        assert "Stable ID: stable-cam-001" in result.output
        assert "Label: Logitech C920 HD Pro Webcam" in result.output
        assert "System Index: 0" in result.output
        assert "Vendor ID: 046d" in result.output
        assert "Product ID: 085b" in result.output
        assert "Serial Number: ABC123456" in result.output
        assert "Port Path: /dev/usb1/1-1" in result.output
        
        # Verify method calls
        mock_manager.detect.assert_called_once()
        mock_manager.register.assert_called_once_with(self.mock_device)
    
    @patch('stablecam.cli.StableCam')
    def test_register_with_custom_registry_path(self, mock_stablecam_class):
        """Test registration with custom registry path."""
        # Setup mock
        mock_manager = Mock()
        mock_stablecam_class.return_value = mock_manager
        mock_manager.detect.return_value = [self.mock_device]
        mock_manager.register.return_value = "stable-cam-001"
        
        # Run command with custom registry path
        result = self.runner.invoke(register, ['--registry-path', '/custom/path/registry.json'])
        
        # Verify results
        assert result.exit_code == 0
        assert "Camera registered with stable ID: stable-cam-001" in result.output
        
        # Verify StableCam was initialized with custom path
        mock_stablecam_class.assert_called_once_with(registry_path='/custom/path/registry.json')
    
    @patch('stablecam.cli.StableCam')
    def test_register_no_cameras_detected(self, mock_stablecam_class):
        """Test registration when no cameras are detected."""
        # Setup mock
        mock_manager = Mock()
        mock_stablecam_class.return_value = mock_manager
        mock_manager.detect.return_value = []
        
        # Run command
        result = self.runner.invoke(register)
        
        # Verify results
        assert result.exit_code == 1
        assert "Detecting USB cameras..." in result.output
        assert "No USB cameras detected." in result.output
        
        # Verify register was not called
        mock_manager.register.assert_not_called()
    
    @patch('stablecam.cli.StableCam')
    def test_register_detection_error(self, mock_stablecam_class):
        """Test registration when camera detection fails."""
        # Setup mock
        mock_manager = Mock()
        mock_stablecam_class.return_value = mock_manager
        mock_manager.detect.side_effect = PlatformDetectionError("Detection failed")
        
        # Run command
        result = self.runner.invoke(register)
        
        # Verify results
        assert result.exit_code == 1
        assert "Camera detection failed: Detection failed" in result.output
    
    @patch('stablecam.cli.StableCam')
    def test_register_registry_error(self, mock_stablecam_class):
        """Test registration when registry operation fails."""
        # Setup mock
        mock_manager = Mock()
        mock_stablecam_class.return_value = mock_manager
        mock_manager.detect.return_value = [self.mock_device]
        mock_manager.register.side_effect = RegistryError("Registry error")
        
        # Run command
        result = self.runner.invoke(register)
        
        # Verify results
        assert result.exit_code == 1
        assert "Found camera: Logitech C920 HD Pro Webcam" in result.output
        assert "Registration failed: Registry error" in result.output
    
    @patch('stablecam.cli.StableCam')
    def test_register_device_without_serial_and_port(self, mock_stablecam_class):
        """Test registration of device without serial number and port path."""
        # Create device without serial and port
        device_no_serial = CameraDevice(
            system_index=1,
            vendor_id="1234",
            product_id="5678",
            serial_number=None,
            port_path=None,
            label="Generic USB Camera",
            platform_data={}
        )
        
        # Setup mock
        mock_manager = Mock()
        mock_stablecam_class.return_value = mock_manager
        mock_manager.detect.return_value = [device_no_serial]
        mock_manager.register.return_value = "stable-cam-002"
        
        # Run command
        result = self.runner.invoke(register)
        
        # Verify results
        assert result.exit_code == 0
        assert "Camera registered with stable ID: stable-cam-002" in result.output
        assert "Label: Generic USB Camera" in result.output
        assert "Vendor ID: 1234" in result.output
        assert "Product ID: 5678" in result.output
        # Serial and port should not appear in output
        assert "Serial Number:" not in result.output
        assert "Port Path:" not in result.output


class TestListCommand:
    """Test cases for the list command."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        
        # Create mock devices
        self.mock_device1 = CameraDevice(
            system_index=0,
            vendor_id="046d",
            product_id="085b",
            serial_number="ABC123456",
            port_path="/dev/usb1/1-1",
            label="Logitech C920 HD Pro Webcam",
            platform_data={}
        )
        
        self.mock_device2 = CameraDevice(
            system_index=None,  # Disconnected device
            vendor_id="1234",
            product_id="5678",
            serial_number="XYZ789012",
            port_path="/dev/usb1/1-2",
            label="Generic USB Camera",
            platform_data={}
        )
        
        # Create mock registered devices
        self.mock_registered_device1 = RegisteredDevice(
            stable_id="stable-cam-001",
            device_info=self.mock_device1,
            status=DeviceStatus.CONNECTED,
            registered_at=datetime(2024, 1, 15, 10, 30, 0),
            last_seen=datetime(2024, 1, 15, 14, 22, 0)
        )
        
        self.mock_registered_device2 = RegisteredDevice(
            stable_id="stable-cam-002",
            device_info=self.mock_device2,
            status=DeviceStatus.DISCONNECTED,
            registered_at=datetime(2024, 1, 14, 9, 15, 0),
            last_seen=datetime(2024, 1, 14, 18, 45, 0)
        )
    
    @patch('stablecam.cli.StableCam')
    def test_list_success_table_format(self, mock_stablecam_class):
        """Test successful device listing in table format."""
        # Setup mock
        mock_manager = Mock()
        mock_stablecam_class.return_value = mock_manager
        mock_manager.list.return_value = [self.mock_registered_device1, self.mock_registered_device2]
        
        # Run command
        result = self.runner.invoke(list_cmd)
        
        # Verify results
        assert result.exit_code == 0
        assert "Found 2 registered device(s):" in result.output
        assert "Stable ID" in result.output
        assert "Status" in result.output
        assert "System Index" in result.output
        assert "Label" in result.output
        assert "stable-cam-001" in result.output
        assert "stable-cam-002" in result.output
        assert "● connected" in result.output
        assert "○ disconnected" in result.output
        assert "Logitech C920 HD Pro Webcam" in result.output
        assert "Generic USB Camera" in result.output
        assert "0" in result.output  # System index for connected device
        assert "N/A" in result.output  # System index for disconnected device
        
        # Verify method calls
        mock_manager.list.assert_called_once()
    
    @patch('stablecam.cli.StableCam')
    def test_list_success_json_format(self, mock_stablecam_class):
        """Test successful device listing in JSON format."""
        # Setup mock
        mock_manager = Mock()
        mock_stablecam_class.return_value = mock_manager
        mock_manager.list.return_value = [self.mock_registered_device1]
        
        # Run command
        result = self.runner.invoke(list_cmd, ['--format', 'json'])
        
        # Verify results
        assert result.exit_code == 0
        
        # Parse JSON output
        output_data = json.loads(result.output)
        assert len(output_data) == 1
        
        device_data = output_data[0]
        assert device_data['stable_id'] == 'stable-cam-001'
        assert device_data['label'] == 'Logitech C920 HD Pro Webcam'
        assert device_data['status'] == 'connected'
        assert device_data['system_index'] == 0
        assert device_data['vendor_id'] == '046d'
        assert device_data['product_id'] == '085b'
        assert device_data['serial_number'] == 'ABC123456'
        assert device_data['port_path'] == '/dev/usb1/1-1'
        assert device_data['registered_at'] == '2024-01-15T10:30:00'
        assert device_data['last_seen'] == '2024-01-15T14:22:00'
    
    @patch('stablecam.cli.StableCam')
    def test_list_with_custom_registry_path(self, mock_stablecam_class):
        """Test listing with custom registry path."""
        # Setup mock
        mock_manager = Mock()
        mock_stablecam_class.return_value = mock_manager
        mock_manager.list.return_value = [self.mock_registered_device1]
        
        # Run command with custom registry path
        result = self.runner.invoke(list_cmd, ['--registry-path', '/custom/path/registry.json'])
        
        # Verify results
        assert result.exit_code == 0
        assert "stable-cam-001" in result.output
        
        # Verify StableCam was initialized with custom path
        mock_stablecam_class.assert_called_once_with(registry_path='/custom/path/registry.json')
    
    @patch('stablecam.cli.StableCam')
    def test_list_no_devices(self, mock_stablecam_class):
        """Test listing when no devices are registered."""
        # Setup mock
        mock_manager = Mock()
        mock_stablecam_class.return_value = mock_manager
        mock_manager.list.return_value = []
        
        # Run command
        result = self.runner.invoke(list_cmd)
        
        # Verify results
        assert result.exit_code == 0
        assert "No registered devices found." in result.output
        
        # Verify method calls
        mock_manager.list.assert_called_once()
    
    @patch('stablecam.cli.StableCam')
    def test_list_error(self, mock_stablecam_class):
        """Test listing when an error occurs."""
        # Setup mock
        mock_manager = Mock()
        mock_stablecam_class.return_value = mock_manager
        mock_manager.list.side_effect = Exception("Database error")
        
        # Run command
        result = self.runner.invoke(list_cmd)
        
        # Verify results
        assert result.exit_code == 1
        assert "Error listing devices: Database error" in result.output
    
    @patch('stablecam.cli.StableCam')
    def test_list_json_format_with_none_values(self, mock_stablecam_class):
        """Test JSON format with None values for timestamps and optional fields."""
        # Create device with None values
        device_with_nones = RegisteredDevice(
            stable_id="stable-cam-003",
            device_info=CameraDevice(
                system_index=2,
                vendor_id="abcd",
                product_id="efgh",
                serial_number=None,
                port_path=None,
                label="Camera Without Serial",
                platform_data={}
            ),
            status=DeviceStatus.CONNECTED,
            registered_at=None,
            last_seen=None
        )
        
        # Setup mock
        mock_manager = Mock()
        mock_stablecam_class.return_value = mock_manager
        mock_manager.list.return_value = [device_with_nones]
        
        # Run command
        result = self.runner.invoke(list_cmd, ['--format', 'json'])
        
        # Verify results
        assert result.exit_code == 0
        
        # Parse JSON output
        output_data = json.loads(result.output)
        device_data = output_data[0]
        
        assert device_data['stable_id'] == 'stable-cam-003'
        assert device_data['serial_number'] is None
        assert device_data['port_path'] is None
        assert device_data['registered_at'] is None
        assert device_data['last_seen'] is None


class TestCLIIntegration:
    """Integration tests for CLI commands."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def test_register_help(self):
        """Test register command help."""
        result = self.runner.invoke(register, ['--help'])
        assert result.exit_code == 0
        assert "Register the first detected camera" in result.output
        assert "--registry-path" in result.output
    
    def test_list_help(self):
        """Test list command help."""
        result = self.runner.invoke(list_cmd, ['--help'])
        assert result.exit_code == 0
        assert "List all registered devices" in result.output
        assert "--registry-path" in result.output
        assert "--format" in result.output
        assert "table" in result.output
        assert "json" in result.output