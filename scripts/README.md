
# BACnet Network Testing Tool

This tool allows for testing BACnet networks using the [bacpypes3](https://bacpypes.readthedocs.io/en/stable/) library. It provides a console interface for sending BACnet commands, discovering devices, reading and writing to BACnet points, checking priority arrays, and performing supervisory logic checks. The tool also supports saving BACnet device configurations in YAML format.

## Features
- **Device Discovery (Who-Is)**
- **Mapping out BAS Supervisory Level Writing and save data to YAML**
- **Reading and Writing BACnet Points**
- **Checking BACnet Priority Arrays**
- **Saving Device Configurations to YAML**
- **Performing Supervisory Logic Checks**
- **Running on a specific IP and UDP port**
- **Interactive BACpypes3 Console for BACnet Network Exploration**

## Installation

Install the required dependencies:

```bash
pip install bacpypes3 iffaddr pyyaml
```

## Running the Tool

To start the bacpypes3 console with your script:

```bash
python tester.py --debug
```

Alternatively, to run on a specific IP and UDP port:

```bash
python tester.py --address <ip-address>/24:<port> --debug
```

Example:

```bash
python tester.py --address 10.7.6.201/24:47820 --debug
```

## Basic Commands

You can access all available commands in the console by typing:

```bash
> help
```

Here are the most commonly used commands:

### Discover Devices

Discover BACnet devices using the `whois` command. You can specify a range of device instance IDs.

```bash
> whois <low_limit> <high_limit>

## Supervisory Logic Check
Discover devices within a range of instance IDs and check the BACnet priority array to detect supervisory logic:

```bash
> supervisory_logic_checks <low_limit> <high_limit>
```

Example:

```bash
> whois 10 110
```

### Read Point Priority Array

Check the priority array of a specific point:

```bash
> read_point_priority_arr <device_address> <object_type>,<instance_id>
```

Example:

```bash
> read_point_priority_arr 10.200.200.27 analog-value,8
```

### Read Multiple Points

Use `rpm` (Read Property Multiple) to read multiple properties at once:

```bash
> rpm <device_address> <object_type>,<instance_id> <property_identifier>
```

Example:

```bash
> rpm 10.200.200.27 analog-input,1 present-value analog-input,2 present-value
```

### Supervisory Logic Check

Discover devices within a range of instance IDs and check the BACnet priority array to detect supervisory logic:

```bash
> supervisory_logic_checks <low_limit> <high_limit>
```

Example:

```bash
> supervisory_logic_checks 1 100
```

### Save Device Configuration

Save the discovered points from a device to a YAML file:

```bash
> save_device_yaml_config <instance_id>
```

Example:

```bash
> save_device_yaml_config 201201
```

### Discover Points on a Device

Discover all points available on a specific device:

```bash
> point_discovery <instance_id>
```

Example:

```bash
> point_discovery 792000
```

### Reading and Writing Points

You can read or write the present value of a specific point.

#### Reading a Point:

```bash
> read <device_address> <object_type>,<instance_id> <property_identifier>
```

Example:

```bash
> read 10.7.6.161/24:47820 analog-value,99 present-value
```

#### Writing to a Point (with priority):

```bash
> write <device_address> <object_type>,<instance_id> <property_identifier> <value> <priority>
```

Example:

```bash
> write 32:18 analog-value,14 present-value 72.0 10
```

### Other Commands

- **Who-Has:**
  ```bash
  > whohas <object_type>,<instance_id> <device_address>
  ```
  Example:
  ```bash
  > whohas analog-value,302 10.7.6.161/24:47820
  > whohas "ZN-T"
  ```

- **Who-Is Router to Network:**
  ```bash
  > who_is_router_to_network
  ```

## Example Session

```bash
$ python tester.py
> whois 10 110
device,24 @ 12:24
description: VAV CTRL/ACT/DP,HTG,FAN
...
> read_point_priority_arr 10.200.200.27 analog-value,8
Priority level 1: null = ()
Priority level 2: null = ()
Priority level 9: real = 60.13
...
> rpm 10.200.200.27 analog-input,1 present-value analog-input,2 present-value
analog-input,1 present-value 62.65
analog-input,2 present-value 59.34
...
> who_is_router_to_network
10.200.200.26
    11, 12

```

## Conclusion

This tool provides a flexible way to interact with BACnet devices using the bacpypes3 library. You can explore BACnet networks, perform diagnostics, read/write points, and check for supervisory logic overrides through an intuitive console interface.
