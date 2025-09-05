"""
Device registry with persistent JSON storage.

This module provides the DeviceRegistry class that manages persistent storage
and retrieval of registered camera devices with thread-safe operations.
"""

import json
import os
import fcntl
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from contextlib import contextmanager

from .models import CameraDevice, RegisteredDevice, DeviceStatus, generate_stable_id


class RegistryError(Exception):
    """Base exception for registry operations."""
    pass


class RegistryCorruptionError(RegistryError):
    """Raised when registry file is corrupted and cannot be recovered."""
    pass


class DeviceRegistry:
    """
    Manages persistent storage and retrieval of registered camera devices.
    
    Provides thread-safe operations for device registration, lookup, and status
    updates with JSON-based persistence and atomic write operations.
    """
    
    REGISTRY_VERSION = "1.0"
    DEFAULT_REGISTRY_DIR = Path.home() / ".stablecam"
    DEFAULT_REGISTRY_FILE = "registry.json"
    
    def __init__(self, registry_path: Optional[Path] = None):
        """
        Initialize the device registry.
        
        Args:
            registry_path: Optional custom path for registry file.
                          Defaults to ~/.stablecam/registry.json
        """
        if registry_path is None:
            self.registry_dir = self.DEFAULT_REGISTRY_DIR
            self.registry_path = self.registry_dir / self.DEFAULT_REGISTRY_FILE
        else:
            self.registry_path = Path(registry_path)
            self.registry_dir = self.registry_path.parent
            
        # Ensure registry directory exists
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize empty registry if file doesn't exist
        if not self.registry_path.exists():
            self._create_empty_registry()
    
    def _create_empty_registry(self) -> None:
        """Create an empty registry file with proper structure."""
        empty_registry = {
            "version": self.REGISTRY_VERSION,
            "devices": {}
        }
        self._write_registry_atomic(empty_registry)
    
    @contextmanager
    def _file_lock(self, file_handle):
        """Context manager for file locking."""
        try:
            fcntl.flock(file_handle.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)
    
    def _read_registry(self) -> Dict:
        """
        Read and parse the registry file with file locking.
        
        Returns:
            Dict: The parsed registry data
            
        Raises:
            RegistryCorruptionError: If registry file is corrupted
        """
        if not self.registry_path.exists():
            self._create_empty_registry()
            
        try:
            with open(self.registry_path, 'r') as f:
                with self._file_lock(f):
                    data = json.load(f)
                    
            # Validate registry structure
            if not isinstance(data, dict) or "version" not in data or "devices" not in data:
                # Handle corruption by creating backup and new registry
                backup_path = self.registry_path.with_suffix('.json.backup')
                self.registry_path.rename(backup_path)
                self._create_empty_registry()
                raise RegistryCorruptionError("Invalid registry structure")
                
            return data
            
        except (json.JSONDecodeError, FileNotFoundError) as e:
            # Handle corruption by creating backup and new registry
            if self.registry_path.exists():
                backup_path = self.registry_path.with_suffix('.json.backup')
                self.registry_path.rename(backup_path)
                
            self._create_empty_registry()
            raise RegistryCorruptionError(f"Registry corrupted, created backup: {e}")
    
    def _write_registry_atomic(self, data: Dict) -> None:
        """
        Write registry data atomically to prevent corruption.
        
        Args:
            data: Registry data to write
        """
        # Write to temporary file first
        with tempfile.NamedTemporaryFile(
            mode='w', 
            dir=self.registry_dir, 
            delete=False,
            suffix='.tmp'
        ) as tmp_file:
            json.dump(data, tmp_file, indent=2, default=str)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
            tmp_path = tmp_file.name
        
        # Atomic move to final location
        os.replace(tmp_path, self.registry_path)
    
    def register(self, device: CameraDevice) -> str:
        """
        Register a new camera device and assign it a stable ID.
        
        Args:
            device: The camera device to register
            
        Returns:
            str: The assigned stable ID
            
        Raises:
            RegistryError: If device is already registered
        """
        # Use file locking for the entire registration process to ensure atomicity
        with open(self.registry_path, 'r+') as f:
            with self._file_lock(f):
                # Re-read registry with lock held
                f.seek(0)
                try:
                    registry_data = json.load(f)
                except json.JSONDecodeError:
                    registry_data = {"version": self.REGISTRY_VERSION, "devices": {}}
                
                # Check if device is already registered
                hardware_id = device.generate_hardware_id()
                for device_data in registry_data["devices"].values():
                    existing_device_info = CameraDevice(
                        system_index=0,
                        vendor_id=device_data["vendor_id"],
                        product_id=device_data["product_id"],
                        serial_number=device_data["serial_number"],
                        port_path=device_data["port_path"],
                        label=device_data["label"],
                        platform_data=device_data["platform_data"]
                    )
                    if existing_device_info.generate_hardware_id() == hardware_id:
                        raise RegistryError(f"Device already registered with ID: {device_data['stable_id']}")
                
                # Generate unique stable ID
                existing_ids = set(registry_data["devices"].keys())
                stable_id = generate_stable_id(device, existing_ids)
                
                # Create registered device entry
                registered_device = RegisteredDevice(
                    stable_id=stable_id,
                    device_info=device,
                    status=DeviceStatus.CONNECTED,
                    registered_at=datetime.now(),
                    last_seen=datetime.now()
                )
                
                # Add to registry
                registry_data["devices"][stable_id] = self._serialize_device(registered_device)
                
                # Write back to file
                f.seek(0)
                f.truncate()
                json.dump(registry_data, f, indent=2, default=str)
                f.flush()
                os.fsync(f.fileno())
        
        return stable_id
    
    def get_all(self) -> List[RegisteredDevice]:
        """
        Get all registered devices.
        
        Returns:
            List[RegisteredDevice]: List of all registered devices
        """
        registry_data = self._read_registry()
        devices = []
        
        for device_data in registry_data["devices"].values():
            devices.append(self._deserialize_device(device_data))
            
        return devices
    
    def get_by_id(self, stable_id: str) -> Optional[RegisteredDevice]:
        """
        Get a registered device by its stable ID.
        
        Args:
            stable_id: The stable ID to look up
            
        Returns:
            Optional[RegisteredDevice]: The device if found, None otherwise
        """
        registry_data = self._read_registry()
        
        if stable_id in registry_data["devices"]:
            return self._deserialize_device(registry_data["devices"][stable_id])
        
        return None
    
    def update_status(self, stable_id: str, status: DeviceStatus) -> None:
        """
        Update the status of a registered device.
        
        Args:
            stable_id: The stable ID of the device to update
            status: The new status to set
            
        Raises:
            RegistryError: If device is not found
        """
        registry_data = self._read_registry()
        
        if stable_id not in registry_data["devices"]:
            raise RegistryError(f"Device not found: {stable_id}")
        
        # Update status and last_seen if connecting
        device_data = registry_data["devices"][stable_id]
        device_data["status"] = status.value
        
        if status == DeviceStatus.CONNECTED:
            device_data["last_seen"] = datetime.now().isoformat()
        
        self._write_registry_atomic(registry_data)
    
    def find_by_hardware_id(self, device: CameraDevice) -> Optional[RegisteredDevice]:
        """
        Find a registered device by its hardware identifier.
        
        Args:
            device: The device to search for
            
        Returns:
            Optional[RegisteredDevice]: The registered device if found
        """
        hardware_id = device.generate_hardware_id()
        
        for registered_device in self.get_all():
            if registered_device.get_hardware_id() == hardware_id:
                return registered_device
                
        return None
    
    def _serialize_device(self, device: RegisteredDevice) -> Dict:
        """Convert RegisteredDevice to dictionary for JSON storage."""
        return {
            "stable_id": device.stable_id,
            "vendor_id": device.device_info.vendor_id,
            "product_id": device.device_info.product_id,
            "serial_number": device.device_info.serial_number,
            "port_path": device.device_info.port_path,
            "label": device.device_info.label,
            "platform_data": device.device_info.platform_data,
            "status": device.status.value,
            "registered_at": device.registered_at.isoformat(),
            "last_seen": device.last_seen.isoformat() if device.last_seen else None
        }
    
    def _deserialize_device(self, data: Dict) -> RegisteredDevice:
        """Convert dictionary from JSON storage to RegisteredDevice."""
        device_info = CameraDevice(
            system_index=0,  # Will be updated during detection
            vendor_id=data["vendor_id"],
            product_id=data["product_id"],
            serial_number=data["serial_number"],
            port_path=data["port_path"],
            label=data["label"],
            platform_data=data["platform_data"]
        )
        
        return RegisteredDevice(
            stable_id=data["stable_id"],
            device_info=device_info,
            status=DeviceStatus(data["status"]),
            registered_at=datetime.fromisoformat(data["registered_at"]),
            last_seen=datetime.fromisoformat(data["last_seen"]) if data["last_seen"] else None
        )