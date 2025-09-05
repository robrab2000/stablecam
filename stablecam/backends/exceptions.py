"""
Exception classes for platform backend operations.
"""

import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)


class StableCamError(Exception):
    """Base exception class for all StableCam errors."""
    
    def __init__(self, message: str, cause: Optional[Exception] = None, context: Optional[dict] = None):
        """
        Initialize StableCam error.
        
        Args:
            message: Error message
            cause: Original exception that caused this error
            context: Additional context information
        """
        super().__init__(message)
        self.message = message
        self.cause = cause
        self.context = context or {}
        
        # Log the error with context
        logger.error(f"{self.__class__.__name__}: {message}", extra={
            'cause': str(cause) if cause else None,
            'context': self.context
        })


class PlatformDetectionError(StableCamError):
    """Raised when platform-specific camera detection fails."""
    
    def __init__(self, message: str, platform: Optional[str] = None, cause: Optional[Exception] = None):
        context = {'platform': platform} if platform else {}
        super().__init__(message, cause, context)


class DeviceNotFoundError(StableCamError):
    """Raised when a requested device cannot be found."""
    
    def __init__(self, message: str, device_id: Optional[str] = None, cause: Optional[Exception] = None):
        context = {'device_id': device_id} if device_id else {}
        super().__init__(message, cause, context)


class UnsupportedPlatformError(StableCamError):
    """Raised when the current platform is not supported."""
    
    def __init__(self, message: str, platform: Optional[str] = None):
        context = {'platform': platform} if platform else {}
        super().__init__(message, context=context)


class PermissionError(StableCamError):
    """Raised when insufficient permissions prevent device access."""
    
    def __init__(self, message: str, resource: Optional[str] = None, cause: Optional[Exception] = None):
        context = {'resource': resource} if resource else {}
        super().__init__(message, cause, context)


class HardwareError(StableCamError):
    """Raised when hardware-related operations fail."""
    
    def __init__(self, message: str, device_path: Optional[str] = None, cause: Optional[Exception] = None):
        context = {'device_path': device_path} if device_path else {}
        super().__init__(message, cause, context)


class ConfigurationError(StableCamError):
    """Raised when configuration is invalid or missing."""
    
    def __init__(self, message: str, config_key: Optional[str] = None, cause: Optional[Exception] = None):
        context = {'config_key': config_key} if config_key else {}
        super().__init__(message, cause, context)