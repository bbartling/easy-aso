from __future__ import annotations

import asyncio
import os

from easy_aso.bacnet_client.remote_client import RemoteBacnetClient


def _env(name: str, default: str) -> str:
    v = os.environ.get(name)
    return v if v is not None and v != "" else default


async def main() -> None:
    """Placeholder HVAC optimization agent.

    This is a template to show how an algorithm agent can be deployed as a container
    that talks to the shared BACnet gateway.
    """

    gateway_url = _env("BACNET_GATEWAY_URL", "http://bacnet-gateway:8000")
    address = _env("DEVICE_ADDRESS", "10.0.0.1")
    rpm_args_raw = os.environ.get("RPM_ARGS", "")
    rpm_args = rpm_args_raw.split() if rpm_args_raw else []
    step_s = float(_env("STEP_SECONDS", "10.0"))
    name = _env("AGENT_NAME", "hvac_agent")

    client = RemoteBacnetClient(gateway_url)
    try:
        while True:
            if rpm_args:
                results = await client.rpm(address, *rpm_args)
                print(f"[{name}] RPM len={len(results)}")
            else:
                print(f"[{name}] running; set RPM_ARGS to do real reads")
            await asyncio.sleep(step_s)
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
