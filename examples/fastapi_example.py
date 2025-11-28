"""
A minimal FastAPI application exposing BACnet read/write operations and a simple
kill switch using the refactored ``easy_aso`` framework.  This example
demonstrates how a web developer can interact with BACnet points via HTTP
without needing intimate knowledge of the protocol.

To run this app:

1. Install the required dependencies (in a virtual environment):

   ```sh
   pip install fastapi uvicorn pydantic
   pip install -e .
   ```

   The second command installs the ``easy_aso`` package in editable mode
   from the current directory.  If you only need the in‑memory BACnet
   client for testing, you can omit installing external BACnet stacks.

2. Start the server with:

   ```sh
   uvicorn fastapi_example:app --reload
   ```

This will launch a development server on http://127.0.0.1:8000/.  You can
interact with the API using your browser or any HTTP client.  For example:

```
# Write a value
curl -X POST -H "Content-Type: application/json" \
  -d '{"address": "zone1", "object_id": "temp", "value": 22.5}' \
  http://127.0.0.1:8000/write

# Read it back
curl 'http://127.0.0.1:8000/read?address=zone1&object_id=temp'

# Disable optimization via kill switch
curl -X POST http://127.0.0.1:8000/kill

# Re‑enable optimization
curl -X POST http://127.0.0.1:8000/enable
```

In a real deployment you would replace the ``InMemoryBACnetClient`` with an
implementation that talks to a BACnet/IP stack such as bacpypes3.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from easy_aso.bacnet_client import InMemoryBACnetClient


app = FastAPI(title="easy‑aso BACnet API", version="0.1.0")

# Use the in‑memory client for demonstration; swap with a real BACnet client
# implementation (e.g. bacpypes3 wrapper) in production.
bacnet = InMemoryBACnetClient()


class WriteRequest(BaseModel):
    """Schema for write requests."""

    address: str
    object_id: str
    value: float
    priority: int = -1
    property_id: str = "present-value"


@app.get("/read")
async def read_property(
    address: str, object_id: str, property_id: str = "present-value"
):
    """Read a BACnet present value.

    Parameters
    ----------
    address: str
        The device or zone address (e.g. IP or device name).
    object_id: str
        The BACnet object identifier (e.g. "analog-input,1").
    property_id: str
        The BACnet property to read (default ``present-value``).

    Returns
    -------
    dict
        A JSON object containing the property value.
    """
    value = await bacnet.read_property(address, object_id, property_id)
    if value is None:
        raise HTTPException(status_code=404, detail="Property not found")
    return {"value": value}


@app.post("/write")
async def write_property(req: WriteRequest) -> dict:
    """Write a value to a BACnet object.

    Accepts a JSON body matching the ``WriteRequest`` schema.  The
    priority field is optional and defaults to ``-1``, which means
    the default BACnet priority.
    """
    await bacnet.write_property(
        req.address,
        req.object_id,
        req.value,
        priority=req.priority,
        property_id=req.property_id,
    )
    return {"status": "ok"}


# A simple in‑memory kill switch.  When disabled, writes can be ignored
optimization_enabled: bool = True


@app.post("/kill")
async def disable_optimization() -> dict:
    """Disable optimization (kill switch)."""
    global optimization_enabled
    optimization_enabled = False
    return {"optimization": False}


@app.post("/enable")
async def enable_optimization() -> dict:
    """Re‑enable optimization."""
    global optimization_enabled
    optimization_enabled = True
    return {"optimization": True}