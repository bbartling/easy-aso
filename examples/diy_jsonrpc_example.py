"""DIY BACnet Server JSON-RPC example.

This script shows how easy-aso can talk to diy-bacnet-server as an external
BACnet "core" microservice.

Run diy-bacnet-server first (from this repo's docker-compose, or standalone):

  docker compose up -d --build bacnet-core

Then run this (in another terminal):

  export DIY_BACNET_URL=http://127.0.0.1:8080
  export DEVICE_INSTANCE=123456
  python examples/diy_jsonrpc_example.py

NOTE: `DEVICE_INSTANCE` must be the BACnet device instance on your network.
"""

import asyncio
import os

from easy_aso.bacnet_client.factory import create_bacnet_client_from_env


async def main() -> None:
    os.environ.setdefault("BACNET_BACKEND", "diy_jsonrpc")

    client, device_instance = create_bacnet_client_from_env()

    # Example: read AI1 present-value
    value = await client.read(device_instance, "analogInput,1", "present-value")
    print("present-value:", value)

    # Example: RPM for AI1 present-value + units
    results = await client.rpm(
        device_instance,
        "analogInput,1",
        "present-value",
        "analogInput,1",
        "units",
    )
    print("RPM results:", results)

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
