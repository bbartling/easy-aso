from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Any, Dict

from asyncio_mqtt import Client as MQTTClient

from easy_aso.bacnet_client.factory import create_bacnet_client_from_env


def _env(name: str, default: str) -> str:
    v = os.environ.get(name)
    return v if v is not None and v != "" else default


async def main() -> None:
    mqtt_host = _env("MQTT_HOST", "mqtt")
    mqtt_port = int(_env("MQTT_PORT", "1883"))
    topic = _env("MQTT_TOPIC", "easyaso/telemetry")

    rpm_args_raw = os.environ.get("RPM_ARGS", "")
    rpm_args = rpm_args_raw.split() if rpm_args_raw else []

    step_s = float(_env("STEP_SECONDS", "5.0"))
    name = _env("AGENT_NAME", "mqtt_publisher")

    bac, address = create_bacnet_client_from_env()

    if hasattr(bac, "start"):
        await getattr(bac, "start")()

    async with MQTTClient(mqtt_host, mqtt_port) as mqtt:
        try:
            while True:
                payload: Dict[str, Any] = {
                    "agent": name,
                    "ts": time.time(),
                    "device": address,
                }

                payload["rpm"] = await bac.rpm(address, *rpm_args) if rpm_args else []

                msg = json.dumps(payload, default=str)
                await mqtt.publish(topic, msg)
                print(f"[{name}] published {len(msg)} bytes to {topic}")

                await asyncio.sleep(step_s)
        finally:
            if hasattr(bac, "close"):
                await getattr(bac, "close")()
            if hasattr(bac, "stop"):
                await getattr(bac, "stop")()


if __name__ == "__main__":
    asyncio.run(main())
