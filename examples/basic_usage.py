#!/usr/bin/env python3
"""
Basic StableCam Usage Example

This example demonstrates the fundamental operations of StableCam:
- Detecting connected cameras
- Registering cameras with stable IDs
- Listing registered devices
- Checking device status
"""

from stablecam import StableCam, DeviceStatus


def main():
    """Demonstrate basic StableCam operations."""
    print("StableCam Basic Usage Example")
    print("=" * 40)
    
    # Create StableCam instance
    print("Initializing StableCam...")
    cam = StableCam(log_level="INFO")
    
    # Detect currently connected cameras
    print("\n1. Detecting connected cameras...")
    try:
        devices = cam.detect()
        print(f"Found {len(devices)} camera(s)")
        
        for i, device in enumerate(devices):
            print(f"  Camera {i + 1}:")
            print(f"    System Index: {device.system_index}")
            print(f"    Label: {device.label}")
            print(f"    Vendor ID: {device.vendor_id}")
            print(f"    Product ID: {device.product_id}")
            print(f"    Serial Number: {device.serial_number or 'N/A'}")
            print(f"    Port Path: {device.port_path or 'N/A'}")
            print()
            
    except Exception as e:
        print(f"Error detecting cameras: {e}")
        return
    
    # Register cameras if any are detected
    if devices:
        print("2. Registering cameras...")
        registered_ids = []
        
        for device in devices:
            try:
                stable_id = cam.register(device)
                registered_ids.append(stable_id)
                print(f"  Registered '{device.label}' with stable ID: {stable_id}")
            except Exception as e:
                print(f"  Failed to register '{device.label}': {e}")
        
        print(f"\nSuccessfully registered {len(registered_ids)} camera(s)")
    else:
        print("2. No cameras to register")
    
    # List all registered devices
    print("\n3. Listing all registered devices...")
    try:
        registered = cam.list()
        
        if registered:
            print(f"Found {len(registered)} registered device(s):")
            
            for device in registered:
                status_icon = "🟢" if device.is_connected() else "🔴"
                print(f"  {status_icon} {device.stable_id}")
                print(f"    Label: {device.device_info.label}")
                print(f"    Status: {device.status.value}")
                print(f"    Registered: {device.registered_at.strftime('%Y-%m-%d %H:%M:%S')}")
                
                if device.last_seen:
                    print(f"    Last Seen: {device.last_seen.strftime('%Y-%m-%d %H:%M:%S')}")
                else:
                    print("    Last Seen: Never")
                print()
        else:
            print("  No registered devices found")
            
    except Exception as e:
        print(f"Error listing devices: {e}")
    
    # Demonstrate getting device by ID
    if registered:
        print("4. Getting device by stable ID...")
        first_device = registered[0]
        
        try:
            device = cam.get_by_id(first_device.stable_id)
            if device:
                print(f"  Found device: {device.stable_id}")
                print(f"    Current system index: {device.device_info.system_index}")
                print(f"    Status: {device.status.value}")
            else:
                print(f"  Device {first_device.stable_id} not found")
        except Exception as e:
            print(f"  Error getting device: {e}")
    
    print("\nBasic usage example completed!")


if __name__ == "__main__":
    main()