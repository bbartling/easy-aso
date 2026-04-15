"""Talk to diy-bacnet-server over JSON-RPC (recommended edge pattern).

diy-bacnet-server owns BACnet/IP (UDP 47808); this script uses the same HTTP JSON-RPC
surface as the supervisor (``JsonRpcBacnetClient``).

**Run diy-bacnet-server first** (e.g. port 8080). Then::

  pip install -e .[platform]

  set BACNET_BACKEND=diy_jsonrpc
  set DIY_BACNET_URL=http://127.0.0.1:8080
  set DEVICE_INSTANCE=123456

  python examples/diy_jsonrpc_example.py

Optional (same script)::

  set TEST_OBJECT=binaryValue,1
  set DO_WRITE=1
  set RPM_ARGS=analogValue,1 present-value analogValue,1 units
  set RUN_DEFAULT_RPM_DEMO=1

``DEVICE_INSTANCE`` must match the BACnet device instance your diy-bacnet stack uses
for JSON-RPC client calls (see diy-bacnet-server docs).

See also: ``easy_aso.runtime`` for RPC-docked ``EasyASO`` subclass agents (multi-container).
"""

from __future__ import annotations

import asyncio
import os

from easy_aso.bacnet_client.factory import create_bacnet_client_from_env

make_bacnet_client_from_env = create_bacnet_client_from_env


async def main() -> None:
    os.environ.setdefault("BACNET_BACKEND", "diy_jsonrpc")

    client, device_instance = create_bacnet_client_from_env()

    try:
        obj = os.environ.get("TEST_OBJECT", "analogInput,1")

        v = await client.read(device_instance, obj, "present-value")
        print(f"READ {device_instance} {obj} -> {v}")

        if os.environ.get("DO_WRITE") == "1":
            await client.write(device_instance, obj, "active", priority=8)
            print("WRITE active @P8")
            await client.write(device_instance, obj, "null", priority=8)
            print("RELEASE @P8")

        rpm_args_raw = os.environ.get("RPM_ARGS", "")
        if rpm_args_raw.strip():
            rpm_args = rpm_args_raw.split()
            results = await client.rpm(device_instance, *rpm_args)
            print(f"RPM len={len(results)}", results)
        elif os.environ.get("RUN_DEFAULT_RPM_DEMO") == "1":
            results = await client.rpm(
                device_instance,
                "analogInput,1",
                "present-value",
                "analogInput,1",
                "units",
            )
            print("RPM results:", results)

    finally:
        close = getattr(client, "close", None)
        if callable(close):
            await close()


if __name__ == "__main__":
    asyncio.run(main())
