"""Common logging setup utilities."""

from logging import getLogger, Logger, FileHandler, StreamHandler, Formatter
from datetime import datetime, timezone
import os

# TODO: add a way to select the log size and number of files to keep

LOGGERS = {}
MAIN_LOG_FILE = None


def setup_logger(name: str, stream_log_level: str = 'INFO') -> Logger:
    """
    this function will setup a logger and return it for use
    if the logger already exists, it will return the existing logger

    :param name: the name of the logger
    :type name: str
    :param stream_log_level: the log level for the stream handler, defaults to 'DEBUG'
    :type stream_log_level: str
    :return: the logger
    :rtype: Logger
    """
    global MAIN_LOG_FILE
    global LOGGERS

    if MAIN_LOG_FILE is None:
        # Create the log directory if it doesn't exist
        os.makedirs('log', exist_ok=True)
        # Set the main log file path
        MAIN_LOG_FILE = f'log/{name}_{datetime.now(timezone.utc).strftime("%Y-%m-%d_%H_%M")}.log'

    if name in LOGGERS.keys():
        return LOGGERS[name]

    new_logger = getLogger(name)
    new_logger.setLevel('DEBUG')
    LOGGERS[name] = new_logger
    formatter = Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    file_handler = FileHandler(MAIN_LOG_FILE)
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