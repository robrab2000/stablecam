"""
Exception classes for platform backend operations.
"""


class PlatformDetectionError(Exception):
    """Raised when platform-specific camera detection fails."""
    pass


class DeviceNotFoundError(Exception):
    """Raised when a requested device cannot be found."""
    pass


class UnsupportedPlatformError(Exception):
    """Raised when the current platform is not supported."""
    pass