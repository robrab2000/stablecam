# StableCam

Cross-platform USB camera monitoring with persistent anchoring.

StableCam is a Python library and terminal UI tool for managing USB cameras with stable IDs that persist across disconnections and port changes. It solves the common problem where camera device indexes change when cameras are unplugged and replugged into different ports.

## Features

- **Persistent Stable IDs**: Cameras maintain the same ID across disconnections and port changes
- **Cross-Platform Support**: Works on Linux, Windows, and macOS
- **Real-Time Monitoring**: Detect camera connections and disconnections in real-time
- **Event System**: Subscribe to camera state change events
- **Terminal UI**: Visual interface for monitoring camera status
- **Python API**: Clean API for integration into applications
- **Hardware Identification**: Uses serial numbers, vendor/product IDs, and port paths for reliable identification

## Installation

### Basic Installation

```bash
pip install stablecam
```

### Installation with Terminal UI Support

```bash
pip install stablecam[tui]
```

### Platform-Specific Enhanced Features

For enhanced platform-specific features, install the appropriate extras:

```bash
# Linux enhanced support (v4l2)
pip install stablecam[linux-enhanced]

# Windows enhanced support (WMI)
pip install stablecam[windows-enhanced]

# macOS enhanced support (AVFoundation/IOKit)
pip install stablecam[macos-enhanced]

# All features
pip install stablecam[all]
```

### Development Installation

```bash
git clone https://github.com/stablecam/stablecam.git
cd stablecam
pip install -e .[dev,test,all]
```

## Quick Start

### Basic Usage

```python
from stablecam import StableCam

# Create StableCam instance
cam = StableCam()

# Detect connected cameras
devices = cam.detect()
print(f"Found {len(devices)} cameras")

# Register a camera
if devices:
    stable_id = cam.register(devices[0])
    print(f"Registered camera with stable ID: {stable_id}")

# List all registered cameras
registered = cam.list()
for device in registered:
    status = "🟢" if device.is_connected() else "🔴"
    print(f"{status} {device.stable_id}: {device.device_info.label}")
```

### Real-Time Monitoring

```python
from stablecam import StableCam

def on_connect(device):
    print(f"Camera connected: {device.stable_id}")

def on_disconnect(device):
    print(f"Camera disconnected: {device.stable_id}")

# Set up monitoring
cam = StableCam()
cam.on('on_connect', on_connect)
cam.on('on_disconnect', on_disconnect)

# Start monitoring (runs in background thread)
cam.run()

# Your application code here...
# Monitoring continues until cam.stop() is called
```

### Terminal UI

Launch the terminal UI to visually monitor cameras:

```bash
stablecam tui
```

### Command Line Interface

```bash
# Register the first detected camera
stablecam register

# List all registered cameras
stablecam list

# Show help
stablecam --help
```

## API Documentation

### StableCam Class

The main class for camera management and monitoring.

#### Constructor

```python
StableCam(registry_path=None, poll_interval=2.0, log_level="INFO", enable_logging=True)
```

**Parameters:**
- `registry_path` (Path, optional): Custom path for registry file
- `poll_interval` (float): Interval in seconds for device monitoring (default: 2.0)
- `log_level` (str): Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `enable_logging` (bool): Whether to set up logging configuration

#### Methods

##### `detect() -> List[CameraDevice]`

Detect all currently connected USB cameras.

**Returns:** List of detected camera devices

**Raises:** `PlatformDetectionError` if camera detection fails

##### `register(device: CameraDevice) -> str`

Register a camera device and assign it a stable ID.

**Parameters:**
- `device`: The camera device to register

**Returns:** The assigned stable ID

**Raises:** `RegistryError` if device registration fails

##### `list() -> List[RegisteredDevice]`

Get all registered devices with their current status.

**Returns:** List of all registered devices

##### `get_by_id(stable_id: str) -> Optional[RegisteredDevice]`

Get a registered device by its stable ID.

**Parameters:**
- `stable_id`: The stable ID to look up

**Returns:** The device if found, None otherwise

##### `on(event_type: str, callback: Callable) -> None`

Subscribe to device events.

**Parameters:**
- `event_type`: Event type ('on_connect', 'on_disconnect', 'on_status_change')
- `callback`: Function to call when event occurs

##### `run() -> None`

Start device monitoring in a background thread.

##### `stop() -> None`

Stop device monitoring.

### Data Models

#### CameraDevice

Represents a detected USB camera.

```python
@dataclass
class CameraDevice:
    system_index: int              # Current system device index
    vendor_id: str                 # USB vendor ID
    product_id: str               # USB product ID
    serial_number: Optional[str]   # Device serial number
    port_path: Optional[str]       # USB port path
    label: str                     # Human-readable device name
    platform_data: Dict[str, Any] # Platform-specific data
```

#### RegisteredDevice

Represents a camera in the persistent registry.

```python
@dataclass
class RegisteredDevice:
    stable_id: str                 # Persistent stable ID
    device_info: CameraDevice      # Camera device information
    status: DeviceStatus           # Current connection status
    registered_at: datetime        # Registration timestamp
    last_seen: Optional[datetime]  # Last seen timestamp
```

#### DeviceStatus

Enumeration of device connection states.

```python
class DeviceStatus(Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
```

## Platform-Specific Requirements

### Linux

**Required System Packages:**
```bash
# Ubuntu/Debian
sudo apt-get install libudev-dev

# CentOS/RHEL/Fedora
sudo yum install libudev-devel
# or
sudo dnf install libudev-devel
```

**Enhanced Features:**
- Install `stablecam[linux-enhanced]` for v4l2 support
- Requires v4l2 development headers for compilation

### Windows

**Requirements:**
- Windows 7 or later
- No additional system packages required

**Enhanced Features:**
- Install `stablecam[windows-enhanced]` for WMI support
- Provides additional device metadata

### macOS

**Requirements:**
- macOS 10.12 or later
- Xcode command line tools for compilation

**Enhanced Features:**
- Install `stablecam[macos-enhanced]` for AVFoundation/IOKit support
- Provides richer device information

## Examples

See the `examples/` directory for complete example scripts:

- `basic_usage.py` - Basic camera detection and registration
- `event_monitoring.py` - Real-time event monitoring
- `multi_camera_setup.py` - Managing multiple cameras
- `integration_example.py` - Integration with other applications

## Troubleshooting

### Common Issues

#### Permission Denied Errors

**Linux:**
```bash
# Add user to video group
sudo usermod -a -G video $USER
# Log out and back in for changes to take effect
```

**Windows:**
- Run as Administrator if needed
- Check Windows Camera privacy settings

**macOS:**
- Grant camera permissions in System Preferences > Security & Privacy

#### No Cameras Detected

1. **Verify camera connection:**
   ```bash
   # Linux
   lsusb | grep -i camera
   
   # Windows
   Get-PnpDevice -Class Camera
   
   # macOS
   system_profiler SPCameraDataType
   ```

2. **Check platform-specific tools:**
   ```bash
   # Linux - list video devices
   ls /dev/video*
   
   # Test with v4l2
   v4l2-ctl --list-devices
   ```

3. **Enable debug logging:**
   ```python
   cam = StableCam(log_level="DEBUG")
   ```

#### Registry Corruption

If the registry becomes corrupted, StableCam will automatically create a backup and start fresh:

```python
# Force registry reset (removes all registered devices)
import os
from pathlib import Path

registry_path = Path.home() / ".stablecam" / "registry.json"
if registry_path.exists():
    os.remove(registry_path)
```

### Performance Considerations

- **Polling Interval**: Adjust `poll_interval` based on your needs (default: 2.0 seconds)
- **Multiple Instances**: Avoid running multiple StableCam instances simultaneously
- **Resource Usage**: Monitoring uses minimal CPU/memory but consider stopping when not needed

### Platform-Specific Notes

#### Linux
- Requires read access to `/dev/video*` devices
- udev rules may be needed for non-standard devices
- Some virtual cameras may not be detected

#### Windows
- Windows Media Foundation provides the most reliable detection
- DirectShow fallback for older systems
- Some USB hubs may cause detection issues

#### macOS
- AVFoundation provides comprehensive device information
- System permissions required for camera access
- USB-C hubs may affect port path detection

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
git clone https://github.com/stablecam/stablecam.git
cd stablecam
pip install -e .[dev,test,all]

# Run tests
pytest

# Run linting
ruff check .
black --check .
mypy stablecam/
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and changes.