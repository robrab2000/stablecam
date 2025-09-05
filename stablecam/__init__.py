"""
StableCam - Cross-platform USB camera monitoring with persistent anchoring.

A Python library and terminal UI tool for managing USB cameras with stable IDs
that persist across disconnections and port changes.
"""

from .models import CameraDevice, RegisteredDevice, DeviceStatus
from .manager import StableCam
from .registry import DeviceRegistry, RegistryError, RegistryCorruptionError
from .backends import DeviceDetector, PlatformBackend

__version__ = "0.1.0"
__all__ = [
    "CameraDevice", 
    "RegisteredDevice", 
    "DeviceStatus", 
    "StableCam",
    "DeviceRegistry",
    "RegistryError",
    "RegistryCorruptionError",
    "DeviceDetector",
    "PlatformBackend"
]