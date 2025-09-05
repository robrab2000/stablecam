"""
Centralized logging configuration for StableCam.

This module provides logging setup and configuration utilities to ensure
consistent logging across all StableCam components with appropriate log levels
and formatting.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional


class StableCamLogger:
    """
    Centralized logger configuration for StableCam.
    
    Provides consistent logging setup with file and console handlers,
    appropriate formatting, and configurable log levels.
    """
    
    _configured = False
    _log_file_path: Optional[Path] = None
    
    @classmethod
    def configure(
        cls,
        log_level: str = "INFO",
        log_file: Optional[Path] = None,
        console_output: bool = True,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5
    ) -> None:
        """
        Configure logging for StableCam.
        
        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Optional path to log file. Defaults to ~/.stablecam/stablecam.log
            console_output: Whether to output logs to console
            max_file_size: Maximum size of log file before rotation
            backup_count: Number of backup log files to keep
        """
        if cls._configured:
            return
        
        # Set up log file path
        if log_file is None:
            log_dir = Path.home() / ".stablecam"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / "stablecam.log"
        
        cls._log_file_path = log_file
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        
        # Clear any existing handlers
        root_logger.handlers.clear()
        
        # Create formatter
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Add file handler with rotation
        try:
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.DEBUG)  # File gets all messages
            root_logger.addHandler(file_handler)
        except Exception as e:
            # If file logging fails, continue with console only
            print(f"Warning: Could not set up file logging: {e}", file=sys.stderr)
        
        # Add console handler if requested
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            console_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
            root_logger.addHandler(console_handler)
        
        # Configure StableCam loggers
        cls._configure_stablecam_loggers()
        
        cls._configured = True
        
        # Log configuration success
        logger = logging.getLogger(__name__)
        logger.info(f"Logging configured - Level: {log_level}, File: {log_file}")
    
    @classmethod
    def _configure_stablecam_loggers(cls) -> None:
        """Configure specific loggers for StableCam modules."""
        # Set appropriate levels for different modules
        module_levels = {
            'stablecam.manager': logging.INFO,
            'stablecam.registry': logging.INFO,
            'stablecam.events': logging.INFO,
            'stablecam.backends': logging.INFO,
            'stablecam.backends.linux': logging.INFO,
            'stablecam.backends.windows': logging.INFO,
            'stablecam.backends.macos': logging.INFO,
            'stablecam.cli': logging.INFO,
            'stablecam.tui': logging.INFO,
        }
        
        for module_name, level in module_levels.items():
            logger = logging.getLogger(module_name)
            logger.setLevel(level)
    
    @classmethod
    def get_log_file_path(cls) -> Optional[Path]:
        """Get the current log file path."""
        return cls._log_file_path
    
    @classmethod
    def set_level(cls, level: str) -> None:
        """
        Change the logging level for all StableCam loggers.
        
        Args:
            level: New logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        log_level = getattr(logging, level.upper(), logging.INFO)
        
        # Update root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        
        # Update console handler if it exists
        for handler in root_logger.handlers:
            if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
                handler.setLevel(log_level)
        
        logger = logging.getLogger(__name__)
        logger.info(f"Logging level changed to {level.upper()}")


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    console_output: bool = True
) -> None:
    """
    Convenience function to set up StableCam logging.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        console_output: Whether to output logs to console
    """
    StableCamLogger.configure(
        log_level=log_level,
        log_file=log_file,
        console_output=console_output
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name)