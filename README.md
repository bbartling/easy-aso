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
- [ ] Test basic functionality on a test bench scenario with another fake BACnet app to simulate a fake AHU system and VAVs
- [ ] Create unit tests for generic supervisory processes in BAS contracting, such as OA-Temp share and Occupancy Scheduling
- [ ] Publish the project as a Python library on PyPI
- [ ] Add support for BACnet Read Multiple
- [ ] Make tutorials for:
  - Electrical load shed example
  - BAS global variable sharing
  - AHU Trim and Respond
  - Overnight building flush

## Schematic: Python Script Deployment Behind the Firewall

![Schematic of Python script deployment](https://raw.githubusercontent.com/bbartling/easy-aso/develop/new_building.png)

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
See examples directory for how to run files with Python.
* **TODO** - make tutorial for the fake BACnet device that runs on a rasp pi and running example scripts.

## Cybersecurity Disclaimer

Easy ASO is designed as an operations technology (OT) application with no built-in cloud connectivity but it is fully capable of anything programmed in Python. Any implementation of cloud connectivity for this app is the responsibility of the user. It is crucial to understand the cybersecurity implications of sending bi-directional signals to building systems.

**Security Best Practices**:
- Adhere to the highest cybersecurity standards, including network hardening, secure configurations, and regular security audits.
- Involve your organization's IT department when implementing cloud connectivity to ensure compliance with security policies.
- Implement access controls, encryption, and secure communication protocols to protect building systems from unauthorized access or cyberattacks.

**Responsibility**:
The creator of this app and its affiliates take no responsibility for damage to equipment, property, or people resulting from inadequate cybersecurity practices. The provided examples do not include cloud connectivity to minimize risk. Implementing cloud connectivity is at the user's discretion and should be done with the utmost care and adherence to industry security standards.

**Important Note**:
For any scenarios involving cloud-based control of building systems, it is highly recommended to work closely with cybersecurity professionals to secure all communication channels and minimize potential risks.


## License:
【MIT License】

Copyright 2024 Ben Bartling

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## Contributing:

PR, git issues, or discussions encouraged! Requirements are the app must be easy, configurable, and not complex.

By incorporating these changes, your README will provide a more comprehensive overview of the FreeBAS project and help users understand its purpose and how they can contribute or use it.

      
