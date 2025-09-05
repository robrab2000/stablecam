# StableCam API Documentation

Complete API reference for the StableCam library.

## Table of Contents

- [Core Classes](#core-classes)
  - [StableCam](#stablecam)
  - [CameraDevice](#cameradevice)
  - [RegisteredDevice](#registereddevice)
  - [DeviceStatus](#devicestatus)
- [Registry Management](#registry-management)
  - [DeviceRegistry](#deviceregistry)
- [Event System](#event-system)
  - [EventManager](#eventmanager)
  - [EventType](#eventtype)
- [Platform Backends](#platform-backends)
  - [DeviceDetector](#devicedetector)
  - [PlatformBackend](#platformbackend)
- [Exceptions](#exceptions)
- [Usage Patterns](#usage-patterns)

## Core Classes

### StableCam

The main class for camera management and monitoring.

```python
class StableCam:
    def __init__(
        self, 
        registry_path: Optional[Path] = None,
        poll_interval: float = 2.0,
        log_level: str = "INFO",
        enable_logging: bool = True
    )
```

#### Constructor Parameters

- **registry_path** (`Path`, optional): Custom path for registry file. Defaults to `~/.stablecam/registry.json`
- **poll_interval** (`float`): Interval in seconds for device monitoring loop. Default: 2.0, minimum: 0.1
- **log_level** (`str`): Logging level. Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **enable_logging** (`bool`): Whether to set up logging configuration

#### Methods

##### `detect() -> List[CameraDevice]`

Detect all currently connected USB cameras.

```python
cam = StableCam()
devices = cam.detect()

for device in devices:
    print(f"Found: {device.label} (Index: {device.system_index})")
```

**Returns:** List of `CameraDevice` objects representing detected cameras

**Raises:**
- `PlatformDetectionError`: If camera detection fails due to platform issues
- `PermissionError`: If insufficient permissions to access camera devices

##### `register(device: CameraDevice) -> str`

Register a camera device and assign it a stable ID.

```python
devices = cam.detect()
if devices:
    stable_id = cam.register(devices[0])
    print(f"Registered with ID: {stable_id}")
```

**Parameters:**
- **device** (`CameraDevice`): The camera device to register

**Returns:** The assigned stable ID (string)

**Raises:**
- `RegistryError`: If device registration fails
- `ValueError`: If device is invalid

**Note:** If the device is already registered, returns the existing stable ID and updates status to CONNECTED.

##### `list() -> List[RegisteredDevice]`

Get all registered devices with their current status.

```python
registered = cam.list()
for device in registered:
    status = "🟢" if device.is_connected() else "🔴"
    print(f"{status} {device.stable_id}: {device.device_info.label}")
```

**Returns:** List of `RegisteredDevice` objects

##### `get_by_id(stable_id: str) -> Optional[RegisteredDevice]`

Get a registered device by its stable ID.

```python
device = cam.get_by_id("stable-cam-001")
if device:
    print(f"Device: {device.device_info.label}")
    print(f"Status: {device.status.value}")
    print(f"System Index: {device.device_info.system_index}")
else:
    print("Device not found")
```

**Parameters:**
- **stable_id** (`str`): The stable ID to look up

**Returns:** `RegisteredDevice` if found, `None` otherwise

##### `on(event_type: str, callback: Callable) -> None`

Subscribe to device events.

```python
def on_connect(device):
    print(f"Camera connected: {device.stable_id}")

def on_disconnect(device):
    print(f"Camera disconnected: {device.stable_id}")

cam.on('on_connect', on_connect)
cam.on('on_disconnect', on_disconnect)
```

**Parameters:**
- **event_type** (`str`): Event type to subscribe to
  - `'on_connect'`: Camera connection events
  - `'on_disconnect'`: Camera disconnection events  
  - `'on_status_change'`: Any status change events
- **callback** (`Callable`): Function to call when event occurs. Receives `RegisteredDevice` as parameter.

**Raises:**
- `ValueError`: If event_type is invalid
- `TypeError`: If callback is not callable

##### `run() -> None`

Start device monitoring in a background thread.

```python
cam.run()  # Start monitoring
# Your application code here...
cam.stop()  # Stop monitoring when done
```

Continuously monitors for device connections and disconnections, updating registry status and emitting appropriate events.

##### `stop() -> None`

Stop device monitoring.

```python
cam.stop()
```

Gracefully stops the monitoring thread and cleans up resources.

#### Context Manager Support

StableCam supports context manager protocol for automatic cleanup:

```python
with StableCam() as cam:
    devices = cam.detect()
    # Monitoring automatically stops when exiting context
```

#### Example: Complete Usage

```python
from stablecam import StableCam
import time

def on_camera_event(device):
    print(f"Camera {device.stable_id}: {device.status.value}")

# Initialize with custom settings
cam = StableCam(
    poll_interval=1.0,
    log_level="DEBUG"
)

# Set up event handlers
cam.on('on_connect', on_camera_event)
cam.on('on_disconnect', on_camera_event)

# Detect and register cameras
devices = cam.detect()
for device in devices:
    stable_id = cam.register(device)
    print(f"Registered: {stable_id}")

# Start monitoring
cam.run()

try:
    # Keep running for 30 seconds
    time.sleep(30)
finally:
    cam.stop()
```

### CameraDevice

Represents a detected USB camera with hardware identifiers.

```python
@dataclass
class CameraDevice:
    system_index: int
    vendor_id: str
    product_id: str
    serial_number: Optional[str]
    port_path: Optional[str]
    label: str
    platform_data: Dict[str, Any]
```

#### Attributes

- **system_index** (`int`): Current system device index (e.g., `/dev/video0` → 0)
- **vendor_id** (`str`): USB vendor ID (hexadecimal string)
- **product_id** (`str`): USB product ID (hexadecimal string)
- **serial_number** (`Optional[str]`): Device serial number if available
- **port_path** (`Optional[str]`): USB port path for physical location
- **label** (`str`): Human-readable device name
- **platform_data** (`Dict[str, Any]`): Platform-specific additional data

#### Methods

##### `generate_hardware_id() -> str`

Generate a unique hardware identifier for this device.

```python
device = cam.detect()[0]
hw_id = device.generate_hardware_id()
print(f"Hardware ID: {hw_id}")
# Output examples:
# "serial:ABC123456" (if serial number available)
# "vid-pid-port:046d:085b:/dev/usb1/1-1" (vendor/product + port)
# "vid-pid-hash:046d:085b:a1b2c3d4" (fallback with hash)
```

Uses hierarchical approach:
1. **Primary**: Serial number (if available)
2. **Secondary**: Vendor ID + Product ID + Port Path
3. **Fallback**: Vendor ID + Product ID + Hash

##### `matches_hardware_id(hardware_id: str) -> bool`

Check if this device matches the given hardware identifier.

```python
device = cam.detect()[0]
hw_id = device.generate_hardware_id()

if device.matches_hardware_id(hw_id):
    print("Device matches!")
```

#### Example: Device Information

```python
devices = cam.detect()
for device in devices:
    print(f"Device: {device.label}")
    print(f"  System Index: {device.system_index}")
    print(f"  Vendor ID: {device.vendor_id}")
    print(f"  Product ID: {device.product_id}")
    print(f"  Serial: {device.serial_number or 'N/A'}")
    print(f"  Port: {device.port_path or 'N/A'}")
    print(f"  Hardware ID: {device.generate_hardware_id()}")
    print()
```

### RegisteredDevice

Represents a camera in the persistent registry with stable ID.

```python
@dataclass
class RegisteredDevice:
    stable_id: str
    device_info: CameraDevice
    status: DeviceStatus
    registered_at: datetime
    last_seen: Optional[datetime]
```

#### Attributes

- **stable_id** (`str`): Persistent stable ID (e.g., "stable-cam-001")
- **device_info** (`CameraDevice`): Camera device information
- **status** (`DeviceStatus`): Current connection status
- **registered_at** (`datetime`): When device was first registered
- **last_seen** (`Optional[datetime]`): When device was last seen connected

#### Methods

##### `update_status(new_status: DeviceStatus) -> None`

Update the device status and last seen timestamp.

```python
device = cam.get_by_id("stable-cam-001")
device.update_status(DeviceStatus.CONNECTED)
```

##### `is_connected() -> bool`

Check if the device is currently connected.

```python
device = cam.get_by_id("stable-cam-001")
if device.is_connected():
    print("Camera is ready to use")
else:
    print("Camera is not available")
```

##### `get_hardware_id() -> str`

Get the hardware identifier for this registered device.

```python
device = cam.get_by_id("stable-cam-001")
hw_id = device.get_hardware_id()
```

#### Example: Device Status Monitoring

```python
registered = cam.list()
for device in registered:
    print(f"Camera: {device.stable_id}")
    print(f"  Label: {device.device_info.label}")
    print(f"  Status: {device.status.value}")
    print(f"  Connected: {device.is_connected()}")
    print(f"  Registered: {device.registered_at.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if device.last_seen:
        print(f"  Last Seen: {device.last_seen.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if device.is_connected():
        print(f"  Current Index: {device.device_info.system_index}")
    print()
```

### DeviceStatus

Enumeration of possible device connection states.

```python
class DeviceStatus(Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
```

#### Values

- **CONNECTED**: Device is currently connected and available
- **DISCONNECTED**: Device is registered but not currently connected
- **ERROR**: Device encountered an error during detection or operation

#### Usage

```python
from stablecam import DeviceStatus

device = cam.get_by_id("stable-cam-001")

if device.status == DeviceStatus.CONNECTED:
    print("Camera is ready")
elif device.status == DeviceStatus.DISCONNECTED:
    print("Camera is unplugged")
elif device.status == DeviceStatus.ERROR:
    print("Camera has an error")

# Or use the convenience method
if device.is_connected():
    print("Camera is available")
```

## Registry Management

### DeviceRegistry

Manages persistent storage and retrieval of registered devices.

```python
from stablecam import DeviceRegistry
from pathlib import Path

# Use default location
registry = DeviceRegistry()

# Use custom location
registry = DeviceRegistry(Path("./my_cameras.json"))
```

#### Methods

##### `register(device: CameraDevice) -> str`

Register a new device and return its stable ID.

##### `get_all() -> List[RegisteredDevice]`

Get all registered devices.

##### `get_by_id(stable_id: str) -> Optional[RegisteredDevice]`

Get device by stable ID.

##### `update_status(stable_id: str, status: DeviceStatus) -> None`

Update device status.

##### `find_by_hardware_id(device: CameraDevice) -> Optional[RegisteredDevice]`

Find registered device by hardware identifier.

#### Registry File Format

The registry is stored as JSON:

```json
{
    "version": "1.0",
    "devices": {
        "stable-cam-001": {
            "stable_id": "stable-cam-001",
            "vendor_id": "046d",
            "product_id": "085b",
            "serial_number": "ABC123456",
            "port_path": "/dev/usb1/1-1",
            "label": "Logitech C920 HD Pro Webcam",
            "status": "connected",
            "registered_at": "2024-01-15T10:30:00Z",
            "last_seen": "2024-01-15T14:22:00Z",
            "platform_data": {}
        }
    }
}
```

## Event System

### EventManager

Manages event subscriptions and emissions.

```python
from stablecam import EventManager

events = EventManager()
```

#### Methods

##### `subscribe(event_type: str, callback: Callable) -> None`

Subscribe to an event type.

##### `unsubscribe(event_type: str, callback: Callable) -> None`

Unsubscribe from an event type.

##### `emit(event_type: str, data: Any) -> None`

Emit an event to all subscribers.

### EventType

Enumeration of available event types.

```python
class EventType(Enum):
    ON_CONNECT = "on_connect"
    ON_DISCONNECT = "on_disconnect"
    ON_STATUS_CHANGE = "on_status_change"
```

#### Event Handler Signature

All event handlers receive a `RegisteredDevice` object:

```python
def event_handler(device: RegisteredDevice) -> None:
    print(f"Event for {device.stable_id}: {device.status.value}")
```

## Platform Backends

### DeviceDetector

Manages platform-specific camera detection.

```python
from stablecam import DeviceDetector

detector = DeviceDetector()
devices = detector.detect_cameras()
backend = detector.get_platform_backend()
print(f"Using {backend.platform_name} backend")
```

### PlatformBackend

Abstract base class for platform-specific implementations.

#### Implementations

- **LinuxBackend**: Uses v4l2 and udev
- **WindowsBackend**: Uses Windows Media Foundation
- **MacOSBackend**: Uses AVFoundation and IOKit

## Exceptions

### StableCamError

Base exception for all StableCam errors.

### PlatformDetectionError

Raised when camera detection fails due to platform issues.

```python
from stablecam.backends.exceptions import PlatformDetectionError

try:
    devices = cam.detect()
except PlatformDetectionError as e:
    print(f"Detection failed: {e}")
    print(f"Platform: {e.platform}")
```

### RegistryError

Raised when registry operations fail.

```python
from stablecam import RegistryError

try:
    stable_id = cam.register(device)
except RegistryError as e:
    print(f"Registration failed: {e}")
```

### RegistryCorruptionError

Raised when registry file is corrupted (automatically recovered).

## Usage Patterns

### Basic Detection and Registration

```python
from stablecam import StableCam

cam = StableCam()

# Detect and register all cameras
devices = cam.detect()
for device in devices:
    stable_id = cam.register(device)
    print(f"Registered {device.label} as {stable_id}")
```

### Real-time Monitoring

```python
from stablecam import StableCam
import time

def on_connect(device):
    print(f"📷 Connected: {device.stable_id}")

def on_disconnect(device):
    print(f"📷 Disconnected: {device.stable_id}")

cam = StableCam()
cam.on('on_connect', on_connect)
cam.on('on_disconnect', on_disconnect)

cam.run()
try:
    time.sleep(60)  # Monitor for 1 minute
finally:
    cam.stop()
```

### Error Handling

```python
from stablecam import StableCam, RegistryError
from stablecam.backends.exceptions import PlatformDetectionError

cam = StableCam()

try:
    devices = cam.detect()
except PlatformDetectionError as e:
    print(f"Platform detection failed: {e}")
    # Handle platform-specific issues
except PermissionError as e:
    print(f"Permission denied: {e}")
    # Guide user to fix permissions
except Exception as e:
    print(f"Unexpected error: {e}")

for device in devices:
    try:
        stable_id = cam.register(device)
    except RegistryError as e:
        print(f"Registration failed for {device.label}: {e}")
```

### Custom Registry Location

```python
from stablecam import StableCam
from pathlib import Path

# Use project-specific registry
registry_path = Path("./project_cameras.json")
cam = StableCam(registry_path=registry_path)
```

### Context Manager Usage

```python
from stablecam import StableCam

with StableCam() as cam:
    devices = cam.detect()
    for device in devices:
        stable_id = cam.register(device)
        print(f"Registered: {stable_id}")
    
    # Start monitoring
    cam.run()
    
    # Your application logic here
    time.sleep(30)
    
    # Cleanup happens automatically
```

### Integration with Logging

```python
import logging
from stablecam import StableCam

# Set up your application logging
logging.basicConfig(level=logging.INFO)

# StableCam will use your logging configuration
cam = StableCam(enable_logging=False)  # Don't override logging

# Or customize StableCam logging
cam = StableCam(log_level="DEBUG")
```

This completes the comprehensive API documentation with detailed examples and usage patterns.