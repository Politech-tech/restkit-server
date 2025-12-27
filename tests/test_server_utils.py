"""Tests for SimpleServer and AdvancedServer REST endpoint behavior.

This module validates:
 - Automatic endpoint registration and response formatting.
 - Error handling / status code mapping (success & failure paths).
 - Parameter extraction from JSON payloads for POST/GET.
 - Dynamic unit method exposure & namespacing in AdvancedServer.
 - Logging functionality including verbosity control and enter/exit tracing.
"""

import io
import os
import pytest
import logging
from .mock_server import MyServer, MyAdvancedServer, Fizz, Foo
from restkit_server import RestCodes, SimpleServer


@pytest.fixture()
def simple_server():
    """Provide a configured instance of MyServer with Flask test mode enabled."""
    server = MyServer(demo_mode=True)
    server.app.config['TESTING'] = True
    yield server


@pytest.fixture()
def advanced_server():
    """Provide an AdvancedServer instance with Foo & Fizz units registered for testing."""
    server = MyAdvancedServer(demo_mode=True, unit_instances={'foo': Foo(), "fizz": Fizz()}, app_name="TestAdvancedServerApp", verbose=True)
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
        """Exercise /post_example success path + multiple failure scenarios (missing arg, unexpected arg, wrong method)."""
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
        # Check that the property endpoint is in the endpoint map
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


@pytest.mark.usefixtures("advanced_server")
class TestAdvancedServer:
    """Tests for AdvancedServer dynamic unit method exposure and error scenarios."""

    def test_hello(self, advanced_server):
        """Verify /hello endpoint from subclass returns expected greeting."""
        client = advanced_server.app.test_client()
        response = client.get("/hello")
        assert response.status_code == RestCodes.OK.value
        assert response.get_json()['data'] == {"message": "Hello from MyAdvancedServer.hello!"}
        assert response.get_json()['status'] == RestCodes.OK.name

    def test_fizz_buzz(self, advanced_server):
        """Verify /fizz/buzz endpoint proxies to Fizz.buzz method."""
        client = advanced_server.app.test_client()
        response = client.get("/fizz/buzz")
        assert response.status_code == RestCodes.OK.value
        assert response.get_json()['data'] == {"message": "Hello from Fizz.buzz!"}
        assert response.get_json()['status'] == RestCodes.OK.name

    def test_fizz_error(self, advanced_server):
        """Verify exceptions in unit methods (Fizz.error) return structured 500 JSON."""
        client = advanced_server.app.test_client()
        response = client.get("/fizz/error")
        assert response.status_code == RestCodes.INTERNAL_SERVER_ERROR.value
        assert "error" in response.get_json()['data'].keys()
        assert response.get_json()['status'] == RestCodes.INTERNAL_SERVER_ERROR.name
        assert response.get_json()['data']['error'] == "Error from Fizz.error"

    def test_foo_bar(self, advanced_server):
        """Verify /foo/bar endpoint proxies to Foo.bar method."""
        client = advanced_server.app.test_client()
        response = client.get("/foo/bar")
        assert response.status_code == RestCodes.OK.value
        assert response.get_json()['data'] == {"message": "Hello from Foo.bar!"}
        assert response.get_json()['status'] == RestCodes.OK.name

    def test_foo_echo(self, advanced_server):
        """Verify /foo/echo correctly forwards JSON kwargs and returns them intact."""
        client = advanced_server.app.test_client()
        response = client.get("/foo/echo", json={'var1': 'value1', 'var2': [1, 2, 3]})
        assert response.status_code == RestCodes.OK.value
        assert response.get_json()['data']['message'] == "Hello from Foo.echo!"
        assert response.get_json()['data']['kwargs'] == {'var1': 'value1', 'var2': [1, 2, 3]}
        assert response.get_json()['status'] == RestCodes.OK.name

    def test_foo_static_method(self, advanced_server):
        """Verify /foo/test_static endpoint calls Foo's static method."""
        client = advanced_server.app.test_client()
        response = client.get("/foo/test_static")
        assert response.status_code == RestCodes.OK.value
        assert response.get_json()['data'] == {"message": "Hello from Foo.test_static!"}
        assert response.get_json()['status'] == RestCodes.OK.name

    def test_foo_class_method(self, advanced_server):
        """Verify /foo/test_class_method endpoint calls Foo's class method."""
        client = advanced_server.app.test_client()
        response = client.get("/foo/test_class_method")
        assert response.status_code == RestCodes.OK.value
        assert response.get_json()['data'] == {"message": "Hello from Foo.test_class_method!"}
        assert response.get_json()['status'] == RestCodes.OK.name

    def test_foo_property_getter(self, advanced_server):
        """Verify /foo/property/test_property endpoint accesses Foo's property getter."""
        client = advanced_server.app.test_client()
        response = client.get("/foo/property/test_property")
        assert response.status_code == RestCodes.OK.value
        data = response.get_json()['data']
        assert data['message'] == "Hello from Foo.test_property!"
        assert 'access_count' in data
        assert response.get_json()['status'] == RestCodes.OK.name
        
        # Verify property is actually called each time
        response2 = client.get("/foo/property/test_property")
        data2 = response2.get_json()['data']
        assert data2['access_count'] == data['access_count'] + 1

    def test_property_endpoints_exist(self, advanced_server):
        """Verify that properties are mapped to /unit/property/name endpoints."""
        # Check that the property endpoint is in the endpoint map
        property_endpoint = '/foo/property/test_property'
        assert property_endpoint in advanced_server._endpoint_map
        
    def test_static_and_class_methods_exist(self, advanced_server):
        """Verify that static and class methods are registered as endpoints."""
        # Check that static and class method endpoints exist
        assert '/foo/test_static' in advanced_server._endpoint_map
        assert '/foo/test_class_method' in advanced_server._endpoint_map


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
        
        # Large payload should be rejected with 500 (RequestEntityTooLarge wrapped by our error handler)
        large_data = {"data": "x" * 1000}
        response = client.post("/upload", json=large_data)
        # Our wrapper catches RequestEntityTooLarge and returns 500
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
        from restkit_server import AdvancedServer
        
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
