# Requirements Document

## Introduction

StableCam is a cross-platform Python library and optional terminal UI (TUI) tool for monitoring and managing USB cameras with persistent anchoring. The system solves the common problem where multiple cameras' device indexes change when they're unplugged and replugged into different ports. StableCam ensures each camera is assigned a persistent, stable ID (anchor) based on its unique hardware identifier, maintaining device visibility even when disconnected.

## Requirements

### Requirement 1

**User Story:** As a developer working with multiple USB cameras, I want to assign persistent stable IDs to my cameras, so that I can reliably reference them regardless of connection order or port changes.

#### Acceptance Criteria

1. WHEN a USB camera is first detected THEN the system SHALL extract unique hardware identifiers (serial number, vendor/product ID, or port path)
2. WHEN a camera is registered THEN the system SHALL assign it a persistent stable ID that remains constant across disconnections
3. WHEN a camera is reconnected to a different port THEN the system SHALL maintain the same stable ID based on hardware identifiers
4. IF a camera lacks a serial number THEN the system SHALL use vendor/product ID and port path as fallback identifiers

### Requirement 2

**User Story:** As a developer, I want a Python library API for integrating stable camera mapping into my applications, so that I can build reliable multi-camera systems.

#### Acceptance Criteria

1. WHEN using the library API THEN the system SHALL provide methods to detect, register, and query cameras
2. WHEN calling detect() THEN the system SHALL return a list of currently connected USB cameras
3. WHEN calling register(device) THEN the system SHALL assign and return a stable ID for the device
4. WHEN calling list() THEN the system SHALL return all registered devices with their stable IDs and current status
5. WHEN a device status changes THEN the system SHALL update the device status in the registry

### Requirement 3

**User Story:** As a developer, I want to subscribe to camera connection events, so that my application can respond to camera state changes in real-time.

#### Acceptance Criteria

1. WHEN subscribing to events THEN the system SHALL support on_connect, on_disconnect, and on_status_change event types
2. WHEN a camera is connected THEN the system SHALL trigger on_connect events for registered listeners
3. WHEN a camera is disconnected THEN the system SHALL trigger on_disconnect events for registered listeners
4. WHEN a camera status changes THEN the system SHALL trigger on_status_change events with the updated device information
5. WHEN run() is called THEN the system SHALL start a monitoring loop that continuously detects device changes

### Requirement 4

**User Story:** As a user, I want a terminal UI tool for monitoring cameras, so that I can visually track camera connections and manage my setup without writing code.

#### Acceptance Criteria

1. WHEN running the CLI tool THEN the system SHALL display a live list of all registered cameras
2. WHEN displaying camera information THEN the system SHALL show stable IDs alongside system device indexes
3. WHEN a camera connects or disconnects THEN the system SHALL provide visual alerts in the interface
4. WHEN a camera is disconnected THEN the system SHALL keep the device visible in the list with disconnected status
5. WHEN using the register command THEN the system SHALL register the first detected camera and display confirmation

### Requirement 5

**User Story:** As a developer, I want cross-platform support, so that I can use StableCam on Linux, Windows, and macOS systems.

#### Acceptance Criteria

1. WHEN running on Linux THEN the system SHALL detect USB cameras using appropriate Linux APIs
2. WHEN running on Windows THEN the system SHALL detect USB cameras using appropriate Windows APIs  
3. WHEN running on macOS THEN the system SHALL detect USB cameras using appropriate macOS APIs
4. WHEN extracting device identifiers THEN the system SHALL use platform-appropriate methods for each operating system
5. WHEN installing via pip THEN the system SHALL work on all supported platforms without additional configuration

### Requirement 6

**User Story:** As a user, I want persistent device registry, so that my camera configurations are maintained across application restarts and system reboots.

#### Acceptance Criteria

1. WHEN a device is registered THEN the system SHALL store the device information persistently to disk
2. WHEN the application starts THEN the system SHALL load previously registered devices from persistent storage
3. WHEN a registered device is disconnected THEN the system SHALL maintain the device in the registry with disconnected status
4. WHEN the registry is updated THEN the system SHALL automatically save changes to persistent storage
5. IF the registry file is corrupted THEN the system SHALL handle the error gracefully and create a new registry

### Requirement 7

**User Story:** As a developer, I want reliable device identification, so that cameras are correctly matched to their stable IDs even after hardware changes.

#### Acceptance Criteria

1. WHEN multiple identification methods are available THEN the system SHALL prioritize serial number over other identifiers
2. WHEN a serial number is not available THEN the system SHALL use vendor ID and product ID combination
3. WHEN vendor/product ID is insufficient THEN the system SHALL include port path information as additional identifier
4. WHEN a device identifier conflicts with existing registry THEN the system SHALL handle the conflict and provide clear error messaging
5. WHEN device hardware changes significantly THEN the system SHALL treat it as a new device requiring re-registration