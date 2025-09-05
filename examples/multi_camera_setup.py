#!/usr/bin/env python3
"""
Multi-Camera Setup Example

This example demonstrates managing multiple cameras with StableCam,
including assigning roles and tracking camera assignments.
"""

import time
from typing import Dict, Optional
from dataclasses import dataclass
from stablecam import StableCam, RegisteredDevice, DeviceStatus


@dataclass
class CameraRole:
    """Represents a camera role assignment."""
    stable_id: str
    role: str
    description: str
    required: bool = True


class MultiCameraManager:
    """Example multi-camera management system."""
    
    def __init__(self):
        self.cam = StableCam(log_level="INFO")
        self.camera_roles: Dict[str, CameraRole] = {}
        self.role_assignments: Dict[str, str] = {}  # role -> stable_id
        
        # Set up event handlers
        self.cam.on('on_connect', self.on_camera_connect)
        self.cam.on('on_disconnect', self.on_camera_disconnect)
    
    def define_camera_roles(self):
        """Define the camera roles needed for this setup."""
        roles = [
            ("main", "Main Camera", "Primary recording camera", True),
            ("overhead", "Overhead Camera", "Top-down view camera", True),
            ("side", "Side Camera", "Side angle camera", False),
            ("backup", "Backup Camera", "Backup/spare camera", False),
        ]
        
        print("Defining camera roles:")
        for role, name, desc, required in roles:
            print(f"  - {role}: {name} ({'Required' if required else 'Optional'})")
            print(f"    {desc}")
        print()
    
    def assign_camera_role(self, stable_id: str, role: str) -> bool:
        """Assign a role to a camera."""
        if role in self.role_assignments:
            print(f"Role '{role}' is already assigned to {self.role_assignments[role]}")
            return False
        
        device = self.cam.get_by_id(stable_id)
        if not device:
            print(f"Camera {stable_id} not found")
            return False
        
        self.role_assignments[role] = stable_id
        self.camera_roles[stable_id] = CameraRole(
            stable_id=stable_id,
            role=role,
            description=f"{device.device_info.label} assigned as {role}",
        )
        
        print(f"✅ Assigned {stable_id} to role '{role}'")
        return True
    
    def unassign_camera_role(self, stable_id: str):
        """Remove role assignment from a camera."""
        if stable_id in self.camera_roles:
            role = self.camera_roles[stable_id].role
            del self.camera_roles[stable_id]
            if role in self.role_assignments:
                del self.role_assignments[role]
            print(f"❌ Unassigned {stable_id} from role '{role}'")
    
    def get_camera_by_role(self, role: str) -> Optional[RegisteredDevice]:
        """Get the camera assigned to a specific role."""
        if role in self.role_assignments:
            stable_id = self.role_assignments[role]
            return self.cam.get_by_id(stable_id)
        return None
    
    def check_setup_status(self):
        """Check if all required cameras are connected and assigned."""
        required_roles = ["main", "overhead"]
        optional_roles = ["side", "backup"]
        
        print("Camera Setup Status:")
        print("-" * 30)
        
        all_required_ok = True
        
        for role in required_roles:
            camera = self.get_camera_by_role(role)
            if camera and camera.is_connected():
                print(f"✅ {role.upper()}: {camera.stable_id} (Connected)")
            elif camera:
                print(f"⚠️  {role.upper()}: {camera.stable_id} (Disconnected)")
                all_required_ok = False
            else:
                print(f"❌ {role.upper()}: Not assigned")
                all_required_ok = False
        
        for role in optional_roles:
            camera = self.get_camera_by_role(role)
            if camera and camera.is_connected():
                print(f"✅ {role.upper()}: {camera.stable_id} (Connected)")
            elif camera:
                print(f"⚠️  {role.upper()}: {camera.stable_id} (Disconnected)")
            else:
                print(f"➖ {role.upper()}: Not assigned (Optional)")
        
        print()
        if all_required_ok:
            print("🎉 All required cameras are ready!")
        else:
            print("⚠️  Some required cameras are missing or disconnected")
        
        return all_required_ok
    
    def on_camera_connect(self, device: RegisteredDevice):
        """Handle camera connection."""
        print(f"📷 Camera connected: {device.stable_id}")
        
        # Check if this camera has a role assignment
        if device.stable_id in self.camera_roles:
            role = self.camera_roles[device.stable_id].role
            print(f"   Role: {role}")
        else:
            print("   No role assigned")
        
        self.check_setup_status()
        print()
    
    def on_camera_disconnect(self, device: RegisteredDevice):
        """Handle camera disconnection."""
        print(f"📷 Camera disconnected: {device.stable_id}")
        
        if device.stable_id in self.camera_roles:
            role = self.camera_roles[device.stable_id].role
            print(f"   Role affected: {role}")
        
        self.check_setup_status()
        print()
    
    def interactive_setup(self):
        """Interactive camera role assignment."""
        print("Interactive Camera Setup")
        print("=" * 30)
        
        # Detect and register cameras
        print("Detecting cameras...")
        devices = self.cam.detect()
        
        if not devices:
            print("No cameras detected. Please connect cameras and try again.")
            return
        
        # Register all detected cameras
        registered_ids = []
        for device in devices:
            try:
                stable_id = self.cam.register(device)
                registered_ids.append(stable_id)
                print(f"  Registered: {stable_id} ({device.label})")
            except Exception as e:
                print(f"  Failed to register {device.label}: {e}")
        
        if not registered_ids:
            print("No cameras could be registered.")
            return
        
        print(f"\nRegistered {len(registered_ids)} cameras")
        
        # Interactive role assignment
        roles = ["main", "overhead", "side", "backup"]
        
        print("\nAssign cameras to roles:")
        print("Available cameras:")
        for i, stable_id in enumerate(registered_ids):
            device = self.cam.get_by_id(stable_id)
            print(f"  {i + 1}. {stable_id}: {device.device_info.label}")
        
        print("\nAvailable roles:")
        for i, role in enumerate(roles):
            required = "Required" if role in ["main", "overhead"] else "Optional"
            print(f"  {role}: {required}")
        
        print("\nEnter assignments (camera_number:role), or 'done' to finish:")
        print("Example: 1:main, 2:overhead")
        
        while True:
            try:
                user_input = input("> ").strip()
                
                if user_input.lower() == 'done':
                    break
                
                if ':' not in user_input:
                    print("Invalid format. Use: camera_number:role")
                    continue
                
                camera_num, role = user_input.split(':', 1)
                camera_num = int(camera_num) - 1
                
                if camera_num < 0 or camera_num >= len(registered_ids):
                    print(f"Invalid camera number. Use 1-{len(registered_ids)}")
                    continue
                
                if role not in roles:
                    print(f"Invalid role. Available: {', '.join(roles)}")
                    continue
                
                stable_id = registered_ids[camera_num]
                if self.assign_camera_role(stable_id, role):
                    roles.remove(role)  # Remove assigned role from available
                
            except (ValueError, KeyboardInterrupt):
                print("Invalid input or interrupted.")
                break
        
        print("\nFinal setup:")
        self.check_setup_status()


def main():
    """Run the multi-camera setup example."""
    manager = MultiCameraManager()
    
    # Define camera roles
    manager.define_camera_roles()
    
    # Start monitoring
    manager.cam.run()
    
    try:
        # Run interactive setup
        manager.interactive_setup()
        
        # Keep monitoring for a while to demonstrate events
        print("\nMonitoring for camera changes (30 seconds)...")
        print("Try connecting/disconnecting cameras to see role status updates.")
        
        for i in range(30):
            time.sleep(1)
            if i % 10 == 9:  # Check status every 10 seconds
                print(f"\n--- Status check ({i + 1}s) ---")
                manager.check_setup_status()
        
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        manager.cam.stop()
        print("Multi-camera setup example completed!")


if __name__ == "__main__":
    main()