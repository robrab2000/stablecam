"""
Base classes and interfaces for platform-specific camera detection backends.
"""

import platform
from abc import ABC, abstractmethod
from typing import List

from ..models import CameraDevice
from .exceptions import UnsupportedPlatformError


class PlatformBackend(ABC):
    """
    Abstract base class for platform-specific camera detection backends.
    
    Each platform (Linux, Windows, macOS) implements this interface to provide
    camera enumeration using OS-specific APIs while maintaining a common interface.
    """

    @abstractmethod
    def enumerate_cameras(self) -> List[CameraDevice]:
        """
        Enumerate all available USB cameras on the current platform.
        
        Returns:
            List[CameraDevice]: List of detected camera devices with hardware info
            
        Raises:
            PlatformDetectionError: If camera detection fails due to platform issues
        """
        pass

    @abstractmethod
    def get_device_info(self, system_index: int) -> CameraDevice:
        """
        Get detailed information for a specific camera device.
        
        Args:
            system_index: The system-assigned index for the camera device
            
        Returns:
            CameraDevice: Detailed device information including hardware identifiers
            
        Raises:
            DeviceNotFoundError: If the device at the given index doesn't exist
            PlatformDetectionError: If device info extraction fails
        """
        pass

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Get the name of the platform this backend supports."""
        pass


class DeviceDetector:
    """
    Manages platform-specific backends and provides unified camera detection.
    
    This class automatically selects the appropriate backend based on the current
    platform and provides a consistent interface for camera detection across
    different operating systems.
    """

    def __init__(self):
        """Initialize the detector with the appropriate platform backend."""
        self._backend = self._get_platform_backend()

    def detect_cameras(self) -> List[CameraDevice]:
        """
        Detect all available USB cameras using the current platform backend.
        
        Returns:
            List[CameraDevice]: List of detected camera devices
            
        Raises:
            PlatformDetectionError: If camera detection fails
        """
        return self._backend.enumerate_cameras()

    def get_platform_backend(self) -> PlatformBackend:
        """
        Get the current platform backend instance.
        
        Returns:
            PlatformBackend: The active backend for the current platform
        """
        return self._backend

    def _get_platform_backend(self) -> PlatformBackend:
        """
        Select and instantiate the appropriate backend for the current platform.
        
        Returns:
            PlatformBackend: Platform-specific backend instance
            
        Raises:
            UnsupportedPlatformError: If the current platform is not supported
        """
        system = platform.system().lower()
        
        if system == "linux":
            from .linux import LinuxBackend
            return LinuxBackend()
        elif system == "windows":
            from .windows import WindowsBackend
            return WindowsBackend()
        elif system == "darwin":
            from .macos import MacOSBackend
            return MacOSBackend()
        else:
            raise UnsupportedPlatformError(f"Unsupported platform: {system}", platform=system)