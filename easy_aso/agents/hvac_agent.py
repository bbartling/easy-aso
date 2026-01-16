from __future__ import annotations

import asyncio
import os

from easy_aso.bacnet_client.factory import create_bacnet_client_from_env


def _env(name: str, default: str) -> str:
    v = os.environ.get(name)
    return v if v is not None and v != "" else default


async def main() -> None:
    """Placeholder HVAC optimization agent.

    This agent demonstrates the *containerized architecture*:

      - One "BACnet core" container owns UDP/47808.
      - Agents like this one talk to it over TCP (HTTP/JSON-RPC).

    Select backend with:
      BACNET_BACKEND=easy_gateway | diy_jsonrpc | bacpypes_direct

    Address input depends on backend:
      - easy_gateway / bacpypes_direct: DEVICE_ADDRESS (e.g. 10.200.200.233)
      - diy_jsonrpc: DEVICE_INSTANCE (e.g. 3456789)
    """

    rpm_args_raw = os.environ.get("RPM_ARGS", "")
    rpm_args = rpm_args_raw.split() if rpm_args_raw else []
    step_s = float(_env("STEP_SECONDS", "10.0"))
    name = _env("AGENT_NAME", "hvac_agent")

    client, address = create_bacnet_client_from_env()

    # bacpypes_direct requires explicit start()
    if hasattr(client, "start"):
        await getattr(client, "start")()

    try:
        while True:
            if rpm_args:
                results = await client.rpm(address, *rpm_args)
                print(f"[{name}] RPM len={len(results)}")
            else:
                print(f"[{name}] running; set RPM_ARGS to do real reads")
            await asyncio.sleep(step_s)
    finally:
        if hasattr(client, "close"):
            await getattr(client, "close")()
        if hasattr(client, "stop"):
            await getattr(client, "stop")()


if __name__ == "__main__":
    asyncio.run(main())
