# Easy ASO

Easy ASO is a streamlined tool designed for Automated Supervisory Optimization (ASO) of BACnet systems. With simple configuration and intuitive commands, it simplifies the process of monitoring and adjusting building systems to optimize performance, reduce energy consumption, and maintain comfort levels.

By automating BACnet property reads and writes, Easy ASO enables users to implement control strategies with ease, eliminating complexity and making optimization accessible and highly customizable. With Python as your tool, your creativity is the only limitation. Examples are designed to be 100 lines of code or less!



## BACnet Services Supported

- [x] Read
- [x] Write

## `Tester.py` inside the scripts directory for exploring a remote BACnet site via the bacpypes3 console to aid in the setup of `easy-aso`

- [x] Read Property (`read_property`)
- [x] Write Property (`write_property`)
- [x] Read Property Multiple (`read_property_multiple`)
- [x] Read Priority Array (`read_property` with `priority-array`)
- [x] Device Discovery (`who-is`)
- [x] Object Discovery (`who-has`)
- [x] Read All Points (`do_point_discovery`)
- [x] Router Discovery (`who_is_router_to_network`)


## Writeups
Why cant a BAS be free?

* https://www.linkedin.com/pulse/can-building-automation-free-ben-bartling-mtvwc/


## In Progress
- [x] Overhaul app code with bacpypes3
- [X] Test basic functionality with a fake BACnet app
- [ ] Create units for algorithms
- [ ] Publish the project as a Python library on PyPI
- [ ] Add support for BACnet Read Multiple
- [ ] Make tutorials for:
  - Electrical load shed example
  - BAS global variable sharing
  - AHU duct static pressure and temperature setpoint trim and respond (T&R)
  - AHU demand control ventilation based on G36 and ventilation calcs
  - VAV box system occupied-standy with occupancy integration to HVAC
  - Overnight building flush
  - Overnight BACnet override realease bot
  - Heat pump system cold weather staggered start for electrical power management
  - Electrical load shift

## Future
- [ ] Explore updating the fake BACnet app by integrating the [BOPTEST](https://ibpsa.github.io/project1-boptest/) project to simulate realistic physics, allowing for safe, non-production testing of easy-aso.


## Schematics: 

Easy-aso always operates behind the firewall and can operate with an IoT integration to the building systems.
![Schematic of Python script deployment](https://raw.githubusercontent.com/bbartling/easy-aso/develop/new_building.png)

Easy-aso can also operate just fine without an IoT integration to the building systems which would just be traditional operations (OT) technology systems that do not have access to the internet.
![Schematic of Python script deployment traditional](https://raw.githubusercontent.com/bbartling/easy-aso/develop/traditional_building.png)

## Getting Started with easy-aso
Follow the directions below to get the `easy-aso` project on your local linux machine. Until the project is available on PyPI, you can install it locally by following the steps below.

### Step 1: Clone the Repository
First, clone the `easy-aso` repository to your local machine:
```bash
git clone https://github.com/bbartling/easy-aso
```
### Step 2: Install the Package Locally
Navigate into the project directory and install it using `pip`. This will make the `easy-aso` package available in your Python environment.
```bash
cd easy-aso
pip install .
```

## Cybersecurity Disclaimer

Easy ASO is designed as an operations technology (OT) application with no built-in cloud connectivity but it is fully capable of anything programmed in Python. Any implementation of cloud connectivity for this app is the responsibility of the user. It is crucial to understand the cybersecurity implications of sending bi-directional signals to building systems.

**Security Best Practices**:
- Ensure the safety of your systems by following recommended cybersecurity best practices, including network, VPN, and VM access hardening, secure configurations, and routine security checks.
- Work closely with the IT team when enabling cloud connectivity to ensure it complies with your organization's security policies.
- Involve IT in all stages of the project and address any issues related to the implementation of easy-aso.
- Safeguard building control systems by utilizing access controls, encryption, and secure communication protocols to prevent unauthorized access.
- Act in the capacity of an ICS security specialist on behalf of your client, and promptly report any vulnerabilities or issues you discover.
- Develop an incident response plan to ensure the project is prepared for any potential security breaches, enabling swift and effective action from the incident response team should an issue arise during the implementation of easy-aso.

## License:
【MIT License】

Copyright 2024 Ben Bartling

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## Contributing:

PR, git issues, or discussions encouraged! Requirements are the app must be easy, configurable, and not complex.

By incorporating these changes, your README will provide a more comprehensive overview of the FreeBAS project and help users understand its purpose and how they can contribute or use it.

      
