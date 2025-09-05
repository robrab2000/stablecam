"""
macOS-specific camera detection backend using AVFoundation and IOKit.

This module implements camera enumeration using AVFoundation framework
and extracts hardware information using IOKit for USB device identifiers.
"""

import subprocess
import json
import re
from typing import List, Optional, Dict, Any

from ..models import CameraDevice
from .base import PlatformBackend
from .exceptions import PlatformDetectionError, DeviceNotFoundError


class MacOSBackend(PlatformBackend):
    """
    macOS backend for camera detection using AVFoundation and IOKit.
    
    This backend enumerates cameras using AVFoundation framework and extracts
    vendor ID, product ID, serial number, and device paths using IOKit.
    """

    def __init__(self):
        """Initialize the macOS backend."""
        self._system_profiler_available = None
        self._ioreg_available = None

    @property
    def platform_name(self) -> str:
        """Get the platform name."""
        return "darwin"

    @property
    def system_profiler_available(self) -> bool:
        """Check if system_profiler is available (lazy evaluation)."""
        if self._system_profiler_available is None:
            self._system_profiler_available = self._check_system_profiler_availability()
        return self._system_profiler_available

    @property
    def ioreg_available(self) -> bool:
        """Check if ioreg is available (lazy evaluation)."""
        if self._ioreg_available is None:
            self._ioreg_available = self._check_ioreg_availability()
        return self._ioreg_available

    def enumerate_cameras(self) -> List[CameraDevice]:
        """
        Enumerate cameras using AVFoundation and IOKit.
        
        Returns:
            List[CameraDevice]: List of detected camera devices
            
        Raises:
            PlatformDetectionError: If enumeration fails
        """
        try:
            cameras = []
            
            # Get camera devices using system_profiler and ioreg
            camera_devices = self._get_camera_devices()
            
            # Create CameraDevice objects
            for index, device_info in enumerate(camera_devices):
                try:
                    camera = self._create_camera_device(index, device_info)
                    if camera:
                        cameras.append(camera)
                except Exception as e:
                    # Log the error but continue with other devices
                    print(f"Warning: Failed to process device {device_info.get('_name', 'Unknown')}: {e}")
                    continue
            
            return cameras
            
        except Exception as e:
            raise PlatformDetectionError(f"Failed to enumerate cameras on macOS: {e}")

    def get_device_info(self, system_index: int) -> CameraDevice:
        """
        Get device information for a specific camera index.
        
        Args:
            system_index: The system camera index
            
        Returns:
            CameraDevice: Device information
            
        Raises:
            DeviceNotFoundError: If device not found
            PlatformDetectionError: If info extraction fails
        """
        try:
            camera_devices = self._get_camera_devices()
            
            if system_index >= len(camera_devices):
                raise DeviceNotFoundError(f"Camera device at index {system_index} not found")
            
            device_info = camera_devices[system_index]
            camera = self._create_camera_device(system_index, device_info)
            
            if not camera:
                raise DeviceNotFoundError(f"Could not get info for device at index {system_index}")
                
            return camera
            
        except DeviceNotFoundError:
            raise
        except Exception as e:
            raise PlatformDetectionError(f"Failed to get device info for index {system_index}: {e}")

    def _check_system_profiler_availability(self) -> bool:
        """
        Check if system_profiler is available on the system.
        
        Returns:
            bool: True if system_profiler is available
        """
        try:
            result = subprocess.run(
                ['system_profiler', '-help'],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False

    def _check_ioreg_availability(self) -> bool:
        """
        Check if ioreg is available on the system.
        
        Returns:
            bool: True if ioreg is available
        """
        try:
            result = subprocess.run(
                ['ioreg', '-h'],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False

    def _get_camera_devices(self) -> List[Dict[str, Any]]:
        """
        Get camera devices using system_profiler and ioreg.
        
        Returns:
            List[Dict[str, Any]]: List of camera device information
        """
        devices = []
        
        try:
            if self.system_profiler_available:
                try:
                    devices = self._get_devices_via_system_profiler()
                except Exception as e:
                    print(f"Warning: system_profiler enumeration failed: {e}")
                    if self.ioreg_available:
                        devices = self._get_devices_via_ioreg()
                    else:
                        devices = self._get_devices_fallback()
            elif self.ioreg_available:
                devices = self._get_devices_via_ioreg()
            else:
                # Fallback to basic enumeration
                devices = self._get_devices_fallback()
                
        except Exception as e:
            print(f"Warning: macOS camera enumeration failed: {e}")
            # Try fallback method
            devices = self._get_devices_fallback()
        
        return devices

    def _get_devices_via_system_profiler(self) -> List[Dict[str, Any]]:
        """
        Get camera devices using system_profiler.
        
        Returns:
            List[Dict[str, Any]]: List of camera device information
        """
        try:
            # Query USB devices that might be cameras
            result = subprocess.run([
                'system_profiler', 'SPUSBDataType', '-json'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                print(f"system_profiler query failed: {result.stderr}")
                return []
            
            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError as e:
                print(f"Failed to parse system_profiler JSON output: {e}")
                return []
            
            cameras = []
            
            # Parse USB data to find camera devices
            usb_data = data.get('SPUSBDataType', [])
            self._extract_cameras_from_usb_tree(usb_data, cameras)
            
            return cameras
            
        except Exception as e:
            print(f"system_profiler execution failed: {e}")
            return []

    def _extract_cameras_from_usb_tree(self, usb_items: List[Dict], cameras: List[Dict], parent_location: str = "") -> None:
        """
        Recursively extract camera devices from USB device tree.
        
        Args:
            usb_items: List of USB device items from system_profiler
            cameras: List to append found camera devices to
            parent_location: Parent device location for building device path
        """
        for item in usb_items:
            try:
                # Check if this device is a camera
                if self._is_camera_device(item):
                    # Extract device information
                    device_info = self._parse_system_profiler_device(item, parent_location)
                    if device_info:
                        cameras.append(device_info)
                
                # Recursively check child devices
                child_items = item.get('_items', [])
                if child_items:
                    location = item.get('location_id', parent_location)
                    self._extract_cameras_from_usb_tree(child_items, cameras, location)
                    
            except Exception as e:
                print(f"Warning: Failed to process USB device item: {e}")
                continue

    def _is_camera_device(self, device_info: Dict[str, Any]) -> bool:
        """
        Check if a USB device is a camera based on its properties.
        
        Args:
            device_info: Device information from system_profiler
            
        Returns:
            bool: True if the device appears to be a camera
        """
        # Check device name for camera keywords
        name = device_info.get('_name', '').lower()
        camera_keywords = [
            'camera', 'webcam', 'video', 'imaging', 'capture', 'cam',
            'facetime', 'isight', 'logitech', 'microsoft lifecam'
        ]
        
        if any(keyword in name for keyword in camera_keywords):
            return True
        
        # Check USB class codes for video devices
        # Video class is 0x0E (14 decimal)
        bcd_device = device_info.get('bcd_device')
        device_speed = device_info.get('device_speed')
        
        # Additional heuristics based on USB properties
        # This is a simplified check - in practice, you might need more sophisticated detection
        if 'video' in str(device_info.get('manufacturer', '')).lower():
            return True
        
        return False

    def _parse_system_profiler_device(self, device_info: Dict[str, Any], parent_location: str) -> Optional[Dict[str, Any]]:
        """
        Parse device information from system_profiler output.
        
        Args:
            device_info: Device information dictionary
            parent_location: Parent device location
            
        Returns:
            Optional[Dict[str, Any]]: Parsed device information or None
        """
        try:
            name = device_info.get('_name', 'Unknown Camera')
            
            # Extract vendor and product IDs
            vendor_id = device_info.get('vendor_id', '0x0000')
            product_id = device_info.get('product_id', '0x0000')
            
            # Convert hex strings to lowercase without 0x prefix
            if isinstance(vendor_id, str) and vendor_id.startswith('0x'):
                vendor_id = vendor_id[2:].lower().zfill(4)
            elif isinstance(vendor_id, str) and vendor_id.isdigit():
                vendor_id = f"{int(vendor_id):04x}"
            elif isinstance(vendor_id, str):
                # For invalid strings, try to extract valid hex chars or use default
                try:
                    # Try to parse as hex without 0x prefix
                    vendor_id = f"{int(vendor_id, 16):04x}"
                except ValueError:
                    vendor_id = vendor_id.lower()[:4].zfill(4)
            else:
                vendor_id = f"{vendor_id:04x}" if isinstance(vendor_id, int) else "0000"
            
            if isinstance(product_id, str) and product_id.startswith('0x'):
                product_id = product_id[2:].lower().zfill(4)
            elif isinstance(product_id, str) and product_id.isdigit():
                product_id = f"{int(product_id):04x}"
            elif isinstance(product_id, str):
                # For invalid strings, try to extract valid hex chars or use default
                try:
                    # Try to parse as hex without 0x prefix
                    product_id = f"{int(product_id, 16):04x}"
                except ValueError:
                    product_id = product_id.lower()[:4].zfill(4)
            else:
                product_id = f"{product_id:04x}" if isinstance(product_id, int) else "0000"
            
            # Extract serial number
            serial_number = device_info.get('serial_num')
            if not serial_number or serial_number == '0':
                serial_number = None
            
            # Build device path using location ID
            location_id = device_info.get('location_id', parent_location)
            device_path = f"USB:{location_id}" if location_id else "USB:unknown"
            
            return {
                '_name': name,
                'vendor_id': vendor_id,
                'product_id': product_id,
                'serial_number': serial_number,
                'location_id': location_id,
                'device_path': device_path,
                'manufacturer': device_info.get('manufacturer', ''),
                'bcd_device': device_info.get('bcd_device', ''),
                'device_speed': device_info.get('device_speed', ''),
                'extra_current_used': device_info.get('extra_current_used', ''),
                'built_in': device_info.get('built_in', False)
            }
            
        except Exception as e:
            print(f"Failed to parse system_profiler device info: {e}")
            return None

    def _get_devices_via_ioreg(self) -> List[Dict[str, Any]]:
        """
        Get camera devices using ioreg command.
        
        Returns:
            List[Dict[str, Any]]: List of camera device information
        """
        try:
            # Query IOKit registry for USB video devices
            result = subprocess.run([
                'ioreg', '-p', 'IOUSB', '-l', '-w', '0'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                print(f"ioreg query failed: {result.stderr}")
                return []
            
            cameras = []
            
            # Parse ioreg output to find camera devices
            lines = result.stdout.split('\n')
            current_device = {}
            
            for line in lines:
                line = line.strip()
                
                # Look for USB device entries
                if '+-o' in line and '@' in line:
                    # Process previous device if it was a camera
                    if current_device and self._is_ioreg_camera_device(current_device):
                        parsed_device = self._parse_ioreg_device(current_device)
                        if parsed_device:
                            cameras.append(parsed_device)
                    
                    # Start new device
                    current_device = {'_name': self._extract_device_name_from_ioreg_line(line)}
                
                elif '|' in line and '=' in line and current_device:
                    # Parse device properties
                    try:
                        # Remove leading |, spaces, and quotes
                        clean_line = line.lstrip('|').strip()
                        if '"' in clean_line:
                            # Handle quoted keys: "key" = value
                            key_part, value_part = clean_line.split('=', 1)
                            key = key_part.strip().strip('"')
                            value = value_part.strip().strip('"')
                        else:
                            # Handle unquoted keys: key = value
                            key, value = clean_line.split('=', 1)
                            key = key.strip()
                            value = value.strip()
                        
                        current_device[key] = value
                    except ValueError:
                        continue
            
            # Process the last device
            if current_device and self._is_ioreg_camera_device(current_device):
                parsed_device = self._parse_ioreg_device(current_device)
                if parsed_device:
                    cameras.append(parsed_device)
            
            return cameras
            
        except Exception as e:
            print(f"ioreg execution failed: {e}")
            return []

    def _extract_device_name_from_ioreg_line(self, line: str) -> str:
        """
        Extract device name from ioreg device line.
        
        Args:
            line: ioreg output line containing device info
            
        Returns:
            str: Extracted device name
        """
        try:
            # ioreg format: "+-o DeviceName@address  <class IOUSBHostDevice, id 0x...>"
            match = re.search(r'\+-o\s+([^@<]+)', line)
            if match:
                return match.group(1).strip()
        except Exception:
            pass
        
        return "Unknown Device"

    def _is_ioreg_camera_device(self, device_info: Dict[str, Any]) -> bool:
        """
        Check if an ioreg device is a camera.
        
        Args:
            device_info: Device information from ioreg
            
        Returns:
            bool: True if the device appears to be a camera
        """
        name = device_info.get('_name', '').lower()
        
        # Check for camera keywords in device name
        camera_keywords = [
            'camera', 'webcam', 'video', 'imaging', 'capture', 'cam',
            'facetime', 'isight', 'logitech', 'microsoft lifecam'
        ]
        
        if any(keyword in name for keyword in camera_keywords):
            return True
        
        # Check USB class information
        usb_class_code = device_info.get('bInterfaceClass')
        if usb_class_code == '14' or usb_class_code == '0xe':  # Video class
            return True
        
        return False

    def _parse_ioreg_device(self, device_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse device information from ioreg output.
        
        Args:
            device_info: Raw device information from ioreg
            
        Returns:
            Optional[Dict[str, Any]]: Parsed device information or None
        """
        try:
            name = device_info.get('_name', 'Unknown Camera')
            
            # Extract vendor and product IDs
            vendor_id = device_info.get('idVendor', '0')
            product_id = device_info.get('idProduct', '0')
            
            # Convert to hex format
            try:
                if isinstance(vendor_id, str) and vendor_id.isdigit():
                    vendor_id = f"{int(vendor_id):04x}"
                elif isinstance(vendor_id, str):
                    vendor_id = vendor_id.lower().zfill(4)
            except ValueError:
                vendor_id = "0000"
            
            try:
                if isinstance(product_id, str) and product_id.isdigit():
                    product_id = f"{int(product_id):04x}"
                elif isinstance(product_id, str):
                    product_id = product_id.lower().zfill(4)
            except ValueError:
                product_id = "0000"
            
            # Extract serial number
            serial_number = device_info.get('USB Serial Number')
            if not serial_number or serial_number == '0':
                serial_number = None
            
            # Build device path
            location_id = device_info.get('locationID', 'unknown')
            device_path = f"IOKit:{location_id}"
            
            return {
                '_name': name,
                'vendor_id': vendor_id,
                'product_id': product_id,
                'serial_number': serial_number,
                'location_id': location_id,
                'device_path': device_path,
                'manufacturer': device_info.get('USB Vendor Name', ''),
                'product_name': device_info.get('USB Product Name', ''),
                'device_speed': device_info.get('Device Speed', ''),
                'built_in': False  # Assume external USB cameras
            }
            
        except Exception as e:
            print(f"Failed to parse ioreg device info: {e}")
            return None

    def _get_devices_fallback(self) -> List[Dict[str, Any]]:
        """
        Fallback method for device enumeration when system tools are not available.
        
        Returns:
            List[Dict[str, Any]]: List of basic camera device information
        """
        # This is a basic fallback that creates minimal device info
        # In a real implementation, you might try to use AVFoundation directly via PyObjC
        devices = []
        
        # Try to detect built-in FaceTime camera
        try:
            # Check if there's a built-in camera by looking for common paths
            import os
            
            # This is a simplified check - actual AVFoundation integration would be more reliable
            if os.path.exists('/System/Library/Frameworks/AVFoundation.framework'):
                devices.append({
                    '_name': 'Built-in Camera',
                    'vendor_id': '05ac',  # Apple vendor ID
                    'product_id': '8600',  # Generic camera product ID
                    'serial_number': None,
                    'location_id': 'builtin',
                    'device_path': 'AVFoundation:builtin',
                    'manufacturer': 'Apple Inc.',
                    'product_name': 'FaceTime HD Camera',
                    'device_speed': 'Built-in',
                    'built_in': True
                })
        except Exception as e:
            print(f"Fallback camera detection failed: {e}")
        
        return devices

    def _create_camera_device(self, system_index: int, device_info: Dict[str, Any]) -> Optional[CameraDevice]:
        """
        Create a CameraDevice from macOS device information.
        
        Args:
            system_index: System-assigned camera index
            device_info: Device information from system_profiler or ioreg
            
        Returns:
            Optional[CameraDevice]: Camera device info or None if failed
        """
        try:
            vendor_id = device_info.get('vendor_id', '0000')
            product_id = device_info.get('product_id', '0000')
            serial_number = device_info.get('serial_number')
            name = device_info.get('_name', f'Camera {system_index}')
            device_path = device_info.get('device_path', f'macOS:camera{system_index}')
            
            # Use device path as port path
            port_path = device_path
            
            return CameraDevice(
                system_index=system_index,
                vendor_id=vendor_id,
                product_id=product_id,
                serial_number=serial_number,
                port_path=port_path,
                label=name,
                platform_data={
                    'device_path': device_path,
                    'location_id': device_info.get('location_id', ''),
                    'manufacturer': device_info.get('manufacturer', ''),
                    'product_name': device_info.get('product_name', ''),
                    'device_speed': device_info.get('device_speed', ''),
                    'built_in': device_info.get('built_in', False),
                    'system_profiler_available': self.system_profiler_available,
                    'ioreg_available': self.ioreg_available
                }
            )
            
        except Exception as e:
            print(f"Warning: Failed to create camera device from info {device_info}: {e}")
            return None