"""Quickstart: talk to diy-bacnet-server JSON-RPC from easy-aso.

Run diy-bacnet-server first (port 8080). Then:

  pip install -e .[platform]
  export BACNET_BACKEND=diy_jsonrpc
  export DIY_BACNET_URL=http://127.0.0.1:8080
  export DEVICE_INSTANCE=123456

  python examples/diy_jsonrpc_quickstart.py

Set RPM_ARGS to do a real RPM read:
  export RPM_ARGS="analogValue,1 present-value units"
"""

import asyncio
import os

from easy_aso.bacnet_client.factory import make_bacnet_client_from_env


async def main() -> None:
    bac, target = make_bacnet_client_from_env()

    # default: just prove the client can call the server
    obj = os.environ.get("TEST_OBJECT", "binaryValue,1")

    try:
        v = await bac.read(target, obj, "present-value")
        print(f"READ {target} {obj} -> {v}")

        # If you want to test a write/release, use a commandable point.
        # (In diy-bacnet-server CSV, set Commandable,Y)
        if os.environ.get("DO_WRITE") == "1":
            await bac.write(target, obj, "active", priority=8)
            print("WRITE active @P8")
            await bac.write(target, obj, "null", priority=8)
            print("RELEASE @P8")

        rpm_args_raw = os.environ.get("RPM_ARGS", "")
        if rpm_args_raw:
            rpm_args = rpm_args_raw.split()
            results = await bac.rpm(target, *rpm_args)
            print(f"RPM len={len(results)}")

    finally:
        close = getattr(bac, "close", None)
        if callable(close):
            await close()


if __name__ == "__main__":
    asyncio.run(main())
