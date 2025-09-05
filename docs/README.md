# StableCam Documentation

Complete documentation for StableCam - Cross-platform USB camera monitoring with persistent anchoring.

## Quick Navigation

- **[Getting Started](#getting-started)** - Installation and first steps
- **[API Reference](api.md)** - Complete Python API documentation
- **[CLI Guide](cli-guide.md)** - Command-line interface reference
- **[Platform Guide](platform-guide.md)** - Platform-specific setup and troubleshooting
- **[Examples](../examples/)** - Code examples and integration patterns

## Getting Started

### What is StableCam?

StableCam solves the common problem where USB camera device indexes change when cameras are unplugged and replugged into different ports. It provides:

- **Persistent Stable IDs**: Cameras maintain the same ID across disconnections
- **Cross-Platform Support**: Works on Linux, Windows, and macOS
- **Real-Time Monitoring**: Detect camera state changes as they happen
- **Python API**: Clean integration into applications
- **Terminal UI**: Visual monitoring interface

### Quick Installation

```bash
# Basic installation
pip install stablecam

# With terminal UI support
pip install stablecam[tui]

# All features
pip install stablecam[all]
```

### 5-Minute Tutorial

1. **Install StableCam**:
   ```bash
   pip install stablecam[tui]
   ```

2. **Register your first camera**:
   ```bash
   stablecam register
   ```

3. **List registered cameras**:
   ```bash
   stablecam list
   ```

4. **Monitor in real-time**:
   ```bash
   stablecam monitor
   ```

5. **Use in Python**:
   ```python
   from stablecam import StableCam
   
   cam = StableCam()
   devices = cam.detect()
   
   if devices:
       stable_id = cam.register(devices[0])
       print(f"Camera registered as: {stable_id}")
   ```

## Documentation Structure

### Core Documentation

#### [API Reference](api.md)
Complete Python API documentation with examples:
- **StableCam Class**: Main interface for camera management
- **Data Models**: CameraDevice, RegisteredDevice, DeviceStatus
- **Event System**: Real-time monitoring and callbacks
- **Registry Management**: Persistent device storage
- **Platform Backends**: Cross-platform detection
- **Exception Handling**: Error types and recovery

#### [CLI Guide](cli-guide.md)
Command-line interface reference:
- **Commands**: register, list, monitor
- **Output Formats**: Table and JSON output
- **Scripting**: Integration with shell scripts
- **Automation**: Batch operations and health checks

#### [Platform Guide](platform-guide.md)
Platform-specific setup and troubleshooting:
- **Linux**: udev, v4l2, permissions setup
- **Windows**: Media Foundation, privacy settings
- **macOS**: AVFoundation, IOKit, permissions
- **Cross-Platform**: Compatibility considerations

### Examples and Tutorials

#### [Examples Directory](../examples/)
Complete example scripts demonstrating various use cases:
- **[basic_usage.py](../examples/basic_usage.py)**: Fundamental operations
- **[event_monitoring.py](../examples/event_monitoring.py)**: Real-time monitoring
- **[multi_camera_setup.py](../examples/multi_camera_setup.py)**: Multiple camera management
- **[integration_example.py](../examples/integration_example.py)**: Application integration

## Common Use Cases

### 1. Multi-Camera Recording Setup

```python
from stablecam import StableCam

cam = StableCam()

# Register cameras with roles
main_camera = cam.get_by_id("stable-cam-001")  # Main recording camera
overhead_camera = cam.get_by_id("stable-cam-002")  # Overhead view

if main_camera and main_camera.is_connected():
    print(f"Main camera ready at index {main_camera.device_info.system_index}")
```

### 2. Streaming Application

```python
def on_camera_connect(device):
    print(f"Stream source available: {device.stable_id}")
    # Start streaming from device.device_info.system_index

def on_camera_disconnect(device):
    print(f"Stream source lost: {device.stable_id}")
    # Handle stream interruption

cam = StableCam()
cam.on('on_connect', on_camera_connect)
cam.on('on_disconnect', on_camera_disconnect)
cam.run()
```

### 3. Security System

```python
# Monitor specific camera locations
security_cameras = {
    "stable-cam-001": "Front Door",
    "stable-cam-002": "Back Yard", 
    "stable-cam-003": "Garage"
}

for stable_id, location in security_cameras.items():
    device = cam.get_by_id(stable_id)
    if device and device.is_connected():
        print(f"{location} camera online (index: {device.device_info.system_index})")
    else:
        print(f"⚠️ {location} camera offline")
```

### 4. Automated Testing

```bash
#!/bin/bash
# Test script that requires specific cameras

# Check if test cameras are available
cameras=$(stablecam list --format json)
test_camera=$(echo "$cameras" | jq -r '.[] | select(.stable_id == "stable-cam-test") | .system_index')

if [ "$test_camera" != "null" ]; then
    echo "Running tests with camera at index $test_camera"
    python run_camera_tests.py --camera-index "$test_camera"
else
    echo "Test camera not available, skipping camera tests"
fi
```

## Integration Patterns

### Context Manager Pattern

```python
with StableCam() as cam:
    devices = cam.detect()
    # Automatic cleanup when done
```

### Event-Driven Architecture

```python
class CameraManager:
    def __init__(self):
        self.cam = StableCam()
        self.cam.on('on_connect', self.handle_connect)
        self.cam.on('on_disconnect', self.handle_disconnect)
    
    def handle_connect(self, device):
        # Your connection logic
        pass
    
    def handle_disconnect(self, device):
        # Your disconnection logic
        pass
```

### Configuration Management

```python
# Project-specific camera registry
from pathlib import Path

project_registry = Path("./config/cameras.json")
cam = StableCam(registry_path=project_registry)
```

## Best Practices

### 1. Error Handling

Always handle platform-specific errors:

```python
from stablecam import StableCam, RegistryError
from stablecam.backends.exceptions import PlatformDetectionError

try:
    cam = StableCam()
    devices = cam.detect()
except PlatformDetectionError as e:
    print(f"Camera detection failed: {e}")
    # Handle platform issues
except PermissionError as e:
    print(f"Permission denied: {e}")
    # Guide user to fix permissions
```

### 2. Resource Management

Stop monitoring when not needed:

```python
cam = StableCam()
cam.run()  # Start monitoring

try:
    # Your application logic
    pass
finally:
    cam.stop()  # Always stop monitoring
```

### 3. Registry Management

Use project-specific registries for isolation:

```python
# Don't mix different application cameras
app_registry = Path("./app_cameras.json")
cam = StableCam(registry_path=app_registry)
```

### 4. Performance Optimization

Adjust polling for your use case:

```python
# Reduce polling for battery-powered devices
cam = StableCam(poll_interval=5.0)

# Increase polling for real-time applications
cam = StableCam(poll_interval=0.5)
```

## Troubleshooting Quick Reference

### No Cameras Detected

1. **Check physical connection**
2. **Verify permissions** (see [Platform Guide](platform-guide.md))
3. **Enable debug logging**: `StableCam(log_level="DEBUG")`
4. **Test with system tools** (platform-specific)

### Permission Errors

- **Linux**: Add user to `video` group
- **Windows**: Check Camera privacy settings
- **macOS**: Grant camera permissions in System Preferences

### Registry Issues

```python
# Reset corrupted registry
import os
from pathlib import Path

registry_path = Path.home() / ".stablecam" / "registry.json"
if registry_path.exists():
    os.remove(registry_path)
```

### Performance Issues

```python
# Reduce resource usage
cam = StableCam(
    poll_interval=3.0,      # Less frequent polling
    log_level="WARNING"     # Reduce log noise
)
```

## Getting Help

### Documentation

1. **[API Reference](api.md)**: Complete Python API
2. **[CLI Guide](cli-guide.md)**: Command-line usage
3. **[Platform Guide](platform-guide.md)**: Platform-specific help
4. **[Examples](../examples/)**: Working code examples

### Community and Support

- **GitHub Issues**: Report bugs and request features
- **Discussions**: Ask questions and share use cases
- **Examples**: Contribute your own integration examples

### Reporting Issues

When reporting issues, include:

1. **Platform**: OS, Python version, StableCam version
2. **Hardware**: Camera models and connection method
3. **Debug Output**: Run with `log_level="DEBUG"`
4. **Minimal Example**: Reproduce the issue with minimal code

```python
# Debug information template
import platform
import stablecam

print(f"Platform: {platform.system()} {platform.release()}")
print(f"Python: {platform.python_version()}")
print(f"StableCam: {stablecam.__version__}")

cam = stablecam.StableCam(log_level="DEBUG")
devices = cam.detect()
print(f"Detected: {len(devices)} devices")
```

## Contributing

We welcome contributions! Areas where you can help:

- **Platform Support**: Improve detection on specific platforms
- **Documentation**: Add examples, fix typos, improve clarity
- **Testing**: Test with different camera models and configurations
- **Features**: Implement new functionality or improvements

See the main repository for contribution guidelines.

---

This documentation covers the complete StableCam system. Start with the [5-minute tutorial](#5-minute-tutorial) above, then dive into the specific guides based on your needs.