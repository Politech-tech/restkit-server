"""Example server implementations demonstrating RestKit features.

This module provides example implementations of:
 - SimpleServer: Basic REST server with automatic endpoint mapping
 - AdvancedServer: Extended server with dynamic unit method exposure
 
These examples show common use cases and best practices for using the RestKit package.
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

    def __init__(self, demo_mode: bool = False, app_name: str = "MyServerApp"):
        """Initialize server and declare HTTP method constraints for endpoints."""
        self._endpoint_method_map['post_example'] = ['POST']
        super().__init__(demo_mode=demo_mode, app_name=app_name)

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


class Foo:
    """Sample unit class with methods to be exposed via AdvancedServer."""

    def bar(self):
        """Return a greeting from Foo.bar."""
        return {"message": "Hello from Foo.bar!"}

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

    def __init__(self, demo_mode: bool = False, unit_instances: dict | None = None) -> None:
        """Initialize with optional unit instances mapping for dynamic exposure."""
        super().__init__(demo_mode=demo_mode, app_name="MyAdvancedServerApp", unit_instances=unit_instances)

    def hello(self) -> dict:
        """Return a greeting specific to MyAdvancedServer."""
        return {"message": "Hello from MyAdvancedServer.hello!"}


if __name__ == "__main__":
    """Launch either the simple or advanced server based on CLI arg."""
    if len(sys.argv) > 1 and sys.argv[1] == "simple":
        server = MyServer(demo_mode=True)
    else:
        server = MyAdvancedServer(demo_mode=True, unit_instances={'foo': Foo(), "fizz": Fizz()})

    server.run(host="0.0.0.0", port=5001)