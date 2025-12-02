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

This project is designed so that you can start with very simple ASO “bots” and
grow into more complex HVAC optimization services without rewriting the core
plumbing. The key pattern is: **keep `main.py` clean and declarative**, and put
all of your optimization logic into dedicated `algorithm.py` modules. Each
example follows the same structure:

```text
algorithm.py   # ASO logic (reads, writes, decisions)
main.py        # orchestration only (wires things together)
```

### Building off the BACnet ping-pong example

The `bacnet_ping_pong` example shows a single algorithm reading a few BACnet
points and writing to a command point (e.g., AV2) at a defined priority. In a
real HVAC context this “ping-pong” pattern can evolve into more realistic
strategies:

* Treat AV1 as a sensor (e.g., supply air temperature, zone temperature, or kW)
* Treat AV2 as a command (e.g., fan speed, valve position, discharge temp setpoint)
* Use BV1 as a mode flag or optimization enable/disable “kill switch”
* Add simple control logic in `algorithm.py` (e.g., reset curves, demand caps,
  or “if temp > setpoint + deadband, increase command by X%”)

The point is that `algorithm.py` as shown below can grow from “print some values” into a real
HVAC ASO loop without touching the core EasyASO lifecycle or the test harness.


```python
import asyncio
import random

from easy_aso import EasyASO

BACNET_DEVICE = "bacnet-server"
AV1 = "analog-value,1"
AV2 = "analog-value,2"
BV1 = "binary-value,1"

WRITE_PRIORITY = 10
INTERVAL = 5.0  # seconds between steps


class BacnetPingPongAso(EasyASO):
    """
    Demonstrates a basic BACnet-read/write ASO controller using EasyASO.

    Flow:
      - Read present-value of AV1 and BV1
      - Write a random number to AV2 at the configured priority
      - Release overrides safely on stop
    """

    async def on_start(self):
        print("[BacnetPingPongAso] on_start: starting BACnet ping-pong controller")

    async def on_step(self):
        print("[BacnetPingPongAso] on_step: polling BACnet points")

        av1_val = await self.bacnet_read(BACNET_DEVICE, AV1)
        bv1_val = await self.bacnet_read(BACNET_DEVICE, BV1)
        av2_prev = await self.bacnet_read(BACNET_DEVICE, AV2)

        print(f"  AV1 pv: {av1_val}")
        print(f"  BV1 pv: {bv1_val}")
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


And then a `main.py` acts as the orchestrator to wire everything together.  

```python

import asyncio

from .algorithm import BacnetPingPongAso


async def main():
    bot = BacnetPingPongAso()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
```

Run command:

```bash
python main.py
```


### Multiple algorithms and telemetry from a single main.py

You are not limited to a single algorithm. A common best practice is to keep
each control strategy in its own class and module (e.g., `SupplyAirResetAso`,
`DemandLimitAso`, `PingPongAso`), and then have a single `main.py` that runs
several of them in parallel along with telemetry publishers (MQTT, HTTP, file
logger, etc.) using `asyncio.gather`.

Conceptually, a `main.py` might look like this:

```python
# examples/multi_algo_orchestrator/main.py

import asyncio

from .supply_air_reset.algorithm import SupplyAirResetAso
from .demand_limit.algorithm import DemandLimitAso
from .bacnet_ping_pong.algorithm import BacnetPingPongAso
from .telemetry.mqtt_publisher import MqttTelemetry  # your own helper

async def main():
    # Instantiate independent ASO “bots”
    supply_reset_bot = SupplyAirResetAso()
    demand_limit_bot = DemandLimitAso()
    ping_pong_bot = BacnetPingPongAso()

    # Separate task for telemetry / MQTT publishing
    telemetry_task = MqttTelemetry(
        topic_prefix="building/easy-aso",
        interval_seconds=10.0,
    )

    # Run all of them concurrently
    await asyncio.gather(
        supply_reset_bot.run(),
        demand_limit_bot.run(),
        ping_pong_bot.run(),
        telemetry_task.run(),
    )

if __name__ == "__main__":
    asyncio.run(main())
```

In this pattern:

* Each ASO algorithm stays focused on **one job** (e.g., AHU reset, demand
  limiting, simple ping-pong test).
* Telemetry (MQTT, Influx, HTTP, file logging) lives in its **own component**
  that can be reused across bots.
* `main.py` reads almost like a wiring diagram: **instantiate bots, start them,
  and let EasyASO handle the lifecycle**.

This makes it easy to add or remove algorithms, split them across multiple containers, or place them under different process managers—without changing the core optimization logic. Everything is fully asynchronous end-to-end, using `asyncio` in both Easy ASO and the underlying BACnet stack (bacpypes3). The architecture can also be ported into a web framework such as FastAPI if you want to expose ASO services or telemetry in an edge environment.

</details>


---

## 📜 License

Everything here is **MIT Licensed** — free, open source, and made for the BAS community.  
Use it, remix it, or improve it — just share it forward so others can benefit too. 🥰🌍


【MIT License】

Copyright 2025 Ben Bartling

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
