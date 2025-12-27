"""Tests for case-insensitive URL routing functionality.

This module validates:
 - Case-insensitive URL routing with 308 redirects.
 - Query parameter preservation during redirects.
 - Case-insensitive routing in AdvancedServer with unit instances.
"""

import pytest
from .mock_server import MyServer, MyAdvancedServer, Fizz, Foo
from restkit_server import RestCodes


@pytest.fixture()
def simple_server():
    """Provide a configured instance of MyServer with Flask test mode enabled."""
    server = MyServer(demo_mode=True)
    server.app.config['TESTING'] = True
    yield server


@pytest.fixture()
def advanced_server():
    """Provide an AdvancedServer instance with Foo & Fizz units registered for testing."""
    server = MyAdvancedServer(
        demo_mode=True,
        unit_instances={'foo': Foo(), "fizz": Fizz()},
        app_name="TestAdvancedServerApp",
        verbose=True
    )
    server.app.config['TESTING'] = True
    yield server


@pytest.mark.usefixtures("simple_server")
class TestCaseInsensitiveRouting:
    """Tests for case-insensitive URL routing functionality."""

    def test_uppercase_endpoint(self, simple_server):
        """Verify uppercase URL redirects to lowercase endpoint with 308 status."""
        client = simple_server.app.test_client()
        response = client.get("/HELLO_WORLD")
        assert response.status_code == 308  # Permanent Redirect
        assert response.location == "/hello_world"

    def test_mixed_case_endpoint(self, simple_server):
        """Verify mixed case URL redirects to lowercase endpoint."""
        client = simple_server.app.test_client()
        response = client.get("/Hello_World")
        assert response.status_code == 308
        assert response.location == "/hello_world"

    def test_lowercase_endpoint_works(self, simple_server):
        """Verify lowercase URL works normally without redirect."""
        client = simple_server.app.test_client()
        response = client.get("/hello_world")
        assert response.status_code == RestCodes.OK.value
        assert response.get_json()['data'] == {"message": "Hello, world!"}

    def test_case_insensitive_with_query_params(self, simple_server):
        """Verify query parameters are preserved during case-insensitive redirect."""
        client = simple_server.app.test_client()
        response = client.get("/HELLO_WORLD?param1=value1&param2=value2")
        assert response.status_code == 308
        assert "param1=value1" in response.location
        assert "param2=value2" in response.location
        assert response.location.startswith("/hello_world?")

    def test_case_insensitive_post_endpoint(self, simple_server):
        """Verify POST requests are also case-insensitive."""
        client = simple_server.app.test_client()
        response = client.post("/POST_EXAMPLE", json={'var1': 'test', 'var2': 'value'})
        assert response.status_code == 308
        assert response.location == "/post_example"

    def test_case_insensitive_index(self, simple_server):
        """Verify root index endpoint is case-insensitive."""
        client = simple_server.app.test_client()
        response = client.get("/INDEX")
        assert response.status_code == 308
        assert response.location == "/index"

    def test_follow_redirect_uppercase(self, simple_server):
        """Verify following redirect from uppercase URL returns correct response."""
        client = simple_server.app.test_client()
        response = client.get("/HELLO_WORLD", follow_redirects=True)
        assert response.status_code == RestCodes.OK.value
        assert response.get_json()['data'] == {"message": "Hello, world!"}


@pytest.mark.usefixtures("advanced_server")
class TestCaseInsensitiveAdvancedServer:
    """Tests for case-insensitive routing in AdvancedServer with unit instances."""

    def test_unit_endpoint_uppercase(self, advanced_server):
        """Verify unit instance endpoints are case-insensitive."""
        client = advanced_server.app.test_client()
        response = client.get("/FOO/BAR")
        assert response.status_code == 308
        assert response.location == "/foo/bar"

    def test_unit_endpoint_mixed_case(self, advanced_server):
        """Verify mixed case unit endpoints redirect correctly."""
        client = advanced_server.app.test_client()
        response = client.get("/Foo/Bar")
        assert response.status_code == 308
        assert response.location == "/foo/bar"

    def test_unit_endpoint_follow_redirect(self, advanced_server):
        """Verify following redirect on unit endpoint returns correct response."""
        client = advanced_server.app.test_client()
        response = client.get("/FOO/BAR", follow_redirects=True)
        assert response.status_code == RestCodes.OK.value
        assert response.get_json()['data'] == {"message": "Hello from Foo.bar!"}

    def test_unit_property_endpoint_case_insensitive(self, advanced_server):
        """Verify unit property endpoints are case-insensitive."""
        client = advanced_server.app.test_client()
        response = client.get("/FOO/PROPERTY/TEST_PROPERTY")
        assert response.status_code == 308
        assert response.location == "/foo/property/test_property"
