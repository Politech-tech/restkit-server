"""Mock server implementations for testing SimpleServer and AdvancedServer.

This module defines:
 - MyServer: concrete SimpleServer with sample endpoints for hello world,
     error generation, custom status code, and POST argument handling.
 - Foo & Fizz: simple unit classes whose public methods are exposed by
     AdvancedServer when passed via the unit_instances mapping.
 - MyAdvancedServer: example AdvancedServer subclass adding a custom endpoint.

It also provides a CLI entry point to launch either the simple or advanced
server for manual testing.
"""

# pylint: disable=E1101
from restkit_server import SimpleServer, AdvancedServer
import sys


class MyServer(SimpleServer):
    """Concrete SimpleServer implementation with sample endpoints.

    Endpoints automatically exposed (public methods):
     - /hello_world
     - /error_endpoint
     - /spesific_http_code
     - /post_example (POST only)
    """

    def __init__(self, demo_mode: bool = False, app_name: str = "MyServerApp", verbose: bool = False):
        """Initialize server and declare HTTP method constraints for endpoints."""
        self._endpoint_method_map['post_example'] = ['POST']
        self._server_property_counter = 0
        self._another_property_value = "initial"
        super().__init__(demo_mode=demo_mode, app_name=app_name, verbose=verbose)

    def hello_world(self) -> dict:
        """Return a simple hello world JSON payload."""
        return {"message": "Hello, world!"}

    def error_endpoint(self) -> dict:
        """Intentionally raise an exception to test error handling wrapper."""
        raise Exception("This is an error message.")

    def spesific_http_code(self) -> tuple:
        """Return a custom success payload with HTTP 201 status code."""
        return {"message": "This endpoint returns a specific HTTP status code."}, 201

    def post_example(self, var1, var2, var3='default') -> str:
        """Echo provided POST arguments (demonstrates JSON param binding)."""
        return f'{var1=}, {var2=}, {var3=}'

    @property
    def server_property(self):
        """Return a greeting from MyServer.server_property."""
        self._server_property_counter += 1
        return {"message": "Hello from MyServer.server_property!", "access_count": self._server_property_counter}

    @property
    def another_property(self):
        """Return the current value from MyServer.another_property."""
        return {"message": "Hello from MyServer.another_property!", "value": self._another_property_value}


class Foo:
    """Sample unit class with methods to be exposed via AdvancedServer."""

    def bar(self):
        """Return a greeting from Foo.bar."""
        return {"message": "Hello from Foo.bar!"}

    @staticmethod
    def test_static():
        """Return a greeting from Foo.test_static."""
        return {"message": "Hello from Foo.test_static!"}
    
    @classmethod
    def test_class_method(cls):
        """Return a greeting from Foo.test_class_method."""
        return {"message": "Hello from Foo.test_class_method!"}
    
    @property
    def test_property(self):
        """Return a greeting from Foo.test_property."""
        if not hasattr(self, '_property_counter'):
            self._property_counter = 0
        self._property_counter += 1
        return {"message": "Hello from Foo.test_property!", "access_count": self._property_counter}

    def echo(self, *args, **kwargs):
        """Return received positional & keyword arguments for verification."""
        return {"message": "Hello from Foo.echo!", "args": args, "kwargs": kwargs}


class Fizz:
    """Sample unit class including a method that raises an error."""

    def buzz(self):
        """Return a greeting from Fizz.buzz."""
        return {"message": "Hello from Fizz.buzz!"}

    def error(self):
        """Raise an exception to exercise error propagation logic."""
        raise Exception("Error from Fizz.error")


class MyAdvancedServer(AdvancedServer):
    """AdvancedServer subclass adding a custom /hello endpoint."""

    def __init__(self, demo_mode: bool = False, unit_instances: dict | None = None, app_name: str = "MyAdvancedServerApp", verbose: bool = False) -> None:
        """Initialize with optional unit instances mapping for dynamic exposure."""
        super().__init__(demo_mode=demo_mode, app_name=app_name, unit_instances=unit_instances, verbose=verbose)

    def hello(self) -> dict:
        """Return a greeting specific to MyAdvancedServer."""
        return {"message": "Hello from MyAdvancedServer.hello!"}


if __name__ == "__main__":
    """Launch either the simple or advanced server based on CLI arg."""
    if len(sys.argv) > 1 and sys.argv[1] == "simple":
        server = MyServer(demo_mode=True, verbose=True)
    else:
        units = {'foo': Foo(), 'fizz': Fizz()}
        server = MyAdvancedServer(demo_mode=True, unit_instances=units, verbose=True)

    server.run(host="0.0.0.0", port=5001)
