# FreeBAS

FreeBAS is a free and open-source building automation system (BAS) server for HVAC controls interfacing.

## Goals:

- **Ease of Setup:** Easily deployable by organization IT departments within the building's local network, behind the firewall.
- **Interfacing with HVAC Controls:** Seamless integration with existing HVAC controls hardware via the BACnet protocol, supporting typical BACnet discovery processes for device and point discoveries.
- **Web-Based GUI:** Provide a web application with a user-friendly GUI for building operators to monitor HVAC system data.
  - **Schedule Equipment:** Implement a generic weekly calendar interface for scheduling equipment operations.
  - **Alarm Monitoring:** Display sensors in the HVAC system that are in an "alarm" condition. Potentially include efforts made by ASHRAE Guideline 36 for BAS alarm hierarchical suppression and alarm fault detection equations.
  - **User Management:** Implement typical login features with read/write access control.
  - **Bidirectional Interface:** Allow adjusting HVAC system setpoints via the GUI.
- **RESTful Interface:** Support a RESTful API for seamless integration with other systems or applications.
- **BACnet Interface:** Support a BACnet API for seamless integration with other systems or applications.
  - **Global Outside Air Temperature:** Provide access to a global shared value of the current outdoor air dry bulb.
  - **Global Occupancy:** Provide access to a global shared value representing occupancy schedule.
- **Data Storage:** Store short-term operational data of HVAC systems (e.g., one week) in a database.
- **Smart Building Integration:** Incorporate ontologies for smart building metadata efforts, enabling easy access to data by IoT devices using graph methods for long-term data storage and analysis.
  - **Demand Response Client:** Potentially incorporate a demand response client feature such as an Open-ADR Virtual End Node (VEN).

## Design Philosophy and Constraints:

The FreeBAS project adheres to a minimalistic approach to building automation, focusing on simplicity and reliability. The following principles guide the project's design:
- **Minimal Supervisory Logic:** The BAS is designed with minimal supervisory level logic, focusing on essential parameters such as outdoor air temperature and global occupancy for equipment scheduling. This ensures simplicity and ease of use.
- **Fail-Safe Mode:** Field level devices are equipped with fail-safe modes to operate independently in case of network failure or server downtime. This ensures uninterrupted operation of HVAC systems even under adverse conditions.
- **Compatibility:** The project aims for compatibility with field level devices capable of standalone operation based on basic inputs like outdoor air temperature and occupancy. For systems requiring extensive supervisory logic, consideration should be given to hardware replacement or contractors with the ability to support minimalistic operation.
- **Limitations:** FreeBAS may not be suitable for legacy BAS setups with proprietary equipment or poorly maintained HVAC systems. Additionally, organizations with inadequate IT practices may face challenges in implementing and maintaining the system effectively.

## Technologies Used:

- Back End Programming Languages: Python
- Frameworks/Libraries: [TODO]
- Database: [TODO]
- Web Framework: [AioHTTP or FastAPI?]

## Installation:

[TODO]

## License:
【MIT License】

Copyright 2024 Ben Bartling

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## Contributing:

PR, git issues, or discussions encouraged! Requirements are the app must be easy, configurable, and not complex.

By incorporating these changes, your README will provide a more comprehensive overview of the FreeBAS project and help users understand its purpose and how they can contribute or use it.

      
