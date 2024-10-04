
# Easy-ASO API Documentation

This backend utilizes the `bacpypes3` library for BACnet communication, providing methods for reading, writing, and retrieving multiple properties from BACnet devices.

## ABC Requirements for `EasyASO`

The `EasyASO` class is an abstract base class (ABC) that requires subclasses to implement the following methods to handle the lifecycle of an application.

### `on_start()`
```python
@abstractmethod
async def on_start(self):
    """Abstract method that must be implemented by subclasses for start logic."""
    pass
```
This method is called when the application starts. Subclasses must implement this to define the initialization or startup logic required when running the app.

### `on_step()`
```python
@abstractmethod
async def on_step(self):
    """Abstract method that must be implemented by subclasses for step logic."""
    pass
```
This method is intended to handle repetitive operations or tasks within the application. Implement this to define what happens during each "step" or cycle of your application.

### `on_stop()`
```python
@abstractmethod
async def on_stop(self):
    """Abstract method that must be implemented by subclasses for stop logic."""
    pass
```
This method is called when the application is shutting down. Implement this to handle any cleanup or graceful stopping procedures required before termination.

---

### Example Usage:

Subclasses should implement these methods to fulfill the requirements of the abstract `EasyASO` class. Here’s a quick example:

```python
class MyCustomApp(EasyASO):
    async def on_start(self):
        print("App is starting...")

    async def on_step(self):
        print("App is running...")

    async def on_stop(self):
        print("App is stopping...")
```

## BACnet API Methods

---

### `async bacnet_read(address: str, object_identifier: str, property_identifier="present-value") → Any`

Handles reading from a BACnet object. Defaults to reading the `present-value` property.

**Parameters:**
- **address** (`str`): The network address of the BACnet device.
- **object_identifier** (`str`): Identifier for the BACnet object (e.g., `"analogInput 1"`).
- **property_identifier** (`str`, optional): The specific property of the object to read. Defaults to `"present-value"`.

**Returns:**
- The value of the requested property if successful. Returns `None` if an error occurs during the read operation.

**Exceptions:**
- **ErrorRejectAbortNack**: Raised if there is an error or rejection from the BACnet device during the read operation.
- **TypeError**: Raised when there's a type mismatch or invalid inputs during the process.
- **Exception**: Raised for any other unexpected errors during the BACnet read process.

---

### `async bacnet_write(address: str, object_identifier: str, value: Any, priority: int = -1, property_identifier="present-value") → None`

Handles writing a value to a BACnet object. If the value is `"null"`, it releases the override using `Null()`.

**Parameters:**
- **address** (`str`): The network address of the BACnet device.
- **object_identifier** (`str`): Identifier for the BACnet object (e.g., `"analogInput 1"`).
- **value** (`Any`): The value to write to the object. If `"null"`, triggers an override release.
- **priority** (`int`, optional): The priority of the write operation. Defaults to `-1` (no priority).
- **property_identifier** (`str`, optional): The specific property of the object to write to. Defaults to `"present-value"`.

**Returns:**
- None. Logs the outcome of the operation.

**Exceptions:**
- **ErrorRejectAbortNack**: Raised if there is an error or rejection from the BACnet device during the write operation.
- **TypeError**: Raised when there's a type mismatch during the process.
- **Exception**: Raised for any other unexpected errors during the BACnet write process.

---

### `async bacnet_rpm(address: Address, *args: str) → List[Dict[str, Any]]`

Performs a Read Property Multiple (RPM) operation to read multiple BACnet properties in one request.

**Parameters:**
- **address** (`Address`): The network address of the BACnet device.
- **args** (`str`): A list of object identifiers and property identifiers to read.

**Returns:**
- A list of dictionaries, each representing a BACnet object’s property and its value or an error message.

**Notes:**
- RPM retrieves a list of object identifiers, property identifiers, and their values or errors.
- Vendor information is used to resolve object and property types, ensuring compatibility with custom types.

**Exceptions:**
- **ErrorRejectAbortNack**: Raised if an error or rejection occurs during the RPM operation.
- **Exception**: Raised for any unexpected errors during the RPM process.

---

## Additional Notes:
- Make sure the BACnet devices are correctly configured and reachable for the API methods to work properly.
- Logs are provided for troubleshooting purposes.
