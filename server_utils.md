# RestKit Server Utils

Documentation for `SimpleServer` and `AdvancedServer` from `restkit_server.server_utils`.

> 🏠 [Back to README](README.md) | 📚 [Logger Utilities Guide](logger.md)

## Overview

The module provides two Flask-based server helpers:

- **`SimpleServer`** — A framework that automatically maps public instance methods (those not starting with `_`) into REST endpoints with built-in logging and error handling.
- **`AdvancedServer`** — Extends `SimpleServer` and can expose methods of unit instances (service objects) as namespaced endpoints.

Both servers return JSON responses via the `RestResponse` helper. Methods may return either a plain serializable value (dict/str/list/etc.) or a `(data, code)` tuple where `code` is an HTTP status code.

## SimpleServer

### Features

- Automatic endpoint registration for public methods at `/{method_name}`
- JSON request body parsing and parameter extraction
- Built-in error handling with structured error responses
- Configurable logging with verbose mode for debugging
- Enter/exit tracing for all endpoint calls (when verbose=True)
- Support for custom HTTP methods per endpoint
- CORS enabled by default
- **Case-insensitive URL routing** - URLs are automatically normalized to lowercase
- **Custom Flask configuration** - Apply Flask app.config settings via class variable

### Constructor Parameters

```python
SimpleServer(demo_mode=False, app_name="simple_server", verbose=False)
```

- **`demo_mode`** (bool): Enable demo mode with additional logging (default: `False`)
- **`app_name`** (str): Name for the Flask application and logger (default: `"simple_server"`)
- **`verbose`** (bool): Enable DEBUG level logging with enter/exit tracing (default: `False`)

### Methods

- **`set_verbose(verbose: bool)`** — Dynamically change logging verbosity at runtime
- **`index()`** — Built-in endpoint that lists all available routes (accessible at `/` and `/index`)
- **`get_run_mode()`** — Returns whether server is in demo or production mode

### Built-in Download Endpoint

SimpleServer provides a built-in `/download` endpoint for serving files securely.

**Usage:**

```bash
# Download via query parameter
curl "http://localhost:5000/download?path=/path/to/file.txt" --output file.txt

# Download via JSON body
curl -X GET -H "Content-Type: application/json" \
  -d '{"path": "/path/to/file.txt"}' \
  http://localhost:5000/download --output file.txt
```

**Python Example:**

```python
import requests

# Download via query parameter
response = requests.get(
    "http://localhost:5000/download",
    params={"path": "/path/to/file.txt"}
)

if response.status_code == 200:
    with open("downloaded_file.txt", "wb") as f:
        f.write(response.content)
    print("File downloaded successfully!")
else:
    print(f"Error: {response.json()}")

# Download via JSON body
response = requests.get(
    "http://localhost:5000/download",
    json={"path": "/path/to/file.txt"}
)

if response.status_code == 200:
    with open("downloaded_file.txt", "wb") as f:
        f.write(response.content)
```

**Security Features:**

- **Path Traversal Protection**: All paths are normalized using `os.path.realpath()` to prevent directory traversal attacks (e.g., `../../etc/passwd`).
- **Allowed Paths (Whitelist)**: Configure `ALLOWED_DOWNLOAD_PATHS` to restrict downloads to specific directories.
- **Blocked Paths (Blacklist)**: Configure `BLOCKED_DOWNLOAD_PATHS` to block specific paths/directories.

**Configuration Example:**

```python
from restkit_server import SimpleServer

class SecureServer(SimpleServer):
    custom_flask_configs = {
        # Only allow downloads from these directories
        'ALLOWED_DOWNLOAD_PATHS': ['/var/www/files', '/home/user/public'],
        # Block specific sensitive paths (used if ALLOWED_DOWNLOAD_PATHS is not set)
        'BLOCKED_DOWNLOAD_PATHS': ['/etc', '/var/log', 'C:\\Windows']
    }

if __name__ == '__main__':
    server = SecureServer()
    server.run(host='0.0.0.0', port=5000)
```

> ⚠️ **Security Note:** It's recommended to use `ALLOWED_DOWNLOAD_PATHS` (whitelist) over `BLOCKED_DOWNLOAD_PATHS` (blacklist) for better security. If `ALLOWED_DOWNLOAD_PATHS` is configured, files can only be downloaded from within those directories.

### Built-in Upload Endpoint

SimpleServer provides a built-in `/upload` endpoint for receiving file uploads securely.

**Usage:**

```bash
# Upload via curl
curl -X POST -F "file=@/path/to/local/file.txt" http://localhost:5000/upload

# Upload with custom filename
curl -X POST -F "file=@/path/to/local/file.txt" -F "filename=custom_name.txt" http://localhost:5000/upload
```

**Python Example:**

```python
import requests

# Upload a file
with open("/path/to/local/file.txt", "rb") as f:
    response = requests.post(
        "http://localhost:5000/upload",
        files={"file": f}
    )

if response.status_code == 201:
    result = response.json()
    print(f"✅ Uploaded: {result['data']['filename']} ({result['data']['size']} bytes)")
else:
    print(f"❌ Error: {response.json()['data']['error']}")

# Upload with custom filename
with open("/path/to/local/file.txt", "rb") as f:
    response = requests.post(
        "http://localhost:5000/upload",
        files={"file": f},
        data={"filename": "custom_name.txt"}
    )
```

**Security Features:**

- **Path Traversal Protection**: Filenames are sanitized to remove directory components and dangerous characters.
- **Regex-based Blocklist**: Configure `UPLOAD_BLOCKED_PATTERNS` to block files matching regex patterns.
- **Directory Restriction**: Files are always saved within `UPLOAD_DIRECTORY_PATH`.

**Configuration Options:**

| Config Key | Description | Default |
|------------|-------------|---------|
| `UPLOAD_DIRECTORY_PATH` | Directory where uploaded files are saved | `./uploads/` |
| `UPLOAD_BLOCKED_PATTERNS` | List of regex patterns to block filenames | `[]` |
| `MAX_CONTENT_LENGTH` | Maximum upload size (Flask built-in) | No limit |

**Configuration Example:**

```python
from restkit_server import SimpleServer

class SecureUploadServer(SimpleServer):
    custom_flask_configs = {
        # Upload directory
        'UPLOAD_DIRECTORY_PATH': '/var/www/uploads',
        
        # Block dangerous file types using regex patterns
        'UPLOAD_BLOCKED_PATTERNS': [
            r'\.exe$',      # Block .exe files
            r'\.bat$',      # Block .bat files
            r'\.sh$',       # Block .sh files
            r'\.php$',      # Block .php files
            r'^\.',         # Block hidden files (starting with .)
            r'\.\.+',       # Block files with multiple dots (potential traversal)
        ],
        
        # Limit upload size to 16MB
        'MAX_CONTENT_LENGTH': 16 * 1024 * 1024
    }

if __name__ == '__main__':
    server = SecureUploadServer()
    server.run(host='0.0.0.0', port=5000)
```

> ⚠️ **Security Note:** Always configure `UPLOAD_BLOCKED_PATTERNS` in production to prevent uploading of executable or dangerous files. Consider also setting `MAX_CONTENT_LENGTH` to limit upload sizes.

### Built-in Log Viewer

SimpleServer provides built-in endpoints for viewing and listing log files.

**Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/list_logs` | GET | Returns a JSON list of all log files in the logging directory |
| `/logs` | GET | Returns the current log file content as plain text |
| `/logs/<filename>` | GET | Returns a specific log file content |
| `/logs?log_file=<filename>` | GET | Alternative way to request a specific log file |

**Usage Examples:**

```bash
# List all available log files
curl http://localhost:5000/list_logs

# View the current (active) log file
curl http://localhost:5000/logs

# View a specific log file by path
curl http://localhost:5000/logs/myserver_2025-12-27_14_30.log

# View a specific log file by query parameter
curl "http://localhost:5000/logs?log_file=myserver_2025-12-27_14_30.log"
```

**Python Example:**

```python
import requests

# List available log files
response = requests.get("http://localhost:5000/list_logs")
if response.status_code == 200:
    logs = response.json()['data']
    print(f"Available logs: {logs}")

# Get the current log content
response = requests.get("http://localhost:5000/logs")
if response.status_code == 200:
    log_content = response.text
    print(log_content)

# Get a specific log file
response = requests.get(
    "http://localhost:5000/logs",
    params={"log_file": "myserver_2025-12-27_14_30.log"}
)
if response.status_code == 200:
    print(response.text)
```

**Security Features:**

- **Path Traversal Protection**: Log file requests are validated to ensure they remain within the logging directory.
- **Case-insensitive Filenames**: Due to URL normalization, filenames are matched case-insensitively.
- **Directory Restriction**: Only files within the server's logging directory can be accessed.

**Response Formats:**

- `/list_logs` returns JSON: `{"status": "OK", "data": ["file1.log", "file2.log"], "code": 200}`
- `/logs` and `/logs/<filename>` return plain text with `Content-Type: text/plain`

> 🌐 **Browser Viewable:** The `/logs` and `/logs/<filename>` endpoints return plain text and are directly viewable in a web browser. Simply navigate to `http://localhost:5000/logs` to view the current log file in your browser.

> 💡 **Tip:** The log viewer is useful for debugging in development or viewing logs from a web dashboard. In production, consider restricting access to these endpoints using authentication middleware.

### Logging

RestKit Server includes comprehensive logging:

- **File logging**: All logs written to `log/{app_name}_{timestamp}.log`
- **Console logging**: INFO level by default, DEBUG when `verbose=True`
- **Enter/exit tracing**: When verbose, logs function entry/exit with arguments
- **Unified logger**: All endpoints log to the same server logger

> 📖 For detailed logging configuration, see [Logger Utilities Guide](logger.md)

```python
# Enable verbose logging at initialization
server = MyServer(verbose=True)

# Dynamically change verbosity
server.set_verbose(False)  # Switch to INFO level
server.set_verbose(True)   # Switch to DEBUG level
```

### Custom Flask Configuration

You can customize Flask's application settings by defining the `custom_flask_configs` class variable in your `SimpleServer` subclass. This dictionary is applied to `app.config` during initialization.

**Common Flask Configuration Options:**

- `MAX_CONTENT_LENGTH` - Maximum allowed payload size (in bytes)
- `JSON_SORT_KEYS` - Whether to sort JSON keys (default: True)
- `SEND_FILE_MAX_AGE_DEFAULT` - Cache timeout for static files (in seconds)
- `SECRET_KEY` - Secret key for session management
- `SESSION_COOKIE_SECURE` - Restrict cookies to HTTPS only
- `PREFERRED_URL_SCHEME` - URL scheme to use ('http' or 'https')

**Example:**

```python
from restkit_server import SimpleServer

class MyServer(SimpleServer):
    # Define custom Flask configurations
    custom_flask_configs = {
        'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,  # 16MB max upload size
        'JSON_SORT_KEYS': False,  # Preserve JSON key order
        'SEND_FILE_MAX_AGE_DEFAULT': 0,  # Disable caching for development
        'SECRET_KEY': 'your-secret-key-here'  # For session management
    }
    
    def __init__(self):
        super().__init__(app_name='MyConfiguredServer')
    
    def upload_file(self, file_data: str) -> dict:
        """Example endpoint that benefits from MAX_CONTENT_LENGTH config."""
        return {"message": "File uploaded successfully", "size": len(file_data)}

if __name__ == '__main__':
    server = MyServer()
    server.run(host='0.0.0.0', port=5000)
```

> 📘 **Note:** See [Flask Configuration Documentation](https://flask.palletsprojects.com/en/latest/config/) for a complete list of available configuration options.

### Example

```python
from restkit_server import SimpleServer

class MyServer(SimpleServer):
    def __init__(self, demo_mode: bool = False, verbose: bool = False):
        # Configure POST-only endpoints before calling super
        self._endpoint_method_map['post_example'] = ['POST']
        super().__init__(demo_mode=demo_mode, app_name='MyServerApp', verbose=verbose)

    def hello_world(self) -> dict:
        """Returns a hello world message."""
        return {"message": "Hello, world!"}

    def get_user(self, user_id: str) -> dict:
        """Get user by ID from query params or JSON body."""
        return {"user_id": user_id, "name": "John Doe"}

    def post_example(self, var1, var2, var3='default') -> str:
        """Example POST endpoint that accepts JSON body."""
        return f"{var1=}, {var2=}, {var3=}"

# Run server
if __name__ == '__main__':
    server = MyServer(demo_mode=True, verbose=True)
    server.run(host='0.0.0.0', port=5000)
```

## Making Requests

### SimpleServer Requests

```bash
# GET request to hello_world endpoint
curl http://localhost:5000/hello_world

# GET request with query parameters
curl http://localhost:5000/get_user?user_id=123

# POST request with JSON body
curl -X POST -H "Content-Type: application/json" \
  -d '{"var1": "value1", "var2": "value2"}' \
  http://localhost:5000/post_example

# View all available endpoints
curl http://localhost:5000/index
```

### AdvancedServer Requests

```bash
# Call server-level method
curl http://localhost:5001/health

# Call unit method (UserService.get_profile)
curl http://localhost:5001/user/get_profile?user_id=456

# POST to unit method
curl -X POST -H "Content-Type: application/json" \
  -d '{"user_id": "789", "name": "Jane Doe"}' \
  http://localhost:5001/user/update_profile
```

## Response Format

All endpoints return JSON in this standard format:

```json
{
  "status": "OK",
  "data": { "message": "result data here" },
  "code": 200
}
```

### Success Response Example

```json
{
  "status": "OK",
  "data": {
    "user_id": "123",
    "name": "John Doe"
  },
  "code": 200
}
```

### Error Response Example

```json
{
  "status": "INTERNAL_SERVER_ERROR",
  "data": {
    "error": "missing 1 required positional argument: 'user_id'"
  },
  "code": 500
}
```

## Advanced Features

### Custom HTTP Methods

By default, endpoints accept both GET and POST. To restrict to specific methods:

```python
class MyServer(SimpleServer):
    def __init__(self):
        # Must be set BEFORE calling super().__init__()
        self._endpoint_method_map['create_user'] = ['POST']
        self._endpoint_method_map['delete_user'] = ['DELETE']
        super().__init__(app_name='MyServer')
    
    def create_user(self, username, email):
        return {"created": username}
    
    def delete_user(self, user_id):
        return {"deleted": user_id}
```

### Excluded Methods

Certain methods are automatically excluded from endpoint registration:
- Methods starting with `_` (private methods)
- `set_verbose` (utility method for logging control)

### Case-Insensitive Routing

All endpoints are case-insensitive. URLs are automatically normalized to lowercase:

```bash
# All of these work and redirect to /hello_world
curl http://localhost:5000/HELLO_WORLD
curl http://localhost:5000/Hello_World
curl http://localhost:5000/hello_world  # Direct access (no redirect)

# Query parameters are preserved during redirect
curl http://localhost:5000/GET_USER?user_id=123
# Redirects to: /get_user?user_id=123
```

**Implementation Details:**
- Non-lowercase URLs receive a 308 Permanent Redirect to the lowercase version
- Query parameters are preserved during the redirect
- The redirect uses HTTP 308 (Permanent Redirect) for proper caching
- Applies to all endpoints including unit methods in AdvancedServer

### Dynamic Method Assignment (AdvancedServer)

You can dynamically add methods to an AdvancedServer instance:

```python
server = MyAdvancedServer()

# Dynamically add a method
def custom_endpoint():
    return {"message": "Dynamic endpoint"}

server.custom_endpoint = custom_endpoint
# Now accessible at /custom_endpoint
```

### Properties as Endpoints

Properties can be exposed as endpoints (getter only):

```python
class MyServer(SimpleServer):
    @property
    def server_status(self):
        return {"uptime": "24h", "requests": 1000}
```

Access at: `GET /property/server_status`

## Logging Details

### Log Levels

- **INFO**: Standard operational messages, endpoint calls
- **DEBUG**: Detailed tracing including:
  - Function entry with arguments
  - Function exit
  - Request/response details

### Log Format

```
2025-11-15 16:35:38,131 - MyServer - DEBUG - Entering hello_world, args: ('<self>',), kwargs={}
2025-11-15 16:35:38,131 - MyServer - DEBUG - Exiting hello_world
```

### Log Files

Logs are written to: `log/{app_name}_{timestamp}.log`

Example: `log/MyServer_2025-11-15_16_35.log`

### Enabling Verbose Logging

```python
# At initialization
server = MyServer(verbose=True)

# Dynamically at runtime
server.set_verbose(True)   # Enable DEBUG logging
server.set_verbose(False)  # Disable DEBUG logging

# Check current state
is_verbose = server.verbose
```

## AdvancedServer

### Features

- Inherits all `SimpleServer` functionality
- Dynamic unit instance registration for service-oriented architecture
- Namespaced endpoints: `/unit_name/method_name`
- Automatic endpoint wrapping for unit methods
- Shared logger across all units and server methods

### Constructor Parameters

```python
AdvancedServer(demo_mode=False, app_name=None, unit_instances=None, verbose=False)
```

- **`demo_mode`** (bool): Enable demo mode (default: `False`)
- **`app_name`** (str | None): Application name; defaults to class name if not provided
- **`unit_instances`** (dict | None): Dictionary mapping unit names to instance objects (default: `{}`)
- **`verbose`** (bool): Enable DEBUG logging (default: `False`)

### Behavior

When `unit_instances` is provided:
1. Each instance is stored as a private attribute (e.g., `_foo` for unit `'foo'`)
2. All public methods of the instance become endpoints at `/unit_name/method_name`
3. All unit methods use the server's unified logger for consistent logging
4. Enter/exit tracing works for both server methods and unit methods

### Example with Unit Instances

```python
from restkit_server import AdvancedServer

class UserService:
    """Service for user-related operations."""
    def get_profile(self, user_id):
        return {"user_id": user_id, "profile": "data"}

    def update_profile(self, user_id, name):
        return {"status": "updated", "user_id": user_id, "name": name}

class ProductService:
    """Service for product-related operations."""
    def get_product(self, product_id):
        return {"product_id": product_id, "name": "Widget"}

class MyAdvancedServer(AdvancedServer):
    def __init__(self, demo_mode: bool = False, unit_instances: dict | None = None, verbose: bool = False):
        super().__init__(
            demo_mode=demo_mode,
            app_name='MyAdvancedServerApp',
            unit_instances=unit_instances,
            verbose=verbose
        )

    def health(self) -> dict:
        """Health check endpoint."""
        return {"status": "healthy", "version": "1.0.0"}

if __name__ == '__main__':
    server = MyAdvancedServer(
        demo_mode=True,
        verbose=True,
        unit_instances={
            'user': UserService(),
            'product': ProductService()
        }
    )
    server.run(host='0.0.0.0', port=5001)
    # Available endpoints:
    # /health
    # /user/get_profile
    # /user/update_profile
    # /product/get_product
```
## Built-in Endpoints

The servers provide built-in endpoints:

### `/` and `/index`

Lists all registered routes with their HTTP methods and docstrings.

**Example Response:**

```json
{
  "status": "OK",
  "data": {
    "message": "Welcome to the MyServer",
    "routes": [
      {
        "endpoint": "hello_world",
        "methods": ["GET", "POST"],
        "url": "/hello_world",
        "docs": "Returns a hello world message."
      },
      {
        "endpoint": "get_user",
        "methods": ["GET", "POST"],
        "url": "/get_user",
        "docs": "Get user by ID."
      }
    ]
  },
  "code": 200
}
```

### `/get_run_mode`

Returns the server's runtime mode.

**Example Response:**

```json
{
  "status": "OK",
  "data": {
    "message": "Server is running in demo mode",
    "run_mode": "demo"
  },
  "code": 200
}
```

## Troubleshooting

### Endpoint Not Appearing

1. Check if the method starts with `_` (private methods are not exposed)
2. Verify method is defined before calling `super().__init__()`
3. Check `/index` endpoint to see all registered routes
4. Ensure method is not in the `excluded_methods` list

### JSON Not Being Parsed

1. Ensure `Content-Type: application/json` header is set
2. Verify JSON syntax is valid
3. Check server logs for parsing errors

### Method Requires Positional Arguments

Use POST with a JSON body providing named parameters:

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"param1": "value1", "param2": "value2"}' \
  http://localhost:5000/endpoint
```

### Verbose Logging Not Working

1. Ensure `verbose=True` is passed to constructor
2. Check that handlers are configured (should happen automatically)
3. Verify log level with `server.logger.level`

### Unit Methods Not Logging

All unit methods should automatically use the server's logger. If not seeing logs:
1. Verify `verbose=True` is set
2. Check that the logger is configured (happens in `__init__`)
3. Ensure unit instances are passed correctly

## Technical Details

### Metaclass: MetaSimpleServer

SimpleServer uses a metaclass that:
- Wraps all public methods as REST endpoints
- Applies enter/exit logging decorator
- Registers endpoints in `_endpoint_map`
- Excludes specific utility methods (`set_verbose`)

### Endpoint Wrapping

Each endpoint is wrapped to:
1. Apply enter/exit logging (when verbose)
2. Extract query parameters from `request.args`
3. Parse JSON body when `Content-Type: application/json`
4. Merge parameters and pass to method as kwargs
5. Handle exceptions and return structured errors
6. Format successful responses

### Logger Architecture

- **One logger per server instance**: Named after the class
- **Unified logging**: All endpoints log to the same logger
- **File and console handlers**: Logs go to both file and stdout
- **Enter/exit decorator**: Applied to all endpoints automatically

## Best Practices

1. **Use type hints** in method signatures for better documentation
2. **Add docstrings** to methods (shown in `/index` endpoint)
3. **Enable verbose mode during development** for detailed tracing
4. **Use unit instances** (AdvancedServer) to organize code by domain
5. **Set HTTP methods explicitly** for security (e.g., POST for mutations)
6. **Return structured data** (dicts) rather than strings when possible
7. **Use tuple returns** `(data, code)` for custom status codes

## Example: Complete Service

```python
from restkit_server import AdvancedServer

class UserService:
    """Manages user operations."""
    
    def __init__(self):
        self.users = {"1": {"name": "Alice"}, "2": {"name": "Bob"}}
    
    def get_user(self, user_id: str):
        """Get user by ID."""
        if user_id in self.users:
            return self.users[user_id]
        return {"error": "User not found"}, 404
    
    def create_user(self, user_id: str, name: str):
        """Create a new user."""
        self.users[user_id] = {"name": name}
        return {"created": user_id, "name": name}, 201

class APIServer(AdvancedServer):
    def __init__(self):
        self._endpoint_method_map['user_create_user'] = ['POST']
        super().__init__(
            app_name='APIServer',
            verbose=True,
            unit_instances={'user': UserService()}
        )
    
    def status(self):
        """API status check."""
        return {"status": "operational", "version": "1.0.0"}

if __name__ == '__main__':
    server = APIServer()
    server.run(host='0.0.0.0', port=8000, debug=False)
```

Available endpoints:
- `GET /status` - API status
- `GET /user/get_user?user_id=1` - Get user
- `POST /user/create_user` - Create user (JSON body required)
- `GET /index` - List all endpoints

---

For more examples, see the `examples/` directory in the repository.
