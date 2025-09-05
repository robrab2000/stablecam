"""
Device registry with persistent JSON storage.

This module provides the DeviceRegistry class that manages persistent storage
and retrieval of registered camera devices with thread-safe operations.
"""

import json
import os
import fcntl
import tempfile
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from contextlib import contextmanager

from .models import CameraDevice, RegisteredDevice, DeviceStatus, generate_stable_id
from .backends.exceptions import StableCamError

logger = logging.getLogger(__name__)


class RegistryError(StableCamError):
    """Base exception for registry operations."""
    
    def __init__(self, message: str, registry_path: Optional[Path] = None, cause: Optional[Exception] = None):
        context = {'registry_path': str(registry_path)} if registry_path else {}
        super().__init__(message, cause, context)


class RegistryCorruptionError(RegistryError):
    """Raised when registry file is corrupted and cannot be recovered."""
    
    def __init__(self, message: str, registry_path: Optional[Path] = None, backup_created: bool = False, cause: Optional[Exception] = None):
        context = {
            'registry_path': str(registry_path) if registry_path else None,
            'backup_created': backup_created
        }
        super().__init__(message, cause, context)


class RegistryPermissionError(RegistryError):
    """Raised when registry operations fail due to permission issues."""
    pass


class RegistryLockError(RegistryError):
    """Raised when registry file cannot be locked for exclusive access."""
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
        
        try:
            # Ensure registry directory exists
            self.registry_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Registry directory ensured: {self.registry_dir}")
        except PermissionError as e:
            raise RegistryPermissionError(
                f"Cannot create registry directory: {self.registry_dir}",
                registry_path=self.registry_path,
                cause=e
            )
        except Exception as e:
            raise RegistryError(
                f"Failed to initialize registry directory: {self.registry_dir}",
                registry_path=self.registry_path,
                cause=e
            )
        
        # Initialize empty registry if file doesn't exist
        if not self.registry_path.exists():
            try:
                self._create_empty_registry()
                logger.info(f"Created new registry file: {self.registry_path}")
            except Exception as e:
                raise RegistryError(
                    f"Failed to create initial registry file",
                    registry_path=self.registry_path,
                    cause=e
                )
        else:
            # Validate existing registry
            try:
                self._validate_registry()
                logger.debug(f"Registry validated: {self.registry_path}")
            except RegistryCorruptionError:
                # Already handled in _validate_registry
                pass
            except Exception as e:
                logger.warning(f"Registry validation failed: {e}")
                # Try to recover or recreate
                self._handle_registry_corruption(e)
    
    def _create_empty_registry(self) -> None:
        """Create an empty registry file with proper structure."""
        empty_registry = {
            "version": self.REGISTRY_VERSION,
            "devices": {},
            "created_at": datetime.now().isoformat(),
            "last_modified": datetime.now().isoformat()
        }
        try:
            self._write_registry_atomic(empty_registry)
            logger.info("Created empty registry file")
        except Exception as e:
            raise RegistryError(
                "Failed to create empty registry file",
                registry_path=self.registry_path,
                cause=e
            )
    
    def _validate_registry(self) -> None:
        """
        Validate the registry file structure and content.
        
        Raises:
            RegistryCorruptionError: If registry is corrupted beyond repair
        """
        try:
            with open(self.registry_path, 'r') as f:
                data = json.load(f)
            
            # Check required fields
            required_fields = ["version", "devices"]
            for field in required_fields:
                if field not in data:
                    raise RegistryCorruptionError(
                        f"Registry missing required field: {field}",
                        registry_path=self.registry_path
                    )
            
            # Validate version compatibility
            if data["version"] != self.REGISTRY_VERSION:
                logger.warning(f"Registry version mismatch: {data['version']} != {self.REGISTRY_VERSION}")
                # Could implement migration logic here
            
            # Validate devices structure
            if not isinstance(data["devices"], dict):
                raise RegistryCorruptionError(
                    "Registry devices field is not a dictionary",
                    registry_path=self.registry_path
                )
            
            # Validate each device entry
            for stable_id, device_data in data["devices"].items():
                self._validate_device_entry(stable_id, device_data)
            
            logger.debug("Registry validation successful")
            
        except json.JSONDecodeError as e:
            self._handle_registry_corruption(e)
        except FileNotFoundError:
            # File doesn't exist, will be created
            pass
        except RegistryCorruptionError:
            raise
        except Exception as e:
            self._handle_registry_corruption(e)
    
    def _validate_device_entry(self, stable_id: str, device_data: dict) -> None:
        """
        Validate a single device entry in the registry.
        
        Args:
            stable_id: The stable ID of the device
            device_data: The device data dictionary
            
        Raises:
            RegistryCorruptionError: If device entry is invalid
        """
        required_fields = [
            "stable_id", "vendor_id", "product_id", "label",
            "status", "registered_at"
        ]
        
        for field in required_fields:
            if field not in device_data:
                logger.warning(f"Device {stable_id} missing field: {field}")
                # Could attempt to repair or mark as corrupted
        
        # Validate status
        try:
            DeviceStatus(device_data.get("status", "unknown"))
        except ValueError:
            logger.warning(f"Device {stable_id} has invalid status: {device_data.get('status')}")
            # Could attempt to repair by setting to DISCONNECTED
    
    def _handle_registry_corruption(self, error: Exception) -> None:
        """
        Handle registry corruption by creating backup and attempting recovery.
        
        Args:
            error: The error that indicated corruption
        """
        logger.error(f"Registry corruption detected: {error}")
        
        backup_created = False
        try:
            # Create backup of corrupted file
            if self.registry_path.exists():
                backup_path = self._create_backup()
                backup_created = True
                logger.info(f"Created backup of corrupted registry: {backup_path}")
            
            # Try to recover data from backup
            recovered_data = self._attempt_recovery()
            
            if recovered_data:
                # Write recovered data
                self._write_registry_atomic(recovered_data)
                logger.info("Successfully recovered registry from backup")
            else:
                # Create new empty registry
                self._create_empty_registry()
                logger.warning("Could not recover registry data, created new empty registry")
                
        except Exception as recovery_error:
            logger.error(f"Registry recovery failed: {recovery_error}")
            raise RegistryCorruptionError(
                f"Registry corrupted and recovery failed: {error}",
                registry_path=self.registry_path,
                backup_created=backup_created,
                cause=error
            )
    
    def _create_backup(self) -> Path:
        """
        Create a backup of the current registry file.
        
        Returns:
            Path: Path to the backup file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.registry_path.with_suffix(f'.backup_{timestamp}.json')
        
        try:
            shutil.copy2(self.registry_path, backup_path)
            return backup_path
        except Exception as e:
            logger.error(f"Failed to create registry backup: {e}")
            raise
    
    def _attempt_recovery(self) -> Optional[Dict]:
        """
        Attempt to recover registry data from backup files.
        
        Returns:
            Optional[Dict]: Recovered registry data or None if recovery failed
        """
        # Look for backup files
        backup_pattern = f"{self.registry_path.stem}.backup_*.json"
        backup_files = list(self.registry_dir.glob(backup_pattern))
        
        # Sort by modification time (newest first)
        backup_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        
        for backup_file in backup_files:
            try:
                logger.info(f"Attempting recovery from backup: {backup_file}")
                with open(backup_file, 'r') as f:
                    data = json.load(f)
                
                # Validate recovered data
                if isinstance(data, dict) and "devices" in data:
                    logger.info(f"Successfully recovered data from {backup_file}")
                    # Update metadata
                    data["last_modified"] = datetime.now().isoformat()
                    data["recovered_from"] = str(backup_file)
                    return data
                    
            except Exception as e:
                logger.warning(f"Failed to recover from {backup_file}: {e}")
                continue
        
        logger.warning("No valid backup files found for recovery")
        return None
    
    @contextmanager
    def _file_lock(self, file_handle, timeout: float = 5.0):
        """
        Context manager for file locking with timeout.
        
        Args:
            file_handle: File handle to lock
            timeout: Maximum time to wait for lock in seconds
        """
        import time
        
        start_time = time.time()
        locked = False
        
        try:
            while time.time() - start_time < timeout:
                try:
                    fcntl.flock(file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    locked = True
                    break
                except (IOError, OSError):
                    time.sleep(0.1)
            
            if not locked:
                raise RegistryLockError(
                    f"Could not acquire file lock within {timeout} seconds",
                    registry_path=self.registry_path
                )
            
            yield
            
        finally:
            if locked:
                try:
                    fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)
                except (IOError, OSError) as e:
                    logger.warning(f"Failed to release file lock: {e}")
    
    def _read_registry(self) -> Dict:
        """
        Read and parse the registry file with file locking.
        
        Returns:
            Dict: The parsed registry data
            
        Raises:
            RegistryCorruptionError: If registry file is corrupted
            RegistryError: If read operation fails
        """
        if not self.registry_path.exists():
            logger.debug("Registry file doesn't exist, creating empty registry")
            self._create_empty_registry()
            
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                with open(self.registry_path, 'r', encoding='utf-8') as f:
                    with self._file_lock(f):
                        data = json.load(f)
                        
                # Validate registry structure
                if not isinstance(data, dict) or "version" not in data or "devices" not in data:
                    logger.error("Registry has invalid structure")
                    self._handle_registry_corruption(ValueError("Invalid registry structure"))
                    # After handling corruption, try reading again
                    retry_count += 1
                    continue
                
                # Update last access time
                data["last_accessed"] = datetime.now().isoformat()
                logger.debug(f"Successfully read registry with {len(data.get('devices', {}))} devices")
                return data
                
            except json.JSONDecodeError as e:
                logger.error(f"Registry JSON decode error: {e}")
                self._handle_registry_corruption(e)
                retry_count += 1
                
            except FileNotFoundError:
                logger.debug("Registry file not found, creating new one")
                self._create_empty_registry()
                retry_count += 1
                
            except PermissionError as e:
                raise RegistryPermissionError(
                    f"Permission denied reading registry file",
                    registry_path=self.registry_path,
                    cause=e
                )
                
            except RegistryLockError:
                logger.warning(f"Could not acquire registry lock, retry {retry_count + 1}/{max_retries}")
                retry_count += 1
                if retry_count >= max_retries:
                    raise
                
            except Exception as e:
                logger.error(f"Unexpected error reading registry: {e}")
                if retry_count < max_retries - 1:
                    self._handle_registry_corruption(e)
                    retry_count += 1
                else:
                    raise RegistryError(
                        f"Failed to read registry after {max_retries} attempts",
                        registry_path=self.registry_path,
                        cause=e
                    )
        
        # If we get here, all retries failed
        raise RegistryError(
            f"Failed to read registry after {max_retries} attempts",
            registry_path=self.registry_path
        )
    
    def _write_registry_atomic(self, data: Dict) -> None:
        """
        Write registry data atomically to prevent corruption.
        
        Args:
            data: Registry data to write
            
        Raises:
            RegistryError: If write operation fails
        """
        # Update metadata
        data["last_modified"] = datetime.now().isoformat()
        data["version"] = self.REGISTRY_VERSION
        
        tmp_path = None
        try:
            # Write to temporary file first
            with tempfile.NamedTemporaryFile(
                mode='w', 
                dir=self.registry_dir, 
                delete=False,
                suffix='.tmp',
                encoding='utf-8'
            ) as tmp_file:
                json.dump(data, tmp_file, indent=2, default=str, ensure_ascii=False)
                tmp_file.flush()
                os.fsync(tmp_file.fileno())
                tmp_path = tmp_file.name
            
            # Verify the written file is valid JSON
            try:
                with open(tmp_path, 'r', encoding='utf-8') as verify_file:
                    json.load(verify_file)
            except json.JSONDecodeError as e:
                raise RegistryError(
                    f"Written registry file is invalid JSON",
                    registry_path=self.registry_path,
                    cause=e
                )
            
            # Atomic move to final location
            os.replace(tmp_path, self.registry_path)
            logger.debug(f"Successfully wrote registry with {len(data.get('devices', {}))} devices")
            
        except PermissionError as e:
            raise RegistryPermissionError(
                f"Permission denied writing registry file",
                registry_path=self.registry_path,
                cause=e
            )
        except OSError as e:
            raise RegistryError(
                f"OS error writing registry file",
                registry_path=self.registry_path,
                cause=e
            )
        except Exception as e:
            raise RegistryError(
                f"Unexpected error writing registry file",
                registry_path=self.registry_path,
                cause=e
            )
        finally:
            # Clean up temporary file if it still exists
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary file {tmp_path}: {e}")
    
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