# Easy ASO BACnet Application

This project allows you to create BACnet-enabled applications for Automated Supervisory Optimization (ASO). You can read BACnet properties, interact with BACnet devices, and optionally disable the BACnet server functionality based on your needs.


## Running the Application

After getting setup with the local pip install process you can run the application by specifying various arguments such as the name of the BACnet server, BACnet instance ID, and optionally the network address which arguments built into the `bacpypes3` project.

### Basic Example:

```bash
python examples/make_read_request.py --name EasyAso --instance 99999
```

This will:
- Create a BACnet application named `EasyAso`.
- Assign the BACnet instance ID `99999`.
- Begin interacting with BACnet devices.

### Running with a Custom UDP Port and Address

If you need to specify a custom UDP port or IP address for your device, you can pass the `--address` argument:

```bash
python examples/make_read_request.py --name EasyAso --instance 99999 --address 10.200.200.223/24:47820
```

This will:
- Use the IP address `10.200.200.223/24` and UDP port `47820`.

### Disabling BACnet Server Functionality

"You can disable the BACnet optimization kill switch, represented by the `self.get_optimization_enabled_status()` callback in the app examples, by using the `--no-bacnet-server` flag. When this argument is passed, the app will start without creating the `binary-value,1` BACnet point for `optimization-enabled`. The app will still be discoverable as a BACnet device, but without the `optimization-enabled` BACnet point. This feature can be useful if your ASO project does not require a BACnet kill switch."

```bash
python examples/make_read_request.py --name EasyAso --instance 99999 --no-bacnet-server
```

This will:
- Skip creating the BACnet server and the `optimization_enabled` kill switch functionality during initialization.
  
## Application Architecture

Your application contains lifecycle methods that are invoked during the execution:

- **`on_start()`**: Initializes the application and sets up any required configurations.
- **`on_step()`**: This runs at regular intervals and includes the logic for BACnet reads or other processing.
- **`on_stop()`**: Clean-up method to gracefully shutdown the application.

### Example: VAV Box Discharge Air Temperature Read

The example script reads the discharge air temperature sensor value from a BACnet MSTP device (`11:21`) or an IP device (`10.200.200.233`) by performing a BACnet read request:

```bash
python examples/make_read_request.py --name EasyAso --instance 99999
```

This will periodically read the sensor value and print it to the console.

---

## Arguments Overview

- **`--name`**: The name of the BACnet server (e.g., `EasyAso`).
- **`--instance`**: The BACnet instance ID (e.g., `99999`).
- **`--address`**: The network address in the format `<IP>/<Subnet>:<Port>`. This is optional if you're using a standard address.
- **`--no-bacnet-server`**: Disables the BACnet server functionality like the optimization kill switch.

