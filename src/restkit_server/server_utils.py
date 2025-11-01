# pylint: disable=E1101
"""
utilities for Flask applications
"""


from enum import Enum
import inspect
import os
import sys
import traceback

from flask import Flask, request, jsonify
from flask_cors import CORS
from functools import wraps

try:  # Prefer package-relative import
    from .logger import setup_logger, LoggerWriter  # type: ignore
except ImportError:  # Fallback to path manipulation when not in a package context
    THIS_DIR = os.path.dirname(os.path.abspath(__file__))
    if THIS_DIR not in sys.path:
        sys.path.append(THIS_DIR)
    from logger import setup_logger, LoggerWriter


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
        # create the new instance than update it, this is done
        # so we can inspect the methods of the new instance with its hierarchy
        # other wise we would only see the methods of the base class
        attrs['_endpoint_map'] = {}
        attrs['_endpoint_method_map'] = {}
        new_instance = super().__new__(mcs, name, bases, attrs) 
        all_attrs = inspect.getmembers(new_instance, predicate=inspect.isfunction)
        for key, value in all_attrs:
            if not key.startswith("_"):
                # Register the method as a REST endpoint
                new_method = mcs._wrap_endpoint(value)
                setattr(new_instance, key, new_method)
                new_instance._endpoint_map[f'/{key}'] = key

        return new_instance
        
    @classmethod
    def _wrap_endpoint(mcs, func):
        """
        Wrap a method to be a REST endpoint.

        If the function has parameters, they will be extracted from the request and passed to the function.

        """
        # 

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

    try: 

    class MyServer(SimpleServer):
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
    def __init__(self, demo_mode: bool = False, app_name: str = "simple_server"):
        """
        Initializes the server application.
            
            :param demo_mode: If True, enables demo mode with additional logging.
            :type demo_mode: bool, optional
            :param app_name: The name of the application.
            :type app_name: str, optional

            :ivar demo_mode: Indicates whether the server is running in demo mode.
            :ivar app: The Flask application instance.
            :ivar logger: The logger instance for the server.
            :ivar run: Reference to the Flask app's run method.
            
            Initializes the Flask application, sets up CORS, configures logging, and registers all endpoints.
            If demo mode is enabled, logs an informational message.
        """
        self.demo_mode = demo_mode
        self.logger_name = app_name
        self.app = Flask(app_name)
        CORS(self.app)
        
        # setup logger
        self.logger = setup_logger(self.__class__.__name__)
        ## add werkzeug logger(flask)
        setup_logger('werkzeug')
        ## redirect stdout and stderr
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        sys.stdout = LoggerWriter(self.logger, level=20)  # INFO
        sys.stderr = LoggerWriter(self.logger, level=40)  # ERROR

        self.run = self.app.run
        if self.demo_mode:
            self.logger.info("Demo mode is on")

        # route stdout & stderr to logger

        self._endpoint_map['/'] = 'index' # Map the root URL to the index method 

        self._register_endpoints()

    def _register_endpoints(self):
        for route, func_name in self._endpoint_map.items():
            methods = self._endpoint_method_map.get(func_name, ["GET", "POST"])
            self.app.route(route, methods=methods)(getattr(self, func_name))

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
                value = MetaSimpleServer._wrap_endpoint(value)
                value.__name__ = name
                value._is_wrapped = True
                # Add to endpoint map
                self._endpoint_map[f'/{name}'] = name

        super().__setattr__(name, value)

    def __init__(self, demo_mode: bool = False, app_name: str | None = None, unit_instances: dict | None = None) -> None:
        """
        :param demo_mode: Whether to run the server in demo mode.
        :param app_name: The name of the application.
        :param unit_instances: A dictionary of unit instances to register with the server.
         the unit dictionary maps unit names to their instances. i.e. {'foo': Foo(), 'fizz': Fizz()}
        :return: None
        """

        self.unit_instances = {} if unit_instances is None else unit_instances  # dont use {} as default as its a bad practice
        app_name = app_name if app_name else self.__class__.__name__
        for unit_name, inst in self.unit_instances.items():
            # add instance to the server as a discrete attribute
            setattr(self, f'_{unit_name}', inst)
            # register all public methods of the unit instance as endpoint methods
            for method_name, method in inspect.getmembers(inst, predicate=inspect.ismethod):
                if not method_name.startswith("_"):
                    setattr(self, f'{unit_name}_{method_name}', method)

            # Update endpoint paths for a pretty path /unit_method -> /unit/method
            for path, value in list(self._endpoint_map.items()):
                if path.startswith(f'/{unit_name}_'):
                    new_path = path.replace(f'/{unit_name}_', f'/{unit_name}/')
                    self._endpoint_map[new_path] = value
                    del self._endpoint_map[path]
        # after all unit instances have been processed super will generate the app
        super().__init__(demo_mode, app_name=app_name)