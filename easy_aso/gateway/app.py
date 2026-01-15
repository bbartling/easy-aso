from __future__ import annotations

import os
import shlex
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from easy_aso.bacnet_client.bacpypes_client import BacpypesClient


class ReadRequest(BaseModel):
    address: str
    object_identifier: str
    property_identifier: str = "present-value"


class WriteRequest(BaseModel):
    address: str
    object_identifier: str
    value: Any
    priority: Optional[int] = Field(default=None, description="BACnet priority (e.g. 8). Use null release via value='null'.")
    property_identifier: str = "present-value"


class RPMRequest(BaseModel):
    address: str
    args: List[str]


app = FastAPI(title="easy-aso bacnet-gateway", version="0.2.0")

_client: BacpypesClient | None = None


def _argv_from_env() -> List[str]:
    """Parse BACNET_ARGS env var into argv for bacpypes3 SimpleArgumentParser.

    Example:
      BACNET_ARGS="--name Gateway --instance 123 --address 10.0.0.10/24"
    """
    raw = os.environ.get("BACNET_ARGS", "")
    return shlex.split(raw) if raw else []


@app.on_event("startup")
async def _startup() -> None:
    global _client
    argv = _argv_from_env()
    _client = BacpypesClient(argv=argv)
    await _client.start()


@app.on_event("shutdown")
async def _shutdown() -> None:
    global _client
    if _client is not None:
        await _client.stop()
        _client = None


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/read")
async def read(req: ReadRequest) -> Dict[str, Any]:
    if _client is None:
        raise HTTPException(status_code=503, detail="gateway not ready")
    try:
        value = await _client.read(req.address, req.object_identifier, req.property_identifier)
        return {"value": value}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/write")
async def write(req: WriteRequest) -> Dict[str, str]:
    if _client is None:
        raise HTTPException(status_code=503, detail="gateway not ready")
    try:
        await _client.write(req.address, req.object_identifier, req.value, req.priority, req.property_identifier)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/rpm")
async def rpm(req: RPMRequest) -> Dict[str, Any]:
    if _client is None:
        raise HTTPException(status_code=503, detail="gateway not ready")
    try:
        results = await _client.rpm(req.address, *req.args)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
