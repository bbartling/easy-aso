# Easy ASO

Easy ASO is a lightweight, Python-based orchestration layer that acts as the easy button for Automated Supervisory Optimization (ASO) in BACnet-powered HVAC systems.
Built on top of an asyncio-first architecture, it provides a clean and modern control loop for energy optimization strategies while handling all BACnet/IP communication in the background.

Whether used as a standalone service, embedded inside an EMIS pipeline, or integrated into a larger IoT/microservice framework, Easy ASO simplifies the complex task of supervisory control. Its design supports BACnet out of the box and can be extended to additional building automation protocols as your platform evolves.


## The Skeleton of ASO
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


<details>
<summary>Preproject Exploring Remote BACnet Sites</summary>

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

</details>


<details>
<summary>Getting Setup and Running Tests</summary>


Make sure you run system updates in Linux and install Docker and Docker Compose before proceeding.

### Step 1: Clone the Repository
First, (I'm on Windows) clone the `easy-aso` repository to your local machine:
```bash
git clone https://github.com/bbartling/easy-aso
```

### Step 2: From a fresh WSL session
Run these bash commands from project root directory after cloning. Make sure docker-compose alias works:
```bash
echo "alias docker-compose='docker compose'" >> ~/.bashrc
source ~/.bashrc

docker-compose version
```

Setup Python Environment:
```bash
python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -e ".[test]"
pytest

```

You should notice in console when tests are completed.

```text
collected 5 items

tests/test_abc.py ....            [ 80%]
tests/test_bacnet.py .            [100%]

```

The test suite verifies two major behaviors in the system. The first set of tests ensures the `EasyASO` abstract base class behaves correctly by enforcing the required method contract for any ASO application. These tests confirm that subclasses must fully implement `on_start`, `on_step`, and `on_stop`, that argument parsing for flags such as `--no-bacnet-server` works correctly, and that improper subclasses raise errors when abstract methods are missing. Together these checks guarantee a stable API boundary before any BACnet communication logic is ever exercised.

The second test validates full BACnet communication between two simulated devices running inside Docker containers: a fake BACnet device and a fake `easy-aso` instance. Over roughly fifteen seconds of runtime, the test confirms the client can read, write, and release BACnet points across the bridge network defined in the Compose file, including alternating present-value writes, null-priority releases, and the end-to-end kill-switch logic based on optimization status. After execution, container logs are inspected to assert that no Python errors occurred, that optimization toggled True/False as expected, and that all overrides were successfully released during shutdown. This test ensures the complete lifecycle of read, write, override release, and kill-switch behavior works correctly in a realistic BACnet/IP environment.

</details>


<details>
<summary>Examples and Best Practices</summary>

This project is designed so that you can start with simple ASO “bots” and grow
into more capable HVAC optimization services without rewriting the core
plumbing. The pattern is straightforward: keep `main.py` clean and declarative,
and put all optimization logic into dedicated `algorithm.py` modules. Each
example follows the same layout:

```text
algorithm.py   # ASO logic (reads, writes, decisions)
main.py        # orchestration only (wires things together)
```

### Building off the BACnet ping-pong example

The `bacnet_ping_pong` example shows a single algorithm reading a BACnet sensor
point and writing to a command point (e.g., AV2) at a defined priority. In real
HVAC applications this pattern can evolve into meaningful strategies:

- Treat AV1 as a sensor (supply temperature, zone temp, or measured kW)
- Treat AV2 as a command (fan speed, valve position, discharge temperature)
- Use the built-in EasyASO optimization flag (`optimization_enabled_bv`) as the
  enable/disable **kill switch**, accessible via the local method
  `get_optimization_enabled_status()`
- Add incremental control logic in `algorithm.py` (reset curves, demand limits,
  deadband logic)

The example below shows how the built-in kill switch is checked before running
any optimization logic. This kill switch is not a network request; it is a
local boolean stored in the EasyASO app and also exposed as
`binaryValue,1` to the BAS.

```python
import asyncio
import random

from easy_aso import EasyASO

BACNET_DEVICE = "bacnet-server"
AV1 = "analog-value,1"
AV2 = "analog-value,2"

WRITE_PRIORITY = 10
INTERVAL = 5.0  # seconds between steps


class BacnetPingPongAso(EasyASO):
    """
    Demonstrates a basic BACnet-read/write ASO controller using EasyASO.

    Flow:
      - Honor the built-in optimization kill switch (optimization_enabled_bv)
      - Read present-value of AV1
      - Write to AV2 at the configured priority
      - Release overrides safely on stop
    """

    async def on_start(self):
        print("[BacnetPingPongAso] on_start: starting BACnet ping-pong controller")

    async def on_step(self):
        # Local optimization enable flag (built-in BV1 exposed to the BAS)
        optimization_enabled = self.get_optimization_enabled_status()
        if not optimization_enabled:
            print("[BacnetPingPongAso] Optimization disabled (kill switch).")
            await self.release_all()
            await asyncio.sleep(INTERVAL)
            return

        print("[BacnetPingPongAso] on_step: polling BACnet points")

        av1_val = await self.bacnet_read(BACNET_DEVICE, AV1)
        av2_prev = await self.bacnet_read(BACNET_DEVICE, AV2)

        print(f"  AV1 pv: {av1_val}")
        print(f"  AV2 pv before write: {av2_prev}")

        new_val = random.uniform(0.0, 100.0)
        print(f"  Writing {new_val:.2f} → AV2 @ priority {WRITE_PRIORITY}")

        await self.bacnet_write(BACNET_DEVICE, AV2, new_val, WRITE_PRIORITY)
        await asyncio.sleep(INTERVAL)

    async def on_stop(self):
        print("[BacnetPingPongAso] on_stop: releasing all overrides…")
        await self.release_all()
        print("[BacnetPingPongAso] on_stop: shutdown complete")
```

And a simple `main.py` orchestrates it:

```python
import asyncio
from .algorithm import BacnetPingPongAso

async def main():
    bot = BacnetPingPongAso()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())
```

Run the example:

```bash
python main.py
```

### Multiple algorithms and telemetry from a single main.py

You can run multiple ASO algorithms at once. A common pattern is to keep each
strategy in its own module (such as a supply-air reset, demand-limit module,
and a ping-pong diagnostic task) and wire them together in one `main.py` using
`asyncio.gather`. Telemetry publishers (MQTT, HTTP, file logs) can be included
the same way.

```python
# main.py

import asyncio

from .supply_air_reset.algorithm import SupplyAirResetAso
from .demand_limit.algorithm import DemandLimitAso
from .bacnet_ping_pong.algorithm import BacnetPingPongAso
from .telemetry.mqtt_publisher import MqttTelemetry

async def main():
    supply_reset_bot = SupplyAirResetAso()
    demand_limit_bot = DemandLimitAso()
    ping_pong_bot = BacnetPingPongAso()

    telemetry_task = MqttTelemetry(
        topic_prefix="building/easy-aso",
        interval_seconds=10.0,
    )

    await asyncio.gather(
        supply_reset_bot.run(),
        demand_limit_bot.run(),
        ping_pong_bot.run(),
        telemetry_task.run(),
    )

if __name__ == "__main__":
    asyncio.run(main())
```

This structure keeps each algorithm independent while allowing a single process
to coordinate several optimization routines and telemetry publishers. It also
makes it simple to move algorithms into separate containers or supervisors
without modifying the optimization code. Everything runs under asyncio,
including the underlying BACnet stack, so the same design can be extended into
a FastAPI service for edge deployments.

</details>

<details>
<summary>Dockerized "VOLTTRON-like" Agent Deployment (Modernized)</summary>

This repo now includes a **singleton BACnet gateway** container (owns UDP/47808) plus multiple **algorithm agents** that behave like VOLTTRON agents (start/stop/restart) but run as independent containers.

### Why a Gateway?
BACnet/IP uses a single well-known UDP port (47808). Instead of letting every agent fight over that socket, we run **one** container that owns the BACnet stack and expose a small async HTTP API for agents.

### Quick Start (Linux/Raspberry Pi)
1) Set env vars for your host BACnet interface:

```bash
export BACNET_ARGS="--name Gateway --instance 123 --address 10.200.200.10/24"
export DEVICE_ADDRESS="10.200.200.233"
export BOOL_POINT="binaryValue,1"
# Optional: prove RPM too
export RPM_ARGS="analogValue,1 present-value units binaryValue,1 present-value"
```

2) Bring the platform up:

```bash
./bin/easyasoctl up
```

3) Start/stop like VOLTTRON:

```bash
./bin/easyasoctl status
./bin/easyasoctl restart dueler_a
./bin/easyasoctl stop hvac_agent
./bin/easyasoctl logs bacnet-gateway dueler_a
```

### Services
- **bacnet-gateway**: FastAPI + bacpypes3. Endpoints: `/health`, `/read`, `/write`, `/rpm`.
- **dueler_a / dueler_b**: test bench agents that continuously:
  1) optionally RPM,
  2) read a boolean point,
  3) write the opposite,
  4) release with Null (priority 8 by default).
- **mqtt**: Eclipse Mosquitto broker.
- **mqtt_publisher**: publishes gateway RPM results to MQTT.
- **hvac_agent**: a minimal placeholder showing where your real ASO logic would live.

> Note: The provided `docker-compose.yml` uses `network_mode: host` because it is the most reliable way to talk BACnet/IP on a LAN from containers.

</details>

---

## 📜 License

Everything here is **MIT Licensed** — free, open source, and made for the BAS community.  
Use it, remix it, or improve it — just share it forward so others can benefit too. 🥰🌍


【MIT License】

Copyright 2026 Ben Bartling

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.