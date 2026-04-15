"""BACnet JSON-RPC configuration from environment (diy-bacnet-server compatible)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class BacnetRpcConfig:
    """Outbound BACnet-over-JSON-RPC settings."""

    base_url: str
    entrypoint: str
    bearer_token: Optional[str] = None
    timeout_s: float = 15.0


def load_rpc_config_from_env() -> BacnetRpcConfig:
    """
    Read the same environment variables used by the supervisor and demo stacks.

    - ``SUPERVISOR_BACNET_RPC_URL`` (default ``http://127.0.0.1:8080``)
    - ``SUPERVISOR_BACNET_RPC_ENTRYPOINT`` (default ``/api``)
    - ``BACNET_RPC_API_KEY`` optional Bearer token
    """
    base = os.environ.get("SUPERVISOR_BACNET_RPC_URL", "http://127.0.0.1:8080").rstrip("/")
    entry = os.environ.get("SUPERVISOR_BACNET_RPC_ENTRYPOINT", "/api").strip()
    if not entry.startswith("/"):
        entry = "/" + entry
    raw = (os.environ.get("BACNET_RPC_API_KEY") or "").strip()
    tok = raw or None
    return BacnetRpcConfig(base_url=base, entrypoint=entry, bearer_token=tok)
