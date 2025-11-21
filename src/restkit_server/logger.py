"""Common logging setup utilities."""

from logging import getLogger, Logger, StreamHandler, Formatter
from datetime import datetime, timezone
from logging.handlers import TimedRotatingFileHandler
import os

# TODO: add a way to select the log size and number of files to keep

LOGGERS = {}
MAIN_LOG_FILE = None


class TimedAndSizedRotatingFileHandler(TimedRotatingFileHandler):
    """
    Handler that rotates based on both time and file size.
    """
    def __init__(self, filename, when='midnight', interval=1, backupCount=0, 
                 maxBytes=0, encoding=None, delay=False, utc=False):
        super().__init__(filename, when, interval, backupCount, encoding, delay, utc)
        self.maxBytes = maxBytes
        
    def shouldRollover(self, record):
        """
        Determine if rollover should occur.
        Returns True if either time-based or size-based rollover is needed.
        """
        # Check time-based rollover
        if super().shouldRollover(record):
            return True
            
        # Check size-based rollover
        if self.maxBytes > 0:
            msg = "%s\n" % self.format(record)
            self.stream.seek(0, 2)  # Seek to end
            if self.stream.tell() + len(msg) >= self.maxBytes:
                return True
                
        return False


def setup_logger(name: str,
                 directory_path: str = 'log',
                 stream_log_level: str = 'INFO',
                 intervarl: int = 1,
                 max_file_size: int | None = None,
                 max_backup_files: int | None = None) -> Logger:
    """
    this function will setup a logger and return it for use
    if the logger already exists, it will return the existing logger

    :param name: the name of the logger
    :type name: str
    :param directory_path: the directory path for the log files, defaults to 'log'
    :type directory_path: str
    :param stream_log_level: the log level for the stream handler, defaults to 'DEBUG'
    :type stream_log_level: str
    :param intervarl: the interval in days for time-based log rotation, defaults to None
    :type intervarl: int | None
    :param max_file_size: the maximum file size in bytes for size-based log rotation, defaults to None
    :type max_file_size: int | None
    :param max_backup_files: the maximum number of backup files to keep, defaults to None
    :type max_backup_files: int | None
    :return: the logger
    :rtype: Logger
    """
    global MAIN_LOG_FILE
    global LOGGERS

    if MAIN_LOG_FILE is None:
        # Create the log directory if it doesn't exist
        os.makedirs(directory_path, exist_ok=True)
        # Set the main log file path
        MAIN_LOG_FILE = f'{directory_path}/{name}_{datetime.now(timezone.utc).strftime("%Y-%m-%d_%H_%M")}.log'

    if name in LOGGERS.keys():
        return LOGGERS[name]

    new_logger = getLogger(name)
    new_logger.setLevel('DEBUG')
    
    if max_file_size is None:
        # No size limit 
        max_file_size = 0

    LOGGERS[name] = new_logger
    formatter = Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    file_handler = TimedAndSizedRotatingFileHandler(MAIN_LOG_FILE, 
                                                    interval=intervarl,
                                                    maxBytes=max_file_size,
                                                    backupCount=max_backup_files)
    file_handler.name = 'file_handler'
    file_handler.setLevel('DEBUG')
    file_handler.setFormatter(formatter)
    new_logger.addHandler(file_handler)

    stream_handler = StreamHandler()
    stream_handler.setLevel(stream_log_level)
    stream_handler.setFormatter(formatter)
    new_logger.addHandler(stream_handler)

    return new_logger


def enter_exit_logger(logger):
    """
    this function will log the entry and exit of a function
    :param logger: the logger name to use
    :type logger: str
    :return: the decorator
    :rtype: function
    """
    from functools import wraps
    logger = getLogger(logger)
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):

            if len(args) > 0 and hasattr(args[0].__class__, func.__name__):
                print_args = ('<self>',) + args[1:]
            else:
                print_args = args

            logger.debug(f'Entering {func.__qualname__}, args: {print_args}, {kwargs=}')
            result = func(*args, **kwargs)
            logger.debug(f'Exiting {func.__qualname__}')
            return result
        return wrapper
    return decorator


class LoggerWriter:
    """
    This class is a wrapper around a logger that allows it to be used as a stream writer.

    Usage:
        logger = setup_logger('my_logger')
        sys.stdout = LoggerWriter(logger, 'INFO')
        sys.stderr = LoggerWriter(logger, 'ERROR')

    """
    def __init__(self, logger, level):
        self.logger = logger
        self.level = level
        self._buffer = ""

    def write(self, message):
        """
        Write a message to the logger.

        :param message: the message to log
        :type message: str
        """
        message = message.rstrip()
        if message:
            self.logger.log(self.level, message)

    def flush(self):
        """
        this function is here in name only, it is not used.
        it is a no-op for compatibility
        """
        pass 