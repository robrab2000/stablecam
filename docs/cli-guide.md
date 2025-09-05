# StableCam CLI Guide

Complete guide to using the StableCam command-line interface.

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Commands](#commands)
  - [register](#register)
  - [list](#list)
  - [monitor](#monitor)
- [Global Options](#global-options)
- [Output Formats](#output-formats)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

## Installation

The CLI is included with StableCam installation:

```bash
# Basic installation
pip install stablecam

# With terminal UI support
pip install stablecam[tui]

# Verify installation
stablecam --version
```

## Quick Start

```bash
# Register the first detected camera
stablecam register

# List all registered cameras
stablecam list

# Launch terminal UI for monitoring
stablecam monitor
```

## Commands

### register

Register the first detected camera with a stable ID.

```bash
stablecam register [OPTIONS]
```

#### Options

- `--registry-path PATH`: Custom path for the device registry file
- `--help`: Show help message

#### Description

Detects connected USB cameras and registers the first one found, assigning it a persistent stable ID for future reference. If the camera is already registered, it will update its status to connected.

#### Examples

```bash
# Register first detected camera
stablecam register

# Use custom registry location
stablecam register --registry-path ./project_cameras.json

# Register with verbose output
stablecam register
```

#### Sample Output

```
Detecting USB cameras...
Found camera: Logitech HD Pro Webcam C920
✓ Camera registered with stable ID: stable-cam-001

Device details:
  Stable ID: stable-cam-001
  Label: Logitech HD Pro Webcam C920
  System Index: 0
  Vendor ID: 046d
  Product ID: 085b
  Serial Number: ABC123456
  Port Path: /dev/usb1/1-1.2
```

#### Exit Codes

- `0`: Success
- `1`: No cameras detected or registration failed

### list

List all registered devices with their stable IDs and current status.

```bash
stablecam list [OPTIONS]
```

#### Options

- `--registry-path PATH`: Custom path for the device registry file
- `--format [table|json]`: Output format (default: table)
- `--help`: Show help message

#### Description

Shows all cameras that have been registered with StableCam, including their stable IDs, connection status, and device information.

#### Examples

```bash
# List in table format (default)
stablecam list

# List in JSON format
stablecam list --format json

# Use custom registry
stablecam list --registry-path ./project_cameras.json
```

#### Sample Output

**Table Format:**
```
Found 2 registered device(s):

Stable ID       Status       System Index Label                         
----------------------------------------------------------------------
stable-cam-001  ● connected  0            Logitech HD Pro Webcam C920   
stable-cam-002  ○ disconnected N/A        Microsoft LifeCam HD-3000     

Use 'stablecam list --format json' for detailed device information.
```

**JSON Format:**
```json
[
  {
    "stable_id": "stable-cam-001",
    "label": "Logitech HD Pro Webcam C920",
    "status": "connected",
    "system_index": 0,
    "vendor_id": "046d",
    "product_id": "085b",
    "serial_number": "ABC123456",
    "port_path": "/dev/usb1/1-1.2",
    "registered_at": "2024-01-15T10:30:00",
    "last_seen": "2024-01-15T14:22:00"
  },
  {
    "stable_id": "stable-cam-002",
    "label": "Microsoft LifeCam HD-3000",
    "status": "disconnected",
    "system_index": null,
    "vendor_id": "045e",
    "product_id": "0779",
    "serial_number": null,
    "port_path": null,
    "registered_at": "2024-01-14T09:15:00",
    "last_seen": "2024-01-14T16:45:00"
  }
]
```

#### Status Indicators

- `● connected`: Camera is currently connected and available
- `○ disconnected`: Camera is registered but not currently connected
- `⚠ error`: Camera encountered an error during detection

### monitor

Launch the terminal UI for real-time camera monitoring.

```bash
stablecam monitor [OPTIONS]
```

#### Options

- `--registry-path PATH`: Custom path for the device registry file
- `--help`: Show help message

#### Description

Opens an interactive terminal interface that displays all registered cameras with their stable IDs, connection status, and real-time updates when devices connect or disconnect.

#### Requirements

Terminal UI requires additional dependencies:

```bash
pip install stablecam[tui]
```

#### Examples

```bash
# Launch terminal UI
stablecam monitor

# Use custom registry
stablecam monitor --registry-path ./project_cameras.json
```

#### Terminal UI Features

- **Real-time Updates**: Live display of camera connection status
- **Device Information**: Shows stable IDs, labels, and system indexes
- **Connection Events**: Visual alerts when cameras connect/disconnect
- **Keyboard Controls**:
  - `q` or `Ctrl+C`: Quit
  - `r`: Refresh device list
  - `↑/↓`: Navigate device list

#### Sample Terminal UI

```
┌─ StableCam Monitor ─────────────────────────────────────────────────────┐
│                                                                         │
│ Registered Cameras (2)                                                  │
│                                                                         │
│ ● stable-cam-001  Logitech HD Pro Webcam C920        Index: 0          │
│ ○ stable-cam-002  Microsoft LifeCam HD-3000          Disconnected       │
│                                                                         │
│ Last Update: 2024-01-15 14:22:35                                       │
│                                                                         │
│ Press 'q' to quit, 'r' to refresh                                      │
└─────────────────────────────────────────────────────────────────────────┘
```

## Global Options

These options are available for all commands:

### --version

Show the StableCam version and exit.

```bash
stablecam --version
```

### --help

Show help information for the command.

```bash
# Global help
stablecam --help

# Command-specific help
stablecam register --help
stablecam list --help
stablecam monitor --help
```

## Output Formats

### Table Format

Human-readable table format suitable for terminal display:

- Compact layout with essential information
- Status indicators (● ○ ⚠)
- Aligned columns for easy reading
- Summary information

### JSON Format

Machine-readable JSON format for scripting and integration:

- Complete device information
- ISO timestamp formats
- Null values for missing data
- Array of device objects

#### JSON Schema

```json
{
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "stable_id": {"type": "string"},
      "label": {"type": "string"},
      "status": {"type": "string", "enum": ["connected", "disconnected", "error"]},
      "system_index": {"type": ["integer", "null"]},
      "vendor_id": {"type": "string"},
      "product_id": {"type": "string"},
      "serial_number": {"type": ["string", "null"]},
      "port_path": {"type": ["string", "null"]},
      "registered_at": {"type": ["string", "null"], "format": "date-time"},
      "last_seen": {"type": ["string", "null"], "format": "date-time"}
    }
  }
}
```

## Examples

### Basic Workflow

```bash
# 1. Register cameras
stablecam register
# ✓ Camera registered with stable ID: stable-cam-001

# 2. Connect another camera and register it
stablecam register
# ✓ Camera registered with stable ID: stable-cam-002

# 3. List all registered cameras
stablecam list
# Shows table with both cameras

# 4. Monitor in real-time
stablecam monitor
# Opens terminal UI
```

### Scripting with JSON Output

```bash
#!/bin/bash

# Get connected cameras as JSON
cameras=$(stablecam list --format json)

# Parse with jq to get connected camera count
connected_count=$(echo "$cameras" | jq '[.[] | select(.status == "connected")] | length')

echo "Connected cameras: $connected_count"

# Get stable IDs of connected cameras
echo "$cameras" | jq -r '.[] | select(.status == "connected") | .stable_id'
```

### Python Integration

```python
import subprocess
import json

# Get device list as JSON
result = subprocess.run(['stablecam', 'list', '--format', 'json'], 
                       capture_output=True, text=True)

if result.returncode == 0:
    devices = json.loads(result.stdout)
    
    for device in devices:
        if device['status'] == 'connected':
            print(f"Camera {device['stable_id']} is ready at index {device['system_index']}")
else:
    print(f"Error: {result.stderr}")
```

### Custom Registry Management

```bash
# Project-specific camera registry
PROJECT_REGISTRY="./cameras.json"

# Register cameras for this project
stablecam register --registry-path "$PROJECT_REGISTRY"

# List project cameras
stablecam list --registry-path "$PROJECT_REGISTRY"

# Monitor project cameras
stablecam monitor --registry-path "$PROJECT_REGISTRY"
```

### Automation Scripts

#### Camera Health Check

```bash
#!/bin/bash
# check_cameras.sh - Monitor camera health

REGISTRY_PATH="./production_cameras.json"

# Get camera status
cameras=$(stablecam list --registry-path "$REGISTRY_PATH" --format json)

# Check if all required cameras are connected
required_cameras=("stable-cam-001" "stable-cam-002")

for camera_id in "${required_cameras[@]}"; do
    status=$(echo "$cameras" | jq -r ".[] | select(.stable_id == \"$camera_id\") | .status")
    
    if [ "$status" != "connected" ]; then
        echo "ALERT: Camera $camera_id is $status"
        exit 1
    fi
done

echo "All cameras are connected and ready"
```

#### Batch Registration

```bash
#!/bin/bash
# register_all_cameras.sh - Register all detected cameras

echo "Registering all detected cameras..."

while true; do
    # Try to register a camera
    if stablecam register 2>/dev/null; then
        echo "Registered a camera"
        sleep 1  # Brief pause
    else
        echo "No more cameras to register"
        break
    fi
done

echo "Registration complete"
stablecam list
```

## Troubleshooting

### Common Issues

#### Command Not Found

```bash
# Check if StableCam is installed
pip show stablecam

# Reinstall if needed
pip install --force-reinstall stablecam

# Check PATH
which stablecam
```

#### No Cameras Detected

```bash
# Enable debug output (not available in CLI, use Python)
python -c "
from stablecam import StableCam
cam = StableCam(log_level='DEBUG')
devices = cam.detect()
print(f'Found {len(devices)} devices')
"
```

#### Permission Errors

See the [Platform Guide](platform-guide.md) for platform-specific permission setup.

#### Registry Issues

```bash
# Check registry file location
ls -la ~/.stablecam/

# Reset registry (removes all registered devices)
rm ~/.stablecam/registry.json

# Use custom registry location
stablecam list --registry-path ./backup_registry.json
```

#### Terminal UI Issues

```bash
# Install TUI dependencies
pip install stablecam[tui]

# Check terminal compatibility
echo $TERM

# Try basic terminal test
python -c "from textual.app import App; print('Textual is working')"
```

### Debug Information

When reporting CLI issues, include:

```bash
# System information
uname -a
python --version
pip show stablecam

# CLI version
stablecam --version

# Test basic functionality
stablecam list --format json

# Check registry location
ls -la ~/.stablecam/
```

### Exit Codes

StableCam CLI uses standard exit codes:

- `0`: Success
- `1`: General error (no cameras, registration failed, etc.)
- `2`: Command line usage error
- `130`: Interrupted by user (Ctrl+C)

### Getting Help

For CLI-specific issues:

1. **Check Command Help**: `stablecam <command> --help`
2. **Verify Installation**: `pip show stablecam`
3. **Test Basic Detection**: Use Python API for detailed debugging
4. **Check Permissions**: See platform-specific guides
5. **Report Issues**: Include CLI output and system information

The CLI provides a convenient interface for basic StableCam operations and integrates well with shell scripts and automation workflows.