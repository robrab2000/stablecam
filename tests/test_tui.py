"""
Tests for the StableCam TUI module.

This module tests the terminal user interface functionality including
device display, real-time updates, and user interactions.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from pathlib import Path

# Skip all tests if textual is not available
pytest_plugins = []
try:
    from stablecam.tui import StableCamTUI, DeviceTable, StatusBar, run_tui
    from stablecam.models import CameraDevice, RegisteredDevice, DeviceStatus
    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False


@pytest.mark.skipif(not TEXTUAL_AVAILABLE, reason="Textual not available")
class TestDeviceTable:
    """Test cases for the DeviceTable widget."""
    
    def test_device_table_initialization(self):
        """Test that DeviceTable class is properly defined."""
        from stablecam.tui import DeviceTable
        from textual.widgets import DataTable
        
        # Verify DeviceTable inherits from DataTable
        assert issubclass(DeviceTable, DataTable)
        
        # Test cursor_type and zebra_stripes are set correctly in __init__
        # We'll test this by checking the class definition rather than instantiating
        import inspect
        source = inspect.getsource(DeviceTable.__init__)
        assert 'cursor_type = "row"' in source
        assert 'zebra_stripes = True' in source


@pytest.mark.skipif(not TEXTUAL_AVAILABLE, reason="Textual not available")
class TestStatusBar:
    """Test cases for the StatusBar widget."""
    
    def test_status_bar_initialization(self):
        """Test that StatusBar class can be imported and has update_status method."""
        from stablecam.tui import StatusBar
        
        # Verify the class has the expected method
        assert hasattr(StatusBar, 'update_status')
        
        # Check that the method signature is correct
        import inspect
        sig = inspect.signature(StatusBar.update_status)
        assert 'message' in sig.parameters
    
    def test_status_bar_update(self):
        """Test StatusBar update_status method logic."""
        from stablecam.tui import StatusBar
        
        # Test the method exists and can be called
        # We can't test the actual update without an app context
        assert callable(getattr(StatusBar, 'update_status', None))


@pytest.mark.skipif(not TEXTUAL_AVAILABLE, reason="Textual not available")
class TestStableCamTUI:
    """Test cases for the main StableCamTUI application."""
    
    @pytest.fixture
    def mock_manager(self):
        """Create a mock StableCam manager."""
        manager = Mock()
        manager.list.return_value = []
        manager.detect.return_value = []
        manager.register.return_value = "stable-cam-001"
        manager.run.return_value = None
        manager.stop.return_value = None
        manager.on.return_value = None
        return manager
    
    @pytest.fixture
    def sample_devices(self):
        """Create sample device data for testing."""
        device1 = CameraDevice(
            system_index=0,
            vendor_id="046d",
            product_id="085b",
            serial_number="ABC123",
            port_path="/dev/usb1/1-1",
            label="Logitech C920 HD Pro Webcam",
            platform_data={}
        )
        
        device2 = CameraDevice(
            system_index=1,
            vendor_id="0c45",
            product_id="6366",
            serial_number=None,
            port_path="/dev/usb1/1-2",
            label="Generic USB Camera",
            platform_data={}
        )
        
        registered1 = RegisteredDevice(
            stable_id="stable-cam-001",
            device_info=device1,
            status=DeviceStatus.CONNECTED,
            registered_at=datetime.now(),
            last_seen=datetime.now()
        )
        
        registered2 = RegisteredDevice(
            stable_id="stable-cam-002",
            device_info=device2,
            status=DeviceStatus.DISCONNECTED,
            registered_at=datetime.now(),
            last_seen=None
        )
        
        return [registered1, registered2]
    
    def test_tui_initialization(self, mock_manager):
        """Test TUI initialization with custom registry path."""
        registry_path = "/custom/path/registry.json"
        
        with patch('stablecam.tui.StableCam') as mock_stablecam_class:
            mock_stablecam_class.return_value = mock_manager
            
            tui = StableCamTUI(registry_path=registry_path)
            
            assert tui.registry_path == registry_path
            assert tui.manager is None  # Not initialized until mount
            assert tui.devices == []
    
    @patch('stablecam.tui.StableCam')
    def test_tui_mount_initialization(self, mock_stablecam_class, mock_manager):
        """Test TUI mount process and manager initialization."""
        mock_stablecam_class.return_value = mock_manager
        
        tui = StableCamTUI()
        
        # Simulate mount process
        with patch.object(tui, 'set_interval') as mock_set_interval:
            with patch.object(tui, '_refresh_devices') as mock_refresh:
                with patch.object(tui, '_update_status') as mock_update_status:
                    # Call on_mount directly since we can't easily test the async mount
                    import asyncio
                    asyncio.run(tui.on_mount())
        
        # Verify manager was initialized and configured
        mock_stablecam_class.assert_called_once_with(registry_path=None)
        mock_manager.on.assert_called()  # Event handlers should be set up
        mock_manager.run.assert_called_once()  # Monitoring should start
    
    def test_get_status_display(self, mock_manager):
        """Test status display formatting for different device states."""
        tui = StableCamTUI()
        
        # Test connected device
        connected_device = Mock()
        connected_device.status = DeviceStatus.CONNECTED
        indicator, css_class = tui._get_status_display(connected_device)
        assert indicator == "● Online"
        assert css_class == "connected"
        
        # Test disconnected device
        disconnected_device = Mock()
        disconnected_device.status = DeviceStatus.DISCONNECTED
        indicator, css_class = tui._get_status_display(disconnected_device)
        assert indicator == "○ Offline"
        assert css_class == "disconnected"
        
        # Test error device
        error_device = Mock()
        error_device.status = DeviceStatus.ERROR
        indicator, css_class = tui._get_status_display(error_device)
        assert indicator == "✗ Error"
        assert css_class == "error"
    
    def test_recent_change_tracking(self, mock_manager):
        """Test tracking of recent device status changes."""
        tui = StableCamTUI()
        
        stable_id = "stable-cam-001"
        
        # Initially no recent changes
        assert not tui._is_recent_change(stable_id)
        
        # Mark as recent change
        tui._mark_recent_change(stable_id)
        assert tui._is_recent_change(stable_id)
        
        # Simulate time passing (mock datetime)
        with patch('stablecam.tui.datetime') as mock_datetime:
            # Get the original time and add 6 seconds using timedelta
            from datetime import timedelta
            original_time = tui._recent_changes[stable_id]
            future_time = original_time + timedelta(seconds=6)
            mock_datetime.now.return_value = future_time
            
            # Should no longer be recent (>5 seconds)
            assert not tui._is_recent_change(stable_id)
    
    @patch('stablecam.tui.StableCam')
    def test_refresh_devices(self, mock_stablecam_class, mock_manager, sample_devices):
        """Test device list refresh functionality."""
        mock_stablecam_class.return_value = mock_manager
        mock_manager.list.return_value = sample_devices
        
        tui = StableCamTUI()
        tui.manager = mock_manager
        
        # Mock the table update method
        with patch.object(tui, '_update_device_table') as mock_update_table:
            with patch.object(tui, '_update_status') as mock_update_status:
                import asyncio
                asyncio.run(tui._refresh_devices())
        
        # Verify devices were loaded
        assert len(tui.devices) == 2
        assert tui.device_count == 2
        assert tui.connected_count == 1  # Only one connected device
        
        # Verify table was updated
        mock_update_table.assert_called_once()
        mock_update_status.assert_called()
    
    @patch('stablecam.tui.StableCam')
    def test_register_new_device(self, mock_stablecam_class, mock_manager):
        """Test registering a new device through the TUI."""
        # Set up mock data
        new_device = CameraDevice(
            system_index=2,
            vendor_id="1234",
            product_id="5678",
            serial_number="NEW123",
            port_path="/dev/usb1/1-3",
            label="New Camera",
            platform_data={}
        )
        
        mock_stablecam_class.return_value = mock_manager
        mock_manager.detect.return_value = [new_device]
        mock_manager.register.return_value = "stable-cam-003"
        
        tui = StableCamTUI()
        tui.manager = mock_manager
        tui.devices = []  # No existing devices
        
        with patch.object(tui, '_refresh_devices') as mock_refresh:
            with patch.object(tui, '_update_status') as mock_update_status:
                import asyncio
                asyncio.run(tui._register_new_device())
        
        # Verify registration was attempted
        mock_manager.detect.assert_called_once()
        mock_manager.register.assert_called_once_with(new_device)
        mock_refresh.assert_called_once()
    
    @patch('stablecam.tui.StableCam')
    def test_register_no_new_devices(self, mock_stablecam_class, mock_manager, sample_devices):
        """Test registration when no new devices are available."""
        # Mock detection returning already registered device
        existing_device = sample_devices[0].device_info
        
        mock_stablecam_class.return_value = mock_manager
        mock_manager.detect.return_value = [existing_device]
        
        tui = StableCamTUI()
        tui.manager = mock_manager
        tui.devices = sample_devices  # Existing registered devices
        
        with patch.object(tui, '_update_status') as mock_update_status:
            import asyncio
            asyncio.run(tui._register_new_device())
        
        # Should not attempt registration
        mock_manager.register.assert_not_called()
        mock_update_status.assert_called_with("All detected cameras are already registered")
    
    def test_event_handlers(self, mock_manager):
        """Test device event handlers."""
        tui = StableCamTUI()
        
        device = Mock()
        device.stable_id = "stable-cam-001"
        
        # Test connect event
        tui._on_device_connect(device)
        assert tui._is_recent_change("stable-cam-001")
        
        # Test disconnect event
        tui._on_device_disconnect(device)
        assert tui._is_recent_change("stable-cam-001")
        
        # Test status change event
        tui._on_device_status_change(device)
        assert tui._is_recent_change("stable-cam-001")


@pytest.mark.skipif(not TEXTUAL_AVAILABLE, reason="Textual not available")
def test_run_tui_function():
    """Test the run_tui function."""
    with patch('stablecam.tui.StableCamTUI') as mock_tui_class:
        mock_app = Mock()
        mock_tui_class.return_value = mock_app
        
        registry_path = "/test/path"
        run_tui(registry_path=registry_path)
        
        # Verify TUI was created with correct path and run
        mock_tui_class.assert_called_once_with(registry_path=registry_path)
        mock_app.run.assert_called_once()


@pytest.mark.skipif(TEXTUAL_AVAILABLE, reason="Testing import error handling")
def test_tui_import_error():
    """Test handling when textual is not available."""
    # This test only runs when textual is NOT available
    # Since textual is available, this test is skipped
    pass


class TestTUIIntegration:
    """Integration tests for TUI functionality."""
    
    @pytest.mark.skipif(not TEXTUAL_AVAILABLE, reason="Textual not available")
    def test_tui_css_classes(self):
        """Test that CSS classes are properly defined."""
        tui = StableCamTUI()
        
        # Verify CSS contains expected classes
        css = tui.CSS
        assert ".connected" in css
        assert ".disconnected" in css
        assert ".error" in css
        assert ".highlight" in css
        assert ".device-table" in css
        assert ".status-bar" in css
    
    @pytest.mark.skipif(not TEXTUAL_AVAILABLE, reason="Textual not available")
    def test_tui_title_and_subtitle(self):
        """Test TUI title and subtitle are set correctly."""
        tui = StableCamTUI()
        
        assert tui.TITLE == "StableCam - USB Camera Monitor"
        assert tui.SUB_TITLE == "Real-time camera monitoring with stable IDs"
    
    @pytest.mark.skipif(not TEXTUAL_AVAILABLE, reason="Textual not available")
    @patch('stablecam.tui.StableCam')
    def test_tui_cleanup_on_unmount(self, mock_stablecam_class):
        """Test proper cleanup when TUI is unmounted."""
        mock_manager = Mock()
        mock_stablecam_class.return_value = mock_manager
        
        tui = StableCamTUI()
        tui.manager = mock_manager
        
        # Mock timer
        mock_timer = Mock()
        tui.update_timer = mock_timer
        
        # Test unmount
        import asyncio
        asyncio.run(tui.on_unmount())
        
        # Verify cleanup
        mock_timer.stop.assert_called_once()
        mock_manager.stop.assert_called_once()