# RestKit Server

[![Tests](https://github.com/Politech-tech/restkit-server/actions/workflows/tests.yml/badge.svg)](https://github.com/Politech-tech/restkit-server/actions/workflows/tests.yml)
[![Coverage](https://img.shields.io/badge/coverage-89%25-brightgreen)](https://github.com/Politech-tech/restkit-server/actions/workflows/tests.yml)

A Flask-based REST server toolkit providing simple and advanced server implementations.

## Installation

```bash
pip install restkit-server
```

## Features

- SimpleServer - Automatically maps class methods to REST endpoints
- AdvancedServer - Extends SimpleServer with dynamic unit method exposure
- Built-in logging and error handling
- JSON response formatting
- CORS support

## Quick Start

```python
from restkit.server_utils import SimpleServer

class MyServer(SimpleServer):
    def hello_world(self):
        return {"message": "Hello, world!"}

if __name__ == "__main__":
    server = MyServer(demo_mode=True)
    server.run(host="0.0.0.0", port=5000)
```

## Documentation

See the [full documentation](flask_utils.md) for detailed usage instructions.

## License

This project is licensed under the MIT License - see the LICENSE file for details.