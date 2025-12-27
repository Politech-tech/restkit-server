# pylint: disable=E1101
"""
utilities for Flask applications
"""


import inspect
import sys
import os 
import traceback
from enum import Enum
from functools import wraps

from flask import Flask, Response, jsonify, request, redirect, send_file
from flask_cors import CORS

from .logger import LoggerWriter, enter_exit_logger, setup_logger  # type: ignore


class RestCodes(Enum):
    """
    HTTP status codes for RESTful APIs.
    """
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    INTERNAL_SERVER_ERROR = 500
    SERVICE_UNAVAILABLE = 503
    SUCCESS = 200
    FAILURE = 500


class RestResponse:
    """
    a RESTful response class
    """
    def __init__(self, data: dict, code: RestCodes, status: str = None) -> None:
        """
        Initialize a RESTful response.

        :param data: The data to include in the response.
        :param code: The HTTP status code (can be an int or a string).
        :param status: The status message (optional).
        """
        self.data = data
        self.code = code
        self.status = status if status else code.name
        self.response = jsonify({"status": self.status,
                                 "data": self.data,
                                 "code": self.code.value}), self.code.value
    
    @staticmethod
    def create(data: dict, code: int | str | RestCodes = 200, status: str = None) -> tuple:
        """
        Create a RESTful response.
        :param data: The data to include in the response.
        :param code: The HTTP status code (can be an int, string, or RestCodes).
        :param status: The status message (optional).
        :return: A tuple containing the JSON response and the HTTP status code.
        """
        if not isinstance(code, RestCodes):

            try: 
                if isinstance(code, str):
                    if code.isdigit():
                        code = RestCodes(int(code))
                    else:
                        code = RestCodes[code.upper()]
                
                elif isinstance(code, int):
                    code = RestCodes(code)

            except Exception:
                code = RestCodes.INTERNAL_SERVER_ERROR

        response = RestResponse(data, code, status)
        return response.response
    

class MetaSimpleServer(type):
    """
    this is a meta class for SimpleServer 

    this meta class will make sure that any method in the SimpleServer that does't start with `_` is treated as a REST endpoint.

    
    In MetaSimpleServer.__new__:
    We use inspect.getmembers to wrap all public methods, including inherited ones,
    so that endpoints are available in subclasses as well.
    """

    def __new__(mcs, name, bases, attrs):
        """
        this magic method is called when a new class is created 
        it will iterate over all the methods in the class and if the method doesn't start with `_` it will be registered as a REST endpoint.
        """
        # Methods that should not be registered as endpoints
        excluded_methods = {'set_verbose'}
        
        # create the new instance than update it, this is done
        # so we can inspect the methods of the new instance with its hierarchy
        # other wise we would only see the methods of the base class
        attrs['_endpoint_map'] = {}
        attrs['_endpoint_method_map'] = {}
        new_instance = super().__new__(mcs, name, bases, attrs) 
        # predicate checks for both functions and methods by lambda if either is true it will return the member
        all_attrs = inspect.getmembers(new_instance, predicate=lambda x: inspect.isfunction(x) or inspect.ismethod(x))       
        for key, value in all_attrs:
            if not key.startswith("_") and key not in excluded_methods:
                # Register the method as a REST endpoint
                # Use the class name as logger name for unified logging
                new_method = mcs._wrap_endpoint(value, logger_name=name)
                setattr(new_instance, key, new_method)
                
                path = f'/{key}'.lower()

                if path in new_instance._endpoint_map:
                    raise ValueError(f"Endpoint path conflict: {path} is already registered. remember that endpoint paths are case-insensitive.")
                new_instance._endpoint_map[path] = key

        for property_name, property_obj in inspect.getmembers(new_instance, predicate=lambda x: isinstance(x, property)):
            if not property_name.startswith("_"):
                # Create a getter method for the property endpoint 
                # Use a factory function to capture property_name correctly in the closure
                def make_property_getter(prop_name):
                    def property_getter(self):
                        return getattr(self, prop_name)
                    property_getter.__name__ = f'_property_getter_{prop_name}'
                    return property_getter

                property_getter = make_property_getter(property_name)
                wrapped_getter = mcs._wrap_endpoint(property_getter)
                wrapped_getter.__name__ = f'_property_getter_{property_name}'
                
                setattr(new_instance, f'_property_getter_{property_name}', wrapped_getter)
                path = f'/property/{property_name}'.lower()
                if path in new_instance._endpoint_map:
                    raise ValueError(f"Endpoint path conflict: {path} is already registered. remember that endpoint paths are case-insensitive.")
                new_instance._endpoint_map[path] = f'_property_getter_{property_name}'

        return new_instance
        
    @classmethod
    def _wrap_endpoint(mcs, func, logger_name=None):
        """
        Wrap a method to be a REST endpoint.

        If the function has parameters, they will be extracted from the request and passed to the function.

        """
        # Apply enter_exit_logger decorator first with the function's qualified name
        # If logger_name is not provided, use the function's qualified name
        if logger_name is None:
            logger_name = func.__qualname__ if hasattr(func, '__qualname__') else func.__name__
        func = enter_exit_logger(logger_name)(func)

        @wraps(func)
        def wrapper(*args, **kwargs):
            if hasattr(func, '_is_wrapped'):
                return func(*args, **kwargs)
            try:
                # if json data is sent, update kwargs with the json data
                query_params = request.args.to_dict(flat=True)
                kwargs.update(query_params)
                
                if request.is_json:
                    input_data = request.get_json()
                    kwargs.update(input_data)

                result = func(*args, **kwargs)

                if isinstance(result, tuple) and len(result) == 2:
                    data, code = result
                    return RestResponse.create(data, code)
                
                return RestResponse.create(result)
            
            except Exception as e:
                print(traceback.format_exc())
                return RestResponse.create({"error": str(e)}, RestCodes.INTERNAL_SERVER_ERROR)

        wrapper._is_wrapped = True # Mark the function as wrapped to avoid double-wrapping
        return wrapper


class SimpleServer(metaclass=MetaSimpleServer):
    """
    A simple Flask server infrastructure.
    
    this class provides endpoints :
    - /
    - /index
    - /get_run_mode

    any other endpoints can be added in the future.

    to add a new endpoint, simply define a new method in this class with a unique name (that doesn't start with an underscore).

    to bind an endpoint to a spesific HTTP method (GET, POST, etc.), before super  
    add to self._endpoint_method_map  key, value pair i.e. self._endpoint_method_map['/new_endpoint'] = ['POST']

    Custom Flask Configuration:
    To add custom Flask configurations, set the custom_flask_configs class variable in your subclass.
    This dictionary will be applied to Flask's app.config during initialization.

    Example: 

    class MyServer(SimpleServer):
        # Custom Flask configuration
        custom_flask_configs = {
            'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,  # 16MB max file upload
            'JSON_SORT_KEYS': False,  # Don't sort JSON keys
            'SEND_FILE_MAX_AGE_DEFAULT': 0  # Disable caching for development
        }

        def __init__(self, demo_mode: bool = False, app_name: str = "MyServerApp"):
            self._endpoint_method_map['post_example'] = ['POST']
            super().__init__(demo_mode=demo_mode, app_name=app_name)
            
        def hello_world(self) -> dict:
            '''
            Returns a hello world message.
            '''
            return {"message": "Hello, world!"}

        def error_endpoint(self) -> dict:
            '''
            Returns an error message.
            '''
            raise Exception("This is an error message.")
        
        def spesific_http_code(self) -> tuple:
            '''
            Returns a specific HTTP status code.
            '''
            return {"message": "This endpoint returns a specific HTTP status code."}, 204 

        def post_example(self, var1, var2, var3='default') -> str:
            '''
            Returns a message indicating that a POST request was received.
            '''
            return f'{var1=}, {var2=}, {var3=}'

    """

    custom_flask_configs: dict = {} # add any custom flask configs here as key, value pairs

    def __init__(self, demo_mode: bool = False, app_name: str = "simple_server", verbose: bool = False) -> None:
        """
        Initializes the server application.
            
            :param demo_mode: If True, enables demo mode with additional logging.
            :type demo_mode: bool, optional
            :param app_name: The name of the application.
            :type app_name: str, optional
            :param verbose: If True, enables verbose logging.
            :type verbose: bool, optional

            :ivar demo_mode: Indicates whether the server is running in demo mode.
            :ivar app: The Flask application instance.
            :ivar logger: The logger instance for the server.
            :ivar run: Reference to the Flask app's run method.
            
            Initializes the Flask application, sets up CORS, applies custom Flask configurations from 
            the custom_flask_configs class variable, configures logging, and registers all endpoints.
            If demo mode is enabled, logs an informational message.
        """
        self.demo_mode = demo_mode
        self.logger_name = app_name
        self.app = Flask(app_name)
        CORS(self.app)

        for key, value in self.custom_flask_configs.items():
            self.app.config[key] = value
        
        # Add case-insensitive routing
        @self.app.before_request
        def normalize_url():
            """Normalize URL paths to lowercase for case-insensitive routing."""
            if request.path != request.path.lower():
                
                # Preserve query string if present
                if request.query_string:
                    new_url = request.path.lower() + '?' + request.query_string.decode('utf-8')
                else:
                    new_url = request.path.lower()
                return redirect(new_url, code=308)
            return None
        
        # setup logger
        self.logger = setup_logger(self.__class__.__name__)
        ## add werkzeug logger(flask)
        setup_logger('werkzeug')
        ## redirect stdout and stderr
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        sys.stdout = LoggerWriter(self.logger, level=20)  # INFO
        sys.stderr = LoggerWriter(self.logger, level=40)  # ERROR
        self.set_verbose(verbose)

        if self.custom_flask_configs:
            self.logger.debug(f"Applied custom Flask configurations: {self.custom_flask_configs}")

        self.run = self.app.run
        if self.demo_mode:
            self.logger.info("Demo mode is on")

        # route stdout & stderr to logger

        self._endpoint_map['/'] = 'index' # Map the root URL to the index method 

        self._register_endpoints()

        # add download endpoint
        logger_decorated_download = enter_exit_logger(self.logger_name)(self._download)
        self.app.route('/download', methods=['GET'])(logger_decorated_download)
        
    @property
    def verbose(self) -> bool:
        """
        Returns whether verbose logging is enabled.

        :return: True if verbose logging is enabled, False otherwise.
        :rtype: bool
        """
        return self._verbose

    def set_verbose(self, verbose: bool) -> None:
        """
        Sets the verbose logging mode.

        :param verbose: True to enable verbose logging, False to disable.
        :type verbose: bool
        """
        self._verbose = verbose

        if self._verbose:
            self.logger.setLevel("DEBUG")
            # Also update all handlers to DEBUG level
            for handler in self.logger.handlers:
                handler.setLevel("DEBUG")
            self.logger.debug("Verbose logging enabled.")
        else:
            self.logger.setLevel("INFO")
            # Set handlers back to INFO level
            for handler in self.logger.handlers:
                handler.setLevel("INFO")
            self.logger.info("Verbose logging disabled.")


    def _register_endpoints(self):
        for route, func_name in self._endpoint_map.items():
            methods = self._endpoint_method_map.get(func_name, ["GET", "POST"])
            func = getattr(self, func_name)
            self.app.route(route, methods=methods)(func)

    def index(self) -> tuple:
        """
        Returns the index page. 

        the index page lists all available API endpoints.
        """
        routes = []
        for rule in self.app.url_map.iter_rules():
            try:
                docs = rule.endpoint and getattr(self, rule.endpoint).__doc__
            except Exception:
                docs = ""
            routes.append({"endpoint": rule.endpoint, "methods": list(rule.methods), "url": str(rule), 'docs': docs})

        return {"message": f"Welcome to the {self.__class__.__name__} ", "routes": routes}
    
    def get_run_mode(self) -> tuple:
        """
        Returns the current run mode of the server.

        :return: A tuple containing the run mode and a message.
        """
        if self.demo_mode:
            return {"message": "Server is running in demo mode", "run_mode": "demo"}
        return {"message": "Server is running in production mode", "run_mode": "production"}

    def _download(self) -> Response:
        """
        Download a file from the server.

        The file path can be provided as:
        - A query parameter: GET /download?path=/path/to/file
        - A JSON body parameter: {"path": "/path/to/file"}

        Security Features:
        - Path traversal protection: Paths are normalized to prevent directory traversal attacks.
        - Blocked paths: Configure BLOCKED_DOWNLOAD_PATHS in custom_flask_configs to block specific paths.
        - Allowed paths (whitelist): Configure ALLOWED_DOWNLOAD_PATHS in custom_flask_configs to restrict 
          downloads to specific directories. If set, only files within these directories can be downloaded.

        :return: The file as an attachment, or an error response.
        :rtype: Response
        """
        # get path from url query parameter
        file_path = request.args.get('path', None)

        # if not in query parameter, get from json body
        if not file_path and request.is_json:
            try:
                input_data = request.get_json()
                file_path = input_data.get('path', None)
            except Exception:
                file_path = None

        # validate file path parameter
        if not file_path:
            return RestResponse.create({"error": "No file path provided"}, RestCodes.BAD_REQUEST)

        # normalize path to prevent directory traversal attacks (e.g., ../../etc/passwd)
        file_path = os.path.realpath(file_path)

        # check for allowed paths (whitelist) - if configured, file must be within one of these directories
        allowed_paths = self.app.config.get('ALLOWED_DOWNLOAD_PATHS', [])
        if allowed_paths:
            is_allowed = any(
                file_path.startswith(os.path.realpath(allowed_path))
                for allowed_path in allowed_paths
            )
            if not is_allowed:
                return RestResponse.create(
                    {"error": "Access to the specified file path is not allowed"},
                    RestCodes.FORBIDDEN
                )

        # check for blocked paths (blacklist)
        blocked_paths = self.app.config.get('BLOCKED_DOWNLOAD_PATHS', [])
        if blocked_paths:
            is_blocked = any(
                file_path.startswith(os.path.realpath(blocked_path))
                for blocked_path in blocked_paths
            )
            if is_blocked:
                return RestResponse.create(
                    {"error": "Access to the specified file path is blocked"},
                    RestCodes.FORBIDDEN
                )

        # check if file exists
        if not os.path.isfile(file_path):
            return RestResponse.create({"error": f"File not found: {file_path}"}, RestCodes.NOT_FOUND)

        base_name = os.path.basename(file_path)
        try:
            return send_file(file_path, as_attachment=True, download_name=base_name)
        except Exception as e:
            trace = traceback.format_exc()
            self.logger.debug(trace)
            self.logger.error(f"Error sending file {file_path}: {str(e)}")
            return RestResponse.create({"error": str(e)}, RestCodes.INTERNAL_SERVER_ERROR)
            
        

class AdvancedServer(SimpleServer):
    """
    This class extends the SimpleServer to provide advanced features such as
    dynamic endpoint registration and method exposure for unit instances.

    when a unit instance is added, its public methods are automatically exposed as endpoints.
    the endpoint paths are namespaced by the unit instance name, i.e., /{unit_name}/{method_name}.

    the units are instances of classes that define their own methods.

    See example below for clarification:

    class Foo:
     def bar(self):
          return {"message": "Hello from Foo.bar!"}
     def echo(self, *args, **kwargs):
         return {"message": "Hello from Foo.echo!", "args": args, "kwargs": kwargs}

    class Fizz:
        def buzz(self):
            return {"message": "Hello from Fizz.buzz!"}
        def error(self):
            raise Exception("Error from Fizz.error")

    class MyAdvancedServer(AdvancedServer):
        def __init__(self, demo_mode: bool = False, unit_instances: dict | None = None) -> None:
            super().__init__(demo_mode=demo_mode, app_name="MyAdvancedServerApp", unit_instances=unit_instances)

        def hello(self) -> dict:
            return {"message": "Hello from MyAdvancedServer.hello!"}

    if __name__ == "__main__":
        server = MyAdvancedServer(demo_mode=True, unit_instances={'foo':Foo(), "fizz": Fizz()})
        server.run(host="0.0.0.0", port=5001)

    """

    def __setattr__(self, name, value) -> None:
        """
        If the class sets an attribute that is a method, it should be wrapped as an endpoint method
        and register them in self._endpoint_map for public methods of the server class.

        this logic will be skipped for private methods (starting with _) and internal 'run', 'app' methods.

        :param name: The name of the attribute being set.
        :param value: The value of the attribute being set.
        :return: None
        """

        if (inspect.ismethod(value) or inspect.isfunction(value)) and not name.startswith("_") and name not in ['run', 'app']:
            # Wrap the method if not already wrapped
            if not getattr(value, '_is_wrapped', False):
                # Use the server's logger name for all unit methods
                server_logger_name = getattr(self, 'logger_name', self.__class__.__name__)
                value = MetaSimpleServer._wrap_endpoint(value, logger_name=server_logger_name)
                value.__name__ = name
                value._is_wrapped = True
                # Add to endpoint map
                self._endpoint_map[f'/{name}'] = name

        super().__setattr__(name, value)

    def __init__(self, demo_mode: bool = False, app_name: str | None = None, unit_instances: dict | None = None, verbose: bool = False) -> None:
        """
        :param demo_mode: Whether to run the server in demo mode.
        :param app_name: The name of the application.
        :param unit_instances: A dictionary of unit instances to register with the server.
         the unit dictionary maps unit names to their instances. i.e. {'foo': Foo(), 'fizz': Fizz()}
        :param verbose: Whether to enable verbose logging.

        :return: None
        """

        self.unit_instances = {} if unit_instances is None else unit_instances  # dont use {} as default as its a bad practice
        app_name = app_name if app_name else self.__class__.__name__
        for unit_name, inst in self.unit_instances.items():
            # add instance to the server as a discrete attribute
            setattr(self, f'_{unit_name}', inst)
            # register all public methods of the unit instance as endpoint methods
            # predicate checks for both functions and methods by lambda if either is true it will return the member
            for method_name, method in inspect.getmembers(inst, predicate=lambda x: inspect.isfunction(x) or inspect.ismethod(x)):
                if not method_name.startswith("_"):
                    # setattr will trigger __setattr__ which wraps the method with _wrap_endpoint
                    # _wrap_endpoint will use the server's logger (app_name) for all unit methods
                    setattr(self, f'{unit_name}_{method_name}', method)

            for property_name, _ in inspect.getmembers(inst.__class__, predicate=lambda x: isinstance(x, property)):
                if not property_name.startswith("_"):

                    def property_getter(prop_name=property_name, unit_inst=inst):
                        return getattr(unit_inst, prop_name)
                         
                    setattr(self, f'{unit_name}_property_{property_name}', property_getter)        

            # Update endpoint paths for a pretty path /unit_method -> /unit/method
            for path, value in list(self._endpoint_map.items()):
                
                if path.startswith(f'/{unit_name}_property_'):
                    new_path = path.replace(f'/{unit_name}_property_', f'/{unit_name}/property/')
                    self._endpoint_map[new_path] = value
                    del self._endpoint_map[path]
                    continue

                if path.startswith(f'/{unit_name}_'):
                    new_path = path.replace(f'/{unit_name}_', f'/{unit_name}/')
                    self._endpoint_map[new_path] = value
                    del self._endpoint_map[path]
        # after all unit instances have been processed super will generate the app
        super().__init__(demo_mode, app_name=app_name, verbose=verbose)