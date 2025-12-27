"""Tests for the built-in /download endpoint.

This module validates:
 - File download via query parameter and JSON body.
 - Security features (path traversal protection, allowed/blocked paths).
 - Error handling for missing files and directories.
"""

import pytest
from restkit_server import SimpleServer, RestCodes
from .mock_server import MyServer


class TestDownloadEndpoint:
    """Tests for the built-in /download endpoint."""

    @pytest.fixture()
    def temp_file(self, tmp_path):
        """Create a temporary file for download testing."""
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("Hello, this is test content!")
        return str(test_file)

    @pytest.fixture()
    def download_server(self):
        """Provide a SimpleServer instance for download testing."""
        server = MyServer(demo_mode=False)
        server.app.config['TESTING'] = True
        return server

    def test_download_with_query_param(self, download_server, temp_file):
        """Verify file download via query parameter works correctly."""
        client = download_server.app.test_client()
        response = client.get(f"/download?path={temp_file}")
        assert response.status_code == 200
        assert response.data == b"Hello, this is test content!"
        assert 'attachment' in response.headers.get('Content-Disposition', '')

    def test_download_with_json_body(self, download_server, temp_file):
        """Verify file download via JSON body works correctly."""
        client = download_server.app.test_client()
        response = client.get("/download", json={"path": temp_file})
        assert response.status_code == 200
        assert response.data == b"Hello, this is test content!"

    def test_download_no_path_provided(self, download_server):
        """Verify 400 error when no file path is provided."""
        client = download_server.app.test_client()
        response = client.get("/download")
        assert response.status_code == RestCodes.BAD_REQUEST.value
        assert "No file path provided" in response.get_json()['data']['error']

    def test_download_file_not_found(self, download_server):
        """Verify 404 error when file does not exist."""
        client = download_server.app.test_client()
        response = client.get("/download?path=/nonexistent/file.txt")
        assert response.status_code == RestCodes.NOT_FOUND.value
        assert "File not found" in response.get_json()['data']['error']

    def test_download_blocked_path(self, tmp_path):
        """Verify blocked paths are rejected with 403."""
        # Create a file in a directory we'll block
        blocked_dir = tmp_path / "blocked"
        blocked_dir.mkdir()
        blocked_file = blocked_dir / "secret.txt"
        blocked_file.write_text("secret content")

        class BlockedPathServer(SimpleServer):  # pylint: disable=C0115
            custom_flask_configs = {
                'BLOCKED_DOWNLOAD_PATHS': [str(blocked_dir)]
            }

        server = BlockedPathServer(demo_mode=False)
        server.app.config['TESTING'] = True
        client = server.app.test_client()

        response = client.get(f"/download?path={blocked_file}")
        assert response.status_code == RestCodes.FORBIDDEN.value
        assert "blocked" in response.get_json()['data']['error']

    def test_download_allowed_path(self, tmp_path):
        """Verify allowed paths whitelist works correctly."""
        # Create allowed and disallowed directories
        allowed_dir = tmp_path / "allowed"
        allowed_dir.mkdir()
        allowed_file = allowed_dir / "public.txt"
        allowed_file.write_text("public content")

        disallowed_dir = tmp_path / "disallowed"
        disallowed_dir.mkdir()
        disallowed_file = disallowed_dir / "private.txt"
        disallowed_file.write_text("private content")

        class AllowedPathServer(SimpleServer):  # pylint: disable=C0115
            custom_flask_configs = {
                'ALLOWED_DOWNLOAD_PATHS': [str(allowed_dir)]
            }

        server = AllowedPathServer(demo_mode=False)
        server.app.config['TESTING'] = True
        client = server.app.test_client()

        # Allowed file should work
        response = client.get(f"/download?path={allowed_file}")
        assert response.status_code == 200
        assert response.data == b"public content"

        # Disallowed file should be rejected
        response = client.get(f"/download?path={disallowed_file}")
        assert response.status_code == RestCodes.FORBIDDEN.value
        assert "not allowed" in response.get_json()['data']['error']

    def test_download_path_traversal_protection(self, tmp_path):
        """Verify path traversal attacks are prevented."""
        # Create a file and try to access it via path traversal
        allowed_dir = tmp_path / "public"
        allowed_dir.mkdir()
        allowed_file = allowed_dir / "safe.txt"
        allowed_file.write_text("safe content")

        secret_dir = tmp_path / "secret"
        secret_dir.mkdir()
        secret_file = secret_dir / "sensitive.txt"
        secret_file.write_text("sensitive data")

        class SecureServer(SimpleServer):  # pylint: disable=C0115
            custom_flask_configs = {
                'ALLOWED_DOWNLOAD_PATHS': [str(allowed_dir)]
            }

        server = SecureServer(demo_mode=False)
        server.app.config['TESTING'] = True
        client = server.app.test_client()

        # Try path traversal to access secret file from allowed dir
        traversal_path = str(allowed_dir / ".." / "secret" / "sensitive.txt")
        response = client.get(f"/download?path={traversal_path}")
        assert response.status_code == RestCodes.FORBIDDEN.value

    def test_download_directory_rejected(self, download_server, tmp_path):
        """Verify directories cannot be downloaded (only files)."""
        client = download_server.app.test_client()
        response = client.get(f"/download?path={tmp_path}")
        assert response.status_code == RestCodes.NOT_FOUND.value
        assert "File not found" in response.get_json()['data']['error']

    def test_download_preserves_filename(self, download_server, tmp_path):
        """Verify downloaded file has correct filename in Content-Disposition."""
        test_file = tmp_path / "my_document.pdf"
        test_file.write_bytes(b"PDF content")

        client = download_server.app.test_client()
        response = client.get(f"/download?path={test_file}")
        assert response.status_code == 200
        assert 'my_document.pdf' in response.headers.get('Content-Disposition', '')
