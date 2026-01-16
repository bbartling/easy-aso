from __future__ import annotations

import os
from typing import Tuple

from .base import BacnetClient


def _env(name: str, default: str) -> str:
    v = os.environ.get(name)
    return v if v is not None and v != "" else default


def create_bacnet_client_from_env() -> Tuple[BacnetClient, str]:
    """Create a BacnetClient from environment variables.

    Returns (client, address_hint).

    Supported backends:
      - easy_gateway (default): talks to easy-aso's bacnet-gateway REST service
      - diy_jsonrpc: talks to diy-bacnet-server JSON-RPC service
      - bacpypes_direct: owns UDP/47808 directly (only for the gateway container)

    Address hint is what agents should treat as the `address` argument:
      - easy_gateway / bacpypes_direct: DEVICE_ADDRESS (IP:port or bacnet address)
      - diy_jsonrpc: DEVICE_INSTANCE (integer device instance as string)
    """

    backend = _env("BACNET_BACKEND", "easy_gateway").strip().lower()

    if backend in ("diy", "diy_jsonrpc", "jsonrpc"):
        from .jsonrpc_client import JsonRpcBacnetClient

        url = _env("DIY_BACNET_URL", "http://127.0.0.1:8080")
        entrypoint = _env("DIY_BACNET_ENTRYPOINT", "/api")
        client = JsonRpcBacnetClient(url, entrypoint=entrypoint)
        addr = _env("DEVICE_INSTANCE", "123")
        return client, addr

    if backend in ("direct", "bacpypes", "bacpypes_direct"):
        from .bacpypes_client import BacpypesClient

        # bacpypes args come from BACNET_ARGS (same as the gateway container)
        argv = _env("BACNET_ARGS", "--name Agent --instance 123").split()
        client = BacpypesClient(argv=argv)
        addr = _env("DEVICE_ADDRESS", "10.200.200.233")
        return client, addr

    # default: easy-aso gateway REST
    from .remote_client import RemoteBacnetClient

    url = _env("BACNET_GATEWAY_URL", "http://127.0.0.1:8000")
    client = RemoteBacnetClient(url)
    addr = _env("DEVICE_ADDRESS", "10.200.200.233")
    return client, addr
