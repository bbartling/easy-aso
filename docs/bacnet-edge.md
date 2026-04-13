---
layout: default
title: BACnet edge
nav_order: 3
---

# BACnet edge (diy-bacnet-server)

All **on-wire BACnet** — discovery, read property, write property, RPM, priority array, Who-Has, point discovery, router helpers — lives in **[diy-bacnet-server](https://github.com/bbartling/diy-bacnet-server)**. Easy ASO **does not reimplement** those services; it integrates.

This repo **vendors** the core under `vendor/diy-bacnet-server/` and starts it as the **`bacnet-core`** service in `docker-compose.yml`.

---

## What you use in practice

1. **Swagger** on the core (`/docs`) to craft JSON-RPC calls and learn request shapes.
2. **Environment** on agents:
   - `BACNET_BACKEND=diy_jsonrpc`
   - `DIY_BACNET_URL` (e.g. `http://127.0.0.1:8080`)
   - `DEVICE_INSTANCE` — BACnet **device instance number** for client calls (not raw IP for this backend).
3. **`easy_aso.bacnet_client`** in Python for a typed `BacnetClient` over the same RPC.

---

## Why this split

BACnet/IP needs a stable UDP socket and often **host networking** on the edge. Keeping **one core** and many **stateless algorithm containers** matches how IoT contractors deploy gateways — and stays close to the **VOLTTRON “platform agent owns the stack”** idea, without importing VOLTTRON itself.

---

## Further reading

- [Lifecycle & events](lifecycle.html) — how your algorithms call into BACnet.
- [API surface](api-surface.html) — REST gateway vs supervisor HTTP.
