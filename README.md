# StableCam

Cross-platform USB camera monitoring with persistent anchoring.

StableCam is a Python library and terminal UI tool for managing USB cameras with stable IDs that persist across disconnections and port changes.

## Features

- Persistent stable IDs for USB cameras
- Cross-platform support (Linux, Windows, macOS)
- Real-time device monitoring and events
- Terminal UI for visual camera management
- Python API for integration into applications

## Installation

```bash
pip install stablecam
```

## Quick Start

```python
from stablecam import StableCam

# Create StableCam instance
cam = StableCam()

# Detect connected cameras
devices = cam.detect()

# Register a camera
if devices:
    stable_id = cam.register(devices[0])
    print(f"Registered camera with stable ID: {stable_id}")

# List all registered cameras
registered = cam.list()
for device in registered:
    print(f"{device.stable_id}: {device.device_info.label} ({device.status.value})")
```

## Development

This project is currently under development. See the implementation tasks in `.kiro/specs/stable-cam/tasks.md` for current progress.

## License

MIT License