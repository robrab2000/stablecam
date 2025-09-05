#!/usr/bin/env python3
"""
StableCam Event Monitoring Example

This example demonstrates real-time monitoring of camera connections
and disconnections using StableCam's event system.
"""

import time
import signal
import sys
from datetime import datetime
from stablecam import StableCam, RegisteredDevice


class CameraMonitor:
    """Example camera monitoring application."""
    
    def __init__(self):
        self.cam = StableCam(log_level="INFO")
        self.running = False
        
        # Set up event handlers
        self.cam.on('on_connect', self.on_camera_connect)
        self.cam.on('on_disconnect', self.on_camera_disconnect)
        self.cam.on('on_status_change', self.on_status_change)
        
        # Set up signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def on_camera_connect(self, device: RegisteredDevice):
        """Handle camera connection events."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] 🟢 CONNECTED: {device.stable_id}")
        print(f"    Device: {device.device_info.label}")
        print(f"    System Index: {device.device_info.system_index}")
        print()
    
    def on_camera_disconnect(self, device: RegisteredDevice):
        """Handle camera disconnection events."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] 🔴 DISCONNECTED: {device.stable_id}")
        print(f"    Device: {device.device_info.label}")
        print()
    
    def on_status_change(self, device: RegisteredDevice):
        """Handle any status change events."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        status_icon = "🟢" if device.is_connected() else "🔴"
        print(f"[{timestamp}] {status_icon} STATUS CHANGE: {device.stable_id} -> {device.status.value}")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        print(f"\nReceived signal {signum}, shutting down...")
        self.stop()
    
    def start(self):
        """Start monitoring cameras."""
        print("StableCam Event Monitoring Example")
        print("=" * 40)
        
        # First, detect and register any connected cameras
        print("Detecting and registering cameras...")
        try:
            devices = self.cam.detect()
            if devices:
                for device in devices:
                    try:
                        stable_id = self.cam.register(device)
                        print(f"  Registered: {stable_id} ({device.label})")
                    except Exception as e:
                        print(f"  Failed to register {device.label}: {e}")
            else:
                print("  No cameras detected")
        except Exception as e:
            print(f"Error during initial detection: {e}")
        
        # Show current registered devices
        print("\nCurrently registered devices:")
        registered = self.cam.list()
        if registered:
            for device in registered:
                status_icon = "🟢" if device.is_connected() else "🔴"
                print(f"  {status_icon} {device.stable_id}: {device.device_info.label}")
        else:
            print("  No registered devices")
        
        print("\nStarting real-time monitoring...")
        print("Connect or disconnect cameras to see events.")
        print("Press Ctrl+C to stop monitoring.\n")
        
        # Start monitoring
        self.running = True
        self.cam.run()
        
        # Keep the main thread alive
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """Stop monitoring."""
        if self.running:
            print("Stopping camera monitoring...")
            self.running = False
            self.cam.stop()
            print("Monitoring stopped.")
            sys.exit(0)


def main():
    """Run the camera monitoring example."""
    monitor = CameraMonitor()
    monitor.start()


if __name__ == "__main__":
    main()