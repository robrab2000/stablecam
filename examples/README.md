# StableCam Examples

This directory contains example scripts demonstrating various ways to use StableCam in your applications.

## Running the Examples

Make sure you have StableCam installed:

```bash
pip install stablecam[all]
```

Then run any example:

```bash
python examples/basic_usage.py
```

## Example Scripts

### 1. Basic Usage (`basic_usage.py`)

**Purpose:** Demonstrates fundamental StableCam operations

**What it shows:**
- Detecting connected cameras
- Registering cameras with stable IDs
- Listing registered devices
- Checking device status
- Getting devices by stable ID

**Best for:** Learning the core API and getting started

```bash
python examples/basic_usage.py
```

### 2. Event Monitoring (`event_monitoring.py`)

**Purpose:** Real-time monitoring of camera connections and disconnections

**What it shows:**
- Setting up event handlers
- Real-time monitoring with background threads
- Handling connect/disconnect events
- Graceful shutdown with signal handling

**Best for:** Applications that need to respond to camera state changes

```bash
python examples/event_monitoring.py
```

**Usage:**
- The script will start monitoring and show any registered cameras
- Connect or disconnect USB cameras to see real-time events
- Press Ctrl+C to stop monitoring

### 3. Multi-Camera Setup (`multi_camera_setup.py`)

**Purpose:** Managing multiple cameras with role assignments

**What it shows:**
- Assigning roles to cameras (main, overhead, side, backup)
- Interactive camera setup
- Checking setup status and requirements
- Managing camera assignments

**Best for:** Multi-camera applications like streaming setups, security systems, or recording studios

```bash
python examples/multi_camera_setup.py
```

**Usage:**
- Follow the interactive prompts to assign cameras to roles
- The script will guide you through the setup process
- Shows how to handle required vs optional cameras

### 4. Integration Example (`integration_example.py`)

**Purpose:** Complete integration into a video recording application

**What it shows:**
- Integrating StableCam into a larger application
- Camera preferences and configuration
- Recording session management
- Handling camera disconnections during recording
- Application state management

**Best for:** Understanding how to build StableCam into production applications

```bash
python examples/integration_example.py
```

**Features demonstrated:**
- Automatic camera discovery and setup
- Recording session management with pause/resume
- Camera preference storage and application
- Resilient recording that handles disconnections

## Common Patterns

### Error Handling

All examples demonstrate proper error handling:

```python
try:
    devices = cam.detect()
except PlatformDetectionError as e:
    print(f"Camera detection failed: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Event Handling

Setting up event handlers for real-time monitoring:

```python
def on_connect(device):
    print(f"Camera connected: {device.stable_id}")

cam = StableCam()
cam.on('on_connect', on_connect)
cam.run()  # Start monitoring
```

### Context Management

Using StableCam as a context manager for automatic cleanup:

```python
with StableCam() as cam:
    devices = cam.detect()
    # Monitoring automatically stops when exiting context
```

### Configuration

Customizing StableCam behavior:

```python
cam = StableCam(
    poll_interval=1.0,      # Check every second
    log_level="DEBUG",      # Verbose logging
    registry_path=Path("./my_cameras.json")  # Custom registry location
)
```

## Testing the Examples

### Prerequisites

1. **USB Cameras:** Connect one or more USB cameras to test with
2. **Permissions:** Ensure your user has camera access permissions
3. **Platform Dependencies:** Install platform-specific packages if needed

### Linux Testing

```bash
# Check camera detection
ls /dev/video*

# Check permissions
groups $USER  # Should include 'video' group

# Run examples
python examples/basic_usage.py
```

### Windows Testing

```bash
# Check camera detection in PowerShell
Get-PnpDevice -Class Camera

# Run examples
python examples/basic_usage.py
```

### macOS Testing

```bash
# Check camera detection
system_profiler SPCameraDataType

# Run examples
python examples/basic_usage.py
```

## Troubleshooting

### No Cameras Detected

1. **Check physical connection:** Ensure cameras are properly connected
2. **Check permissions:** See platform-specific requirements in main README
3. **Enable debug logging:** Use `log_level="DEBUG"` in examples
4. **Test with system tools:** Use platform-specific camera detection tools

### Permission Errors

- **Linux:** Add user to `video` group: `sudo usermod -a -G video $USER`
- **Windows:** Run as Administrator or check Camera privacy settings
- **macOS:** Grant camera permissions in System Preferences

### Import Errors

```bash
# Install all dependencies
pip install stablecam[all]

# Or install specific platform support
pip install stablecam[linux-enhanced]  # Linux
pip install stablecam[windows-enhanced]  # Windows
pip install stablecam[macos-enhanced]  # macOS
```

## Extending the Examples

### Adding Custom Event Handlers

```python
def my_custom_handler(device):
    # Your custom logic here
    pass

cam.on('on_connect', my_custom_handler)
```

### Custom Camera Roles

Modify `multi_camera_setup.py` to add your own camera roles:

```python
roles = [
    ("presenter", "Presenter Camera", "Focuses on speaker", True),
    ("audience", "Audience Camera", "Shows audience reactions", False),
    ("screen", "Screen Camera", "Captures presentation screen", True),
]
```

### Integration Patterns

Use `integration_example.py` as a template for your own applications:

1. Copy the camera management patterns
2. Replace the recording simulation with your actual camera operations
3. Adapt the preference system to your needs
4. Customize event handling for your use case

## Next Steps

After running these examples:

1. **Read the API Documentation:** See the main README for complete API reference
2. **Check Platform Requirements:** Ensure you have all necessary system dependencies
3. **Build Your Application:** Use these patterns in your own projects
4. **Contribute:** Share your own examples or improvements!

## Support

If you encounter issues with the examples:

1. Check the main README troubleshooting section
2. Enable debug logging to see detailed information
3. Test with the basic example first before trying complex ones
4. Report issues with example output and system information