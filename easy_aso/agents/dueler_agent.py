from __future__ import annotations

import asyncio
import os
import random

from easy_aso.bacnet_client.factory import create_bacnet_client_from_env


def _env(name: str, default: str) -> str:
    v = os.environ.get(name)
    return v if v is not None and v != "" else default


async def main() -> None:
    bool_point = _env("BOOL_POINT", "binaryValue,1")

    # Example RPM args: "analogValue,1 present-value units analogValue,2 present-value"
    rpm_args_raw = os.environ.get("RPM_ARGS", "")
    rpm_args = rpm_args_raw.split() if rpm_args_raw else []

    priority = int(_env("WRITE_PRIORITY", "8"))
    hold_s = float(_env("HOLD_SECONDS", "2.0"))
    step_s = float(_env("STEP_SECONDS", "5.0"))
    jitter_s = float(_env("JITTER_SECONDS", "0.5"))

    name = _env("AGENT_NAME", "dueler")

    client, address = create_bacnet_client_from_env()

    if hasattr(client, "start"):
        await getattr(client, "start")()

    try:
        await asyncio.sleep(random.random() * max(jitter_s, 0.0))

        while True:
            if rpm_args:
                results = await client.rpm(address, *rpm_args)
                print(f"[{name}] RPM results (len={len(results)}): {results[:3]}")

            cur = await client.read(address, bool_point, "present-value")
            print(f"[{name}] Read {address} {bool_point} -> {cur}")

            if isinstance(cur, str):
                cur_norm = cur.strip().lower()
                next_val = "inactive" if cur_norm == "active" else "active"
            else:
                next_val = 0 if bool(cur) else 1

            print(f"[{name}] Write {address} {bool_point} = {next_val} @P{priority}")
            await client.write(address, bool_point, next_val, priority=priority)

            await asyncio.sleep(hold_s)
            print(f"[{name}] Release {address} {bool_point} @P{priority}")
            await client.write(address, bool_point, "null", priority=priority)

            await asyncio.sleep(step_s)

    finally:
        if hasattr(client, "close"):
            await getattr(client, "close")()
        if hasattr(client, "stop"):
            await getattr(client, "stop")()


if __name__ == "__main__":
    asyncio.run(main())
