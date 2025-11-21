"""
Unit tests for restkit_server.logger module.
Tests the custom logging utilities including TimedAndSizedRotatingFileHandler,
setup_logger, enter_exit_logger decorator, and LoggerWriter.
"""

import logging
import os
import tempfile
import shutil
import pytest
import time

from restkit_server.logger import (
    TimedAndSizedRotatingFileHandler,
    setup_logger,
    enter_exit_logger,
    LoggerWriter,
    LOGGERS
)


@pytest.fixture
def test_dir():
    """Create a temporary directory for tests."""
    temp_dir = tempfile.mkdtemp()
    # Reset globals
    from restkit_server import logger as logger_module
    logger_module.MAIN_LOG_FILE = None
    LOGGERS.clear()
    
    yield temp_dir
    
    # Cleanup: Close all logger handlers first
    for logger_inst in LOGGERS.values():
        handlers = logger_inst.handlers[:]
        for handler in handlers:
            handler.close()
            logger_inst.removeHandler(handler)
    LOGGERS.clear()
    
    # Now remove the directory
    if os.path.exists(temp_dir):
        try:
            shutil.rmtree(temp_dir)
        except PermissionError:
            # On Windows, sometimes files are still locked
            pass


@pytest.fixture
def log_file(test_dir):
    """Create a log file path in the test directory."""
    return os.path.join(test_dir, "test.log")


class TestTimedAndSizedRotatingFileHandler:
    """Test cases for TimedAndSizedRotatingFileHandler."""

    def test_handler_initialization(self, log_file):
        """Test handler initializes with correct parameters."""
        handler = TimedAndSizedRotatingFileHandler(
            filename=log_file,
            when='D',
            interval=1,
            backupCount=5,
            maxBytes=1024 * 1024
        )
        
        assert handler.maxBytes == 1024 * 1024
        assert handler.backupCount == 5
        handler.close()

    def test_should_rollover_time_condition(self, log_file):
        """Test rollover triggers on time condition."""
        handler = TimedAndSizedRotatingFileHandler(
            filename=log_file,
            when='S',  # Seconds for quick testing
            interval=1,
            backupCount=3,
            maxBytes=10000  # Large size to not trigger
        )
        
        # Write initial record
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Test message", args=(), exc_info=None
        )
        handler.emit(record)
        
        # Wait for time to pass
        time.sleep(2)
        
        # Should rollover based on time
        should_roll = handler.shouldRollover(record)
        handler.close()
        
        assert should_roll is True

    def test_should_rollover_size_condition(self, log_file):
        """Test rollover triggers on size condition."""
        handler = TimedAndSizedRotatingFileHandler(
            filename=log_file,
            when='D',  # Daily, won't trigger
            interval=1,
            backupCount=3,
            maxBytes=50  # Small size to trigger quickly
        )
        
        # Write records to exceed size limit
        for i in range(10):
            record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="", lineno=0,
                msg="Test message with some content " * 5, args=(), exc_info=None
            )
            handler.emit(record)
        
        # Create a new record to check rollover
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Check rollover", args=(), exc_info=None
        )
        
        should_roll = handler.shouldRollover(record)
        handler.close()
        
        assert should_roll is True

    def test_should_not_rollover_neither_condition(self, log_file):
        """Test no rollover when neither condition is met."""
        handler = TimedAndSizedRotatingFileHandler(
            filename=log_file,
            when='D',  # Daily
            interval=1,
            backupCount=3,
            maxBytes=10000  # Large size
        )
        
        # Write a small record
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Small message", args=(), exc_info=None
        )
        handler.emit(record)
        
        # Check immediately - should not rollover
        should_roll = handler.shouldRollover(record)
        handler.close()
        
        assert should_roll is False

    def test_maxbytes_zero_disables_size_rotation(self, log_file):
        """Test that maxBytes=0 disables size-based rotation."""
        handler = TimedAndSizedRotatingFileHandler(
            filename=log_file,
            when='D',
            interval=1,
            backupCount=3,
            maxBytes=0  # Disabled
        )
        
        # Write many records
        for i in range(100):
            record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="", lineno=0,
                msg="Test message " * 10, args=(), exc_info=None
            )
            handler.emit(record)
        
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Check", args=(), exc_info=None
        )
        
        # Should not rollover based on size
        should_roll = handler.shouldRollover(record)
        handler.close()
        
        # Will only be true if time condition is met (shouldn't be for 'D')
        assert should_roll is False


class TestSetupLogger:
    """Test cases for setup_logger function."""

    def test_logger_creation_basic(self, test_dir):
        """Test basic logger creation."""
        test_logger = setup_logger(
            "test_logger",
            directory_path=test_dir
        )
        
        assert test_logger is not None
        assert test_logger.name == "test_logger"
        assert test_logger.level == logging.DEBUG
        assert "test_logger" in LOGGERS

    def test_logger_directory_creation(self, test_dir):
        """Test that log directory is created if it doesn't exist."""
        log_dir = os.path.join(test_dir, "logs", "nested")
        setup_logger(
            "test_logger",
            directory_path=log_dir
        )
        
        assert os.path.exists(log_dir)

    def test_logger_stream_level_configuration(self, test_dir):
        """Test stream handler level configuration."""
        test_logger = setup_logger(
            "test_logger",
            directory_path=test_dir,
            stream_log_level='ERROR'
        )
        
        # Find stream handler
        stream_handler = None
        for handler in test_logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, TimedAndSizedRotatingFileHandler):
                stream_handler = handler
                break
        
        assert stream_handler is not None
        assert stream_handler.level == logging.ERROR

    def test_logger_with_max_file_size(self, test_dir):
        """Test logger with max file size configuration."""
        max_size = 1024 * 1024  # 1 MB
        test_logger = setup_logger(
            "test_logger",
            directory_path=test_dir,
            max_file_size=max_size
        )
        
        # Find file handler
        file_handler = None
        for handler in test_logger.handlers:
            if isinstance(handler, TimedAndSizedRotatingFileHandler):
                file_handler = handler
                break
        
        assert file_handler is not None
        assert file_handler.maxBytes == max_size

    def test_logger_with_backup_files(self, test_dir):
        """Test logger with backup count configuration."""
        backup_count = 10
        test_logger = setup_logger(
            "test_logger",
            directory_path=test_dir,
            max_backup_files=backup_count
        )
        
        # Find file handler
        file_handler = None
        for handler in test_logger.handlers:
            if isinstance(handler, TimedAndSizedRotatingFileHandler):
                file_handler = handler
                break
        
        assert file_handler is not None
        assert file_handler.backupCount == backup_count

    def test_logger_with_interval(self, test_dir):
        """Test logger with custom interval."""
        test_logger = setup_logger(
            "test_logger",
            directory_path=test_dir,
            intervarl=7  # Note: parameter name has typo in source
        )
        
        # Find file handler
        file_handler = None
        for handler in test_logger.handlers:
            if isinstance(handler, TimedAndSizedRotatingFileHandler):
                file_handler = handler
                break
        
        assert file_handler is not None
        # interval=7 means 7 days, which is 7 * 24 * 60 * 60 = 604800 seconds
        assert file_handler.interval == 604800

    def test_duplicate_logger_returns_same_instance(self, test_dir):
        """Test that requesting same logger returns same instance."""
        logger1 = setup_logger("test_logger", directory_path=test_dir)
        logger2 = setup_logger("test_logger", directory_path=test_dir)
        
        assert logger1 is logger2

    def test_logger_has_correct_handlers(self, test_dir):
        """Test that logger has both stream and file handlers."""
        test_logger = setup_logger("test_logger", directory_path=test_dir)
        
        handler_types = [type(handler).__name__ for handler in test_logger.handlers]
        
        assert 'StreamHandler' in handler_types
        assert 'TimedAndSizedRotatingFileHandler' in handler_types

    def test_main_log_file_global_set(self, test_dir):
        """Test that MAIN_LOG_FILE global is set correctly."""
        from restkit_server import logger as logger_module
        
        setup_logger("test_logger", directory_path=test_dir)
        
        assert logger_module.MAIN_LOG_FILE is not None
        assert logger_module.MAIN_LOG_FILE.endswith(".log")

    def test_logger_with_none_parameters(self, test_dir):
        """Test logger creation with None optional parameters."""
        test_logger = setup_logger(
            "test_logger",
            directory_path=test_dir,
            max_file_size=None,
            max_backup_files=None
        )
        
        # Should create logger successfully with defaults
        assert test_logger is not None
        
        # Find file handler and check defaults
        file_handler = None
        for handler in test_logger.handlers:
            if isinstance(handler, TimedAndSizedRotatingFileHandler):
                file_handler = handler
                break
        
        assert file_handler is not None
        # Default maxBytes should be 0 (no size limit)
        assert file_handler.maxBytes == 0

    def test_logger_actual_logging(self, test_dir, caplog):
        """Test that logger actually writes messages."""
        with caplog.at_level(logging.INFO):
            test_logger = setup_logger("test_logger", directory_path=test_dir)
            test_message = "Test log message"
            
            test_logger.info(test_message)
        
        # Check that message was logged
        assert test_message in caplog.text


class TestEnterExitLogger:
    """Test cases for enter_exit_logger decorator."""

    def test_decorator_logs_enter_exit(self, test_dir, caplog):
        """Test that decorator logs function entry and exit."""
        with caplog.at_level(logging.DEBUG):
            setup_logger("test_logger", directory_path=test_dir)
            
            @enter_exit_logger('test_logger')
            def test_function():
                return "result"
            
            # Execute function
            result = test_function()
        
        # Verify result is correct
        assert result == "result"
        
        # Check logs - use func.__qualname__ which includes full qualified name
        assert "Entering" in caplog.text and "test_function" in caplog.text
        assert "Exiting" in caplog.text and "test_function" in caplog.text

    def test_decorator_logs_arguments(self, test_dir, caplog):
        """Test that decorator logs function arguments."""
        with caplog.at_level(logging.DEBUG):
            setup_logger("test_logger", directory_path=test_dir)
            
            @enter_exit_logger('test_logger')
            def test_function(arg1, arg2, kwarg1=None):
                return arg1 + arg2
            
            # Execute function with arguments
            test_function(5, 10, kwarg1="test")
        
        # Check logs
        assert "Entering" in caplog.text and "test_function" in caplog.text
        assert "(5, 10)" in caplog.text
        assert "kwarg1" in caplog.text and "test" in caplog.text

    def test_decorator_hides_self_parameter(self, test_dir, caplog):
        """Test that decorator hides 'self' parameter from logs."""
        with caplog.at_level(logging.DEBUG):
            setup_logger("test_logger", directory_path=test_dir)
            
            class TestClass:
                @enter_exit_logger('test_logger')
                def test_method(self, arg1):
                    return arg1 * 2
            
            obj = TestClass()
            obj.test_method(5)
        
        # Should show args starting from first real parameter
        assert "Entering" in caplog.text and "test_method" in caplog.text
        assert "('<self>', 5)" in caplog.text or "(5,)" in caplog.text

    def test_decorator_preserves_function_metadata(self):
        """Test that decorator preserves function name and docstring."""
        @enter_exit_logger('test_logger')
        def test_function():
            """Test docstring."""
            return "result"
        
        assert test_function.__name__ == "test_function"
        assert test_function.__doc__ == "Test docstring."

    def test_decorator_handles_exceptions(self, test_dir, caplog):
        """Test that decorator logs entry but not exit when exception occurs."""
        with caplog.at_level(logging.DEBUG):
            setup_logger("test_logger", directory_path=test_dir)
            
            @enter_exit_logger('test_logger')
            def test_function():
                raise ValueError("Test error")
            
            # Execute function and catch exception
            with pytest.raises(ValueError):
                test_function()
        
        # Enter should be logged, but exit won't be (no try/finally in decorator)
        assert "Entering" in caplog.text and "test_function" in caplog.text
        # Exit is not logged when exception occurs
        assert "Exiting" not in caplog.text

    def test_decorator_with_return_value(self):
        """Test that decorator properly returns function result."""
        @enter_exit_logger('test_logger')
        def test_function(x, y):
            return x + y
        
        result = test_function(3, 7)
        assert result == 10

    def test_decorator_with_no_arguments(self, test_dir, caplog):
        """Test decorator with function that has no arguments."""
        with caplog.at_level(logging.DEBUG):
            setup_logger("test_logger", directory_path=test_dir)
            
            @enter_exit_logger('test_logger')
            def test_function():
                return 42
            
            test_function()
        
        assert "Entering" in caplog.text and "test_function" in caplog.text
        assert "args: ()" in caplog.text


class TestLoggerWriter:
    """Test cases for LoggerWriter class."""

    def test_writer_initialization(self, test_dir):
        """Test LoggerWriter initializes correctly."""
        test_logger = setup_logger("test_logger", directory_path=test_dir)
        writer = LoggerWriter(test_logger, logging.INFO)
        
        assert writer.logger == test_logger
        assert writer.level == logging.INFO
        assert writer._buffer == ""

    def test_writer_write_message(self, test_dir, caplog):
        """Test LoggerWriter writes message to logger."""
        with caplog.at_level(logging.INFO):
            test_logger = setup_logger("test_logger", directory_path=test_dir)
            writer = LoggerWriter(test_logger, logging.INFO)
            
            test_message = "Test message from writer"
            writer.write(test_message)
        
        assert test_message in caplog.text

    def test_writer_strips_trailing_whitespace(self, test_dir, caplog):
        """Test LoggerWriter strips trailing whitespace from messages."""
        with caplog.at_level(logging.INFO):
            test_logger = setup_logger("test_logger", directory_path=test_dir)
            writer = LoggerWriter(test_logger, logging.INFO)
            
            writer.write("Test message\n\n")
        
        # Should contain "Test message" but not extra newlines as separate logs
        assert "Test message" in caplog.text
        # Count occurrences of "Test message" - should be exactly one
        assert caplog.text.count("Test message") == 1

    def test_writer_ignores_empty_messages(self, test_dir, caplog):
        """Test LoggerWriter ignores empty messages after stripping."""
        with caplog.at_level(logging.INFO):
            test_logger = setup_logger("test_logger", directory_path=test_dir)
            writer = LoggerWriter(test_logger, logging.INFO)
            
            # Write some empty/whitespace messages
            writer.write("")
            writer.write("   ")
            writer.write("\n")
            
            # Write a real message
            writer.write("Real message")
        
        # Should only contain the real message
        assert "Real message" in caplog.text
        # Should not have empty log entries
        log_records = [r for r in caplog.records if r.levelno == logging.INFO]
        assert len(log_records) == 1

    def test_writer_flush_is_noop(self, test_dir):
        """Test that flush method exists and doesn't raise errors."""
        test_logger = setup_logger("test_logger", directory_path=test_dir)
        writer = LoggerWriter(test_logger, logging.INFO)
        
        # Should not raise any exception
        writer.flush()

    def test_writer_different_log_levels(self, test_dir, caplog):
        """Test LoggerWriter with different log levels."""
        with caplog.at_level(logging.INFO):
            test_logger = setup_logger("test_logger", directory_path=test_dir)
            
            info_writer = LoggerWriter(test_logger, logging.INFO)
            error_writer = LoggerWriter(test_logger, logging.ERROR)
            
            info_writer.write("Info message")
            error_writer.write("Error message")
        
        # Both messages should be present
        assert "Info message" in caplog.text
        assert "Error message" in caplog.text
        # Should have different level indicators
        assert "INFO" in caplog.text
        assert "ERROR" in caplog.text

    def test_writer_with_multiline_message(self, test_dir, caplog):
        """Test LoggerWriter with message containing newlines."""
        with caplog.at_level(logging.INFO):
            test_logger = setup_logger("test_logger", directory_path=test_dir)
            writer = LoggerWriter(test_logger, logging.INFO)
            
            # Write message with newline in the middle
            writer.write("First line\nSecond line")
        
        # The message is stripped and logged as-is
        assert "First line" in caplog.text
