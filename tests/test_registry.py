"""
Unit tests for DeviceRegistry class.

Tests cover device registration, lookup, status updates, persistence,
file locking, atomic operations, and error handling scenarios.
"""

import json
import os
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, mock_open

import pytest

from stablecam.models import CameraDevice, DeviceStatus
from stablecam.registry import DeviceRegistry, RegistryError, RegistryCorruptionError


class TestDeviceRegistry:
    """Test suite for DeviceRegistry class."""
    
    @pytest.fixture
    def temp_registry_path(self):
        """Create a temporary registry file path for testing."""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
            tmp_path = Path(tmp.name)
        tmp_path.unlink()  # Remove the file, we just want the path
        yield tmp_path
        # Cleanup
        if tmp_path.exists():
            tmp_path.unlink()
    
    @pytest.fixture
    def registry(self, temp_registry_path):
        """Create a DeviceRegistry instance with temporary storage."""
        return DeviceRegistry(temp_registry_path)
    
    @pytest.fixture
    def sample_device(self):
        """Create a sample CameraDevice for testing."""
        return CameraDevice(
            system_index=0,
            vendor_id="046d",
            product_id="085b",
            serial_number="ABC123456",
            port_path="/dev/usb1/1-1",
            label="Logitech C920 HD Pro Webcam",
            platform_data={"driver": "uvcvideo"}
        )
    
    @pytest.fixture
    def sample_device_no_serial(self):
        """Create a sample CameraDevice without serial number."""
        return CameraDevice(
            system_index=1,
            vendor_id="1234",
            product_id="5678",
            serial_number=None,
            port_path="/dev/usb1/1-2",
            label="Generic USB Camera",
            platform_data={"driver": "uvcvideo"}
        )
    
    def test_registry_initialization_creates_directory(self, temp_registry_path):
        """Test that registry initialization creates necessary directories."""
        # Create a custom path in a subdirectory that we can safely remove
        import tempfile
        import shutil
        
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_dir = Path(temp_dir) / "test_subdir"
            custom_registry_path = custom_dir / "registry.json"
            
            registry = DeviceRegistry(custom_registry_path)
            
            assert custom_dir.exists()
            assert custom_registry_path.exists()
    
    def test_registry_initialization_creates_empty_registry(self, temp_registry_path):
        """Test that new registry file is created with proper structure."""
        registry = DeviceRegistry(temp_registry_path)
        
        with open(temp_registry_path, 'r') as f:
            data = json.load(f)
        
        assert data["version"] == "1.0"
        assert data["devices"] == {}
    
    def test_register_device_success(self, registry, sample_device):
        """Test successful device registration."""
        stable_id = registry.register(sample_device)
        
        assert stable_id.startswith("stable-cam-")
        assert stable_id == "stable-cam-001"
        
        # Verify device is in registry
        registered_device = registry.get_by_id(stable_id)
        assert registered_device is not None
        assert registered_device.stable_id == stable_id
        assert registered_device.device_info.vendor_id == sample_device.vendor_id
        assert registered_device.status == DeviceStatus.CONNECTED
    
    def test_register_device_duplicate_raises_error(self, registry, sample_device):
        """Test that registering the same device twice raises an error."""
        # Register device first time
        registry.register(sample_device)
        
        # Attempt to register same device again
        with pytest.raises(RegistryError, match="Device already registered"):
            registry.register(sample_device)
    
    def test_register_multiple_devices_unique_ids(self, registry, sample_device, sample_device_no_serial):
        """Test that multiple devices get unique stable IDs."""
        id1 = registry.register(sample_device)
        id2 = registry.register(sample_device_no_serial)
        
        assert id1 != id2
        assert id1 == "stable-cam-001"
        assert id2 == "stable-cam-002"
    
    def test_get_all_devices(self, registry, sample_device, sample_device_no_serial):
        """Test retrieving all registered devices."""
        registry.register(sample_device)
        registry.register(sample_device_no_serial)
        
        all_devices = registry.get_all()
        
        assert len(all_devices) == 2
        stable_ids = {device.stable_id for device in all_devices}
        assert stable_ids == {"stable-cam-001", "stable-cam-002"}
    
    def test_get_by_id_existing_device(self, registry, sample_device):
        """Test retrieving device by stable ID."""
        stable_id = registry.register(sample_device)
        
        retrieved_device = registry.get_by_id(stable_id)
        
        assert retrieved_device is not None
        assert retrieved_device.stable_id == stable_id
        assert retrieved_device.device_info.label == sample_device.label
    
    def test_get_by_id_nonexistent_device(self, registry):
        """Test retrieving nonexistent device returns None."""
        result = registry.get_by_id("nonexistent-id")
        assert result is None
    
    def test_update_status_success(self, registry, sample_device):
        """Test successful status update."""
        stable_id = registry.register(sample_device)
        
        registry.update_status(stable_id, DeviceStatus.DISCONNECTED)
        
        updated_device = registry.get_by_id(stable_id)
        assert updated_device.status == DeviceStatus.DISCONNECTED
    
    def test_update_status_connected_updates_last_seen(self, registry, sample_device):
        """Test that updating to CONNECTED status updates last_seen timestamp."""
        stable_id = registry.register(sample_device)
        original_device = registry.get_by_id(stable_id)
        original_last_seen = original_device.last_seen
        
        # Wait a bit to ensure timestamp difference
        time.sleep(0.01)
        
        registry.update_status(stable_id, DeviceStatus.CONNECTED)
        
        updated_device = registry.get_by_id(stable_id)
        assert updated_device.last_seen > original_last_seen
    
    def test_update_status_nonexistent_device_raises_error(self, registry):
        """Test that updating nonexistent device raises error."""
        with pytest.raises(RegistryError, match="Device not found"):
            registry.update_status("nonexistent-id", DeviceStatus.DISCONNECTED)
    
    def test_find_by_hardware_id_with_serial(self, registry, sample_device):
        """Test finding device by hardware ID when serial number is available."""
        registry.register(sample_device)
        
        found_device = registry.find_by_hardware_id(sample_device)
        
        assert found_device is not None
        assert found_device.device_info.serial_number == sample_device.serial_number
    
    def test_find_by_hardware_id_without_serial(self, registry, sample_device_no_serial):
        """Test finding device by hardware ID when no serial number."""
        registry.register(sample_device_no_serial)
        
        found_device = registry.find_by_hardware_id(sample_device_no_serial)
        
        assert found_device is not None
        assert found_device.device_info.vendor_id == sample_device_no_serial.vendor_id
    
    def test_find_by_hardware_id_not_found(self, registry, sample_device):
        """Test finding nonexistent device returns None."""
        # Create different device
        different_device = CameraDevice(
            system_index=0,
            vendor_id="9999",
            product_id="9999",
            serial_number="DIFFERENT",
            port_path="/dev/usb1/1-3",
            label="Different Camera",
            platform_data={}
        )
        
        found_device = registry.find_by_hardware_id(different_device)
        assert found_device is None
    
    def test_persistence_across_instances(self, temp_registry_path, sample_device):
        """Test that registry data persists across different instances."""
        # Create first registry instance and register device
        registry1 = DeviceRegistry(temp_registry_path)
        stable_id = registry1.register(sample_device)
        
        # Create second registry instance and verify device exists
        registry2 = DeviceRegistry(temp_registry_path)
        retrieved_device = registry2.get_by_id(stable_id)
        
        assert retrieved_device is not None
        assert retrieved_device.stable_id == stable_id
        assert retrieved_device.device_info.label == sample_device.label
    
    def test_atomic_write_operations(self, registry, sample_device, sample_device_no_serial):
        """Test that write operations are atomic and don't corrupt registry."""
        # Register initial device
        registry.register(sample_device)
        
        # Test that the old atomic write method still works for status updates
        # (since register now uses direct file writing with locking)
        stable_id = registry.get_all()[0].stable_id
        
        # Simulate failure in atomic write for status updates
        with patch('tempfile.NamedTemporaryFile', side_effect=OSError("Simulated failure")):
            with pytest.raises(OSError):
                registry._write_registry_atomic({"version": "1.0", "devices": {}})
        
        # Verify registry is still intact and readable
        all_devices = registry.get_all()
        assert len(all_devices) == 1
        assert all_devices[0].device_info.label == sample_device.label
    
    def test_registry_corruption_handling(self, temp_registry_path):
        """Test handling of corrupted registry files."""
        # Create corrupted registry file
        with open(temp_registry_path, 'w') as f:
            f.write("invalid json content {")
        
        # Creating registry should handle corruption gracefully
        registry = DeviceRegistry(temp_registry_path)
        
        # The first read operation should detect corruption and raise exception
        with pytest.raises(RegistryCorruptionError):
            registry.get_all()
        
        # After corruption handling, backup file should be created
        backup_path = temp_registry_path.with_suffix('.json.backup')
        assert backup_path.exists()
        
        # New registry should be created and functional
        assert registry.get_all() == []
    
    def test_invalid_registry_structure_handling(self, temp_registry_path):
        """Test handling of registry with invalid structure."""
        # Create registry with invalid structure
        invalid_data = {"invalid": "structure"}
        with open(temp_registry_path, 'w') as f:
            json.dump(invalid_data, f)
        
        registry = DeviceRegistry(temp_registry_path)
        
        # The first read operation should detect invalid structure
        with pytest.raises(RegistryCorruptionError):
            registry.get_all()
    
    def test_concurrent_access_safety(self, registry, sample_device):
        """Test that concurrent access to registry is safe."""
        results = []
        errors = []
        
        def register_device(device_index):
            try:
                # Create slightly different devices with unique serial numbers
                device = CameraDevice(
                    system_index=device_index,
                    vendor_id="046d",
                    product_id="085b",
                    serial_number=f"UNIQUE_SERIAL_{device_index}_{threading.current_thread().ident}",
                    port_path=f"/dev/usb1/1-{device_index}",
                    label=f"Camera {device_index}",
                    platform_data={}
                )
                stable_id = registry.register(device)
                results.append(stable_id)
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads to register devices concurrently
        threads = []
        for i in range(5):
            thread = threading.Thread(target=register_device, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Print debug info if test fails
        if len(errors) > 0:
            print(f"Errors: {errors}")
        if len(results) != 5:
            print(f"Results: {results}")
        if len(set(results)) != 5:
            print(f"Unique results: {set(results)}")
        
        # Verify no errors occurred and all devices were registered
        assert len(errors) == 0
        assert len(results) == 5
        assert len(set(results)) == 5  # All IDs should be unique
        
        # Verify all devices are in registry
        all_devices = registry.get_all()
        assert len(all_devices) == 5
    
    def test_serialization_deserialization(self, registry, sample_device):
        """Test that device data is correctly serialized and deserialized."""
        stable_id = registry.register(sample_device)
        
        # Retrieve device and verify all fields are preserved
        retrieved_device = registry.get_by_id(stable_id)
        
        assert retrieved_device.stable_id == stable_id
        assert retrieved_device.device_info.vendor_id == sample_device.vendor_id
        assert retrieved_device.device_info.product_id == sample_device.product_id
        assert retrieved_device.device_info.serial_number == sample_device.serial_number
        assert retrieved_device.device_info.port_path == sample_device.port_path
        assert retrieved_device.device_info.label == sample_device.label
        assert retrieved_device.device_info.platform_data == sample_device.platform_data
        assert retrieved_device.status == DeviceStatus.CONNECTED
        assert isinstance(retrieved_device.registered_at, datetime)
        assert isinstance(retrieved_device.last_seen, datetime)
    
    def test_default_registry_location(self):
        """Test that default registry location is used when no path specified."""
        registry = DeviceRegistry()
        
        expected_path = Path.home() / ".stablecam" / "registry.json"
        assert registry.registry_path == expected_path
        assert registry.registry_path.exists()
        
        # Cleanup
        registry.registry_path.unlink()
        registry.registry_dir.rmdir()


if __name__ == "__main__":
    pytest.main([__file__])