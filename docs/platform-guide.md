# Platform-Specific Guide

This guide covers platform-specific requirements, installation, and troubleshooting for StableCam on Linux, Windows, and macOS.

## Table of Contents

- [Linux](#linux)
- [Windows](#windows)
- [macOS](#macos)
- [Cross-Platform Considerations](#cross-platform-considerations)
- [Troubleshooting](#troubleshooting)

## Linux

### System Requirements

- **Kernel Version**: 2.6.32 or later (for udev support)
- **Python**: 3.8 or later
- **Architecture**: x86_64, ARM64, ARM (Raspberry Pi supported)

### Required System Packages

#### Ubuntu/Debian

```bash
# Essential packages
sudo apt-get update
sudo apt-get install libudev-dev python3-dev

# Optional: v4l2 utilities for testing
sudo apt-get install v4l-utils

# Optional: USB utilities for debugging
sudo apt-get install usbutils
```

#### CentOS/RHEL/Fedora

```bash
# CentOS/RHEL
sudo yum install libudev-devel python3-devel

# Fedora
sudo dnf install libudev-devel python3-devel

# Optional: v4l2 utilities
sudo dnf install v4l-utils  # Fedora
sudo yum install v4l-utils  # CentOS/RHEL
```

#### Arch Linux

```bash
sudo pacman -S systemd python

# Optional utilities
sudo pacman -S v4l-utils usbutils
```

### Installation

#### Basic Installation

```bash
pip install stablecam
```

#### Enhanced Linux Support

```bash
# Install with v4l2 support for better device information
pip install stablecam[linux-enhanced]
```

**Note**: v4l2-python requires compilation and may need additional development packages.

### Permissions Setup

#### Add User to Video Group

```bash
# Add current user to video group
sudo usermod -a -G video $USER

# Verify group membership
groups $USER

# Log out and back in for changes to take effect
```

#### Alternative: udev Rules (Advanced)

For custom permission setup or non-standard devices:

```bash
# Create custom udev rule
sudo nano /etc/udev/rules.d/99-stablecam.rules
```

Add content:
```
# StableCam camera access
SUBSYSTEM=="video4linux", GROUP="video", MODE="0664"
KERNEL=="video[0-9]*", GROUP="video", MODE="0664"
```

Reload udev rules:
```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### Platform-Specific Features

#### Device Detection Methods

1. **Primary**: `/dev/video*` enumeration
2. **Enhanced**: v4l2 device capabilities
3. **Hardware Info**: udev device properties

#### Supported Device Information

- Device name and capabilities
- Vendor/Product IDs via udev
- Serial numbers (when available)
- USB port paths
- v4l2 driver information

### Testing Camera Detection

```bash
# List video devices
ls -la /dev/video*

# Show detailed device information
v4l2-ctl --list-devices

# Test camera access
v4l2-ctl --device=/dev/video0 --info

# List USB devices
lsusb | grep -i camera

# Show udev properties
udevadm info --name=/dev/video0 --attribute-walk
```

### Common Issues

#### No Video Devices Found

```bash
# Check if cameras are detected by kernel
dmesg | grep -i video
dmesg | grep -i uvc

# Check USB connection
lsusb

# Verify udev rules
udevadm info --name=/dev/video0
```

#### Permission Denied

```bash
# Check current permissions
ls -la /dev/video*

# Check group membership
groups $USER

# Test access
cat /dev/video0 > /dev/null
```

#### Virtual Cameras

Some virtual camera software creates `/dev/video*` devices that may interfere:

```bash
# List all video devices with details
v4l2-ctl --list-devices

# Check device capabilities
for dev in /dev/video*; do
    echo "=== $dev ==="
    v4l2-ctl --device=$dev --info 2>/dev/null || echo "Cannot access"
done
```

### Performance Optimization

#### Reduce Polling Overhead

```python
# Increase poll interval for battery-powered devices
cam = StableCam(poll_interval=5.0)
```

#### Raspberry Pi Considerations

```bash
# Increase GPU memory split for camera support
sudo raspi-config
# Advanced Options > Memory Split > 128

# Enable camera interface
sudo raspi-config
# Interface Options > Camera > Enable
```

## Windows

### System Requirements

- **OS Version**: Windows 7 SP1 or later (Windows 10/11 recommended)
- **Python**: 3.8 or later
- **Architecture**: x86_64 (64-bit recommended)

### Installation

#### Basic Installation

```powershell
pip install stablecam
```

#### Enhanced Windows Support

```powershell
# Install with WMI support for enhanced device information
pip install stablecam[windows-enhanced]
```

### Permissions and Security

#### Camera Privacy Settings (Windows 10/11)

1. Open **Settings** > **Privacy & Security** > **Camera**
2. Ensure "Allow apps to access your camera" is **On**
3. Ensure "Allow desktop apps to access your camera" is **On**

#### Running as Administrator

Some operations may require elevated privileges:

```powershell
# Run PowerShell as Administrator
# Right-click PowerShell > "Run as Administrator"
```

### Platform-Specific Features

#### Device Detection Methods

1. **Primary**: Windows Media Foundation (WMF)
2. **Fallback**: DirectShow enumeration
3. **Enhanced**: WMI device queries

#### Supported Device Information

- Device friendly names
- Hardware IDs and instance paths
- Vendor/Product IDs
- Device capabilities and formats
- Driver information

### Testing Camera Detection

#### PowerShell Commands

```powershell
# List camera devices
Get-PnpDevice -Class Camera

# Show detailed device information
Get-PnpDevice -Class Camera | Format-List *

# List USB devices
Get-PnpDevice -Class USB | Where-Object {$_.FriendlyName -like "*camera*"}

# Check Windows Media Foundation devices
# (Requires additional tools or custom script)
```

#### Device Manager

1. Open **Device Manager** (`devmgmt.msc`)
2. Expand **Cameras** or **Imaging devices**
3. Right-click device > **Properties** > **Details**
4. View **Hardware Ids** and **Device instance path**

### Common Issues

#### No Cameras Detected

1. **Check Device Manager**: Ensure cameras appear without error icons
2. **Update Drivers**: Right-click device > "Update driver"
3. **Windows Updates**: Install latest Windows updates
4. **USB Power Management**: Disable USB selective suspend

#### Access Denied Errors

1. **Privacy Settings**: Check camera privacy settings
2. **Antivirus Software**: Temporarily disable to test
3. **Windows Defender**: Add Python/StableCam to exclusions
4. **Run as Administrator**: Try elevated privileges

#### Driver Issues

```powershell
# Reinstall camera drivers
# In Device Manager:
# Right-click camera > Uninstall device
# Action > Scan for hardware changes
```

#### USB Hub Issues

Some USB hubs cause detection problems:

1. **Direct Connection**: Connect camera directly to computer
2. **Powered Hub**: Use powered USB hub
3. **USB 3.0 vs 2.0**: Try different USB ports

### Performance Considerations

#### Windows Media Foundation vs DirectShow

```python
# Force specific backend (advanced usage)
from stablecam.backends.windows import WindowsBackend

backend = WindowsBackend()
# WMF is preferred, DirectShow is fallback
```

#### Multiple Camera Performance

Windows may limit simultaneous camera access:

```python
# Reduce polling frequency for multiple cameras
cam = StableCam(poll_interval=3.0)
```

## macOS

### System Requirements

- **OS Version**: macOS 10.12 (Sierra) or later
- **Python**: 3.8 or later
- **Architecture**: x86_64, ARM64 (Apple Silicon supported)

### Installation

#### Basic Installation

```bash
pip install stablecam
```

#### Enhanced macOS Support

```bash
# Install with AVFoundation/IOKit support
pip install stablecam[macos-enhanced]
```

**Note**: Enhanced support requires Xcode command line tools for compilation.

### Development Tools Setup

```bash
# Install Xcode command line tools
xcode-select --install

# Verify installation
xcode-select -p
```

### Permissions and Security

#### Camera Access Permissions

macOS requires explicit permission for camera access:

1. **System Preferences** > **Security & Privacy** > **Privacy** > **Camera**
2. Add Python or your terminal application to allowed apps
3. Grant permission when prompted

#### Terminal Permission

If running from Terminal:

1. **System Preferences** > **Security & Privacy** > **Privacy** > **Camera**
2. Add **Terminal** to the list
3. Restart Terminal after granting permission

### Platform-Specific Features

#### Device Detection Methods

1. **Primary**: AVFoundation device discovery
2. **Enhanced**: IOKit USB device information
3. **Hardware Info**: System profiler data

#### Supported Device Information

- Device names and unique IDs
- Vendor/Product IDs via IOKit
- USB location and topology
- Device capabilities and formats
- Built-in vs external camera detection

### Testing Camera Detection

#### System Commands

```bash
# List camera devices
system_profiler SPCameraDataType

# Show USB device tree
system_profiler SPUSBDataType | grep -A 10 -i camera

# List video devices (if available)
ls /dev/video* 2>/dev/null || echo "No video devices found"

# Check IOKit registry
ioreg -p IOUSB -l -w 0 | grep -i camera
```

#### Camera Test

```bash
# Test camera access with system tools
# Open Photo Booth or FaceTime to verify camera works
```

### Common Issues

#### Permission Denied

1. **Check Privacy Settings**: Ensure camera permission is granted
2. **Reset Permissions**: Remove and re-add app in Privacy settings
3. **Restart Application**: Restart Terminal/IDE after permission changes

#### No Cameras Detected

```bash
# Check system recognition
system_profiler SPCameraDataType

# Verify USB connection
system_profiler SPUSBDataType | grep -i camera

# Check for kernel extensions
kextstat | grep -i camera
```

#### Built-in Camera Issues

```bash
# Reset SMC (System Management Controller)
# Shut down Mac
# Press Shift-Control-Option on left side + power button for 10 seconds
# Release and restart

# Reset NVRAM/PRAM
# Restart and hold Option-Command-P-R until you hear startup sound twice
```

#### External Camera Issues

1. **USB-C Hubs**: Some hubs cause detection issues
2. **Direct Connection**: Try connecting directly to Mac
3. **Different Ports**: Try different USB ports
4. **Cable Quality**: Use high-quality USB cables

### Apple Silicon Considerations

#### Rosetta 2

If using x86_64 Python on Apple Silicon:

```bash
# Install Rosetta 2 if needed
softwareupdate --install-rosetta

# Check Python architecture
python -c "import platform; print(platform.machine())"
```

#### Native ARM64

For best performance, use native ARM64 Python:

```bash
# Install ARM64 Python via Homebrew
brew install python@3.11

# Verify native architecture
/opt/homebrew/bin/python3 -c "import platform; print(platform.machine())"
```

## Cross-Platform Considerations

### Registry File Locations

Default registry locations by platform:

- **Linux**: `~/.stablecam/registry.json`
- **Windows**: `%USERPROFILE%\.stablecam\registry.json`
- **macOS**: `~/.stablecam/registry.json`

### Hardware ID Consistency

Hardware IDs should be consistent across platforms for the same device:

```python
# Same camera on different platforms should generate same hardware ID
# if it has a serial number
device.generate_hardware_id()  # "serial:ABC123456"
```

### Path Separators

StableCam handles path separators automatically:

```python
from pathlib import Path

# Cross-platform registry path
registry_path = Path.home() / ".stablecam" / "registry.json"
cam = StableCam(registry_path=registry_path)
```

### USB Port Paths

Port paths vary by platform:

- **Linux**: `/dev/usb1/1-1.2`
- **Windows**: `USB\VID_046D&PID_085B\5&2E2A2C8F&0&2`
- **macOS**: `IOService:/AppleACPIPlatformExpert/PCI0@0/AppleACPIPCI/XHC1@14/XHC1@14000000/HS02@14200000`

## Troubleshooting

### General Debugging Steps

1. **Enable Debug Logging**:
   ```python
   cam = StableCam(log_level="DEBUG")
   ```

2. **Test Basic Detection**:
   ```python
   from stablecam import StableCam
   cam = StableCam()
   devices = cam.detect()
   print(f"Found {len(devices)} devices")
   ```

3. **Check Platform Backend**:
   ```python
   backend = cam.detector.get_platform_backend()
   print(f"Using: {backend.platform_name}")
   ```

### Platform-Specific Debugging

#### Linux Debug Commands

```bash
# Check kernel messages
dmesg | tail -20

# Monitor udev events
sudo udevadm monitor --property

# Test v4l2 access
v4l2-ctl --list-devices --verbose
```

#### Windows Debug Commands

```powershell
# Check Windows event logs
Get-WinEvent -LogName System | Where-Object {$_.LevelDisplayName -eq "Error"} | Select-Object -First 10

# List PnP devices with problems
Get-PnpDevice | Where-Object {$_.Status -ne "OK"}
```

#### macOS Debug Commands

```bash
# Check system logs
log show --predicate 'subsystem contains "camera"' --last 1h

# Monitor USB events
log stream --predicate 'subsystem contains "usb"'
```

### Performance Issues

#### High CPU Usage

```python
# Increase polling interval
cam = StableCam(poll_interval=5.0)

# Stop monitoring when not needed
cam.stop()
```

#### Memory Leaks

```python
# Use context manager for automatic cleanup
with StableCam() as cam:
    # Your code here
    pass  # Automatic cleanup
```

### Registry Issues

#### Corrupted Registry

StableCam automatically recovers from corruption, but you can manually reset:

```python
import os
from pathlib import Path

# Remove corrupted registry (will be recreated)
registry_path = Path.home() / ".stablecam" / "registry.json"
if registry_path.exists():
    os.remove(registry_path)
```

#### Permission Issues

```bash
# Linux/macOS: Fix registry permissions
chmod 644 ~/.stablecam/registry.json
chmod 755 ~/.stablecam/

# Windows: Check file permissions in Properties
```

### Getting Help

When reporting issues, include:

1. **Platform and Version**: OS, Python version, StableCam version
2. **Hardware**: Camera models and connection method
3. **Debug Output**: Run with `log_level="DEBUG"`
4. **System Information**: Output of platform-specific detection commands
5. **Error Messages**: Complete error messages and stack traces

Example debug information collection:

```python
import platform
import stablecam

print(f"Platform: {platform.system()} {platform.release()}")
print(f"Python: {platform.python_version()}")
print(f"StableCam: {stablecam.__version__}")

cam = stablecam.StableCam(log_level="DEBUG")
try:
    devices = cam.detect()
    print(f"Detected devices: {len(devices)}")
    for device in devices:
        print(f"  {device.label}: {device.generate_hardware_id()}")
except Exception as e:
    print(f"Error: {e}")
```

This comprehensive platform guide should help users successfully install and use StableCam on any supported platform.