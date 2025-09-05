#!/usr/bin/env python3
"""
Test script to verify package configuration and dependencies.
"""

import sys
import platform
import subprocess
from pathlib import Path
from typing import Dict, List


def test_package_installation():
    """Test that the package can be installed and imported."""
    print("Testing package configuration...")
    print(f"Python version: {sys.version}")
    print(f"Platform: {platform.system()} {platform.release()}")
    
    # Test basic import
    try:
        import stablecam
        print("✓ Basic import successful")
    except ImportError as e:
        print(f"✗ Basic import failed: {e}")
        return False
    
    # Test CLI entry point
    try:
        from stablecam.cli import main
        print("✓ CLI entry point accessible")
    except ImportError as e:
        print(f"✗ CLI entry point failed: {e}")
        return False
    
    # Test platform utilities
    try:
        from stablecam.platform_utils import get_platform_info, check_platform_dependencies
        platform_info = get_platform_info()
        print(f"✓ Platform detection working: {platform_info['system']}")
        
        deps_status = check_platform_dependencies()
        print(f"✓ Platform dependency check working: {len(deps_status)} items checked")
    except ImportError as e:
        print(f"✗ Platform utilities failed: {e}")
        return False
    
    return True


def test_platform_dependencies():
    """Test platform-specific dependencies."""
    print("\nTesting platform-specific dependencies...")
    
    system = platform.system().lower()
    
    if system == "linux":
        # Test Linux dependencies
        try:
            import pyudev
            print("✓ Linux core dependency (pyudev) available")
        except ImportError:
            print("⚠ Linux core dependency (pyudev) not available")
            print("  Install with: pip install pyudev")
        
        # Test optional Linux dependencies
        try:
            import v4l2
            print("✓ Linux enhanced dependency (v4l2-python) available")
        except ImportError:
            print("⚠ Linux enhanced dependency (v4l2-python) not available")
            print("  Install with: pip install 'stablecam[linux-enhanced]'")
    
    elif system == "windows":
        # Test Windows dependencies
        print("✓ Windows uses built-in APIs (no core dependencies required)")
        
        # Test optional Windows dependencies
        try:
            import wmi
            print("✓ Windows enhanced dependency (wmi) available")
        except ImportError:
            print("⚠ Windows enhanced dependency (wmi) not available")
            print("  Install with: pip install 'stablecam[windows-enhanced]'")
        
        try:
            import win32api
            print("✓ Windows enhanced dependency (pywin32) available")
        except ImportError:
            print("⚠ Windows enhanced dependency (pywin32) not available")
            print("  Install with: pip install 'stablecam[windows-enhanced]'")
    
    elif system == "darwin":
        # Test macOS dependencies
        print("✓ macOS uses built-in system tools (no core dependencies required)")
        
        # Test optional macOS dependencies
        try:
            import AVFoundation
            print("✓ macOS enhanced dependency (AVFoundation) available")
        except ImportError:
            print("⚠ macOS enhanced dependency (AVFoundation) not available")
            print("  Install with: pip install 'stablecam[macos-enhanced]'")
        
        try:
            import IOKit
            print("✓ macOS enhanced dependency (IOKit) available")
        except ImportError:
            print("⚠ macOS enhanced dependency (IOKit) not available")
            print("  Install with: pip install 'stablecam[macos-enhanced]'")
    
    # Test optional dependencies
    try:
        import textual
        print("✓ TUI dependency (textual) available")
    except ImportError:
        print("⚠ TUI dependency (textual) not available")
        print("  Install with: pip install 'stablecam[tui]'")
    
    return True


def test_entry_points():
    """Test that console scripts are properly configured."""
    print("\nTesting entry points...")
    
    try:
        # Test that the stablecam command is available
        result = subprocess.run(
            [sys.executable, "-c", "from stablecam.cli import main; main(['--help'])"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and "StableCam - Cross-platform USB camera monitoring" in result.stdout:
            print("✓ CLI help text correct")
        else:
            print("⚠ CLI help text may be incorrect")
            print(f"  Return code: {result.returncode}")
            print(f"  Got: {result.stdout[:100]}...")
            if result.stderr:
                print(f"  Error: {result.stderr[:100]}...")
            
    except Exception as e:
        print(f"✗ Entry point test failed: {e}")
        return False
    
    return True


def test_package_metadata():
    """Test that package metadata is correctly configured."""
    print("\nTesting package metadata...")
    
    try:
        import stablecam
        
        # Check if package has version info
        if hasattr(stablecam, '__version__'):
            print(f"✓ Package version: {stablecam.__version__}")
        else:
            print("⚠ Package version not set in __init__.py")
        
        # Check package structure
        package_dir = Path(stablecam.__file__).parent
        
        expected_modules = [
            "cli.py", "manager.py", "models.py", "registry.py", 
            "events.py", "platform_utils.py", "logging_config.py", "tui.py"
        ]
        
        for module in expected_modules:
            if (package_dir / module).exists():
                print(f"✓ Module {module} exists")
            else:
                print(f"✗ Module {module} missing")
        
        # Check backends directory
        backends_dir = package_dir / "backends"
        if backends_dir.exists():
            print("✓ Backends directory exists")
            
            expected_backends = ["__init__.py", "base.py", "linux.py", "windows.py", "macos.py", "exceptions.py"]
            for backend in expected_backends:
                if (backends_dir / backend).exists():
                    print(f"✓ Backend {backend} exists")
                else:
                    print(f"✗ Backend {backend} missing")
        else:
            print("✗ Backends directory missing")
        
        # Check py.typed file for type hints
        if (package_dir / "py.typed").exists():
            print("✓ Type hints marker (py.typed) exists")
        else:
            print("⚠ Type hints marker (py.typed) missing")
            
    except Exception as e:
        print(f"✗ Package metadata test failed: {e}")
        return False
    
    return True


def test_installation_extras():
    """Test that installation extras are properly configured."""
    print("\nTesting installation extras...")
    
    # Test that we can import setup configuration
    try:
        # Try importing setuptools first
        try:
            import setuptools
        except ImportError:
            print("⚠ setuptools not available, skipping setup.py test")
            return True
            
        from setup import get_platform_dependencies, get_platform_extras
        
        platform_deps = get_platform_dependencies()
        print(f"✓ Platform dependencies function works: {len(platform_deps)} deps")
        
        extras = get_platform_extras()
        expected_extras = ["tui", "dev", "test", "linux-enhanced", "windows-enhanced", "macos-enhanced", "all"]
        
        for extra in expected_extras:
            if extra in extras:
                print(f"✓ Extra '{extra}' configured with {len(extras[extra])} dependencies")
            else:
                print(f"✗ Extra '{extra}' missing")
        
        return True
        
    except Exception as e:
        print(f"✗ Installation extras test failed: {e}")
        return False


def test_pyproject_toml():
    """Test that pyproject.toml is properly configured."""
    print("\nTesting pyproject.toml configuration...")
    
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            print("⚠ Cannot test pyproject.toml - no TOML parser available")
            return True
    
    try:
        with open("pyproject.toml", "rb") as f:
            config = tomllib.load(f)
        
        # Check basic project info
        project = config.get("project", {})
        if project.get("name") == "stablecam":
            print("✓ Project name correctly set")
        else:
            print("✗ Project name incorrect or missing")
        
        # Check entry points
        scripts = project.get("scripts", {})
        if "stablecam" in scripts:
            print("✓ CLI entry point configured in pyproject.toml")
        else:
            print("✗ CLI entry point missing in pyproject.toml")
        
        # Check optional dependencies
        optional_deps = project.get("optional-dependencies", {})
        expected_extras = ["tui", "linux-enhanced", "windows-enhanced", "macos-enhanced", "dev", "test", "all"]
        
        for extra in expected_extras:
            if extra in optional_deps:
                print(f"✓ Optional dependency '{extra}' configured")
            else:
                print(f"✗ Optional dependency '{extra}' missing")
        
        return True
        
    except Exception as e:
        print(f"✗ pyproject.toml test failed: {e}")
        return False


if __name__ == "__main__":
    print("StableCam Package Configuration Test")
    print("=" * 40)
    
    success = True
    success &= test_package_installation()
    success &= test_platform_dependencies()
    success &= test_entry_points()
    success &= test_package_metadata()
    success &= test_installation_extras()
    success &= test_pyproject_toml()
    
    print("\n" + "=" * 40)
    if success:
        print("✓ All tests passed!")
        sys.exit(0)
    else:
        print("✗ Some tests failed!")
        sys.exit(1)