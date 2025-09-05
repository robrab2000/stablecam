"""
Setup configuration for StableCam package.

This setup.py is maintained for backward compatibility.
The primary configuration is in pyproject.toml.
"""

import sys
import platform
from setuptools import setup, find_packages

# Read README for long description
try:
    with open("README.md", "r", encoding="utf-8") as fh:
        long_description = fh.read()
except FileNotFoundError:
    long_description = "Cross-platform USB camera monitoring with persistent anchoring"

# Platform-specific dependencies
def get_platform_dependencies():
    """Get platform-specific dependencies based on the current system."""
    deps = []
    
    system = platform.system().lower()
    
    if system == "linux":
        # Linux requires pyudev for proper USB device detection
        deps.extend([
            "pyudev>=0.21.0",  # For USB device information via udev
        ])
        # v4l2-python is optional enhancement (requires system libraries)
    elif system == "windows":
        # Windows uses built-in WMI and PowerShell APIs, no additional deps needed
        # Optional enhanced dependencies are available via extras_require
        pass
    elif system == "darwin":
        # macOS uses built-in system_profiler and ioreg, no additional deps needed
        # Optional enhanced dependencies are available via extras_require
        pass
    
    return deps


def get_platform_extras():
    """Get platform-specific extra dependencies."""
    extras = {
        "tui": [
            "textual>=0.41.0",  # Terminal UI framework
        ],
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
            "pytest-mock>=3.0",
            "black>=22.0",
            "flake8>=4.0",
            "mypy>=0.900",
            "types-click>=7.0",
            "ruff>=0.1.0",
        ],
        "test": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
            "pytest-mock>=3.0",
            "pytest-xdist>=2.0",
        ],
    }
    
    # Platform-specific enhanced support
    extras["linux-enhanced"] = [
        "v4l2-python>=0.2.0; sys_platform == 'linux'",
    ]
    
    extras["windows-enhanced"] = [
        "wmi>=1.5.1; sys_platform == 'win32'",
        "pywin32>=227; sys_platform == 'win32'",
    ]
    
    extras["macos-enhanced"] = [
        "pyobjc-framework-AVFoundation>=8.0; sys_platform == 'darwin'",
        "pyobjc-framework-IOKit>=8.0; sys_platform == 'darwin'",
    ]
    
    # All optional features combined
    extras["all"] = [
        "textual>=0.41.0",
        "v4l2-python>=0.2.0; sys_platform == 'linux'",
        "wmi>=1.5.1; sys_platform == 'win32'",
        "pywin32>=227; sys_platform == 'win32'",
        "pyobjc-framework-AVFoundation>=8.0; sys_platform == 'darwin'",
        "pyobjc-framework-IOKit>=8.0; sys_platform == 'darwin'",
    ]
    
    return extras

# Core dependencies required on all platforms
install_requires = [
    "click>=8.0.0",  # CLI framework
] + get_platform_dependencies()

setup(
    name="stablecam",
    version="0.1.0",
    author="StableCam Development Team",
    description="Cross-platform USB camera monitoring with persistent anchoring",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/stablecam/stablecam",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Video :: Capture",
        "Topic :: System :: Hardware :: Hardware Drivers",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="camera usb video capture monitoring cross-platform",
    python_requires=">=3.8",
    install_requires=install_requires,
    extras_require=get_platform_extras(),
    entry_points={
        "console_scripts": [
            "stablecam=stablecam.cli:main",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/stablecam/stablecam/issues",
        "Source": "https://github.com/stablecam/stablecam",
        "Documentation": "https://github.com/stablecam/stablecam#readme",
    },
    # Include package data
    package_data={
        "stablecam": ["py.typed"],
    },
    # Ensure packages are found correctly
    zip_safe=False,
)