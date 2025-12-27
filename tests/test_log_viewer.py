"""Tests for list_logs and log viewer endpoints.

This module validates:
 - Log file listing functionality.
 - Log viewer endpoint with path and query parameters.
 - Case-insensitive filename matching.
 - Security features (path traversal protection).
"""

import os
import pytest
from restkit_server import RestCodes
from .mock_server import MyServer


@pytest.fixture()
def simple_server():
    """Provide a configured instance of MyServer with Flask test mode enabled."""
    server = MyServer(demo_mode=True)
    server.app.config['TESTING'] = True
    yield server


class TestLogViewer:
    """Tests for list_logs and log viewer endpoints."""

    def test_list_logs_returns_log_files(self, simple_server):
        """Verify list_logs endpoint returns log files from logging directory."""
        client = simple_server.app.test_client()
        response = client.get("/list_logs")

        assert response.status_code == RestCodes.OK.value
        data = response.get_json()['data']
        # Should return a list
        assert isinstance(data, list)
        # At least one log file should exist (created by the server)
        assert len(data) > 0
        # All returned files should have .log extension
        for log_file in data:
            assert '.log' in log_file.lower()

    def test_log_viewer_default_log(self, simple_server):
        """Verify /logs returns the current log file content when no file specified."""
        client = simple_server.app.test_client()
        response = client.get("/logs")

        assert response.status_code == 200
        assert response.content_type == 'text/plain; charset=utf-8'
        # Should contain some log content
        assert len(response.data) > 0

    def test_log_viewer_with_path_parameter(self, simple_server):
        """Verify /logs/<filename> returns specific log file."""
        client = simple_server.app.test_client()

        # First get the list of logs
        list_response = client.get("/list_logs")
        logs = list_response.get_json()['data']
        assert len(logs) > 0

        # Request a specific log file via path (use lowercase to avoid redirect)
        log_file = logs[0].lower()
        response = client.get(f"/logs/{log_file}")

        assert response.status_code == 200
        assert response.content_type == 'text/plain; charset=utf-8'

    def test_log_viewer_with_query_parameter(self, simple_server):
        """Verify /logs?log_file=filename works."""
        client = simple_server.app.test_client()

        # First get the list of logs
        list_response = client.get("/list_logs")
        logs = list_response.get_json()['data']
        assert len(logs) > 0

        # Request a specific log file via query parameter
        log_file = logs[0]
        response = client.get(f"/logs?log_file={log_file}")

        assert response.status_code == 200
        assert response.content_type == 'text/plain; charset=utf-8'

    def test_log_viewer_case_insensitive(self, simple_server):
        """Verify log viewer handles case-insensitive filenames (URL lowercasing)."""
        client = simple_server.app.test_client()

        # First get the list of logs
        list_response = client.get("/list_logs")
        logs = list_response.get_json()['data']
        assert len(logs) > 0

        # Request with lowercase filename (simulating URL normalization)
        log_file = logs[0]
        response = client.get(f"/logs/{log_file.lower()}")

        assert response.status_code == 200
        assert response.content_type == 'text/plain; charset=utf-8'

    def test_log_viewer_file_not_found(self, simple_server):
        """Verify 404 response for non-existent log file."""
        client = simple_server.app.test_client()
        response = client.get("/logs/nonexistent_file_12345.log")

        assert response.status_code == RestCodes.NOT_FOUND.value
        assert response.get_json()['data']['error'] == "Log file not found"

    def test_log_viewer_path_traversal_blocked(self, simple_server):
        """Verify path traversal attempts are blocked."""
        client = simple_server.app.test_client()

        # Try to access file outside logging directory
        response = client.get("/logs/../../../etc/passwd")
        assert response.status_code == RestCodes.NOT_FOUND.value

        response = client.get("/logs/..%2F..%2Fetc%2Fpasswd")
        assert response.status_code == RestCodes.NOT_FOUND.value

    def test_log_viewer_content_matches_file(self, simple_server):
        """Verify log viewer returns actual file content."""
        client = simple_server.app.test_client()

        # Write something to the log
        simple_server.logger.info("TEST_MARKER_FOR_LOG_VIEWER_TEST")

        # Get the log content
        response = client.get("/logs")

        assert response.status_code == 200
        assert b"TEST_MARKER_FOR_LOG_VIEWER_TEST" in response.data

    def test_list_logs_only_returns_log_files(self, simple_server, tmp_path):
        """Verify list_logs filters out non-log files."""
        # Create some non-log files in the logging directory
        log_dir = simple_server._logging_dir

        # Create a non-log file
        non_log_file = os.path.join(log_dir, "readme.txt")
        with open(non_log_file, 'w') as f:
            f.write("test")

        try:
            client = simple_server.app.test_client()
            response = client.get("/list_logs")

            data = response.get_json()['data']
            # readme.txt should not be in the list
            assert "readme.txt" not in data
            # All files should have .log extension
            for log_file in data:
                assert '.log' in log_file.lower()
        finally:
            # Cleanup
            if os.path.exists(non_log_file):
                os.remove(non_log_file)
