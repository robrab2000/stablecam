"""
Platform-specific backend implementations for camera detection.

This package contains backend implementations for different operating systems:
- Linux: Uses v4l2 and udev for camera enumeration
- Windows: Uses Windows Media Foundation APIs
- macOS: Uses AVFoundation and IOKit
"""

from .base import PlatformBackend, DeviceDetector
from .exceptions import PlatformDetectionError, DeviceNotFoundError, UnsupportedPlatformError
from .linux import LinuxBackend
from .windows import WindowsBackend
from .macos import MacOSBackend

__all__ = [
    "PlatformBackend",
    "DeviceDetector", 
    "PlatformDetectionError",
    "DeviceNotFoundError",
    "UnsupportedPlatformError",
    "LinuxBackend",
    "WindowsBackend", 
    "MacOSBackend"
]