"""
macOS-specific camera detection backend using AVFoundation and IOKit.

This module will implement camera enumeration using AVFoundation framework
and extract hardware information using IOKit for USB device properties.
"""

from typing import List

from ..models import CameraDevice
from .base import PlatformBackend
from .exceptions import PlatformDetectionError, DeviceNotFoundError


class MacOSBackend(PlatformBackend):
    """
    macOS backend for camera detection using AVFoundation and IOKit.
    
    This backend enumerates cameras using AVFoundation and extracts
    vendor ID, product ID, serial number, and device paths using IOKit.
    """

    @property
    def platform_name(self) -> str:
        """Get the platform name."""
        return "macos"

    def enumerate_cameras(self) -> List[CameraDevice]:
        """
        Enumerate cameras using AVFoundation framework.
        
        Returns:
            List[CameraDevice]: List of detected camera devices
            
        Raises:
            PlatformDetectionError: If enumeration fails
        """
        # TODO: Implement in task 6 - macOS camera detection backend
        raise NotImplementedError("macOS backend will be implemented in task 6")

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
        # TODO: Implement in task 6 - macOS camera detection backend
        raise NotImplementedError("macOS backend will be implemented in task 6")