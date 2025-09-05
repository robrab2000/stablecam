"""
StableCam manager class - main orchestrator for the StableCam system.

This module contains the main StableCam manager class that integrates device
detection, registry management, and event handling to provide a unified API
for camera monitoring and management.
"""

import threading
import time
import logging
from typing import List, Optional, Callable
from pathlib import Path

from .models import CameraDevice, RegisteredDevice, DeviceStatus
from .registry import DeviceRegistry, RegistryError, RegistryCorruptionError
from .backends import DeviceDetector
from .backends.exceptions import PlatformDetectionError, StableCamError, HardwareError
from .events import EventManager, EventType
from .logging_config import setup_logging

logger = logging.getLogger(__name__)


class StableCam:
    """
    Main StableCam manager class that orchestrates all system components.
    
    Integrates device detection, registry management, and event handling to
    provide a unified API for camera monitoring and management with persistent
    stable IDs.
    """
    
    def __init__(self, registry_path: Optional[Path] = None, poll_interval: float = 2.0, 
                 log_level: str = "INFO", enable_logging: bool = True):
        """
        Initialize the StableCam manager.
        
        Args:
            registry_path: Optional custom path for registry file
            poll_interval: Interval in seconds for device monitoring loop
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            enable_logging: Whether to set up logging configuration
        """
        # Set up logging if requested
        if enable_logging:
            try:
                setup_logging(log_level=log_level)
            except Exception as e:
                # Fallback to basic logging if setup fails
                logging.basicConfig(level=getattr(logging, log_level.upper(), logging.INFO))
                logger.warning(f"Failed to set up advanced logging, using basic config: {e}")
        
        # Initialize components with error handling
        try:
            self.registry = DeviceRegistry(registry_path)
            logger.debug("Registry initialized successfully")
        except RegistryCorruptionError as e:
            logger.error(f"Registry corruption detected during initialization: {e}")
            # Registry should have handled recovery, but log the issue
            self.registry = DeviceRegistry(registry_path)  # Try again after recovery
        except Exception as e:
            logger.error(f"Failed to initialize registry: {e}")
            raise StableCamError(f"Registry initialization failed: {e}", cause=e)
        
        try:
            self.detector = DeviceDetector()
            logger.debug("Device detector initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize device detector: {e}")
            raise StableCamError(f"Device detector initialization failed: {e}", cause=e)
        
        try:
            self.events = EventManager()
            logger.debug("Event manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize event manager: {e}")
            raise StableCamError(f"Event manager initialization failed: {e}", cause=e)
        
        self.poll_interval = max(0.1, poll_interval)  # Minimum 0.1 second interval
        
        # Monitoring state
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._error_count = 0
        self._max_consecutive_errors = 10
        
        # Track last known device states for change detection
        self._last_known_devices: dict[str, DeviceStatus] = {}
        
        # Cache current device info (including transient data like system_index)
        self._current_device_info: dict[str, CameraDevice] = {}
        
        logger.info(f"StableCam manager initialized with poll interval {poll_interval}s")
    
    def detect(self) -> List[CameraDevice]:
        """
        Detect all currently connected USB cameras.
        
        Returns:
            List[CameraDevice]: List of detected camera devices
            
        Raises:
            PlatformDetectionError: If camera detection fails
        """
        try:
            devices = self.detector.detect_cameras()
            logger.debug(f"Detected {len(devices)} camera devices")
            self._error_count = 0  # Reset error count on success
            return devices
        except PlatformDetectionError:
            # Re-raise platform detection errors as-is
            raise
        except PermissionError as e:
            logger.error(f"Permission denied during camera detection: {e}")
            raise PlatformDetectionError(
                f"Permission denied accessing camera devices: {e}",
                platform=self.detector.get_platform_backend().platform_name,
                cause=e
            )
        except Exception as e:
            logger.error(f"Unexpected error during camera detection: {e}")
            raise PlatformDetectionError(
                f"Unexpected error during camera detection: {e}",
                platform=self.detector.get_platform_backend().platform_name,
                cause=e
            )
    
    def register(self, device: CameraDevice) -> str:
        """
        Register a camera device and assign it a stable ID.
        
        Args:
            device: The camera device to register
            
        Returns:
            str: The assigned stable ID
            
        Raises:
            RegistryError: If device is already registered or registration fails
        """
        try:
            # Check if device is already registered
            existing_device = self.registry.find_by_hardware_id(device)
            if existing_device:
                # Update status to connected and return existing ID
                self.registry.update_status(existing_device.stable_id, DeviceStatus.CONNECTED)
                logger.info(f"Device already registered with ID: {existing_device.stable_id}")
                return existing_device.stable_id
            
            # Register new device
            stable_id = self.registry.register(device)
            logger.info(f"Registered new device with stable ID: {stable_id}")
            
            # Cache current device info
            self._current_device_info[stable_id] = device
            
            # Emit connect event
            registered_device = self.registry.get_by_id(stable_id)
            if registered_device:
                self.events.emit(EventType.ON_CONNECT.value, registered_device)
                self.events.emit(EventType.ON_STATUS_CHANGE.value, registered_device)
            
            return stable_id
            
        except Exception as e:
            logger.error(f"Device registration failed: {e}")
            raise RegistryError(f"Failed to register device: {e}")
    
    def list(self) -> List[RegisteredDevice]:
        """
        Get all registered devices with their current status.
        
        Returns:
            List[RegisteredDevice]: List of all registered devices
        """
        try:
            devices = self.registry.get_all()
            logger.debug(f"Retrieved {len(devices)} registered devices")
            return devices
        except Exception as e:
            logger.error(f"Failed to list devices: {e}")
            return []
    
    def get_by_id(self, stable_id: str) -> Optional[RegisteredDevice]:
        """
        Get a registered device by its stable ID.
        
        Args:
            stable_id: The stable ID to look up
            
        Returns:
            Optional[RegisteredDevice]: The device if found, None otherwise
        """
        try:
            device = self.registry.get_by_id(stable_id)
            if device:
                # Update with current device info if available (for transient data like system_index)
                if stable_id in self._current_device_info:
                    current_info = self._current_device_info[stable_id]
                    device.device_info.system_index = current_info.system_index
                    device.device_info.platform_data = current_info.platform_data
                
                logger.debug(f"Found device with stable ID: {stable_id}")
            else:
                logger.debug(f"No device found with stable ID: {stable_id}")
            return device
        except Exception as e:
            logger.error(f"Failed to get device by ID {stable_id}: {e}")
            return None
    
    def on(self, event_type: str, callback: Callable) -> None:
        """
        Subscribe to device events.
        
        Args:
            event_type: Type of event to subscribe to (on_connect, on_disconnect, on_status_change)
            callback: Function to call when event occurs
            
        Raises:
            ValueError: If event_type is invalid
            TypeError: If callback is not callable
        """
        try:
            self.events.subscribe(event_type, callback)
            logger.debug(f"Subscribed callback to {event_type}")
        except Exception as e:
            logger.error(f"Failed to subscribe to {event_type}: {e}")
            raise
    
    def run(self) -> None:
        """
        Start the device monitoring loop in a background thread.
        
        Continuously monitors for device connections and disconnections,
        updating registry status and emitting appropriate events.
        """
        if self._monitoring:
            logger.warning("Monitoring already running")
            return
        
        self._monitoring = True
        self._stop_event.clear()
        
        # Initialize last known devices state
        self._update_last_known_devices()
        
        # Start monitoring thread
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        
        logger.info("Started device monitoring")
    
    def stop(self) -> None:
        """
        Stop the device monitoring loop.
        """
        if not self._monitoring:
            logger.warning("Monitoring not running")
            return
        
        self._monitoring = False
        self._stop_event.set()
        
        # Wait for monitor thread to finish
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5.0)
            if self._monitor_thread.is_alive():
                logger.warning("Monitor thread did not stop gracefully")
        
        logger.info("Stopped device monitoring")
    
    def _monitor_loop(self) -> None:
        """
        Main monitoring loop that runs in background thread.
        
        Continuously detects devices and compares with registry to identify
        connections, disconnections, and status changes.
        """
        logger.debug("Device monitoring loop started")
        
        while self._monitoring and not self._stop_event.is_set():
            try:
                self._check_device_changes()
                self._error_count = 0  # Reset error count on success
                
            except PlatformDetectionError as e:
                self._error_count += 1
                logger.warning(f"Platform detection error in monitoring loop (#{self._error_count}): {e}")
                
                if self._error_count >= self._max_consecutive_errors:
                    logger.error(f"Too many consecutive errors ({self._error_count}), stopping monitoring")
                    self._monitoring = False
                    break
                
                # Exponential backoff for platform errors
                error_delay = min(30.0, self.poll_interval * (2 ** min(self._error_count, 5)))
                logger.debug(f"Waiting {error_delay}s before retry due to platform error")
                if self._stop_event.wait(timeout=error_delay):
                    break
                continue
                
            except RegistryError as e:
                self._error_count += 1
                logger.error(f"Registry error in monitoring loop (#{self._error_count}): {e}")
                
                if self._error_count >= self._max_consecutive_errors:
                    logger.error(f"Too many consecutive registry errors, stopping monitoring")
                    self._monitoring = False
                    break
                
            except Exception as e:
                self._error_count += 1
                logger.error(f"Unexpected error in monitoring loop (#{self._error_count}): {e}")
                
                if self._error_count >= self._max_consecutive_errors:
                    logger.error(f"Too many consecutive errors, stopping monitoring")
                    self._monitoring = False
                    break
            
            # Wait for next poll or stop signal
            if self._stop_event.wait(timeout=self.poll_interval):
                break
        
        if self._error_count >= self._max_consecutive_errors:
            logger.error("Monitoring stopped due to excessive errors")
        else:
            logger.debug("Device monitoring loop stopped normally")
    
    def _check_device_changes(self) -> None:
        """
        Check for device connection/disconnection changes and emit events.
        
        Raises:
            PlatformDetectionError: If device detection fails
            RegistryError: If registry operations fail
        """
        # Get currently detected devices
        detected_devices = self.detect()
        
        # Get all registered devices
        registered_devices = self.list()
        
        # Create mapping of hardware IDs to detected devices
        detected_by_hw_id = {}
        for device in detected_devices:
            try:
                hw_id = device.generate_hardware_id()
                detected_by_hw_id[hw_id] = device
            except Exception as e:
                logger.warning(f"Failed to generate hardware ID for device {device.label}: {e}")
                continue
        
        # Check each registered device for status changes
        for registered_device in registered_devices:
            try:
                hw_id = registered_device.get_hardware_id()
                stable_id = registered_device.stable_id
                current_status = registered_device.status
                
                if hw_id in detected_by_hw_id:
                    # Device is connected
                    detected_device = detected_by_hw_id[hw_id]
                    
                    # Cache current device info (including transient data like system_index)
                    self._current_device_info[stable_id] = detected_device
                    
                    # Update system index in case it changed
                    if registered_device.device_info.system_index != detected_device.system_index:
                        registered_device.device_info.system_index = detected_device.system_index
                        # Update the registry with the new device info
                        try:
                            self._update_device_info_in_registry(stable_id, detected_device)
                        except Exception as e:
                            logger.warning(f"Failed to update device info in registry for {stable_id}: {e}")
                    
                    if current_status != DeviceStatus.CONNECTED:
                        # Device just connected
                        try:
                            self.registry.update_status(stable_id, DeviceStatus.CONNECTED)
                            registered_device.status = DeviceStatus.CONNECTED
                            
                            logger.info(f"Device connected: {stable_id}")
                            self.events.emit(EventType.ON_CONNECT.value, registered_device)
                            self.events.emit(EventType.ON_STATUS_CHANGE.value, registered_device)
                            
                            # Update last known state
                            self._last_known_devices[stable_id] = DeviceStatus.CONNECTED
                        except Exception as e:
                            logger.error(f"Failed to update connection status for {stable_id}: {e}")
                            
                else:
                    # Device is not detected
                    if current_status == DeviceStatus.CONNECTED:
                        # Device just disconnected
                        try:
                            self.registry.update_status(stable_id, DeviceStatus.DISCONNECTED)
                            registered_device.status = DeviceStatus.DISCONNECTED
                            
                            logger.info(f"Device disconnected: {stable_id}")
                            self.events.emit(EventType.ON_DISCONNECT.value, registered_device)
                            self.events.emit(EventType.ON_STATUS_CHANGE.value, registered_device)
                            
                            # Update last known state
                            self._last_known_devices[stable_id] = DeviceStatus.DISCONNECTED
                        except Exception as e:
                            logger.error(f"Failed to update disconnection status for {stable_id}: {e}")
                            
            except Exception as e:
                logger.error(f"Error processing device {registered_device.stable_id}: {e}")
                continue
    
    def _update_last_known_devices(self) -> None:
        """Update the last known devices state from current registry."""
        try:
            registered_devices = self.list()
            self._last_known_devices = {
                device.stable_id: device.status 
                for device in registered_devices
            }
        except Exception as e:
            logger.error(f"Error updating last known devices: {e}")
    
    def _update_device_info_in_registry(self, stable_id: str, detected_device: CameraDevice) -> None:
        """Update device info in registry when system index or other details change."""
        try:
            registry_data = self.registry._read_registry()
            if stable_id in registry_data["devices"]:
                # Update the device info fields that might change
                device_data = registry_data["devices"][stable_id]
                device_data["platform_data"] = detected_device.platform_data
                # Note: We don't update system_index in the registry as it's transient
                # The system_index is updated in memory in the RegisteredDevice object
                self.registry._write_registry_atomic(registry_data)
        except Exception as e:
            logger.error(f"Error updating device info in registry: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure monitoring is stopped."""
        self.stop()