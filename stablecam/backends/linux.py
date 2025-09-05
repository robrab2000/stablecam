"""
Linux-specific camera detection backend using v4l2 and udev.

This module will implement camera enumeration via /dev/video* devices
and extract hardware information using udev libraries.
"""

from typing import List

from ..models import CameraDevice
from .base import PlatformBackend
from .exceptions import PlatformDetectionError, DeviceNotFoundError


class LinuxBackend(PlatformBackend):
    """
    Linux backend for camera detection using v4l2 and udev.
    
    This backend enumerates cameras via /dev/video* devices and extracts
    vendor ID, product ID, serial number, and port path using udev.
    """

    @property
    def platform_name(self) -> str:
        """Get the platform name."""
        return "linux"

    def enumerate_cameras(self) -> List[CameraDevice]:
        """
        Enumerate cameras using Linux v4l2 interface.
        
        Returns:
            List[CameraDevice]: List of detected camera devices
            
        Raises:
            PlatformDetectionError: If enumeration fails
        """
        # TODO: Implement in task 4 - Linux camera detection backend
        raise NotImplementedError("Linux backend will be implemented in task 4")

    def get_device_info(self, system_index: int) -> CameraDevice:
        """
        Get device information for a specific camera index.
        
        Args:
            system_index: The system camera index
            
        Returns:
            CameraDevice: Device information
            
        Raises:
            DeviceNotFoundError: If device not found
            PlatformDetectionError: If info extraction fails
        """
        # TODO: Implement in task 4 - Linux camera detection backend
        raise NotImplementedError("Linux backend will be implemented in task 4")