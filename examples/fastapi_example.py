"""Deprecated example.

This repo used to include a minimal FastAPI wrapper example.

Going forward, the recommended architecture is:
  - diy-bacnet-server owns BACnet/IP on the edge (UDP/47808)
  - easy-aso agents talk to it over JSON-RPC (TCP)

See:
  - docker-compose.yml (bacnet-core + agents)
  - examples/diy_jsonrpc_example.py
"""
