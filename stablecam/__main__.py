"""
Entry point for running StableCam as a module.

This allows running the package with: python -m stablecam
"""

from .cli import main

if __name__ == '__main__':
    main()