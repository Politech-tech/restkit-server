"""Tests for the built-in /upload endpoint.

This module validates:
 - File upload functionality with custom filenames.
 - Security features (path traversal prevention, regex-based blocklist).
 - Upload directory creation and configuration.
"""

import io
import os
import pytest
from restkit_server import SimpleServer, RestCodes
from .mock_server import MyServer


class TestUploadEndpoint:
    """Tests for the built-in /upload endpoint."""

    @pytest.fixture()
    def upload_server(self, tmp_path):
        """Provide a SimpleServer instance with upload directory configured."""
        class UploadTestServer(SimpleServer):  # pylint: disable=C0115
            custom_flask_configs = {
                'UPLOAD_DIRECTORY_PATH': str(tmp_path / "uploads")
            }
        server = UploadTestServer(demo_mode=False)
        server.app.config['TESTING'] = True
        return server

    def test_upload_file_success(self, upload_server, tmp_path):
        """Verify basic file upload works correctly."""
        client = upload_server.app.test_client()
        data = {'file': (io.BytesIO(b"test file content"), 'test_file.txt')}
        response = client.post("/upload", data=data, content_type='multipart/form-data')

        assert response.status_code == RestCodes.CREATED.value
        result = response.get_json()
        assert result['data']['filename'] == 'test_file.txt'
        assert result['data']['size'] == len(b"test file content")
        assert 'path' in result['data']

        # Verify file was actually saved
        saved_path = result['data']['path']
        assert os.path.exists(saved_path)
        with open(saved_path, 'rb') as f:
            assert f.read() == b"test file content"

    def test_upload_with_custom_filename(self, upload_server):
        """Verify upload with custom filename works."""
        client = upload_server.app.test_client()
        data = {
            'file': (io.BytesIO(b"custom name test"), 'original.txt'),
            'filename': 'custom_name.txt'
        }
        response = client.post("/upload", data=data, content_type='multipart/form-data')

        assert response.status_code == RestCodes.CREATED.value
        result = response.get_json()
        assert result['data']['filename'] == 'custom_name.txt'

    def test_upload_no_file_provided(self, upload_server):
        """Verify 400 error when no file is provided."""
        client = upload_server.app.test_client()
        response = client.post("/upload", data={}, content_type='multipart/form-data')

        assert response.status_code == RestCodes.BAD_REQUEST.value
        assert "No file provided" in response.get_json()['data']['error']

    def test_upload_empty_filename(self, upload_server):
        """Verify 400 error when file has empty filename."""
        client = upload_server.app.test_client()
        data = {'file': (io.BytesIO(b"content"), '')}
        response = client.post("/upload", data=data, content_type='multipart/form-data')

        assert response.status_code == RestCodes.BAD_REQUEST.value
        assert "No file selected" in response.get_json()['data']['error']

    def test_upload_blocked_pattern_exe(self, tmp_path):
        """Verify .exe files are blocked when pattern is configured."""
        class BlockedPatternServer(SimpleServer):  # pylint: disable=C0115
            custom_flask_configs = {
                'UPLOAD_DIRECTORY_PATH': str(tmp_path / "uploads"),
                'UPLOAD_BLOCKED_PATTERNS': [r'\.exe$', r'\.bat$']
            }
        server = BlockedPatternServer(demo_mode=False)
        server.app.config['TESTING'] = True
        client = server.app.test_client()

        data = {'file': (io.BytesIO(b"malicious content"), 'malware.exe')}
        response = client.post("/upload", data=data, content_type='multipart/form-data')

        assert response.status_code == RestCodes.FORBIDDEN.value
        assert "blocked pattern" in response.get_json()['data']['error']

    def test_upload_blocked_pattern_hidden_files(self, tmp_path):
        """Verify hidden files (starting with .) are blocked."""
        class BlockedHiddenServer(SimpleServer):  # pylint: disable=C0115
            custom_flask_configs = {
                'UPLOAD_DIRECTORY_PATH': str(tmp_path / "uploads"),
                'UPLOAD_BLOCKED_PATTERNS': [r'^\.']  # Block files starting with .
            }
        server = BlockedHiddenServer(demo_mode=False)
        server.app.config['TESTING'] = True
        client = server.app.test_client()

        data = {'file': (io.BytesIO(b"hidden content"), '.htaccess')}
        response = client.post("/upload", data=data, content_type='multipart/form-data')

        assert response.status_code == RestCodes.FORBIDDEN.value

    def test_upload_allowed_file_with_patterns(self, tmp_path):
        """Verify allowed files pass through when blocked patterns are configured."""
        class PatternServer(SimpleServer):  # pylint: disable=C0115
            custom_flask_configs = {
                'UPLOAD_DIRECTORY_PATH': str(tmp_path / "uploads"),
                'UPLOAD_BLOCKED_PATTERNS': [r'\.exe$', r'\.bat$']
            }
        server = PatternServer(demo_mode=False)
        server.app.config['TESTING'] = True
        client = server.app.test_client()

        # .txt files should be allowed
        data = {'file': (io.BytesIO(b"safe content"), 'document.txt')}
        response = client.post("/upload", data=data, content_type='multipart/form-data')

        assert response.status_code == RestCodes.CREATED.value

    def test_upload_path_traversal_prevention(self, upload_server):
        """Verify path traversal in filename is prevented."""
        client = upload_server.app.test_client()

        # Try path traversal in filename
        data = {'file': (io.BytesIO(b"traversal attempt"), '../../../etc/passwd')}
        response = client.post("/upload", data=data, content_type='multipart/form-data')

        # Should succeed but filename should be sanitized to just 'passwd'
        assert response.status_code == RestCodes.CREATED.value
        result = response.get_json()
        assert result['data']['filename'] == 'passwd'
        # The file should be in the upload directory, not /etc/
        assert 'uploads' in result['data']['path']

    def test_upload_backslash_traversal(self, upload_server):
        """Verify Windows-style path traversal is prevented."""
        client = upload_server.app.test_client()

        data = {'file': (io.BytesIO(b"content"), '..\\..\\windows\\system32\\file.txt')}
        response = client.post("/upload", data=data, content_type='multipart/form-data')

        assert response.status_code == RestCodes.CREATED.value
        result = response.get_json()
        # Should strip path components
        assert '..' not in result['data']['filename']
        assert '\\' not in result['data']['filename']

    def test_upload_creates_directory(self, tmp_path):
        """Verify upload directory is created if it doesn't exist."""
        new_upload_dir = tmp_path / "new_uploads_dir"
        assert not new_upload_dir.exists()

        class NewDirServer(SimpleServer):  # pylint: disable=C0115
            custom_flask_configs = {
                'UPLOAD_DIRECTORY_PATH': str(new_upload_dir)
            }
        server = NewDirServer(demo_mode=False)
        server.app.config['TESTING'] = True
        client = server.app.test_client()

        data = {'file': (io.BytesIO(b"content"), 'test.txt')}
        response = client.post("/upload", data=data, content_type='multipart/form-data')

        assert response.status_code == RestCodes.CREATED.value
        assert new_upload_dir.exists()

    def test_upload_default_directory(self):
        """Verify default upload directory is used when not configured."""
        server = MyServer(demo_mode=False)
        server.app.config['TESTING'] = True
        client = server.app.test_client()

        data = {'file': (io.BytesIO(b"default dir content"), 'default_test.txt')}
        response = client.post("/upload", data=data, content_type='multipart/form-data')

        assert response.status_code == RestCodes.CREATED.value
        result = response.get_json()
        assert 'uploads' in result['data']['path']

    def test_upload_case_insensitive_pattern(self, tmp_path):
        """Verify regex patterns are case-insensitive."""
        class CaseServer(SimpleServer):  # pylint: disable=C0115
            custom_flask_configs = {
                'UPLOAD_DIRECTORY_PATH': str(tmp_path / "uploads"),
                'UPLOAD_BLOCKED_PATTERNS': [r'\.exe$']
            }
        server = CaseServer(demo_mode=False)
        server.app.config['TESTING'] = True
        client = server.app.test_client()

        # .EXE (uppercase) should also be blocked
        data = {'file': (io.BytesIO(b"content"), 'malware.EXE')}
        response = client.post("/upload", data=data, content_type='multipart/form-data')

        assert response.status_code == RestCodes.FORBIDDEN.value

    def test_upload_multiple_patterns(self, tmp_path):
        """Verify multiple blocked patterns work correctly."""
        class MultiPatternServer(SimpleServer):  # pylint: disable=C0115
            custom_flask_configs = {
                'UPLOAD_DIRECTORY_PATH': str(tmp_path / "uploads"),
                'UPLOAD_BLOCKED_PATTERNS': [r'\.exe$', r'\.bat$', r'\.sh$', r'\.php$']
            }
        server = MultiPatternServer(demo_mode=False)
        server.app.config['TESTING'] = True
        client = server.app.test_client()

        blocked_files = ['test.exe', 'script.bat', 'run.sh', 'backdoor.php']
        for filename in blocked_files:
            data = {'file': (io.BytesIO(b"content"), filename)}
            response = client.post("/upload", data=data, content_type='multipart/form-data')
            assert response.status_code == RestCodes.FORBIDDEN.value, f"{filename} should be blocked"

        # Allowed file
        data = {'file': (io.BytesIO(b"content"), 'document.txt')}
        response = client.post("/upload", data=data, content_type='multipart/form-data')
        assert response.status_code == RestCodes.CREATED.value
