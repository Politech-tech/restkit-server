# RestKit Server

[![Tests](https://github.com/Politech-tech/restkit-server/actions/workflows/tests.yml/badge.svg)](https://github.com/Politech-tech/restkit-server/actions/workflows/tests.yml)
[![Coverage](https://img.shields.io/badge/coverage-89%25-brightgreen)](https://github.com/Politech-tech/restkit-server/actions/workflows/tests.yml)
[![PyPI version](https://img.shields.io/pypi/v/restkit-server.svg)](https://pypi.org/project/restkit-server/)
[![Python versions](https://img.shields.io/pypi/pyversions/restkit-server.svg)](https://pypi.org/project/restkit-server/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Flask-based REST server toolkit providing simple and advanced server implementations.

## Installation

```bash
pip install restkit-server
```

## Features

- SimpleServer - Automatically maps class methods to REST endpoints
- AdvancedServer - Extends SimpleServer with dynamic unit method exposure
- Built-in logging and error handling with advanced rotation
- JSON response formatting
- CORS support

> 📚 **Detailed Documentation:**
> - [Server Utilities Guide](server_utils.md) - Complete server implementation details
> - [Logger Utilities Guide](logger.md) - Advanced logging features and configuration

## Quick Start

### SimpleServer Example

```python
from restkit_server import SimpleServer

class MyServer(SimpleServer):
    def hello_world(self):
        return {"message": "Hello, world!"}
    
    def get_user(self, user_id):
        return {"user_id": user_id, "name": "John Doe"}

if __name__ == "__main__":
    server = MyServer(demo_mode=True, verbose=True)
    server.run(host="0.0.0.0", port=5000)
```

### AdvancedServer Example

```python
from restkit_server import AdvancedServer

class UserService:
    def get_profile(self, user_id):
        return {"user_id": user_id, "profile": "data"}
    
    def update_profile(self, user_id, name):
        return {"status": "updated", "user_id": user_id, "name": name}

class MyAdvancedServer(AdvancedServer):
    def health(self):
        return {"status": "healthy"}

if __name__ == "__main__":
    server = MyAdvancedServer(
        demo_mode=True,
        verbose=True,
        unit_instances={'user': UserService()}
    )
    server.run(host="0.0.0.0", port=5000)
    # Endpoints: /health, /user/get_profile, /user/update_profile
```

## Configuration

### Server Parameters

- `demo_mode` (bool): Enable demo mode (default: False) (not implemented)
- `verbose` (bool): Enable DEBUG level logging for detailed tracing (default: False)
- `app_name` (str): Name for the Flask application (default: class name)
- `unit_instances` (dict): Dictionary of service instances for AdvancedServer (default: {})

### Logging

RestKit Server includes built-in logging with enter/exit tracing:

```python
server = MyServer(verbose=True)  # Enables DEBUG logging
server.set_verbose(False)  # Dynamically change log level
```

**Features:**
- Dual rotation (time and size-based)
- Function entry/exit tracing decorator
- Stream redirection support
- Configurable log levels and retention

> 📖 See [Logger Utilities Guide](logger.md) for detailed logging configuration and examples.

## API Reference

### SimpleServer

Automatically exposes public methods as REST endpoints:
- Methods starting with `_` are private and not exposed
- Supports both GET and POST requests by default
- Automatic JSON parameter extraction
- Built-in error handling

> 📖 See [Server Utilities Guide](server_utils.md) for complete API documentation.

### AdvancedServer

Extends SimpleServer with:
- Dynamic unit instance registration
- Namespaced endpoints (`/unit_name/method_name`)
- Service-oriented architecture support

### Response Format

All endpoints return JSON in this format:

```json
{
  "status": "OK",
  "data": { ... },
  "code": 200
}
```

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/Politech-tech/restkit-server.git
cd restkit-server

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in editable mode with dev dependencies
pip install -e .
pip install pytest pytest-cov

# Run tests
pytest tests/

# Run tests with coverage
pytest tests/ --cov=src/restkit_server --cov-report=html
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov --cov-report=term-missing

# Run specific test file
pytest tests/test_server_utils.py -v
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Requirements

- Python >= 3.6
- Flask
- flask-cors

## Support

- **Issues**: [GitHub Issues](https://github.com/Politech-tech/restkit-server/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Politech-tech/restkit-server/discussions)
- **Email**: ido.shafrir@gmail.com

## Documentation

- [Server Utilities Guide](server_utils.md) - Detailed server implementation and API reference
- [Logger Utilities Guide](logger.md) - Advanced logging configuration and usage
- [Changelog](CHANGELOG.md) - Release history and version information

## License

This project is licensed under the MIT License - see the LICENSE file for details.