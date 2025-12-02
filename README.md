# easy‑aso

This project provides a lightweight, asynchronous framework for **Automated
Supervisory Optimization (ASO)** of BACnet building automation systems.
The original monolithic codebase has been refactored into an agent‑based
architecture inspired by PNNL’s VOLTTRON IoT platform.  Agents
encapsulate control logic, run concurrently using `asyncio`, and talk
to BACnet devices through a pluggable client interface.  Guideline 36
(GL36) “Trim & Respond” logic and other optimization sequences can be
implemented as reusable functions or packaged into agents.

## Project structure

- **`easy_aso/agent.py`** – defines the `Agent` base class and
  `AgentManager` used to schedule multiple agents concurrently.
- **`easy_aso/bacnet_client.py`** – contains a minimal `BACnetClient`
  interface and an `InMemoryBACnetClient` stub for testing without
  network access.
- **`easy_aso/gl36/trim_respond.py`** – implements stateless functions
  for calculating GL36 zone requests and trim/respond setpoint resets
  along with a `GL36TrimRespondAgent` that ties them together.
- **`tests/`** – contains unit tests for the agent lifecycle and GL36
  functions.  Legacy integration tests have been stubbed out and
  skipped.

The repository intentionally omits the previous example scripts and
Docker‑based BACnet simulations to focus on the core library.  A
packaged distribution can be created using the provided `setup.py`.

## Installation

The library requires Python 3.8 or newer.  To install the package
locally for development, first create and activate a virtual
environment (optional but recommended):

```sh
python3 -m venv venv
source venv/bin/activate
```

Then install the package and its dependencies.  Because the
``setup.py`` file lives in the same directory as this README, you
should run the installation from the project root (the extracted
folder) rather than referencing a nested path.  Use editable mode
(``-e .``) so that changes you make to the source files are
immediately reflected without reinstalling:

```sh
pip install --upgrade pip

# Install BACnet dependencies (optional)
pip install bacpypes3 ifaddr

# Install the easy‑aso package in editable (development) mode
pip install -e .
```

Installing in editable mode tells pip to create a link to your working
directory instead of copying files into ``site‑packages``.  When you
no longer need the local install, run ``pip uninstall easy-aso`` to
remove it.  Note that the ``bacpypes3`` dependency is only necessary
if you plan to connect to real BACnet devices; the unit tests and
example FastAPI app use the in‑memory client and will run without it.

## Running the tests

The test suite uses Python’s built‑in `unittest` module and does not
depend on any external services.  From the project root (the directory
containing ``setup.py``), run:

```sh
python -m unittest discover -v
```

You should see output indicating that the agent lifecycle and GL36
functions are tested and that legacy tests are skipped.  There is
no need to install or run Docker for these tests.

## Developing custom agents

To implement your own control logic, subclass `easy_aso.agent.Agent`
and override the asynchronous lifecycle hooks:

```python
from easy_aso.agent import Agent

class MyController(Agent):
    async def on_start(self) -> None:
        # initialization logic
        pass

    async def on_update(self) -> None:
        # periodic control logic
        pass

    async def on_stop(self) -> None:
        # cleanup logic
        pass

# Run the agent
import asyncio
from easy_aso.agent import AgentManager

async def main() -> None:
    agent = MyController(update_interval=60.0)
    manager = AgentManager([agent])
    await manager.start_all()
    try:
        await asyncio.Event().wait()  # run forever
    except KeyboardInterrupt:
        await manager.stop_all()

asyncio.run(main())
```

For GL36 trim/respond applications, use the helper functions in
`easy_aso.gl36.trim_respond` or the `GL36TrimRespondAgent` class as
a starting point.  Because the algorithm functions are stateless,
they can also be deployed as serverless functions (e.g. AWS Lambda)
and reused across multiple AHUs or VAV boxes.

## Contributing

Contributions are welcome!  Please open issues or submit pull
requests to discuss new features, improvements or bug fixes.  When
adding new functionality, ensure it includes appropriate unit tests
and documentation.


## 📜 License

Everything here is **MIT Licensed** — free, open source, and made for the BAS community.  
Use it, remix it, or improve it — just share it forward so others can benefit too. 🥰🌍


【MIT License】

Copyright 2025 Ben Bartling

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.