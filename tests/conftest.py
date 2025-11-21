"""Shared pytest configuration and fixtures for all tests."""

import pytest


@pytest.fixture(scope="function", autouse=True)
def reset_logger_state():
    """Reset logger globals between all tests to avoid cross-contamination."""
    from restkit_server import logger as logger_module
    from restkit_server.logger import LOGGERS
    
    # Reset before test
    logger_module.MAIN_LOG_FILE = None
    LOGGERS.clear()
    
    yield
    
    # Clean up after test
    for logger_inst in LOGGERS.values():
        handlers = logger_inst.handlers[:]
        for handler in handlers:
            try:
                handler.close()
                logger_inst.removeHandler(handler)
            except Exception:
                pass
    
    LOGGERS.clear()
    logger_module.MAIN_LOG_FILE = None
