# Implementation Plan

- [x] 1. Set up project structure and core data models
  - Create package directory structure with `stablecam/` module
  - Define core data classes: `CameraDevice`, `RegisteredDevice`, `DeviceStatus`
  - Implement hardware identifier generation logic
  - Write unit tests for data models and identifier generation
  - _Requirements: 1.1, 1.2, 7.1, 7.2, 7.3_

- [x] 2. Implement device registry with persistent storage
  - Create `DeviceRegistry` class with JSON-based persistence
  - Implement device registration, lookup, and status update methods
  - Add file locking and atomic write operations for registry safety
  - Write unit tests for registry operations and persistence
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ] 3. Create platform detection backend interfaces
  - Define abstract `PlatformBackend` base class
  - Create `DeviceDetector` class that manages platform backends
  - Implement backend selection logic based on current platform
  - Write unit tests with mock backends for cross-platform testing
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [ ] 4. Implement Linux camera detection backend
  - Create `LinuxBackend` class using v4l2 and udev libraries
  - Implement camera enumeration via `/dev/video*` devices
  - Extract vendor ID, product ID, serial number, and port path
  - Write unit tests with mocked v4l2/udev responses
  - _Requirements: 5.1, 1.1, 1.4_

- [ ] 5. Implement Windows camera detection backend
  - Create `WindowsBackend` class using Windows Media Foundation APIs
  - Implement camera enumeration and hardware info extraction
  - Handle Windows-specific device identifiers and paths
  - Write unit tests with mocked WMF responses
  - _Requirements: 5.2, 1.1, 1.4_

- [ ] 6. Implement macOS camera detection backend
  - Create `MacOSBackend` class using AVFoundation and IOKit
  - Implement camera enumeration and hardware info extraction
  - Handle macOS-specific device identifiers and paths
  - Write unit tests with mocked AVFoundation responses
  - _Requirements: 5.3, 1.1, 1.4_

- [ ] 7. Create event management system
  - Implement `EventManager` class with subscribe/unsubscribe methods
  - Add event types: `on_connect`, `on_disconnect`, `on_status_change`
  - Implement thread-safe event emission and callback execution
  - Write unit tests for event subscription and emission
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [ ] 8. Implement core StableCam manager class
  - Create `StableCam` class integrating detector, registry, and events
  - Implement `detect()`, `register()`, `list()`, and `get_by_id()` methods
  - Add device monitoring loop with continuous detection
  - Write integration tests for manager functionality
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [ ] 9. Add real-time monitoring and event triggering
  - Implement `run()` method with background monitoring thread
  - Add logic to detect device connections and disconnections
  - Trigger appropriate events when device status changes
  - Write tests for monitoring loop and event triggering
  - _Requirements: 3.5, 3.2, 3.3, 3.4_

- [ ] 10. Create CLI command interface
  - Implement CLI entry point using `click` or `argparse`
  - Add `register` command to register first detected camera
  - Add `list` command to display all registered devices
  - Write tests for CLI command parsing and execution
  - _Requirements: 4.5, 2.2, 2.4_

- [ ] 11. Implement terminal UI using Textual framework
  - Create main TUI application class with device list display
  - Implement real-time updates showing stable IDs and system indexes
  - Add visual indicators for connection/disconnection events
  - Show disconnected devices with appropriate status indicators
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [ ] 12. Add comprehensive error handling and logging
  - Implement error handling for platform detection failures
  - Add graceful handling of registry file corruption and recovery
  - Create logging configuration with appropriate log levels
  - Write tests for error scenarios and recovery mechanisms
  - _Requirements: 6.5, 7.4, 5.5_

- [ ] 13. Create package configuration and dependencies
  - Write `setup.py` or `pyproject.toml` with platform-specific dependencies
  - Configure entry points for CLI tool installation
  - Add platform detection for conditional dependency installation
  - Test package installation on different platforms
  - _Requirements: 5.5_

- [ ] 14. Write comprehensive integration tests
  - Create end-to-end tests simulating device connection scenarios
  - Test cross-platform compatibility with CI/CD pipeline
  - Add performance tests for multi-device detection
  - Test TUI functionality with Textual testing framework
  - _Requirements: 1.3, 2.5, 3.5, 4.1_

- [ ] 15. Add documentation and examples
  - Write API documentation with usage examples
  - Create README with installation and usage instructions
  - Add example scripts demonstrating library integration
  - Document platform-specific requirements and troubleshooting
  - _Requirements: 2.1, 4.5_