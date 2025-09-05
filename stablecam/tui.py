"""
Terminal User Interface for StableCam using Textual framework.

This module provides a real-time TUI for monitoring USB cameras with
stable IDs, showing connection status, and providing visual indicators
for device state changes.
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
    Header, Footer, DataTable, Static, Button, Label, 
    ProgressBar, Placeholder
)
from textual.reactive import reactive
from textual.message import Message
from textual.timer import Timer
from textual import events
from textual.coordinate import Coordinate

from .manager import StableCam
from .models import RegisteredDevice, DeviceStatus
from .backends import PlatformDetectionError
from .registry import RegistryError

logger = logging.getLogger(__name__)


class DeviceTable(DataTable):
    """Custom DataTable widget for displaying camera devices."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cursor_type = "row"
        self.zebra_stripes = True
        
        # Add columns
        self.add_column("Status", width=10)
        self.add_column("Stable ID", width=15)
        self.add_column("System Index", width=12)
        self.add_column("Label", width=30)
        self.add_column("Last Seen", width=20)


class StatusBar(Static):
    """Status bar showing connection information and last update time."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.update_status("Initializing...")
    
    def update_status(self, message: str):
        """Update the status message."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.update(f"[dim]{timestamp}[/dim] {message}")


class StableCamTUI(App):
    """
    Main TUI application for StableCam device monitoring.
    
    Provides real-time display of registered cameras with their stable IDs,
    connection status, and visual indicators for state changes.
    """
    
    CSS = """
    Screen {
        background: $background;
    }
    
    .header {
        dock: top;
        height: 3;
        background: $primary;
        color: $text;
    }
    
    .main-container {
        height: 1fr;
        margin: 1;
    }
    
    .device-table {
        height: 1fr;
        border: solid $primary;
        margin-bottom: 1;
    }
    
    .status-bar {
        dock: bottom;
        height: 1;
        background: $surface;
        color: $text;
        padding: 0 1;
    }
    
    .controls {
        height: 3;
        background: $surface;
        padding: 1;
    }
    
    .connected {
        color: $success;
    }
    
    .disconnected {
        color: $warning;
    }
    
    .error {
        color: $error;
    }
    
    .highlight {
        background: $accent;
        color: $text;
    }
    """
    
    TITLE = "StableCam - USB Camera Monitor"
    SUB_TITLE = "Real-time camera monitoring with stable IDs"
    
    # Reactive attributes
    device_count: reactive[int] = reactive(0)
    connected_count: reactive[int] = reactive(0)
    last_update: reactive[str] = reactive("")
    
    def __init__(self, registry_path: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.registry_path = registry_path
        self.manager: Optional[StableCam] = None
        self.update_timer: Optional[Timer] = None
        self.devices: List[RegisteredDevice] = []
        
        # Track device changes for visual indicators
        self._last_device_states: dict[str, DeviceStatus] = {}
        self._recent_changes: dict[str, datetime] = {}
    
    def compose(self) -> ComposeResult:
        """Compose the TUI layout."""
        yield Header(show_clock=True)
        
        with Container(classes="main-container"):
            with Vertical():
                # Device table
                yield DeviceTable(id="device-table", classes="device-table")
                
                # Controls
                with Horizontal(classes="controls"):
                    yield Button("Refresh", id="refresh-btn", variant="primary")
                    yield Button("Register New", id="register-btn", variant="success")
                    yield Button("Quit", id="quit-btn", variant="error")
        
        yield StatusBar(classes="status-bar", id="status-bar")
        yield Footer()
    
    async def on_mount(self) -> None:
        """Initialize the application when mounted."""
        try:
            # Initialize StableCam manager
            self.manager = StableCam(registry_path=self.registry_path)
            
            # Set up event handlers
            self.manager.on("on_connect", self._on_device_connect)
            self.manager.on("on_disconnect", self._on_device_disconnect)
            self.manager.on("on_status_change", self._on_device_status_change)
            
            # Start monitoring
            self.manager.run()
            
            # Initial device load
            await self._refresh_devices()
            
            # Set up periodic updates
            self.update_timer = self.set_interval(2.0, self._refresh_devices)
            
            self._update_status("Monitoring started")
            
        except Exception as e:
            logger.error(f"Failed to initialize TUI: {e}")
            self._update_status(f"Error: {e}")
    
    async def on_unmount(self) -> None:
        """Cleanup when application is unmounted."""
        if self.update_timer:
            self.update_timer.stop()
        
        if self.manager:
            self.manager.stop()
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "refresh-btn":
            await self._refresh_devices()
        elif event.button.id == "register-btn":
            await self._register_new_device()
        elif event.button.id == "quit-btn":
            self.exit()
    
    async def on_key(self, event: events.Key) -> None:
        """Handle key press events."""
        if event.key == "r":
            await self._refresh_devices()
        elif event.key == "n":
            await self._register_new_device()
        elif event.key == "q":
            self.exit()
    
    async def _refresh_devices(self) -> None:
        """Refresh the device list and update the table."""
        if not self.manager:
            return
        
        try:
            # Get all registered devices
            self.devices = self.manager.list()
            
            # Update reactive attributes
            self.device_count = len(self.devices)
            self.connected_count = sum(1 for d in self.devices if d.status == DeviceStatus.CONNECTED)
            self.last_update = datetime.now().strftime("%H:%M:%S")
            
            # Update the table
            await self._update_device_table()
            
            # Update status
            status_msg = f"Devices: {self.device_count} total, {self.connected_count} connected"
            self._update_status(status_msg)
            
        except Exception as e:
            logger.error(f"Error refreshing devices: {e}")
            self._update_status(f"Refresh error: {e}")
    
    async def _update_device_table(self) -> None:
        """Update the device table with current device information."""
        table = self.query_one("#device-table", DeviceTable)
        
        # Clear existing rows
        table.clear()
        
        # Add device rows
        for device in self.devices:
            # Determine status indicator and styling
            status_indicator, status_class = self._get_status_display(device)
            
            # Format last seen time
            last_seen = "Never"
            if device.last_seen:
                last_seen = device.last_seen.strftime("%m/%d %H:%M:%S")
            elif device.status == DeviceStatus.CONNECTED:
                last_seen = "Now"
            
            # System index display
            system_index = str(device.device_info.system_index) if device.device_info.system_index is not None else "N/A"
            
            # Check if this device had a recent status change
            is_recent_change = self._is_recent_change(device.stable_id)
            
            # Add row with appropriate styling
            row_data = [
                status_indicator,
                device.stable_id,
                system_index,
                device.device_info.label,
                last_seen
            ]
            
            row_key = table.add_row(*row_data)
            
            # Apply styling based on status and recent changes
            if is_recent_change:
                # Highlight recent changes
                table.add_class("highlight", row_key)
            
            # Update last known state
            self._last_device_states[device.stable_id] = device.status
    
    def _get_status_display(self, device: RegisteredDevice) -> tuple[str, str]:
        """Get status indicator and CSS class for a device."""
        if device.status == DeviceStatus.CONNECTED:
            return "● Online", "connected"
        elif device.status == DeviceStatus.DISCONNECTED:
            return "○ Offline", "disconnected"
        else:
            return "✗ Error", "error"
    
    def _is_recent_change(self, stable_id: str) -> bool:
        """Check if a device had a recent status change (within last 5 seconds)."""
        if stable_id in self._recent_changes:
            time_diff = datetime.now() - self._recent_changes[stable_id]
            return time_diff.total_seconds() < 5.0
        return False
    
    def _mark_recent_change(self, stable_id: str) -> None:
        """Mark a device as having a recent status change."""
        self._recent_changes[stable_id] = datetime.now()
    
    async def _register_new_device(self) -> None:
        """Register a new detected camera device."""
        if not self.manager:
            return
        
        try:
            self._update_status("Detecting cameras...")
            
            # Detect cameras
            detected = self.manager.detect()
            
            if not detected:
                self._update_status("No cameras detected")
                return
            
            # Find unregistered devices
            registered_hw_ids = {d.get_hardware_id() for d in self.devices}
            unregistered = [d for d in detected if d.generate_hardware_id() not in registered_hw_ids]
            
            if not unregistered:
                self._update_status("All detected cameras are already registered")
                return
            
            # Register the first unregistered device
            device = unregistered[0]
            stable_id = self.manager.register(device)
            
            self._update_status(f"Registered new device: {stable_id}")
            
            # Refresh the display
            await self._refresh_devices()
            
        except PlatformDetectionError as e:
            self._update_status(f"Detection failed: {e}")
        except RegistryError as e:
            self._update_status(f"Registration failed: {e}")
        except Exception as e:
            logger.error(f"Error registering device: {e}")
            self._update_status(f"Registration error: {e}")
    
    def _update_status(self, message: str) -> None:
        """Update the status bar message."""
        try:
            status_bar = self.query_one("#status-bar", StatusBar)
            status_bar.update_status(message)
        except Exception:
            # Status bar might not be available yet
            pass
    
    def _on_device_connect(self, device: RegisteredDevice) -> None:
        """Handle device connection event."""
        self._mark_recent_change(device.stable_id)
        logger.info(f"Device connected: {device.stable_id}")
    
    def _on_device_disconnect(self, device: RegisteredDevice) -> None:
        """Handle device disconnection event."""
        self._mark_recent_change(device.stable_id)
        logger.info(f"Device disconnected: {device.stable_id}")
    
    def _on_device_status_change(self, device: RegisteredDevice) -> None:
        """Handle device status change event."""
        self._mark_recent_change(device.stable_id)
        logger.debug(f"Device status changed: {device.stable_id} -> {device.status}")


def run_tui(registry_path: Optional[str] = None) -> None:
    """
    Run the StableCam TUI application.
    
    Args:
        registry_path: Optional custom path for the device registry file
    """
    app = StableCamTUI(registry_path=registry_path)
    app.run()


if __name__ == "__main__":
    run_tui()