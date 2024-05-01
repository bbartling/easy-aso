# FreeBAS

**Warbubg this is an UNFINISHED CONCEPT IDEA...** But feel free to nudge me...

FreeBAS stands as an innovative, free, and open-source Building Automation System (BAS) server, designed by a former BAS technician for HVAC control applications. This app is designed to run behind the firewall on the intranet (not cloud) of a larger commercial type building which is typical to any Operations Technology (OT). The core mission is to empower the industry by enabling the cost-free setup of buildings with essential BAS functionalities including advanced alarming, supervisory level logic, and easily discoverable BACnet server properties. Other functionalities which are typical to a BAS server include global variables for the operation of the mechanical system like building occupancy and outdoor air temperature, all managed with the elegance and power of Python.

A key ambition of FreeBAS is to embrace the advanced ontologies of the Brick schema, showcasing a forward-thinking approach to how data is populated and retrieved from the BACnet system. Hopefully this strategic integration using meta data in the BAS heralds a new era of intuitive, efficient, and scalable building management system architecture.

At the heart of FreeBAS's design philosophy lies a steadfast commitment to accessibility, innovation, and the rejection of traditional, proprietary widget dashboards for logic setup. By leveraging modern computer science patterns (Python scripting to setup logic), FreeBAS aims to address the pressing needs of the BAS industry for open and adaptable solutions. With high hopes as a community-driven tool, FreeBAS not only elevates building automation practices but also positions itself to force technological advancements in an industry that seems stuck. 

## Screenshot
![Alt text](/screenshot.jpg)

## Technologies Used:

- Back End Programming Languages: Python
- Frameworks/Libraries: bacpypes3 fastapi
- Database: [TODO]
- Web Framework: fastapi

## Installation:

1. On Linux clone the repo and cd into it.
2. Create the Virtual Environment: `$ python -m venv venv`
3. Activate the Virtual Environment: `$ source venv/bin/activate`
4. Install Python packages: `$ pip bacpypes3 fastapi itsdangerous uvicorn jinja2 python-multipart ifaddr`
5. Run the bash script to generate certs `$ ./scripts/generate_certs.sh` where then you can step through the cert making processes as shown below. This app serves the certs directly and they are self signed so you can fill the info or leave default as shown below. Some IT deptartments may prefer having the information filled in depending on the organizations cyber security policies.

```bash
Country Name (2 letter code) [AU]:
State or Province Name (full name) [Some-State]:
Locality Name (eg, city) []:
Organization Name (eg, company) [Internet Widgits Pty Ltd]:
Organizational Unit Name (eg, section) []:
Common Name (e.g. server FQDN or YOUR name) []:
Email Address []:
```

6. Run and test web app `$ python -m app.main --tls`

## License:
【MIT License】

Copyright 2024 Ben Bartling

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## Contributing:

PR, git issues, or discussions encouraged! Requirements are the app must be easy, configurable, and not complex.

By incorporating these changes, your README will provide a more comprehensive overview of the FreeBAS project and help users understand its purpose and how they can contribute or use it.

      
