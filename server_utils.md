# utils/flask_utils

Documentation for SimpleServer and AdvancedServer from `utils/flask_utils.py`.

## Overview

The module provides two small Flask-based server helpers:

- `SimpleServer` — a tiny framework that maps public instance methods (those not starting with `_`) into REST endpoints.
- `AdvancedServer` — extends `SimpleServer` and can expose methods of added unit instances (objects) as namespaced endpoints.

Both servers return JSON responses via the `RestResponse` helper. Methods may return either a plain serializable value (dict/str/list/etc.) or a `(data, code)` tuple where `code` is an HTTP status code.

## SimpleServer

Behavior:

- Any public method defined on the server class becomes an endpoint at `/{method_name}`.
- Methods are wrapped so they accept JSON body values as keyword arguments when `request.is_json` is true.
- Default HTTP methods for endpoints are `GET` and `POST`. You can override this by setting `self._endpoint_method_map['{method_name}'] = ['POST']` in your `__init__` before calling `super().__init__()`.
- The root path `/` and `/index` list available routes and their docs.

Example:

```python
from utils.flask_utils import SimpleServer

class MyServer(SimpleServer):
    def __init__(self, demo_mode: bool = False):
        # configure methods that should be POST-only before calling super
        self._endpoint_method_map['post_example'] = ['POST']
        super().__init__(demo_mode=demo_mode, app_name='MyServerApp')

    def hello_world(self) -> dict:
        """Returns a hello world message."""
        return {"message": "Hello, world!"}

    def post_example(self, var1, var2, var3='default') -> str:
        """Example POST endpoint that accepts JSON body."""
        return f"{var1=}, {var2=}, {var3=}"

# run
if __name__ == '__main__':
    server = MyServer(demo_mode=True)
    server.run(host='0.0.0.0', port=5000)
```

Requests:

```bash
# GET the hello_world endpoint
curl http://localhost:5000/hello_world

# POST JSON to post_example
curl -X POST -H "Content-Type: application/json" -d '{"var1": 1, "var2": 2}' http://localhost:5000/post_example
```

Notes:

- If the endpoint raises an exception, the server returns a JSON error with HTTP 500.
- Methods that return `(data, code)` will be returned with that HTTP status code.

## AdvancedServer

Behavior:

- Inherits all `SimpleServer` behavior.
- Accepts a `unit_instances` dict mapping names to object instances. When provided, `AdvancedServer` will:
  - Add each instance as a private attribute on the server (prefixed with `_`, e.g. `_foo`).
  - Expose each public method from the instance as an endpoint named `/unit/method` (for example `/foo/bar`). The code accomplishes this by creating endpoints named `{unit_name}_{method_name}` and remapping them to `/unit/method` in the endpoint map.
- You can also add server-level methods as usual; `AdvancedServer` wraps any method assigned as an attribute into an endpoint at assignment time.

Example with unit instances:

```python
from utils.flask_utils import AdvancedServer

class Foo:
    def bar(self):
        return {"message": "Hello from Foo.bar!"}

    def echo(self, *args, **kwargs):
        return {"args": args, "kwargs": kwargs}

class Fizz:
    def buzz(self):
        return {"message": "Hello from Fizz.buzz!"}

class MyAdvancedServer(AdvancedServer):
    def __init__(self, demo_mode: bool = False, unit_instances: dict | None = None):
        super().__init__(demo_mode=demo_mode, app_name='MyAdvancedServerApp', unit_instances=unit_instances)

    def hello(self) -> dict:
        return {"message": "Hello from MyAdvancedServer.hello!"}

if __name__ == '__main__':
    server = MyAdvancedServer(demo_mode=True, unit_instances={'foo': Foo(), 'fizz': Fizz()})
    server.run(host='0.0.0.0', port=5001)
```

Requests:

```bash
# call the Foo.bar method exposed as /foo/bar
curl http://localhost:5001/foo/bar
```

Advanced notes and tips:

- Dynamic method assignment: When you assign a callable to a server instance (e.g. `server.new_method = lambda: {...}`), `AdvancedServer.__setattr__` wraps and registers it as an endpoint automatically (unless the name starts with `_`).
- Use `self._endpoint_method_map` to change allowed HTTP methods per endpoint (set keys to route names or function names before `super().__init__`).
- Endpoints accept JSON bodies — the wrapper will pass JSON keys as keyword args to your methods.
- Logging: `SimpleServer` redirects `stdout`/`stderr` to the configured logger; take that into account if your units print to stdout.

## Troubleshooting

- If an endpoint is not visible, check the server's `routes` at `/index` to verify it was registered.
- If JSON isn't being parsed, ensure `Content-Type: application/json` is set in your client request.
- For methods that require positional arguments, prefer using POST with a JSON body supplying named parameters.

---

## Built-in URLs

The servers provide a few built-in endpoints by default. These are useful for discovery and runtime checks:

- `/` and `/index` — both map to the `index` method and return a JSON listing of all registered routes, their allowed HTTP methods, and docstrings for the endpoint handlers. Use this to quickly inspect which endpoints are available and their documentation.

- `/get_run_mode` — maps to the `get_run_mode` method and returns whether the server is running in `demo` or `production` mode. Example response:

```json
{
    "status": "OK",
    "data": {"message": "Server is running in demo mode", "run_mode": "demo"},
    "code": 200
}
```

How unit and server methods map to URLs:

- Server-level public methods: `def hello(self): ...` -> `/hello`
- Unit instance methods (AdvancedServer): `unit_instances={'foo': Foo()}` and `def bar(self): ...` on `Foo` -> `/foo/bar`

Notes:

- The `_endpoint_map` dictionary maps route paths to handler method names. You can inspect `server._endpoint_map` at runtime to inspect or modify routing behavior programmatically.
- If you dynamically assign methods to a server instance (e.g., `server.new = lambda: {...}`), `AdvancedServer` will register them under `/new` unless the name starts with `_`.


If you'd like, I can also:

- add short runnable examples under `examples/` that launch a server and demonstrate calls, or
- add a small script to produce an OpenAPI-style list of endpoints from the server's `_endpoint_map`.
