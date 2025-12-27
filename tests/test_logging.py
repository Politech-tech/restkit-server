"""Tests for logging functionality.

This module validates:
 - Logging functionality including verbosity control and enter/exit tracing.
 - Logger level changes via set_verbose.
 - Unit methods using server's logger in AdvancedServer.
"""

import logging
from .mock_server import MyServer, MyAdvancedServer, Fizz, Foo


class TestLogging:
    """Tests for logging functionality including verbosity control and enter/exit tracing."""

    def test_verbose_mode_enables_debug_logging(self):
        """Verify that verbose=True sets logger and handlers to DEBUG level."""
        server = MyServer(demo_mode=False, verbose=True)

        # Check that logger is at DEBUG level
        assert server.logger.level == logging.DEBUG

        # Check that all handlers are at DEBUG level
        for handler in server.logger.handlers:
            assert handler.level == logging.DEBUG

        assert server.verbose is True

    def test_non_verbose_mode_uses_info_logging(self):
        """Verify that verbose=False sets logger and handlers to INFO level."""
        server = MyServer(demo_mode=False, verbose=False)

        # Check that logger is at INFO level
        assert server.logger.level == logging.INFO

        # Check that all handlers are at INFO level
        for handler in server.logger.handlers:
            assert handler.level == logging.INFO

        assert server.verbose is False

    def test_set_verbose_changes_log_level(self):
        """Verify that set_verbose dynamically changes logging levels."""
        server = MyServer(demo_mode=False, verbose=False)

        # Initially INFO
        assert server.logger.level == logging.INFO
        assert server.verbose is False

        # Change to DEBUG
        server.set_verbose(True)
        assert server.logger.level == logging.DEBUG
        assert server.verbose is True
        for handler in server.logger.handlers:
            assert handler.level == logging.DEBUG

        # Change back to INFO
        server.set_verbose(False)
        assert server.logger.level == logging.INFO
        assert server.verbose is False
        for handler in server.logger.handlers:
            assert handler.level == logging.INFO

    def test_enter_exit_logging_in_verbose_mode(self, caplog):
        """Verify that enter/exit logging appears in verbose mode."""
        server = MyServer(demo_mode=False, verbose=True)
        client = server.app.test_client()

        with caplog.at_level(logging.DEBUG):
            response = client.get("/hello_world")

        # Check that the endpoint was called successfully
        assert response.status_code == 200

        # Check that enter/exit logs are present
        log_messages = [record.message for record in caplog.records]
        assert any("Entering" in msg and "hello_world" in msg for msg in log_messages), \
            "Expected to find 'Entering hello_world' in debug logs"
        assert any("Exiting" in msg and "hello_world" in msg for msg in log_messages), \
            "Expected to find 'Exiting hello_world' in debug logs"

    def test_no_enter_exit_logging_in_non_verbose_mode(self, caplog):
        """Verify that enter/exit logging does NOT appear when verbose=False."""
        server = MyServer(demo_mode=False, verbose=False)
        client = server.app.test_client()

        with caplog.at_level(logging.DEBUG):
            response = client.get("/hello_world")

        # Check that the endpoint was called successfully
        assert response.status_code == 200

        # Check that enter/exit logs are NOT present (they're DEBUG level)
        log_messages = [record.message for record in caplog.records if record.levelno == logging.DEBUG]
        assert not any("Entering" in msg and "hello_world" in msg for msg in log_messages), \
            "Should not find 'Entering hello_world' debug logs when verbose=False"
        assert not any("Exiting" in msg and "hello_world" in msg for msg in log_messages), \
            "Should not find 'Exiting hello_world' debug logs when verbose=False"

    def test_advanced_server_unit_methods_use_server_logger(self, caplog):
        """Verify that unit methods in AdvancedServer use the server's logger."""
        server = MyAdvancedServer(
            demo_mode=False,
            verbose=True,
            unit_instances={'foo': Foo(), 'fizz': Fizz()},
            app_name="TestAdvancedServer"
        )
        client = server.app.test_client()

        with caplog.at_level(logging.DEBUG):
            response = client.get("/foo/bar")

        # Check that the endpoint was called successfully
        assert response.status_code == 200

        # Check that enter/exit logs use the server's logger name
        log_messages = [(record.name, record.message) for record in caplog.records]

        # Find the enter/exit logs for the foo.bar method
        enter_logs = [msg for name, msg in log_messages if "Entering" in msg and "bar" in msg]
        exit_logs = [msg for name, msg in log_messages if "Exiting" in msg and "bar" in msg]

        assert len(enter_logs) > 0, "Expected to find 'Entering bar' log"
        assert len(exit_logs) > 0, "Expected to find 'Exiting bar' log"

        # Verify logger name is MyAdvancedServer (the class name used for the logger)
        server_logger_records = [record for record in caplog.records if record.name == "MyAdvancedServer"]
        assert len(server_logger_records) > 0, "Expected logs from MyAdvancedServer logger"

    def test_multiple_unit_methods_all_log_correctly(self, caplog):
        """Verify that multiple unit methods all produce enter/exit logs."""
        server = MyAdvancedServer(
            demo_mode=False,
            verbose=True,
            unit_instances={'foo': Foo(), 'fizz': Fizz()},
            app_name="TestMultiUnit"
        )
        client = server.app.test_client()

        with caplog.at_level(logging.DEBUG):
            response1 = client.get("/foo/bar")
            response2 = client.get("/fizz/buzz")
            response3 = client.get("/hello")

        # All should succeed
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response3.status_code == 200

        log_messages = [record.message for record in caplog.records]

        # Check for foo/bar logs
        assert any("Entering" in msg and "bar" in msg for msg in log_messages)
        assert any("Exiting" in msg and "bar" in msg for msg in log_messages)

        # Check for fizz/buzz logs
        assert any("Entering" in msg and "buzz" in msg for msg in log_messages)
        assert any("Exiting" in msg and "buzz" in msg for msg in log_messages)

        # Check for hello logs
        assert any("Entering" in msg and "hello" in msg for msg in log_messages)
        assert any("Exiting" in msg and "hello" in msg for msg in log_messages)

    def test_logger_captures_function_arguments(self, caplog):
        """Verify that enter/exit logger captures function arguments."""
        server = MyAdvancedServer(
            demo_mode=False,
            verbose=True,
            unit_instances={'foo': Foo(), 'fizz': Fizz()},
            app_name="TestArgs"
        )
        client = server.app.test_client()

        with caplog.at_level(logging.DEBUG):
            response = client.get("/foo/echo", json={'var1': 'test_value', 'var2': 42})

        assert response.status_code == 200

        log_messages = [record.message for record in caplog.records]

        # Check that the entering log contains kwargs information
        enter_logs = [msg for msg in log_messages if "Entering" in msg and "echo" in msg]
        assert len(enter_logs) > 0

        # The enter log should mention kwargs
        assert any("kwargs" in msg for msg in enter_logs)
