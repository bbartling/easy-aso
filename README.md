
# Easy ASO 🤖🕹️⚡

Welcome to Easy ASO, the ultimate command tool for Automated Supervisory Optimization (ASO) of BACnet systems in EMIS applications. 
Built on a seamless Python asyncio framework, Easy ASO comes with a fully integrated BACnet asyncio stack for convenience, making BACnet—the default protocol in the HVAC industry—effortless to use. 
Other protocols can also be implemented during the development process, offering flexibility and extensibility.


## The Skeleton of ASO 🦾🎮🏢
Control BACnet systems on a simple `on_start`, `on_step`, and `on_stop` structure:

```python
class CustomHvacAso(EasyASO):
    async def on_start(self):
        print("Custom ASO is deploying! Lets do something!")

    async def on_step(self):
	# BACnet read request
        sensor = await self.bacnet_read("192.168.0.122", "analog-input,1")

        # Custom step logic - BACnet write request
        override_valve = sensor + 5.0
        await self.bacnet_write("192.168.0.122", "analog-output,2", override_valve)

        print("Executing step actions... The system is being optimized!")
        await asyncio.sleep(60)

    async def on_stop(self):
        # Custom stop logic - BACnet release request
        await self.bacnet_write("192.168.0.122", "analog-output,2", 'null')
        print("Executing stop actions... The system is released back to normal!")
```

**⚠️👷🚧🏗️ WARNING** - This repo is new and under construction, so some features are not fully developed yet but stay tuned!  

## BACnet Services Supported 💼

- [x] Read
- [x] Write
- [ ] Read Multiple
- [ ] Write Multiple
- [ ] Whois
- [ ] Read Priority Array
- [ ] Anything else? 🤔

## Exploring Remote BACnet Sites with `tester.py` 🔍

The `tester.py` script, located in the scripts directory, provides a utility for exploring a remote BACnet site via the bacpypes3 console.  
This tool is designed to assist in the setup and configuration of the `easy-aso` project, streamlining the integration process.  

For detailed information and instructions on using the `Tester.py` script, please refer to the `setup_scripts` directory [README](https://github.com/bbartling/easy-aso/tree/develop/setup_scripts) for more information.

- [x] Read Property (`read_property`)
- [x] Write Property (`write_property`)
- [x] Read Property Multiple (`read_property_multiple`)
- [x] Read Priority Array (`read_property` with `priority-array`)
- [x] Device Discovery (`who-is`)
- [x] Object Discovery (`who-has`)
- [x] Read All Points (`do_point_discovery`)
- [x] Router Discovery (`who_is_router_to_network`)

## Writeups 💡

Why can't a BAS be free?  
* https://www.linkedin.com/pulse/can-building-automation-free-ben-bartling-mtvwc/

Can ASO be easy?  
* https://www.linkedin.com/pulse/can-aso-easy-ben-bartling-eftlc/?trackingId=deyXF1fr00wbx2sLt0mSDQ%3D%3D

Can ASO be used to aid Fault Detection and Diagnostics (FDD)?
* https://www.linkedin.com/posts/ben-bartling-510a0961_smartbuildings-faultdetection-buildingautomation-activity-7251264077828653056-EC9l

## In Progress 🛠️
- [x] Overhaul app code with bacpypes3
- [x] Test basic functionality with a fake BACnet app
- [x] Create unit tests for BACnet server and client with docker containers
- [ ] Publish the project as a Python library on PyPI

## Future 🚀
- Make tutorials for ASO based on an [LBNL reference](https://transformingbuildingcontrols.lbl.gov/) for:
  - Electrical load shed example
  - Classic BAS Supervisory control to share data globally via BACnet priority
  - AHU duct static pressure and temperature setpoint trim and respond (T&R)
  - AHU demand control ventilation based on G36 and ventilation calcs
  - VAV box system occupied-standby with occupancy integration to HVAC
  - Overnight building flush
  - Overnight BACnet override release bot
  - Heat pump system cold weather staggered start for electrical power management
  - Electrical load shift
  - Identify rogue zones in an HVAC system
  - Self-commissioning AHU system bots
  - How to run Python scripts long-term in a Docker container


## Schematics 🔧:

`easy-aso` is designed to be a fully discoverable BACnet server that can seamlessly integrate into any existing building automation system (BAS). 
The core of this integration relies on a discoverable BACnet `binary-value` point named `optimization-enabled`. 
This point allows building operators to maintain full control over the Automated Systems Optimization (ASO) processes. 
If, at any time, an operator needs to disable an ASO instance, the `optimization-enabled` point provides a direct means to turn off the optimization for any part of the HVAC system. 
This feature is crucial for maintaining operational flexibility and preventing unwanted system behavior. 

In the event of an issue, such as undesired system behavior or an operator decision to revert control, this BACnet point can be incorporated directly into the logic of `easy-aso`. 
This ensures that any overrides the script may have applied are released safely and promptly. 
For a clearer understanding of how this callback is integrated into the ASO design of `easy-aso`, refer to the example Python files that demonstrate its practical implementation.

By default, `easy-aso` is deployed within a secure, internal network (behind a firewall), where it can operate efficiently with existing IoT.  
![Schematic of Python script deployment](https://raw.githubusercontent.com/bbartling/easy-aso/develop/new_building.png)

However, `easy-aso` is also fully compatible with traditional operational technology (OT) systems that do not have internet access, supporting more traditional building environments that rely solely on local control.  
![Schematic of Python script deployment traditional](https://raw.githubusercontent.com/bbartling/easy-aso/develop/traditional_building.png)

Flexibility is at the heart of `easy-aso`. In a Python asyncio environment, it is easy to extend and build around, enabling the potential for cloud-based integrations. 
This presents an intriguing solution for a Master Systems Integrator (MSI) looking to completely revamp their existing edge environment and start fresh with a modernized approach.
![Schematic of Python script deployment as iot](https://raw.githubusercontent.com/bbartling/easy-aso/develop/easy_aso_as_iot.png)

## Getting Started with easy-aso 🚀

Follow the instructions below to set up the `easy-aso` project on your local Linux machine.  
Until the project is available on PyPI, you can install it locally by following these steps.  

After the scripts are thoroughly tested and commissioned, they can be run long-term in a Docker container.  
See the sub-directory `docker_setup` for more information.

### Step 1: Clone the Repository 📂
First, clone the `easy-aso` repository to your local machine:
```bash
git clone https://github.com/bbartling/easy-aso
```

### Step 2: Install the Package Locally 🖥️
Navigate into the project directory and install it using `pip`. This will make the `easy-aso` package available in your Python environment.
```bash
cd easy-aso
pip install .
```

### Step 3: Try out a few sample Py files 🧪
* Check out the `examples` directory for [sample applications](https://github.com/bbartling/easy-aso/tree/develop/examples).
* Review the `easy-aso` API documentation [README](https://github.com/bbartling/easy-aso/tree/develop/tests) for method call specifics when creating apps.
* Run a [fake BACnet app](https://github.com/bbartling/easy-aso/tree/develop/setup_scripts) and try out code such as `tester.py` in a sandbox environment. Note that both require two Linux devices — I use an Ubuntu VM and a Raspberry Pi for the fake BACnet device, which acts as another BACnet device on the LAN.

## Cybersecurity Disclaimer 🔐

Easy ASO is designed as an operations technology (OT) application with no built-in cloud connectivity, but it is fully capable of anything programmed in Python. Any implementation of cloud connectivity for this app is the responsibility of the user. It is crucial to understand the cybersecurity implications of sending bi-directional signals to building systems.

**Security Best Practices**:  
- Ensure the safety of your systems by following recommended cybersecurity best practices, including network, VPN, and VM access hardening, secure configurations, and routine security checks. 🛡️
- Work closely with the IT team when enabling cloud connectivity to ensure it complies with your organization's security policies. 🔒
- Involve IT in all stages of the project and address any issues related to the implementation of easy-aso.  
- Safeguard building control systems by utilizing access controls, encryption, and secure communication protocols to prevent unauthorized access. 🔐
- Act in the capacity of an ICS security specialist on behalf of your client, and promptly report any vulnerabilities or issues you discover.  
- Develop an incident response plan to ensure the project is prepared for any potential security breaches, enabling swift and effective action from the incident response team should an issue arise during the implementation of easy-aso. 🔧

## Contributing 🛠️

PRs, git issues, and discussions are highly encouraged!  
Please reference the [README](https://github.com/bbartling/easy-aso/tree/develop/tests) for more information.

## License 📄

【MIT License】  
Copyright 2024 Ben Bartling

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
