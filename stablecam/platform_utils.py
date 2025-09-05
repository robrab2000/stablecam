"""
Platform detection utilities for StableCam.

This module provides utilities for detecting the current platform and
checking for platform-specific dependencies and capabilities.
"""

import platform
import sys
import subprocess
from typing import Dict, List, Optional, Tuple


def get_platform_info() -> Dict[str, str]:
    """
    Get comprehensive platform information.
    
    Returns:
        Dict[str, str]: Platform information including system, release, version, etc.
    """
    return {
        'system': platform.system(),
        'release': platform.release(),
        'version': platform.version(),
        'machine': platform.machine(),
        'processor': platform.processor(),
        'architecture': platform.architecture()[0],
        'python_version': platform.python_version(),
        'python_implementation': platform.python_implementation(),
    }


def is_linux() -> bool:
    """Check if running on Linux."""
    return platform.system().lower() == 'linux'


def is_windows() -> bool:
    """Check if running on Windows."""
    return platform.system().lower() == 'windows'


def is_macos() -> bool:
    """Check if running on macOS."""
    return platform.system().lower() == 'darwin'


def get_recommended_dependencies() -> List[str]:
    """
    Get recommended dependencies for the current platform.
    
    Returns:
        List[str]: List of recommended package names for pip install
    """
    deps = []
    
    if is_linux():
        deps.extend([
            'pyudev>=0.21.0',  # For USB device information
            'v4l2-python>=0.2.0',  # For enhanced camera detection (optional)
        ])
    elif is_windows():
        # Windows uses built-in APIs, no additional dependencies needed
        pass
    elif is_macos():
        # macOS uses built-in system tools, no additional dependencies needed
        pass
    
    return deps


def check_platform_dependencies() -> Dict[str, bool]:
    """
    Check availability of platform-specific dependencies and tools.
    
    Returns:
        Dict[str, bool]: Availability status of platform tools and libraries
    """
    status = {}
    
    if is_linux():
        # Check for Linux-specific tools and libraries
        status['udev'] = _check_command_available('udevadm')
        status['v4l2'] = _check_v4l2_available()
        status['pyudev'] = _check_python_package('pyudev')
        status['v4l2_python'] = _check_python_package('v4l2')
        
    elif is_windows():
        # Check for Windows-specific tools
        status['wmic'] = _check_command_available('wmic')
        status['powershell'] = _check_command_available('powershell')
        status['system32'] = _check_windows_system32()
        
    elif is_macos():
        # Check for macOS-specific tools
        status['system_profiler'] = _check_command_available('system_profiler')
        status['ioreg'] = _check_command_available('ioreg')
        status['avfoundation'] = _check_macos_avfoundation()
    
    return status


def get_installation_instructions() -> Dict[str, List[str]]:
    """
    Get platform-specific installation instructions for dependencies.
    
    Returns:
        Dict[str, List[str]]: Installation instructions per platform
    """
    instructions = {}
    
    if is_linux():
        instructions['linux'] = [
            "# Install system dependencies (Ubuntu/Debian):",
            "sudo apt-get update",
            "sudo apt-get install libudev-dev python3-dev",
            "",
            "# Install Python dependencies:",
            "pip install stablecam[linux-enhanced]",
            "",
            "# Or install manually:",
            "pip install pyudev v4l2-python",
        ]
        
    elif is_windows():
        instructions['windows'] = [
            "# Windows uses built-in APIs, no additional system dependencies needed",
            "pip install stablecam",
            "",
            "# For TUI support:",
            "pip install stablecam[tui]",
        ]
        
    elif is_macos():
        instructions['macos'] = [
            "# macOS uses built-in system tools, no additional dependencies needed",
            "pip install stablecam",
            "",
            "# For TUI support:",
            "pip install stablecam[tui]",
        ]
    
    return instructions


def _check_command_available(command: str) -> bool:
    """
    Check if a system command is available.
    
    Args:
        command: Command name to check
        
    Returns:
        bool: True if command is available
    """
    import os
    
    # Check common system paths for macOS commands
    if is_macos():
        common_paths = [
            f'/usr/bin/{command}',
            f'/usr/sbin/{command}',
            f'/bin/{command}',
            f'/sbin/{command}',
        ]
        
        for path in common_paths:
            if os.path.exists(path) and os.access(path, os.X_OK):
                # For macOS system tools, just check if executable exists
                # Some tools like system_profiler return non-zero for --help
                if command in ['system_profiler', 'ioreg']:
                    return True
                
                # Test other commands normally
                try:
                    result = subprocess.run(
                        [path, '--help'],
                        capture_output=True,
                        timeout=5
                    )
                    return result.returncode == 0
                except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                    continue
    
    # Try the command directly (in PATH)
    try:
        # Special handling for different command types
        if command == 'wmic':
            test_args = [command, '/?']
        elif command in ['system_profiler', 'ioreg'] and is_macos():
            # For macOS system tools, just try to run them without args
            # to see if they're available (they'll show usage)
            test_args = [command]
        else:
            test_args = [command, '--help']
        
        result = subprocess.run(
            test_args,
            capture_output=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        
        # For macOS system tools, any return code means the command exists
        if command in ['system_profiler', 'ioreg'] and is_macos():
            return True
        
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def _check_python_package(package_name: str) -> bool:
    """
    Check if a Python package is available.
    
    Args:
        package_name: Package name to check
        
    Returns:
        bool: True if package is importable
    """
    try:
        __import__(package_name)
        return True
    except ImportError:
        return False


def _check_v4l2_available() -> bool:
    """
    Check if v4l2 devices are available on Linux.
    
    Returns:
        bool: True if v4l2 devices are accessible
    """
    try:
        import glob
        import os
        
        # Check if /dev/video* devices exist
        video_devices = glob.glob('/dev/video*')
        if not video_devices:
            return False
        
        # Check if at least one device is readable
        for device in video_devices[:3]:  # Check first 3 devices
            if os.access(device, os.R_OK):
                return True
        
        return False
    except Exception:
        return False


def _check_windows_system32() -> bool:
    """
    Check if Windows System32 directory is accessible.
    
    Returns:
        bool: True if System32 is accessible
    """
    try:
        import os
        system32_path = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'System32')
        return os.path.exists(system32_path) and os.access(system32_path, os.R_OK)
    except Exception:
        return False


def _check_macos_avfoundation() -> bool:
    """
    Check if AVFoundation framework is available on macOS.
    
    Returns:
        bool: True if AVFoundation framework exists
    """
    try:
        import os
        avfoundation_path = '/System/Library/Frameworks/AVFoundation.framework'
        return os.path.exists(avfoundation_path)
    except Exception:
        return False


def print_platform_status() -> None:
    """Print comprehensive platform status information."""
    print("StableCam Platform Information")
    print("=" * 40)
    
    # Basic platform info
    info = get_platform_info()
    print(f"System: {info['system']} {info['release']}")
    print(f"Architecture: {info['architecture']}")
    print(f"Python: {info['python_version']} ({info['python_implementation']})")
    print()
    
    # Platform-specific status
    deps = check_platform_dependencies()
    if deps:
        print("Platform Dependencies:")
        for dep, available in deps.items():
            status = "✓" if available else "✗"
            print(f"  {status} {dep}")
        print()
    
    # Recommended dependencies
    recommended = get_recommended_dependencies()
    if recommended:
        print("Recommended Dependencies:")
        for dep in recommended:
            print(f"  - {dep}")
        print()
    
    # Installation instructions
    instructions = get_installation_instructions()
    current_platform = platform.system().lower()
    if current_platform == 'darwin':
        current_platform = 'macos'
    
    if current_platform in instructions:
        print("Installation Instructions:")
        for line in instructions[current_platform]:
            print(f"  {line}")


if __name__ == '__main__':
    print_platform_status()