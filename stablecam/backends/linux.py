"""
Linux-specific camera detection backend using v4l2 and udev.

This module implements camera enumeration via /dev/video* devices
and extracts hardware information using udev libraries.
"""

import glob
import os
import re
from typing import List, Optional, Dict, Any

from ..models import CameraDevice
from .base import PlatformBackend
from .exceptions import PlatformDetectionError, DeviceNotFoundError


class LinuxBackend(PlatformBackend):
    """
    Linux backend for camera detection using v4l2 and udev.
    
    This backend enumerates cameras via /dev/video* devices and extracts
    vendor ID, product ID, serial number, and port path using udev.
    """

    def __init__(self):
        """Initialize the Linux backend."""
        self._pyudev = None
        self._v4l2 = None
        self._fcntl = None
        self._struct = None
        
        # Try to import required libraries
        try:
            import pyudev
            self._pyudev = pyudev
        except ImportError:
            # pyudev is optional - we'll use fallback methods
            pass
            
        try:
            import v4l2
            import fcntl
            import struct
            self._v4l2 = v4l2
            self._fcntl = fcntl
            self._struct = struct
        except ImportError:
            # v4l2 is optional - we'll use basic enumeration
            pass

    @property
    def platform_name(self) -> str:
        """Get the platform name."""
        return "linux"

    def enumerate_cameras(self) -> List[CameraDevice]:
        """
        Enumerate cameras using Linux v4l2 interface.
        
        Returns:
            List[CameraDevice]: List of detected camera devices
            
        Raises:
            PlatformDetectionError: If enumeration fails
        """
        try:
            cameras = []
            video_devices = self._find_video_devices()
            
            for device_path in video_devices:
                try:
                    camera = self._create_camera_device(device_path)
                    if camera:
                        cameras.append(camera)
                except Exception as e:
                    # Log the error but continue with other devices
                    print(f"Warning: Failed to process device {device_path}: {e}")
                    continue
            
            return cameras
            
        except Exception as e:
            raise PlatformDetectionError(f"Failed to enumerate cameras on Linux: {e}")

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
            device_path = f"/dev/video{system_index}"
            
            if not os.path.exists(device_path):
                raise DeviceNotFoundError(f"Device /dev/video{system_index} not found")
            
            camera = self._create_camera_device(device_path)
            if not camera:
                raise DeviceNotFoundError(f"Could not get info for device {system_index}")
                
            return camera
            
        except DeviceNotFoundError:
            raise
        except Exception as e:
            raise PlatformDetectionError(f"Failed to get device info for index {system_index}: {e}")

    def _find_video_devices(self) -> List[str]:
        """
        Find all video devices on the system.
        
        Returns:
            List[str]: List of video device paths
        """
        # Use glob to find all /dev/video* devices
        video_devices = glob.glob("/dev/video*")
        
        # Filter to only include numeric video devices (cameras)
        # Exclude devices like /dev/video-codec0 or other non-camera devices
        camera_devices = []
        for device in video_devices:
            # Extract the number part
            match = re.search(r'/dev/video(\d+)$', device)
            if match:
                # Check if this is actually a camera device (not a codec or other device)
                if self._is_camera_device(device):
                    camera_devices.append(device)
        
        # Sort by device number
        camera_devices.sort(key=lambda x: int(re.search(r'/dev/video(\d+)$', x).group(1)))
        return camera_devices

    def _is_camera_device(self, device_path: str) -> bool:
        """
        Check if a video device is actually a camera (capture device).
        
        Args:
            device_path: Path to the video device
            
        Returns:
            bool: True if the device is a camera
        """
        try:
            # Try to open the device to check if it's accessible
            if not os.access(device_path, os.R_OK):
                return False
            
            # If we have v4l2 support, check device capabilities
            if self._v4l2 and self._fcntl and self._struct:
                return self._check_v4l2_capabilities(device_path)
            
            # Fallback: assume all /dev/videoN devices are cameras
            return True
            
        except Exception:
            return False

    def _check_v4l2_capabilities(self, device_path: str) -> bool:
        """
        Check v4l2 device capabilities to determine if it's a camera.
        
        Args:
            device_path: Path to the video device
            
        Returns:
            bool: True if the device has capture capabilities
        """
        try:
            with open(device_path, 'rb') as device:
                # Query device capabilities
                caps = self._struct.pack('64s', b'')
                caps = self._fcntl.ioctl(device, self._v4l2.VIDIOC_QUERYCAP, caps)
                
                # Unpack capabilities
                driver, card, bus_info, version, capabilities = self._struct.unpack('16s32s32sII', caps[:88])
                
                # Check if device supports video capture
                V4L2_CAP_VIDEO_CAPTURE = 0x00000001
                return bool(capabilities & V4L2_CAP_VIDEO_CAPTURE)
                
        except Exception:
            # If we can't check capabilities, assume it's a camera
            return True

    def _create_camera_device(self, device_path: str) -> Optional[CameraDevice]:
        """
        Create a CameraDevice from a video device path.
        
        Args:
            device_path: Path to the video device (e.g., /dev/video0)
            
        Returns:
            Optional[CameraDevice]: Camera device info or None if failed
        """
        try:
            # Extract system index from device path
            match = re.search(r'/dev/video(\d+)$', device_path)
            if not match:
                return None
            
            system_index = int(match.group(1))
            
            # Get hardware information using udev if available
            if self._pyudev:
                hardware_info = self._get_udev_info(device_path)
            else:
                hardware_info = self._get_fallback_info(device_path)
            
            # Get device label/name
            label = self._get_device_label(device_path, hardware_info)
            
            return CameraDevice(
                system_index=system_index,
                vendor_id=hardware_info.get('vendor_id', 'unknown'),
                product_id=hardware_info.get('product_id', 'unknown'),
                serial_number=hardware_info.get('serial_number'),
                port_path=hardware_info.get('port_path'),
                label=label,
                platform_data={
                    'device_path': device_path,
                    'subsystem': hardware_info.get('subsystem', 'video4linux'),
                    'driver': hardware_info.get('driver'),
                    'udev_available': self._pyudev is not None
                }
            )
            
        except Exception as e:
            print(f"Warning: Failed to create camera device for {device_path}: {e}")
            return None

    def _get_udev_info(self, device_path: str) -> Dict[str, Any]:
        """
        Get hardware information using udev.
        
        Args:
            device_path: Path to the video device
            
        Returns:
            Dict[str, Any]: Hardware information dictionary
        """
        try:
            context = self._pyudev.Context()
            device = self._pyudev.Devices.from_device_file(context, device_path)
            
            info = {}
            
            # Walk up the device tree to find USB device information
            usb_device = device
            while usb_device:
                if usb_device.subsystem == 'usb' and usb_device.device_type == 'usb_device':
                    # Found the USB device
                    info['vendor_id'] = usb_device.get('ID_VENDOR_ID', 'unknown')
                    info['product_id'] = usb_device.get('ID_MODEL_ID', 'unknown')
                    info['serial_number'] = usb_device.get('ID_SERIAL_SHORT')
                    info['port_path'] = usb_device.get('DEVPATH')
                    info['subsystem'] = usb_device.subsystem
                    break
                usb_device = usb_device.parent
            
            # Get video4linux specific info
            info['driver'] = device.get('ID_V4L_DRIVER')
            if not info.get('driver'):
                info['driver'] = device.get('DRIVER')
            
            return info
            
        except Exception as e:
            print(f"Warning: Failed to get udev info for {device_path}: {e}")
            return self._get_fallback_info(device_path)

    def _get_fallback_info(self, device_path: str) -> Dict[str, Any]:
        """
        Get hardware information using fallback methods when udev is not available.
        
        Args:
            device_path: Path to the video device
            
        Returns:
            Dict[str, Any]: Hardware information dictionary
        """
        info = {
            'vendor_id': 'unknown',
            'product_id': 'unknown',
            'serial_number': None,
            'port_path': device_path,
            'subsystem': 'video4linux',
            'driver': None
        }
        
        try:
            # Try to extract info from sysfs
            match = re.search(r'/dev/video(\d+)$', device_path)
            if match:
                video_num = match.group(1)
                sysfs_path = f"/sys/class/video4linux/video{video_num}"
                
                if os.path.exists(sysfs_path):
                    # Try to find USB device info by following symlinks
                    device_link = os.path.join(sysfs_path, 'device')
                    if os.path.islink(device_link):
                        # Follow the symlink to find USB device
                        real_path = os.path.realpath(device_link)
                        usb_info = self._extract_usb_info_from_path(real_path)
                        info.update(usb_info)
            
        except Exception as e:
            print(f"Warning: Fallback info extraction failed for {device_path}: {e}")
        
        return info

    def _extract_usb_info_from_path(self, sysfs_path: str) -> Dict[str, Any]:
        """
        Extract USB device information from sysfs path.
        
        Args:
            sysfs_path: Path in sysfs
            
        Returns:
            Dict[str, Any]: USB device information
        """
        info = {}
        
        try:
            # Walk up the path to find USB device directory
            current_path = sysfs_path
            while current_path and current_path != '/':
                # Check if this directory contains USB device files
                vendor_file = os.path.join(current_path, 'idVendor')
                product_file = os.path.join(current_path, 'idProduct')
                serial_file = os.path.join(current_path, 'serial')
                
                if os.path.exists(vendor_file) and os.path.exists(product_file):
                    # Found USB device directory
                    try:
                        with open(vendor_file, 'r') as f:
                            info['vendor_id'] = f.read().strip()
                        with open(product_file, 'r') as f:
                            info['product_id'] = f.read().strip()
                        
                        if os.path.exists(serial_file):
                            with open(serial_file, 'r') as f:
                                serial = f.read().strip()
                                if serial:
                                    info['serial_number'] = serial
                        
                        # Use the USB device path as port path
                        info['port_path'] = current_path
                        
                    except Exception as e:
                        print(f"Warning: Failed to read USB device files: {e}")
                    
                    break
                
                # Move up one directory
                current_path = os.path.dirname(current_path)
                
        except Exception as e:
            print(f"Warning: Failed to extract USB info from path {sysfs_path}: {e}")
        
        return info

    def _get_device_label(self, device_path: str, hardware_info: Dict[str, Any]) -> str:
        """
        Get a human-readable label for the device.
        
        Args:
            device_path: Path to the video device
            hardware_info: Hardware information dictionary
            
        Returns:
            str: Human-readable device label
        """
        try:
            # Try to get device name from v4l2 if available
            if self._v4l2 and self._fcntl and self._struct:
                label = self._get_v4l2_device_name(device_path)
                if label:
                    return label
            
            # Try to get name from sysfs
            match = re.search(r'/dev/video(\d+)$', device_path)
            if match:
                video_num = match.group(1)
                name_file = f"/sys/class/video4linux/video{video_num}/name"
                if os.path.exists(name_file):
                    try:
                        with open(name_file, 'r') as f:
                            name = f.read().strip()
                            if name:
                                return name
                    except Exception:
                        pass
            
            # Fallback to generic name with vendor/product info
            vendor_id = hardware_info.get('vendor_id', 'unknown')
            product_id = hardware_info.get('product_id', 'unknown')
            
            if vendor_id != 'unknown' and product_id != 'unknown':
                return f"USB Camera {vendor_id}:{product_id}"
            else:
                return f"Camera {os.path.basename(device_path)}"
                
        except Exception:
            return f"Camera {os.path.basename(device_path)}"

    def _get_v4l2_device_name(self, device_path: str) -> Optional[str]:
        """
        Get device name using v4l2 API.
        
        Args:
            device_path: Path to the video device
            
        Returns:
            Optional[str]: Device name or None if failed
        """
        try:
            with open(device_path, 'rb') as device:
                # Query device capabilities to get card name
                caps = self._struct.pack('64s', b'')
                caps = self._fcntl.ioctl(device, self._v4l2.VIDIOC_QUERYCAP, caps)
                
                # Unpack capabilities - card name is at offset 16, length 32
                card_bytes = caps[16:48]
                # Remove null bytes and decode
                card_name = card_bytes.rstrip(b'\x00').decode('utf-8', errors='ignore')
                
                return card_name if card_name else None
                
        except Exception:
            return None