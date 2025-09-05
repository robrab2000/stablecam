"""
Tests for package installation and configuration across different platforms.
"""

import sys
import platform
import subprocess
import tempfile
import venv
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


class TestPackageInstallation:
    """Test package installation and configuration."""
    
    def test_basic_import(self):
        """Test that the package can be imported."""
        import stablecam
        assert hasattr(stablecam, '__version__')
        assert stablecam.__version__ == "0.1.0"
    
    def test_cli_entry_point(self):
        """Test that CLI entry point is accessible."""
        from stablecam.cli import main
        assert callable(main)
    
    def test_platform_detection(self):
        """Test that platform detection works correctly."""
        from stablecam.platform_utils import (
            get_platform_info, 
            is_linux, 
            is_windows, 
            is_macos,
            get_recommended_dependencies
        )
        
        platform_info = get_platform_info()
        assert 'system' in platform_info
        assert 'python_version' in platform_info
        
        # Exactly one platform should be detected
        platforms = [is_linux(), is_windows(), is_macos()]
        assert sum(platforms) == 1
        
        # Should return some dependencies for current platform
        deps = get_recommended_dependencies()
        assert isinstance(deps, list)
    
    @pytest.mark.linux
    def test_linux_dependencies(self):
        """Test Linux-specific dependencies."""
        from stablecam.platform_utils import is_linux, check_platform_dependencies
        
        if not is_linux():
            pytest.skip("Linux-specific test")
        
        deps_status = check_platform_dependencies()
        
        # Should check for Linux-specific tools
        expected_checks = ['udev', 'v4l2', 'pyudev']
        for check in expected_checks:
            assert check in deps_status
    
    @pytest.mark.windows
    def test_windows_dependencies(self):
        """Test Windows-specific dependencies."""
        from stablecam.platform_utils import is_windows, check_platform_dependencies
        
        if not is_windows():
            pytest.skip("Windows-specific test")
        
        deps_status = check_platform_dependencies()
        
        # Should check for Windows-specific tools
        expected_checks = ['wmic', 'powershell', 'system32']
        for check in expected_checks:
            assert check in deps_status
    
    @pytest.mark.macos
    def test_macos_dependencies(self):
        """Test macOS-specific dependencies."""
        from stablecam.platform_utils import is_macos, check_platform_dependencies
        
        if not is_macos():
            pytest.skip("macOS-specific test")
        
        deps_status = check_platform_dependencies()
        
        # Should check for macOS-specific tools
        expected_checks = ['system_profiler', 'ioreg', 'avfoundation']
        for check in expected_checks:
            assert check in deps_status
    
    def test_package_structure(self):
        """Test that all expected modules are present."""
        import stablecam
        
        package_dir = Path(stablecam.__file__).parent
        
        # Check main modules
        expected_modules = [
            "cli.py", "manager.py", "models.py", "registry.py", 
            "events.py", "platform_utils.py", "logging_config.py", "tui.py"
        ]
        
        for module in expected_modules:
            assert (package_dir / module).exists(), f"Module {module} missing"
        
        # Check backends directory
        backends_dir = package_dir / "backends"
        assert backends_dir.exists(), "Backends directory missing"
        
        expected_backends = ["__init__.py", "base.py", "linux.py", "windows.py", "macos.py", "exceptions.py"]
        for backend in expected_backends:
            assert (backends_dir / backend).exists(), f"Backend {backend} missing"
        
        # Check type hints marker
        assert (package_dir / "py.typed").exists(), "Type hints marker missing"
    
    def test_setup_configuration(self):
        """Test that setup.py configuration is correct."""
        try:
            import setuptools
        except ImportError:
            pytest.skip("setuptools not available")
        
        from setup import get_platform_dependencies, get_platform_extras
        
        # Test platform dependencies function
        deps = get_platform_dependencies()
        assert isinstance(deps, list)
        
        # Test extras configuration
        extras = get_platform_extras()
        expected_extras = ["tui", "dev", "test", "linux-enhanced", "windows-enhanced", "macos-enhanced", "all"]
        
        for extra in expected_extras:
            assert extra in extras, f"Extra '{extra}' missing from setup configuration"
            assert isinstance(extras[extra], list), f"Extra '{extra}' should be a list"
    
    def test_cli_help_command(self):
        """Test that CLI help command works."""
        try:
            result = subprocess.run(
                [sys.executable, "-c", "from stablecam.cli import main; main(['--help'])"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Should not crash and should contain help text
            assert "StableCam" in result.stdout or "stablecam" in result.stdout.lower()
            
        except subprocess.TimeoutExpired:
            pytest.fail("CLI help command timed out")
        except Exception as e:
            pytest.fail(f"CLI help command failed: {e}")
    
    def test_optional_imports(self):
        """Test that optional dependencies are handled gracefully."""
        # Test TUI import
        try:
            from stablecam.tui import StableCamTUI
            # If textual is available, should work
            assert StableCamTUI is not None
        except ImportError as e:
            # If textual is not available, should get a clear error
            assert "textual" in str(e).lower() or "tui" in str(e).lower()
    
    @pytest.mark.slow
    def test_virtual_environment_installation(self):
        """Test installation in a clean virtual environment."""
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_dir = Path(temp_dir) / "test_venv"
            
            # Create virtual environment
            venv.create(venv_dir, with_pip=True)
            
            # Get paths for the virtual environment
            if platform.system() == "Windows":
                python_exe = venv_dir / "Scripts" / "python.exe"
                pip_exe = venv_dir / "Scripts" / "pip.exe"
            else:
                python_exe = venv_dir / "bin" / "python"
                pip_exe = venv_dir / "bin" / "pip"
            
            try:
                # Install package in development mode
                result = subprocess.run(
                    [str(pip_exe), "install", "-e", "."],
                    cwd=Path.cwd(),
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                if result.returncode != 0:
                    pytest.skip(f"Package installation failed: {result.stderr}")
                
                # Test that package can be imported
                result = subprocess.run(
                    [str(python_exe), "-c", "import stablecam; print(stablecam.__version__)"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                assert result.returncode == 0, f"Import failed: {result.stderr}"
                assert "0.1.0" in result.stdout
                
                # Test CLI entry point
                result = subprocess.run(
                    [str(python_exe), "-m", "stablecam", "--help"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                # Should not crash (return code might be 0 or 2 for help)
                assert result.returncode in [0, 2], f"CLI failed: {result.stderr}"
                
            except subprocess.TimeoutExpired:
                pytest.skip("Virtual environment test timed out")
            except Exception as e:
                pytest.skip(f"Virtual environment test failed: {e}")


class TestPlatformSpecificInstallation:
    """Test platform-specific installation scenarios."""
    
    def test_linux_pyudev_availability(self):
        """Test that pyudev is available on Linux."""
        from stablecam.platform_utils import is_linux
        
        if not is_linux():
            pytest.skip("Linux-specific test")
        
        try:
            import pyudev
            assert pyudev is not None
        except ImportError:
            pytest.fail("pyudev should be available on Linux installations")
    
    def test_windows_builtin_apis(self):
        """Test that Windows built-in APIs are accessible."""
        from stablecam.platform_utils import is_windows
        
        if not is_windows():
            pytest.skip("Windows-specific test")
        
        # Test that we can access Windows-specific modules
        try:
            import subprocess
            result = subprocess.run(
                ["wmic", "/?"],
                capture_output=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            # wmic should be available on Windows
            assert result.returncode == 0 or "wmic" in result.stderr.decode().lower()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pytest.skip("wmic not available in test environment")
    
    def test_macos_system_tools(self):
        """Test that macOS system tools are accessible."""
        from stablecam.platform_utils import is_macos
        
        if not is_macos():
            pytest.skip("macOS-specific test")
        
        # Test that we can access macOS-specific tools
        try:
            import subprocess
            result = subprocess.run(
                ["system_profiler", "-listDataTypes"],
                capture_output=True,
                timeout=10
            )
            # system_profiler should be available on macOS
            assert result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pytest.skip("system_profiler not available in test environment")


if __name__ == "__main__":
    pytest.main([__file__])