from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Any, Dict, List

from asyncio_mqtt import Client as MQTTClient

from easy_aso.bacnet_client.remote_client import RemoteBacnetClient


def _env(name: str, default: str) -> str:
    v = os.environ.get(name)
    return v if v is not None and v != "" else default


async def main() -> None:
    gateway_url = _env("BACNET_GATEWAY_URL", "http://bacnet-gateway:8000")
    mqtt_host = _env("MQTT_HOST", "mqtt")
    mqtt_port = int(_env("MQTT_PORT", "1883"))
    topic = _env("MQTT_TOPIC", "easyaso/telemetry")

    address = _env("DEVICE_ADDRESS", "10.0.0.1")
    rpm_args_raw = os.environ.get("RPM_ARGS", "")
    rpm_args = rpm_args_raw.split() if rpm_args_raw else []

    step_s = float(_env("STEP_SECONDS", "5.0"))
    name = _env("AGENT_NAME", "mqtt_publisher")

    bac = RemoteBacnetClient(gateway_url)

    async with MQTTClient(mqtt_host, mqtt_port) as mqtt:
        try:
            while True:
                payload: Dict[str, Any] = {
                    "agent": name,
                    "ts": time.time(),
                    "device": address,
                }

                if rpm_args:
                    payload["rpm"] = await bac.rpm(address, *rpm_args)
                else:
                    # if no RPM args given, publish a minimal heartbeat
                    payload["rpm"] = []

                msg = json.dumps(payload, default=str)
                await mqtt.publish(topic, msg)
                print(f"[{name}] published {len(msg)} bytes to {topic}")

                await asyncio.sleep(step_s)
        finally:
            await bac.close()


if __name__ == "__main__":
    asyncio.run(main())
