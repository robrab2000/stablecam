"""
Unit tests for StableCam data models and identifier generation.

Tests cover CameraDevice, RegisteredDevice, DeviceStatus, and hardware
identifier generation logic according to requirements 1.1, 1.2, 7.1, 7.2, 7.3.
"""

import unittest
from datetime import datetime
from unittest.mock import patch
import time

from stablecam.models import (
    CameraDevice, 
    RegisteredDevice, 
    DeviceStatus,
    generate_stable_id
)


class TestDeviceStatus(unittest.TestCase):
    """Test DeviceStatus enumeration."""
    
    def test_device_status_values(self):
        """Test that DeviceStatus has correct enumeration values."""
        self.assertEqual(DeviceStatus.CONNECTED.value, "connected")
        self.assertEqual(DeviceStatus.DISCONNECTED.value, "disconnected")
        self.assertEqual(DeviceStatus.ERROR.value, "error")


class TestCameraDevice(unittest.TestCase):
    """Test CameraDevice data class and hardware ID generation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.device_with_serial = CameraDevice(
            system_index=0,
            vendor_id="046d",
            product_id="085b",
            serial_number="ABC123456",
            port_path="/dev/usb1/1-1",
            label="Logitech C920 HD Pro Webcam",
            platform_data={"driver": "uvcvideo"}
        )
        
        self.device_without_serial = CameraDevice(
            system_index=1,
            vendor_id="046d",
            product_id="085b",
            serial_number=None,
            port_path="/dev/usb1/1-2",
            label="Logitech C920 HD Pro Webcam",
            platform_data={"driver": "uvcvideo"}
        )
        
        self.device_no_serial_no_port = CameraDevice(
            system_index=2,
            vendor_id="046d",
            product_id="085b",
            serial_number=None,
            port_path=None,
            label="Logitech C920 HD Pro Webcam",
            platform_data={"driver": "uvcvideo"}
        )

    def test_generate_hardware_id_with_serial(self):
        """Test hardware ID generation with serial number (Requirement 7.1)."""
        hardware_id = self.device_with_serial.generate_hardware_id()
        self.assertEqual(hardware_id, "serial:ABC123456")

    def test_generate_hardware_id_without_serial_with_port(self):
        """Test hardware ID generation without serial but with port (Requirement 7.2)."""
        hardware_id = self.device_without_serial.generate_hardware_id()
        expected = "vid-pid-port:046d:085b:/dev/usb1/1-2"
        self.assertEqual(hardware_id, expected)

    def test_generate_hardware_id_fallback(self):
        """Test hardware ID generation fallback method (Requirement 7.3)."""
        with patch('time.time', return_value=1234567890.123):
            hardware_id = self.device_no_serial_no_port.generate_hardware_id()
            # Should start with vid-pid-hash prefix
            self.assertTrue(hardware_id.startswith("vid-pid-hash:046d:085b:"))
            # Should contain a hash component
            parts = hardware_id.split(":")
            self.assertEqual(len(parts), 4)
            self.assertEqual(len(parts[3]), 8)  # MD5 hash truncated to 8 chars

    def test_matches_hardware_id(self):
        """Test hardware ID matching functionality."""
        hardware_id = self.device_with_serial.generate_hardware_id()
        self.assertTrue(self.device_with_serial.matches_hardware_id(hardware_id))
        self.assertFalse(self.device_with_serial.matches_hardware_id("serial:DIFFERENT"))

    def test_hardware_id_consistency(self):
        """Test that hardware ID generation is consistent for same device."""
        id1 = self.device_with_serial.generate_hardware_id()
        id2 = self.device_with_serial.generate_hardware_id()
        self.assertEqual(id1, id2)

    def test_hardware_id_uniqueness_with_serial(self):
        """Test that devices with different serials have different IDs."""
        device2 = CameraDevice(
            system_index=0,
            vendor_id="046d",
            product_id="085b",
            serial_number="XYZ789012",
            port_path="/dev/usb1/1-1",
            label="Logitech C920 HD Pro Webcam",
            platform_data={"driver": "uvcvideo"}
        )
        
        id1 = self.device_with_serial.generate_hardware_id()
        id2 = device2.generate_hardware_id()
        self.assertNotEqual(id1, id2)

    def test_hardware_id_uniqueness_with_port(self):
        """Test that devices on different ports have different IDs."""
        device2 = CameraDevice(
            system_index=1,
            vendor_id="046d",
            product_id="085b",
            serial_number=None,
            port_path="/dev/usb1/1-3",  # Different port
            label="Logitech C920 HD Pro Webcam",
            platform_data={"driver": "uvcvideo"}
        )
        
        id1 = self.device_without_serial.generate_hardware_id()
        id2 = device2.generate_hardware_id()
        self.assertNotEqual(id1, id2)


class TestRegisteredDevice(unittest.TestCase):
    """Test RegisteredDevice data class and methods."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.camera_device = CameraDevice(
            system_index=0,
            vendor_id="046d",
            product_id="085b",
            serial_number="ABC123456",
            port_path="/dev/usb1/1-1",
            label="Logitech C920 HD Pro Webcam",
            platform_data={"driver": "uvcvideo"}
        )
        
        self.registered_device = RegisteredDevice(
            stable_id="stable-cam-001",
            device_info=self.camera_device,
            status=DeviceStatus.CONNECTED,
            registered_at=datetime(2024, 1, 15, 10, 30, 0),
            last_seen=datetime(2024, 1, 15, 14, 22, 0)
        )

    def test_update_status_connected(self):
        """Test updating device status to connected updates last_seen."""
        old_last_seen = self.registered_device.last_seen
        
        # Mock datetime.now() to control the timestamp
        with patch('stablecam.models.datetime') as mock_datetime:
            mock_now = datetime(2024, 1, 15, 15, 0, 0)
            mock_datetime.now.return_value = mock_now
            
            self.registered_device.update_status(DeviceStatus.CONNECTED)
            
            self.assertEqual(self.registered_device.status, DeviceStatus.CONNECTED)
            self.assertEqual(self.registered_device.last_seen, mock_now)
            self.assertNotEqual(self.registered_device.last_seen, old_last_seen)

    def test_update_status_disconnected(self):
        """Test updating device status to disconnected doesn't update last_seen."""
        old_last_seen = self.registered_device.last_seen
        
        self.registered_device.update_status(DeviceStatus.DISCONNECTED)
        
        self.assertEqual(self.registered_device.status, DeviceStatus.DISCONNECTED)
        self.assertEqual(self.registered_device.last_seen, old_last_seen)

    def test_is_connected(self):
        """Test is_connected method."""
        self.assertTrue(self.registered_device.is_connected())
        
        self.registered_device.status = DeviceStatus.DISCONNECTED
        self.assertFalse(self.registered_device.is_connected())
        
        self.registered_device.status = DeviceStatus.ERROR
        self.assertFalse(self.registered_device.is_connected())

    def test_get_hardware_id(self):
        """Test get_hardware_id delegates to device_info."""
        expected_id = self.camera_device.generate_hardware_id()
        actual_id = self.registered_device.get_hardware_id()
        self.assertEqual(actual_id, expected_id)


class TestStableIdGeneration(unittest.TestCase):
    """Test stable ID generation functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.device = CameraDevice(
            system_index=0,
            vendor_id="046d",
            product_id="085b",
            serial_number="ABC123456",
            port_path="/dev/usb1/1-1",
            label="Logitech C920 HD Pro Webcam",
            platform_data={"driver": "uvcvideo"}
        )

    def test_generate_stable_id_first_device(self):
        """Test generating stable ID for first device (Requirement 1.2)."""
        existing_ids = set()
        stable_id = generate_stable_id(self.device, existing_ids)
        self.assertEqual(stable_id, "stable-cam-001")

    def test_generate_stable_id_sequential(self):
        """Test generating sequential stable IDs."""
        existing_ids = {"stable-cam-001", "stable-cam-002"}
        stable_id = generate_stable_id(self.device, existing_ids)
        self.assertEqual(stable_id, "stable-cam-003")

    def test_generate_stable_id_gaps(self):
        """Test generating stable ID fills gaps in sequence."""
        existing_ids = {"stable-cam-001", "stable-cam-003", "stable-cam-005"}
        stable_id = generate_stable_id(self.device, existing_ids)
        self.assertEqual(stable_id, "stable-cam-002")

    def test_generate_stable_id_format(self):
        """Test stable ID format is correct."""
        existing_ids = set()
        stable_id = generate_stable_id(self.device, existing_ids)
        
        # Should match pattern stable-cam-XXX where XXX is zero-padded number
        self.assertTrue(stable_id.startswith("stable-cam-"))
        number_part = stable_id.split("-")[-1]
        self.assertEqual(len(number_part), 3)
        self.assertTrue(number_part.isdigit())

    def test_generate_stable_id_uniqueness(self):
        """Test that generated stable IDs are unique."""
        existing_ids = set()
        
        # Generate multiple IDs
        id1 = generate_stable_id(self.device, existing_ids)
        existing_ids.add(id1)
        
        id2 = generate_stable_id(self.device, existing_ids)
        existing_ids.add(id2)
        
        id3 = generate_stable_id(self.device, existing_ids)
        
        # All should be different
        self.assertNotEqual(id1, id2)
        self.assertNotEqual(id2, id3)
        self.assertNotEqual(id1, id3)


if __name__ == '__main__':
    unittest.main()