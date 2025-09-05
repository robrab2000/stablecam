"""
Core data models for StableCam.

This module defines the primary data structures used throughout the StableCam
system for representing camera devices, registered devices, and device status.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
import hashlib
import time


class DeviceStatus(Enum):
    """Enumeration of possible device connection states."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


@dataclass
class CameraDevice:
    """
    Represents a detected USB camera with hardware identifiers.
    
    This class contains all the information needed to uniquely identify
    a camera device across different connection states and ports.
    """
    system_index: int
    vendor_id: str
    product_id: str
    serial_number: Optional[str]
    port_path: Optional[str]
    label: str
    platform_data: Dict[str, Any]

    def generate_hardware_id(self) -> str:
        """
        Generate a unique hardware identifier for this device.
        
        Uses a hierarchical approach:
        1. Primary: Serial number (if available)
        2. Secondary: Vendor ID + Product ID + Port Path
        3. Fallback: Vendor ID + Product ID + Hash of detection timestamp
        
        Returns:
            str: A unique hardware identifier for the device
        """
        # Primary: Use serial number if available
        if self.serial_number:
            return f"serial:{self.serial_number}"
        
        # Secondary: Use vendor/product ID with port path
        if self.port_path:
            return f"vid-pid-port:{self.vendor_id}:{self.product_id}:{self.port_path}"
        
        # Fallback: Use vendor/product ID with timestamp hash
        # This ensures uniqueness even for identical devices without serial numbers
        timestamp_hash = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
        return f"vid-pid-hash:{self.vendor_id}:{self.product_id}:{timestamp_hash}"

    def matches_hardware_id(self, hardware_id: str) -> bool:
        """
        Check if this device matches the given hardware identifier.
        
        Args:
            hardware_id: The hardware ID to match against
            
        Returns:
            bool: True if this device matches the hardware ID
        """
        return self.generate_hardware_id() == hardware_id


@dataclass
class RegisteredDevice:
    """
    Represents a camera in the persistent registry with stable ID.
    
    This class extends CameraDevice information with registry-specific
    metadata like stable ID, registration timestamp, and current status.
    """
    stable_id: str
    device_info: CameraDevice
    status: DeviceStatus
    registered_at: datetime
    last_seen: Optional[datetime]

    def update_status(self, new_status: DeviceStatus) -> None:
        """
        Update the device status and last seen timestamp.
        
        Args:
            new_status: The new status to set for the device
        """
        self.status = new_status
        if new_status == DeviceStatus.CONNECTED:
            self.last_seen = datetime.now()

    def is_connected(self) -> bool:
        """Check if the device is currently connected."""
        return self.status == DeviceStatus.CONNECTED

    def get_hardware_id(self) -> str:
        """Get the hardware identifier for this registered device."""
        return self.device_info.generate_hardware_id()


def generate_stable_id(device: CameraDevice, existing_ids: set) -> str:
    """
    Generate a unique stable ID for a camera device.
    
    Creates human-readable stable IDs in the format 'stable-cam-XXX'
    where XXX is a zero-padded sequential number.
    
    Args:
        device: The camera device to generate an ID for
        existing_ids: Set of already used stable IDs
        
    Returns:
        str: A unique stable ID for the device
    """
    counter = 1
    while True:
        stable_id = f"stable-cam-{counter:03d}"
        if stable_id not in existing_ids:
            return stable_id
        counter += 1