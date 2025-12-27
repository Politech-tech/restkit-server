"""Tests for endpoint path conflict detection and custom Flask configuration.

This module validates:
 - Endpoint path conflict detection with case-insensitive routing.
 - Custom Flask configuration feature (custom_flask_configs).
"""

import pytest
from restkit_server import SimpleServer, AdvancedServer


class TestEndpointPathConflicts:
    """Tests for endpoint path conflict detection with case-insensitive routing."""

    def test_method_name_conflict_raises_error(self):
        """Verify that methods with names that conflict when lowercased raise ValueError."""
        with pytest.raises(ValueError, match="Endpoint path conflict.*already registered.*case-insensitive"):
            class ConflictingServer(SimpleServer):  # pylint: disable=C0115
                def hello_world(self):  # pylint: disable=C0116
                    return {"message": "First method"}

                def Hello_World(self):  # pylint: disable=C0116  # Conflicts with hello_world when lowercased
                    return {"message": "Second method"}

    def test_property_name_conflict_raises_error(self):
        """Verify that properties with names that conflict when lowercased raise ValueError."""
        with pytest.raises(ValueError, match="Endpoint path conflict.*already registered.*case-insensitive"):
            class ConflictingPropertiesServer(SimpleServer):  # pylint: disable=C0115
                @property
                def my_property(self):  # pylint: disable=C0116
                    return {"value": "First"}

                @property
                def My_Property(self):  # pylint: disable=C0116  # Conflicts with my_property when lowercased
                    return {"value": "Second"}

    def test_method_and_property_same_name_no_conflict(self):
        """Verify that method 'property_X' and property 'X' don't conflict (different paths)."""
        # Property endpoints are /property/{name}, method endpoints are /{name}
        # So 'property_myname' method -> /property_myname
        # and 'myname' property -> /property/myname
        # These are different paths and should NOT conflict
        class MethodPropertyDifferentServer(SimpleServer):  # pylint: disable=C0115
            @property
            def myname(self):  # pylint: disable=C0116
                return {"value": "Property value"}

            def property_myname(self):  # pylint: disable=C0116
                return {"value": "Method value"}

        server = MethodPropertyDifferentServer(demo_mode=False)
        assert '/property_myname' in server._endpoint_map  # pylint: disable=E1101  # method endpoint
        assert '/property/myname' in server._endpoint_map  # pylint: disable=E1101  # property endpoint

    def test_no_conflict_with_different_names(self):
        """Verify that methods with different names (even similar) don't conflict."""
        # This should NOT raise an error
        class NoConflictServer(SimpleServer):  # pylint: disable=C0115
            def hello_world(self):  # pylint: disable=C0116
                return {"message": "Hello"}

            def hello_world2(self):  # pylint: disable=C0116
                return {"message": "Hello 2"}

            @property
            def some_property(self):  # pylint: disable=C0116
                return {"value": "Property"}

        server = NoConflictServer(demo_mode=False)
        assert '/hello_world' in server._endpoint_map  # pylint: disable=E1101
        assert '/hello_world2' in server._endpoint_map  # pylint: disable=E1101
        assert '/property/some_property' in server._endpoint_map  # pylint: disable=E1101


class TestCustomFlaskConfigs:
    """Tests for custom Flask configuration feature."""

    def test_empty_custom_flask_configs(self):
        """Verify that servers with no custom configs work correctly."""
        from .mock_server import MyServer
        server = MyServer(demo_mode=False)
        # Default Flask behavior - no custom configs should be applied
        assert server.app.config.get('MAX_CONTENT_LENGTH') is None
        # Server should still work with empty custom_flask_configs
        client = server.app.test_client()
        response = client.get("/hello_world")
        assert response.status_code == 200

    def test_custom_flask_configs_applied(self):
        """Verify that custom_flask_configs are properly applied to Flask app.config."""
        class CustomConfigServer(SimpleServer):  # pylint: disable=C0115
            custom_flask_configs = {
                'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,  # 16MB
                'JSON_SORT_KEYS': False,
                'SEND_FILE_MAX_AGE_DEFAULT': 0,
                'TESTING': True
            }

            def test_endpoint(self):  # pylint: disable=C0116
                return {"message": "Test"}

        server = CustomConfigServer(demo_mode=False)

        # Verify all custom configs are applied
        assert server.app.config['MAX_CONTENT_LENGTH'] == 16 * 1024 * 1024
        assert server.app.config['JSON_SORT_KEYS'] is False
        assert server.app.config['SEND_FILE_MAX_AGE_DEFAULT'] == 0
        assert server.app.config['TESTING'] is True

    def test_custom_flask_configs_inheritance(self):
        """Verify that custom_flask_configs can be inherited and overridden."""
        class BaseConfigServer(SimpleServer):  # pylint: disable=C0115
            custom_flask_configs = {
                'JSON_SORT_KEYS': False,
                'MAX_CONTENT_LENGTH': 1024
            }

        class DerivedConfigServer(BaseConfigServer):  # pylint: disable=C0115
            custom_flask_configs = {
                'MAX_CONTENT_LENGTH': 2048,  # Override parent
                'TESTING': True  # Add new config
            }

        server = DerivedConfigServer(demo_mode=False)

        # Verify derived class configs are used
        assert server.app.config['MAX_CONTENT_LENGTH'] == 2048
        assert server.app.config['TESTING'] is True
        # Note: JSON_SORT_KEYS is NOT inherited since we completely replace the dict

    def test_max_content_length_enforcement(self):
        """Verify that MAX_CONTENT_LENGTH config actually limits request size."""
        class LimitedSizeServer(SimpleServer):  # pylint: disable=C0115
            custom_flask_configs = {
                'MAX_CONTENT_LENGTH': 100  # 100 bytes limit
            }

            def upload(self, data: str):  # pylint: disable=C0116
                return {"received": len(data)}

        server = LimitedSizeServer(demo_mode=False)
        client = server.app.test_client()

        # Small payload should work
        small_data = {"data": "x" * 50}
        response = client.post("/upload", json=small_data)
        assert response.status_code == 200

        # Large payload should be rejected with 500
        large_data = {"data": "x" * 1000}
        response = client.post("/upload", json=large_data)
        assert response.status_code == 500
        assert "error" in response.get_json()['data']

    def test_json_sort_keys_config(self):
        """Verify that JSON_SORT_KEYS config can be set."""
        class UnsortedJsonServer(SimpleServer):  # pylint: disable=C0115
            custom_flask_configs = {
                'JSON_SORT_KEYS': False
            }

            def get_data(self):  # pylint: disable=C0116
                return {"zebra": 1, "apple": 2, "mango": 3}

        server = UnsortedJsonServer(demo_mode=False)

        # Verify config is set correctly
        assert server.app.config['JSON_SORT_KEYS'] is False

    def test_multiple_custom_configs(self):
        """Verify that multiple custom configs can coexist and all work correctly."""
        class MultiConfigServer(SimpleServer):  # pylint: disable=C0115
            custom_flask_configs = {
                'MAX_CONTENT_LENGTH': 5000,
                'JSON_SORT_KEYS': False,
                'SEND_FILE_MAX_AGE_DEFAULT': 300,
                'SECRET_KEY': 'test-secret-key',
                'TESTING': True
            }

            def info(self):  # pylint: disable=C0116
                return {
                    "max_content": self.app.config['MAX_CONTENT_LENGTH'],
                    "sort_keys": self.app.config['JSON_SORT_KEYS'],
                    "cache_timeout": self.app.config['SEND_FILE_MAX_AGE_DEFAULT']
                }

        server = MultiConfigServer(demo_mode=False)

        # Verify all configs are set
        assert server.app.config['MAX_CONTENT_LENGTH'] == 5000
        assert server.app.config['JSON_SORT_KEYS'] is False
        assert server.app.config['SEND_FILE_MAX_AGE_DEFAULT'] == 300
        assert server.app.config['SECRET_KEY'] == 'test-secret-key'
        assert server.app.config['TESTING'] is True

        # Verify endpoint can access the configs
        client = server.app.test_client()
        response = client.get("/info")
        data = response.get_json()['data']
        assert data['max_content'] == 5000
        assert data['sort_keys'] is False
        assert data['cache_timeout'] == 300

    def test_custom_configs_in_advanced_server(self):
        """Verify that custom_flask_configs works with AdvancedServer as well."""
        class CustomAdvancedServer(AdvancedServer):  # pylint: disable=C0115
            custom_flask_configs = {
                'MAX_CONTENT_LENGTH': 8192,
                'JSON_SORT_KEYS': False
            }

            def server_info(self):  # pylint: disable=C0116
                return {"server_type": "advanced"}

        server = CustomAdvancedServer(demo_mode=False)

        # Verify configs are applied
        assert server.app.config['MAX_CONTENT_LENGTH'] == 8192
        assert server.app.config['JSON_SORT_KEYS'] is False
