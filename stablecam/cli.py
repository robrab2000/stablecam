"""
Command-line interface for StableCam.

This module provides CLI commands for registering cameras and listing devices
using the StableCam library API.
"""

import sys
import click
from typing import Optional

from .manager import StableCam
from .backends import PlatformDetectionError
from .registry import RegistryError


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """
    StableCam - Cross-platform USB camera monitoring with persistent anchoring.
    
    Manage USB cameras with stable IDs that persist across disconnections
    and port changes.
    """
    pass


@cli.command()
@click.option(
    '--registry-path', 
    type=click.Path(),
    help='Custom path for the device registry file'
)
def register(registry_path: Optional[str]):
    """
    Register the first detected camera with a stable ID.
    
    Detects connected USB cameras and registers the first one found,
    assigning it a persistent stable ID for future reference.
    """
    try:
        # Initialize StableCam manager
        manager = StableCam(registry_path=registry_path)
        
        # Detect cameras
        click.echo("Detecting USB cameras...")
        devices = manager.detect()
        
        if not devices:
            click.echo("No USB cameras detected.", err=True)
            sys.exit(1)
        
        # Register the first detected camera
        first_device = devices[0]
        click.echo(f"Found camera: {first_device.label}")
        
        try:
            stable_id = manager.register(first_device)
            click.echo(f"✓ Camera registered with stable ID: {stable_id}")
            
            # Show device details
            click.echo("\nDevice details:")
            click.echo(f"  Stable ID: {stable_id}")
            click.echo(f"  Label: {first_device.label}")
            click.echo(f"  System Index: {first_device.system_index}")
            click.echo(f"  Vendor ID: {first_device.vendor_id}")
            click.echo(f"  Product ID: {first_device.product_id}")
            if first_device.serial_number:
                click.echo(f"  Serial Number: {first_device.serial_number}")
            if first_device.port_path:
                click.echo(f"  Port Path: {first_device.port_path}")
                
        except RegistryError as e:
            click.echo(f"Registration failed: {e}", err=True)
            sys.exit(1)
            
    except PlatformDetectionError as e:
        click.echo(f"Camera detection failed: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    '--registry-path', 
    type=click.Path(),
    help='Custom path for the device registry file'
)
def monitor(registry_path: Optional[str]):
    """
    Launch the terminal UI for real-time camera monitoring.
    
    Opens an interactive terminal interface that displays all registered
    cameras with their stable IDs, connection status, and real-time updates
    when devices connect or disconnect.
    """
    try:
        from .tui import run_tui
        run_tui(registry_path=registry_path)
    except ImportError as e:
        click.echo(f"TUI dependencies not available: {e}", err=True)
        click.echo("Install with: pip install 'stablecam[tui]'", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"TUI error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    '--registry-path', 
    type=click.Path(),
    help='Custom path for the device registry file'
)
@click.option(
    '--format', 
    'output_format',
    type=click.Choice(['table', 'json']),
    default='table',
    help='Output format for device list'
)
def list(registry_path: Optional[str], output_format: str):
    """
    List all registered devices with their stable IDs and current status.
    
    Shows all cameras that have been registered with StableCam, including
    their stable IDs, connection status, and device information.
    """
    try:
        # Initialize StableCam manager
        manager = StableCam(registry_path=registry_path)
        
        # Get all registered devices
        devices = manager.list()
        
        if not devices:
            click.echo("No registered devices found.")
            return
        
        if output_format == 'json':
            import json
            device_data = []
            for device in devices:
                device_data.append({
                    'stable_id': device.stable_id,
                    'label': device.device_info.label,
                    'status': device.status.value,
                    'system_index': device.device_info.system_index,
                    'vendor_id': device.device_info.vendor_id,
                    'product_id': device.device_info.product_id,
                    'serial_number': device.device_info.serial_number,
                    'port_path': device.device_info.port_path,
                    'registered_at': device.registered_at.isoformat() if device.registered_at else None,
                    'last_seen': device.last_seen.isoformat() if device.last_seen else None
                })
            click.echo(json.dumps(device_data, indent=2))
        else:
            # Table format
            click.echo(f"Found {len(devices)} registered device(s):\n")
            
            # Header
            click.echo(f"{'Stable ID':<15} {'Status':<12} {'System Index':<12} {'Label':<30}")
            click.echo("-" * 70)
            
            # Device rows
            for device in devices:
                status_indicator = "●" if device.status.value == "connected" else "○"
                status_text = f"{status_indicator} {device.status.value}"
                
                system_index = str(device.device_info.system_index) if device.device_info.system_index is not None else "N/A"
                
                click.echo(f"{device.stable_id:<15} {status_text:<12} {system_index:<12} {device.device_info.label:<30}")
            
            # Show detailed info if requested
            click.echo(f"\nUse 'stablecam list --format json' for detailed device information.")
            
    except Exception as e:
        click.echo(f"Error listing devices: {e}", err=True)
        sys.exit(1)


def main(args=None):
    """Main entry point for the CLI."""
    cli(args)


if __name__ == '__main__':
    main()