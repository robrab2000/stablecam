#!/usr/bin/env python3
"""
StableCam Integration Example

This example demonstrates how to integrate StableCam into a larger application,
such as a video recording system or streaming application.
"""

import time
import threading
from typing import Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime
from stablecam import StableCam, RegisteredDevice, DeviceStatus


@dataclass
class RecordingSession:
    """Represents an active recording session."""
    camera_id: str
    start_time: datetime
    output_file: str
    active: bool = True


class VideoRecordingApp:
    """
    Example video recording application that uses StableCam for camera management.
    
    This demonstrates how StableCam can be integrated into a real application
    to provide stable camera references that persist across hardware changes.
    """
    
    def __init__(self):
        # Initialize StableCam with custom settings
        self.cam = StableCam(
            poll_interval=1.0,  # Check for changes every second
            log_level="WARNING"  # Reduce log noise in production app
        )
        
        # Application state
        self.active_recordings: Dict[str, RecordingSession] = {}
        self.camera_preferences: Dict[str, dict] = {}
        self.app_running = False
        
        # Set up StableCam event handlers
        self.cam.on('on_connect', self.on_camera_available)
        self.cam.on('on_disconnect', self.on_camera_unavailable)
        
        print("Video Recording Application initialized")
    
    def on_camera_available(self, device: RegisteredDevice):
        """Handle camera becoming available."""
        print(f"📷 Camera available: {device.stable_id}")
        
        # Check if this camera was being used for recording
        if device.stable_id in self.active_recordings:
            session = self.active_recordings[device.stable_id]
            if not session.active:
                print(f"   Resuming recording session: {session.output_file}")
                self.resume_recording(device.stable_id)
        
        # Apply saved preferences if any
        if device.stable_id in self.camera_preferences:
            prefs = self.camera_preferences[device.stable_id]
            print(f"   Applying saved preferences: {prefs}")
            self.apply_camera_preferences(device.stable_id, prefs)
    
    def on_camera_unavailable(self, device: RegisteredDevice):
        """Handle camera becoming unavailable."""
        print(f"📷 Camera unavailable: {device.stable_id}")
        
        # Pause any active recording
        if device.stable_id in self.active_recordings:
            session = self.active_recordings[device.stable_id]
            if session.active:
                print(f"   Pausing recording session: {session.output_file}")
                self.pause_recording(device.stable_id)
    
    def discover_and_setup_cameras(self):
        """Discover and set up cameras for the application."""
        print("\nDiscovering cameras...")
        
        try:
            # Detect currently connected cameras
            devices = self.cam.detect()
            print(f"Found {len(devices)} connected cameras")
            
            # Register any new cameras
            for device in devices:
                try:
                    stable_id = self.cam.register(device)
                    print(f"  Camera ready: {stable_id} ({device.label})")
                    
                    # Set up default preferences for new cameras
                    self.setup_default_preferences(stable_id, device)
                    
                except Exception as e:
                    print(f"  Failed to register {device.label}: {e}")
            
            # Show all registered cameras
            registered = self.cam.list()
            print(f"\nTotal registered cameras: {len(registered)}")
            
            for device in registered:
                status = "Available" if device.is_connected() else "Unavailable"
                print(f"  {device.stable_id}: {status}")
                
        except Exception as e:
            print(f"Error during camera discovery: {e}")
    
    def setup_default_preferences(self, stable_id: str, device):
        """Set up default preferences for a camera."""
        # Example preferences based on camera type
        preferences = {
            "resolution": "1920x1080",
            "framerate": 30,
            "format": "mjpeg"
        }
        
        # Customize based on device characteristics
        if "logitech" in device.label.lower():
            preferences["format"] = "h264"
        elif "microsoft" in device.label.lower():
            preferences["resolution"] = "1280x720"
        
        self.camera_preferences[stable_id] = preferences
        print(f"    Set default preferences for {stable_id}: {preferences}")
    
    def apply_camera_preferences(self, stable_id: str, preferences: dict):
        """Apply preferences to a camera (simulated)."""
        # In a real application, this would configure the actual camera
        print(f"    Applying preferences to {stable_id}:")
        for key, value in preferences.items():
            print(f"      {key}: {value}")
    
    def start_recording(self, stable_id: str, output_file: str) -> bool:
        """Start recording from a specific camera."""
        device = self.cam.get_by_id(stable_id)
        
        if not device:
            print(f"❌ Camera {stable_id} not found")
            return False
        
        if not device.is_connected():
            print(f"❌ Camera {stable_id} is not connected")
            return False
        
        if stable_id in self.active_recordings:
            print(f"❌ Camera {stable_id} is already recording")
            return False
        
        # Create recording session
        session = RecordingSession(
            camera_id=stable_id,
            start_time=datetime.now(),
            output_file=output_file,
            active=True
        )
        
        self.active_recordings[stable_id] = session
        
        # In a real application, this would start actual video capture
        print(f"🎬 Started recording from {stable_id} to {output_file}")
        print(f"    System index: {device.device_info.system_index}")
        
        return True
    
    def stop_recording(self, stable_id: str) -> bool:
        """Stop recording from a specific camera."""
        if stable_id not in self.active_recordings:
            print(f"❌ No active recording for camera {stable_id}")
            return False
        
        session = self.active_recordings[stable_id]
        session.active = False
        
        duration = datetime.now() - session.start_time
        print(f"⏹️  Stopped recording from {stable_id}")
        print(f"    Duration: {duration.total_seconds():.1f} seconds")
        print(f"    Output: {session.output_file}")
        
        del self.active_recordings[stable_id]
        return True
    
    def pause_recording(self, stable_id: str):
        """Pause recording (camera disconnected)."""
        if stable_id in self.active_recordings:
            session = self.active_recordings[stable_id]
            session.active = False
            print(f"⏸️  Paused recording from {stable_id} (camera disconnected)")
    
    def resume_recording(self, stable_id: str):
        """Resume recording (camera reconnected)."""
        if stable_id in self.active_recordings:
            session = self.active_recordings[stable_id]
            session.active = True
            print(f"▶️  Resumed recording from {stable_id} (camera reconnected)")
    
    def list_cameras(self):
        """List all cameras and their status."""
        print("\nCamera Status:")
        print("-" * 40)
        
        registered = self.cam.list()
        
        if not registered:
            print("No cameras registered")
            return
        
        for device in registered:
            status_icon = "🟢" if device.is_connected() else "🔴"
            recording_icon = "🎬" if device.stable_id in self.active_recordings else "  "
            
            print(f"{status_icon} {recording_icon} {device.stable_id}")
            print(f"    Device: {device.device_info.label}")
            print(f"    Status: {device.status.value}")
            
            if device.is_connected():
                print(f"    System Index: {device.device_info.system_index}")
            
            if device.stable_id in self.active_recordings:
                session = self.active_recordings[device.stable_id]
                duration = datetime.now() - session.start_time
                status = "Active" if session.active else "Paused"
                print(f"    Recording: {status} ({duration.total_seconds():.1f}s)")
                print(f"    Output: {session.output_file}")
            
            print()
    
    def run_demo(self):
        """Run a demonstration of the application."""
        print("Starting Video Recording Application Demo")
        print("=" * 50)
        
        # Start StableCam monitoring
        self.cam.run()
        self.app_running = True
        
        try:
            # Discover and set up cameras
            self.discover_and_setup_cameras()
            
            # Show initial status
            self.list_cameras()
            
            # Get available cameras for demo
            available_cameras = [
                device for device in self.cam.list() 
                if device.is_connected()
            ]
            
            if available_cameras:
                # Start recording from first available camera
                camera = available_cameras[0]
                output_file = f"recording_{camera.stable_id}_{int(time.time())}.mp4"
                
                print(f"\nStarting demo recording...")
                if self.start_recording(camera.stable_id, output_file):
                    
                    # Monitor for 15 seconds
                    print("\nMonitoring recording (15 seconds)...")
                    print("Try disconnecting/reconnecting the camera to see resilience.")
                    
                    for i in range(15):
                        time.sleep(1)
                        if i % 5 == 4:  # Status update every 5 seconds
                            print(f"\n--- Status Update ({i + 1}s) ---")
                            self.list_cameras()
                    
                    # Stop recording
                    print(f"\nStopping demo recording...")
                    self.stop_recording(camera.stable_id)
                
            else:
                print("\nNo cameras available for demo recording")
                print("Monitoring for camera connections (10 seconds)...")
                
                for i in range(10):
                    time.sleep(1)
                    if i % 3 == 2:
                        available = [d for d in self.cam.list() if d.is_connected()]
                        if available:
                            print(f"Camera became available: {available[0].stable_id}")
                            break
            
            print("\nDemo completed!")
            
        except KeyboardInterrupt:
            print("\nDemo interrupted by user")
        
        finally:
            # Clean up
            print("\nCleaning up...")
            
            # Stop any active recordings
            for stable_id in list(self.active_recordings.keys()):
                self.stop_recording(stable_id)
            
            # Stop monitoring
            self.cam.stop()
            self.app_running = False
            
            print("Application shutdown complete")


def main():
    """Run the integration example."""
    app = VideoRecordingApp()
    app.run_demo()


if __name__ == "__main__":
    main()