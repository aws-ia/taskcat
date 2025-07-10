"""
TaskCat Logging Module

This module provides custom logging functionality for TaskCat with colored output
and specialized formatting. It includes ANSI color codes for terminal output and
custom log level formatting to provide a consistent and visually appealing
command-line interface.

The logging system supports different log levels with distinct colors and provides
special formatting for TaskCat-specific operations like S3 interactions.
"""

import logging

# Initialize module-level logger
LOG = logging.getLogger(__name__)


class PrintMsg:
    """
    ANSI color codes and formatted log level strings for terminal output.
    
    This class provides consistent color coding across the TaskCat CLI interface.
    Each log level has its own color scheme to help users quickly identify
    different types of messages.
    
    Color Attributes:
        header: Red background for headers
        highlight: White background for highlighting
        name_color: Blue background for name tags
        aqua: Cyan background for debug messages
        green: Green background for success messages
        white: White background for info messages
        orange: Yellow background for warnings
        red: Red background for errors
        rst_color: Reset color code to return to default
    
    Formatted Log Levels:
        Each log level includes color coding and consistent spacing for alignment
    """
    
    # ANSI color code definitions
    header = "\x1b[1;41;0m"        # Bold red background
    highlight = "\x1b[0;30;47m"    # Black text on white background
    name_color = "\x1b[0;37;44m"   # White text on blue background
    aqua = "\x1b[0;30;46m"         # Black text on cyan background
    green = "\x1b[0;30;42m"        # Black text on green background
    white = "\x1b[0;30;47m"        # Black text on white background
    orange = "\x1b[0;30;43m"       # Black text on yellow background
    red = "\x1b[0;30;41m"          # Black text on red background
    rst_color = "\x1b[0m"          # Reset to default colors
    
    # Formatted log level strings with consistent spacing
    CRITICAL = "{}[FATAL  ]{} : ".format(red, rst_color)
    ERROR = "{}[ERROR  ]{} : ".format(red, rst_color)
    DEBUG = "{}[DEBUG  ]{} : ".format(aqua, rst_color)
    PASS = "{}[PASS   ]{} : ".format(green, rst_color)
    INFO = "{}[INFO   ]{} : ".format(white, rst_color)
    WARNING = "{}[WARN   ]{} : ".format(orange, rst_color)
    
    # Special formatting for TaskCat branding
    NAMETAG = "{1}{0}{2}".format("taskcat", name_color, rst_color)
    
    # Special formatting for S3 operations
    S3 = "{}[S3: -> ]{} ".format(white, rst_color)
    S3DELETE = "{}[S3: DELETE ]{} ".format(white, rst_color)


class AppFilter(logging.Filter):
    """
    Custom logging filter to add color formatting to log records.
    
    This filter processes each log record and adds a 'color_loglevel' attribute
    that contains the appropriately colored log level string. It allows for
    custom formatting on a per-record basis by checking for special attributes.
    """
    
    def filter(self, record):
        """
        Process a log record and add color formatting.
        
        Args:
            record (logging.LogRecord): The log record to process
            
        Returns:
            bool: Always returns True to allow the record to be processed
        """
        # Check if this record has a custom nametag (for special formatting)
        if "nametag" in dir(record):
            record.color_loglevel = record.nametag
        else:
            # Use the standard colored log level based on the record's level
            record.color_loglevel = getattr(PrintMsg, record.levelname)
        
        return True


def init_taskcat_cli_logger(loglevel=None):
    """
    Initialize and configure the TaskCat CLI logger with colored output.
    
    Sets up a logger with custom formatting that includes ANSI color codes
    for terminal output. The logger uses a custom filter to add color
    information to each log record.
    
    Args:
        loglevel (str, optional): The logging level to set. Can be any standard
                                 logging level name (DEBUG, INFO, WARNING, ERROR, CRITICAL).
                                 If not provided, the logger level is not explicitly set.
    
    Returns:
        logging.Logger: Configured logger instance ready for use
        
    Example:
        >>> logger = init_taskcat_cli_logger('INFO')
        >>> logger.info("This will appear with colored formatting")
    """
    # Get the logger for the TaskCat package
    log = logging.getLogger(__package__)
    
    # Create a stream handler for console output
    cli_handler = logging.StreamHandler()
    
    # Set up custom formatter that uses the color_loglevel attribute
    formatter = logging.Formatter("%(color_loglevel)s%(message)s")
    cli_handler.setFormatter(formatter)
    
    # Add the custom filter to inject color information
    cli_handler.addFilter(AppFilter())
    
    # Attach the handler to the logger
    log.addHandler(cli_handler)
    
    # Set the log level if provided
    if loglevel:
        # Convert string level name to numeric level
        loglevel = getattr(logging, loglevel.upper(), 20)  # Default to INFO (20) if invalid
        log.setLevel(loglevel)
    
    return log
