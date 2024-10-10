
# Easy-ASO Developer Documentation

This backend utilizes the `bacpypes3` library for BACnet communication, providing methods for reading, writing, and retrieving multiple properties from BACnet devices. Below is the documentation aimed at developers, focusing on method usage, exceptions, and best practices for integrating EasyASO with BACnet devices.

## Abstract Base Class (EasyASO)
The `EasyASO` class is an abstract base class (ABC) that requires subclasses to implement key lifecycle methods. This structure allows for consistent management of application lifecycles and BACnet communication tasks.

### on_start()
```python
@abstractmethod
async def on_start(self):
    """Abstract method that must be implemented by subclasses for start logic."""
    pass
```
This method is invoked at the start of the application. Implement this to define logic that should run on initialization, such as setting up connections or initializing application-level variables.

### on_step()
```python
@abstractmethod
async def on_step(self):
    """Abstract method that must be implemented by subclasses for step logic."""
    pass
```
Called on each cycle during the runtime of the application. Use this to define repetitive operations such as polling BACnet devices, updating sensors, or performing computations that must run continuously.

### on_stop()
```python
@abstractmethod
async def on_stop(self):
    """Abstract method that must be implemented by subclasses for stop logic."""
    pass
```
Invoked when the application is about to terminate. Implement this to handle any necessary cleanup, such as closing connections, saving application state, or releasing resources.

## Example Subclass Implementation with Exception Handling
Below is an example of how to extend EasyASO to implement lifecycle methods with proper exception handling, ensuring that any errors are caught and logged, preventing the application from crashing unexpectedly:

```python
class MyCustomApp(EasyASO):
    async def on_start(self):
        try:
            print("App is starting...")
            # Add any initialization logic here
        except Exception as e:
            print(f"ERROR in on_start: {e}")

    async def on_step(self):
        try:
            print("App is running...")
            # Add core processing logic here
        except Exception as e:
            print(f"ERROR in on_step: {e}")
            # Handle specific errors or reattempt logic if necessary

    async def on_stop(self):
        try:
            print("App is stopping...")
            # Add any cleanup logic here
        except Exception as e:
            print(f"ERROR in on_stop: {e}")

```

## BACnet API Methods

### async bacnet_read(address: str, object_identifier: str, property_identifier="present-value") → Any
Handles reading a property from a BACnet object. Defaults to reading the present-value property.

#### Parameters:
- `address (str)`: The network address of the BACnet device.
- `object_identifier (str)`: The object identifier (e.g., "analogInput 1").
- `property_identifier (str, optional)`: The property to read (default is "present-value").

#### Returns:
- The value of the property if successful, or `None` if an error occurs.

#### Exceptions:
- `ErrorRejectAbortNack`: Raised when there is an error or rejection from the BACnet device.
- `TypeError`: Raised if invalid types are used for parameters.
- `Exception`: Raised for any other unexpected errors.

### async bacnet_write(address: str, object_identifier: str, value: Any, priority: int = -1, property_identifier="present-value") → None
Handles writing a value to a BACnet object. If the value is "null", it releases an override using `Null()`.

#### Parameters:
- `address (str)`: The network address of the BACnet device.
- `object_identifier (str)`: The object identifier (e.g., "analogInput 1").
- `value (Any)`: The value to write to the object. "null" triggers an override release.
- `priority (int, optional)`: Write priority (defaults to -1).
- `property_identifier (str, optional)`: The property to write (default is "present-value").

#### Exceptions:
- `ErrorRejectAbortNack`: Raised if the device rejects the write request.
- `TypeError`: Raised if parameter types are incorrect.
- `Exception`: Raised for other unexpected errors.

### async bacnet_rpm(address: Address, *args: str) → List[Dict[str, Any]]
Performs a Read Property Multiple (RPM) operation to read multiple properties from a BACnet device in one request.

#### Parameters:
- `address (Address)`: The network address of the BACnet device.
- `args (str)`: A list of object identifiers and property identifiers to read.

#### Returns:
- A list of dictionaries with BACnet object property values or error messages.

#### Notes:
- RPM retrieves object identifiers, property identifiers, and their values or errors.
- Vendor-specific information is used to ensure compatibility with custom object types.

#### Exceptions:
- `ErrorRejectAbortNack`: Raised if the device rejects the request.
- `Exception`: Raised for other unexpected errors.

## Additional Notes
- Ensure that BACnet devices are correctly configured and reachable for API methods to function as expected.
- Logs are provided for troubleshooting communication issues.
- Always handle exceptions properly to prevent the application from crashing unexpectedly.

## Signal Handling and Lifecycle Management
The `run()` method in `EasyASO` manages signal processing for clean application shutdown using signals such as `SIGINT` and `SIGTERM`. The lifecycle methods (`on_start`, `on_step`, `on_stop`) are orchestrated automatically.
