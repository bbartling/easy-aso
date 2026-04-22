# Examples

Scripts here are **educational** and often use **hard-coded BACnet addresses** — copy into your own package and adapt.

> ALSO be sure to check out this other project for more real-life advanced examples
> * https://github.com/bbartling/py-bacnet-stacks-playground

## Choose a pattern

| Pattern | Scripts / entry points | When to use |
|--------|-------------------------|-------------|
| **JSON-RPC to diy-bacnet-server** | `diy_jsonrpc_example.py` | Production-style edge: one container owns UDP `47808`, agents use HTTP JSON-RPC. |
| **RPC-docked `EasyASO` lifecycle** | `easy_aso.runtime` + `easy-aso-agent run` | Same as JSON-RPC, but full `on_start` / `on_step` / `on_stop` in a sidecar (see library docs). |
| **Local BACnet (bacpypes3)** | `make_read_request.py`, `make_write_request.py`, `make_rpm.py`, `mqtt_example.py` | Lab or gateway that runs a BACnet stack **in this process**. |
| **MQTT telemetry** | `mqtt_example.py` | After a BACnet read, publish to a broker. Use a **topic prefix** that does not collide with diy-bacnet’s BACnet2MQTT or MQTT-RPC topics if both share a broker. |
| **Domain demos** | `bas_supervisory.py`, `load_shed.py` | Larger sketches; replace IPs and objects for your site. |

## diy-bacnet-server + MQTT (sibling containers)

- **diy-bacnet** optional MQTT: BACnet2MQTT bridge (`MQTT_BASE_TOPIC`, …) and MQTT RPC gateway — see [diy-bacnet-server MQTT docs](https://github.com/bbartling/diy-bacnet-server) (`docs/mqtt.md` in that repo).
- **This repo’s** `mqtt_example.py` defaults to a separate topic (`easyaso/telemetry/...`) so an easy-aso agent can live on the **same broker** without stealing bridge/RPC topic names.

Environment variables `MQTT_BROKER_URL` / `MQTT_BROKER` are recognized so one `.env` can align with diy-bacnet-style settings.

## Quick commands

**JSON-RPC client (no local BACnet UDP):**

```bash
pip install -e ".[platform]"
set BACNET_BACKEND=diy_jsonrpc
set DIY_BACNET_URL=http://127.0.0.1:8080
set DEVICE_INSTANCE=123456
python examples/diy_jsonrpc_example.py
```

**Classic read loop (local BACnet server in app):**

```bash
python examples/make_read_request.py --name EasyAso --instance 99999
```

**Minimal skeleton:**

```bash
python examples/blank.py --name EasyAso --instance 99999
```

**Read + MQTT publish:**

```bash
pip install aiomqtt
set MQTT_BROKER_URL=mqtt://mosquitto:1883
set MQTT_TOPIC=easyaso/telemetry/my_sensor
python examples/mqtt_example.py --name EasyAso --instance 99999
```

## Removed / consolidated (changelog)

- **`fastapi_example.py`** — removed (was an empty deprecation notice; use supervisor + diy-bacnet JSON-RPC).
- **`diy_jsonrpc_quickstart.py`** — merged into **`diy_jsonrpc_example.py`** (one script, env-driven optional RPM/write).
