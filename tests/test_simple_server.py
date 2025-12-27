"""Tests for SimpleServer core endpoint behavior.

This module validates:
 - Automatic endpoint registration and response formatting.
 - Error handling / status code mapping (success & failure paths).
 - Parameter extraction from JSON payloads for POST/GET.
 - Property endpoints functionality.
"""

import pytest
from .mock_server import MyServer
from restkit_server import RestCodes


@pytest.fixture()
def simple_server():
    """Provide a configured instance of MyServer with Flask test mode enabled."""
    server = MyServer(demo_mode=True)
    server.app.config['TESTING'] = True
    yield server


@pytest.mark.usefixtures("simple_server")
class TestSimpleServer:
    """Tests covering core MyServer endpoints and error handling."""

    def test_hello_world(self, simple_server):
        """Verify /hello_world returns expected success payload and status 200."""
        client = simple_server.app.test_client()
        response = client.get("/hello_world")
        assert response.status_code == RestCodes.OK.value
        assert response.get_json()['data'] == {"message": "Hello, world!"}
        assert response.get_json()['status'] == 'OK'

    def test_error_endpoint(self, simple_server):
        """Verify /error_endpoint surfaces exceptions as structured 500 JSON response."""
        client = simple_server.app.test_client()
        response = client.get("/error_endpoint")
        assert response.status_code == RestCodes.INTERNAL_SERVER_ERROR.value
        assert "error" in response.get_json()['data'].keys()
        assert response.get_json()['status'] == RestCodes.INTERNAL_SERVER_ERROR.name
        assert response.get_json()['data']['error'] == "This is an error message."

    def test_specific_http_code(self, simple_server):
        """Verify endpoint returning a non-200 success code propagates correctly."""
        client = simple_server.app.test_client()
        response = client.get("/spesific_http_code")
        assert response.status_code == RestCodes.CREATED.value
        assert response.get_json()['data'] == {"message": "This endpoint returns a specific HTTP status code."}
        assert response.get_json()['status'] == RestCodes(201).name

    def test_post_example(self, simple_server):
        """Exercise /post_example success path + multiple failure scenarios."""
        client = simple_server.app.test_client()
        response = client.post("/post_example", json={"var1": "value1", "var2": "value2"})
        # good path
        assert response.status_code == RestCodes.OK.value
        assert "var1='value1', var2='value2', var3='default'" in response.get_json()['data']
        assert response.get_json()['status'] == RestCodes(200).name

        # bad path missing var2
        response = client.post("/post_example", json={"var1": "value1"})
        assert response.status_code == 500
        assert response.get_json()['status'] == RestCodes(500).name
        assert 'missing 1 required positional argument' in response.get_json()['data']['error']

        # bad path unknown variable
        response = client.post("/post_example", json={"var1": "value1", "var2": "value2", "var4": "value4"})
        assert response.status_code == 500
        assert response.get_json()['status'] == RestCodes(500).name
        assert 'unexpected keyword argument' in response.get_json()['data']['error']

        # bad path get instead of post
        response = client.get("/post_example", json={"var1": "value1", "var2": "value2"})
        assert response.status_code == 405

    def test_simple_server_property_getter(self, simple_server):
        """Verify /property/server_property endpoint accesses MyServer's property getter."""
        client = simple_server.app.test_client()
        response = client.get("/property/server_property")
        assert response.status_code == RestCodes.OK.value
        data = response.get_json()['data']
        assert data['message'] == "Hello from MyServer.server_property!"
        assert 'access_count' in data
        assert response.get_json()['status'] == RestCodes.OK.name

        # Verify property is actually called each time and counter increments
        response2 = client.get("/property/server_property")
        data2 = response2.get_json()['data']
        assert data2['access_count'] == data['access_count'] + 1

    def test_simple_server_property_endpoint_exists(self, simple_server):
        """Verify that SimpleServer properties are mapped to /property/name endpoints."""
        property_endpoint = '/property/server_property'
        assert property_endpoint in simple_server._endpoint_map

    def test_simple_server_second_property_getter(self, simple_server):
        """Verify /property/another_property endpoint accesses MyServer's second property getter."""
        client = simple_server.app.test_client()
        response = client.get("/property/another_property")
        assert response.status_code == RestCodes.OK.value
        data = response.get_json()['data']
        assert data['message'] == "Hello from MyServer.another_property!"
        assert data['value'] == "initial"
        assert response.get_json()['status'] == RestCodes.OK.name

    def test_multiple_properties_coexist(self, simple_server):
        """Verify that multiple properties can coexist and be accessed independently."""
        client = simple_server.app.test_client()

        # Check both properties are in the endpoint map
        assert '/property/server_property' in simple_server._endpoint_map
        assert '/property/another_property' in simple_server._endpoint_map

        # Access first property
        response1 = client.get("/property/server_property")
        assert response1.status_code == RestCodes.OK.value
        data1 = response1.get_json()['data']
        assert data1['message'] == "Hello from MyServer.server_property!"
        assert data1['access_count'] == 1

        # Access second property
        response2 = client.get("/property/another_property")
        assert response2.status_code == RestCodes.OK.value
        data2 = response2.get_json()['data']
        assert data2['message'] == "Hello from MyServer.another_property!"
        assert data2['value'] == "initial"

        # Access first property again and verify state is maintained independently
        response3 = client.get("/property/server_property")
        data3 = response3.get_json()['data']
        assert data3['access_count'] == 2

        # Access second property again and verify it's unchanged
        response4 = client.get("/property/another_property")
        data4 = response4.get_json()['data']
        assert data4['value'] == "initial"
