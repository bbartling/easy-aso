"""EasyASO + BACnet read, then publish telemetry on MQTT.

Uses a **local BACnet stack** (this process participates on the wire). For
Docker edge deployments where **diy-bacnet-server** owns UDP 47808, prefer
JSON-RPC (``examples/diy_jsonrpc_example.py``) or ``easy_aso.runtime.RpcDockedEasyASO``
instead.

**Sibling container with diy-bacnet-server**

When both services share a Compose network and the same MQTT broker:

- diy-bacnet may expose **BACnet2MQTT** (under ``MQTT_BASE_TOPIC``) and/or **MQTT RPC
  gateway**. See diy-bacnet-server ``docs/mqtt.md``.
- Use a **different topic** for this agent (e.g. ``easyaso/telemetry/...``) so you
  do not collide with bridge or RPC topics.

**Environment** (aligned with diy-bacnet where possible)::

  MQTT_BROKER_URL or MQTT_BROKER   # optional scheme mqtt://host:1883
  MQTT_PORT
  MQTT_TOPIC
  MQTT_USER / MQTT_PASSWORD
  STEP_INTERVAL_SECONDS

Install::

  pip install aiomqtt

Run::

  python examples/mqtt_example.py --name EasyAso --instance 99999
"""

from __future__ import annotations

import asyncio
import os

import aiomqtt

from easy_aso import EasyASO

BACNET_DEVICE_ADDR = "11:21"
BACNET_OBJ_ID = "analog-input,1019"


def _mqtt_host_port() -> tuple[str, int]:
    raw = (os.environ.get("MQTT_BROKER_URL") or os.environ.get("MQTT_BROKER") or "").strip()
    default_port = int(os.environ.get("MQTT_PORT", "1883"))
    if not raw:
        return "test.mosquitto.org", default_port
    if raw.startswith("mqtt://"):
        raw = raw[6:]
    if "/" in raw:
        raw = raw.split("/")[0]
    if ":" in raw:
        host, _, port_s = raw.partition(":")
        try:
            return host, int(port_s)
        except ValueError:
            return host, default_port
    return raw, default_port


MQTT_TOPIC = os.environ.get("MQTT_TOPIC", "easyaso/telemetry/discharge_air_temp")
STEP_INTERVAL_SECONDS = float(os.environ.get("STEP_INTERVAL_SECONDS", "30"))


class CustomBot(EasyASO):
    def __init__(self, args=None):
        super().__init__(args)
        self._host, self._port = _mqtt_host_port()

    async def on_start(self):
        print(
            f"mqtt_example on_start broker={self._host}:{self._port} topic={MQTT_TOPIC}"
        )

    async def on_step(self):
        optimization_status = self.get_optimization_enabled_status()
        print(f"Optimization enabled: {optimization_status}")

        sensor_value_pv = await self.bacnet_read(BACNET_DEVICE_ADDR, BACNET_OBJ_ID)
        print(f"BACnet read: {sensor_value_pv}")

        user = os.environ.get("MQTT_USER", "").strip() or None
        password = os.environ.get("MQTT_PASSWORD", "").strip() or None
        client_kw: dict = {"hostname": self._host, "port": self._port}
        if user is not None:
            client_kw["username"] = user
        if password is not None:
            client_kw["password"] = password

        async with aiomqtt.Client(**client_kw) as client:
            await client.publish(
                MQTT_TOPIC,
                payload=f"Discharge Air Temp: {sensor_value_pv}",
            )
            print(f"Published to {MQTT_TOPIC}")

        await asyncio.sleep(STEP_INTERVAL_SECONDS)

    async def on_stop(self):
        print("mqtt_example on_stop")


async def main():
    bot = CustomBot()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
