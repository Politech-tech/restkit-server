# Logger Utilities

Centralized logging utilities with advanced features including time and size-based log rotation, function entry/exit tracing, and stream redirection.

> 🏠 [Back to README](README.md) | 🖥️ [Server Utilities Guide](server_utils.md)

## Features

- **Dual Rotation**: Logs rotate based on either time or file size
- **Function Tracing**: Decorator to log function entry/exit with arguments
- **Stream Redirection**: Redirect stdout/stderr to logger
- **Global Registry**: Reuse loggers across your application

## Quick Start

### Basic Logger Setup

```python
from restkit_server.logger import setup_logger

# Create a logger
logger = setup_logger('my_app')

# Use it
logger.info("Application started")
logger.debug("Debug information")
logger.error("Something went wrong")
```

### Custom Configuration

```python
from restkit_server.logger import setup_logger

logger = setup_logger(
    name='my_app',
    directory_path='logs',              # Log directory (default: 'log')
    stream_log_level='INFO',            # Console log level (default: 'INFO')
    intervarl=7,                        # Rotate every 7 days (default: 1)
    max_file_size=10 * 1024 * 1024,    # Max 10MB per file (default: None)
    max_backup_files=5                  # Keep 5 backup files (default: None)
)

logger.info("Configured logger with custom settings")
```

## Function Entry/Exit Logging

Use the `@enter_exit_logger` decorator to automatically log when functions are called and return:

```python
from restkit_server import setup_logger, enter_exit_logger

# Setup logger first
setup_logger('my_app')

# Decorate your functions
@enter_exit_logger('my_app')
def calculate(x, y):
    """Calculate sum of two numbers."""
    return x + y

@enter_exit_logger('my_app')
def process_data(data, verbose=False):
    """Process some data."""
    return len(data)

# Use functions normally
result = calculate(10, 20)
items = process_data([1, 2, 3], verbose=True)
```

**Output:**
```
DEBUG - Entering calculate, args: (10, 20), kwargs={}
DEBUG - Exiting calculate
DEBUG - Entering process_data, args: ([1, 2, 3],), kwargs={'verbose': True}
DEBUG - Exiting process_data
```

## Stream Redirection

Redirect stdout/stderr to your logger:

```python
import sys
from restkit_server import setup_logger, LoggerWriter

logger = setup_logger('my_app')

# Redirect stdout to INFO level
sys.stdout = LoggerWriter(logger, logger.INFO)

# Redirect stderr to ERROR level
sys.stderr = LoggerWriter(logger, logger.ERROR)

# Now print statements go to the logger
print("This will be logged at INFO level")
```

## Log Rotation

### Time-Based Rotation
Logs automatically rotate daily (default) or at custom intervals:

```python
# Rotate every 7 days
logger = setup_logger('my_app', intervarl=7)
```

### Size-Based Rotation
Logs rotate when they reach a maximum size:

```python
# Rotate when log file reaches 5MB
logger = setup_logger(
    'my_app',
    max_file_size=5 * 1024 * 1024,
    max_backup_files=3  # Keep 3 old files
)
```

### Dual Rotation (Time AND Size)
Logs rotate when EITHER condition is met:

```python
logger = setup_logger(
    'my_app',
    intervarl=1,                      # Daily rotation
    max_file_size=10 * 1024 * 1024,  # OR when reaching 10MB
    max_backup_files=7                # Keep 7 backups
)
```

## Reusing Loggers

Loggers are automatically cached. Calling `setup_logger` with the same name returns the existing logger:

```python
# First call creates the logger
logger1 = setup_logger('my_app')

# Second call returns the same logger
logger2 = setup_logger('my_app')

assert logger1 is logger2  # True
```

## Log Levels

From most to least verbose:
- `DEBUG`: Detailed diagnostic information
- `INFO`: General informational messages
- `WARNING`: Warning messages for potentially harmful situations
- `ERROR`: Error messages for serious problems
- `CRITICAL`: Critical messages for very serious errors

```python
logger.debug("Detailed debug information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred")
logger.critical("Critical failure")
```

## Complete Example

```python
from restkit_server.logger import setup_logger, enter_exit_logger

# Setup logger with rotation
logger = setup_logger(
    name='my_service',
    directory_path='logs',
    stream_log_level='INFO',
    intervarl=1,
    max_file_size=5 * 1024 * 1024,
    max_backup_files=7
)

@enter_exit_logger('my_service')
def startup_service(config_path):
    """Start the service with given config."""
    logger.info(f"Loading configuration from {config_path}")
    
    try:
        # Service startup logic
        logger.info("Service started successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to start service: {e}")
        return False

@enter_exit_logger('my_service')
def process_request(request_id, data):
    """Process incoming request."""
    logger.debug(f"Processing request {request_id}")
    
    # Request processing logic
    result = {"status": "success", "processed": len(data)}
    
    logger.info(f"Request {request_id} completed")
    return result

# Use the service
if startup_service('/etc/config.json'):
    result = process_request('REQ-001', [1, 2, 3, 4, 5])
    logger.info(f"Result: {result}")
```

## Notes

- The first logger created sets the log file path for all subsequent loggers
- Log files are named with timestamp: `{name}_{YYYY-MM-DD_HH_MM}.log`
- Setting `max_file_size=None` or `0` disables size-based rotation
- The `@enter_exit_logger` decorator logs at DEBUG level
- All file logs are at DEBUG level; stream (console) logs are at INFO level by default
