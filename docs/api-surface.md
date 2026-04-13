---
layout: default
title: API surface
nav_order: 55
---

# API surface

Easy ASO exposes a few **HTTP** surfaces; pick the one that matches how you deploy.

## diy-bacnet-server (BACnet core)

- **JSON-RPC** (+ OpenAPI/Swagger) on the core container — the **source of truth** for client BACnet operations.
- Base URL set via `DIY_BACNET_URL` on agents (default `http://127.0.0.1:8080` in Compose).

## Legacy BACnet gateway (`easy_aso.gateway.app`)

- Small **FastAPI** app wrapping a **direct bacpypes3** client (`/read`, `/write`, `/rpm`).
- Use when you want the *old* “gateway owns UDP” pattern with REST instead of JSON-RPC.
- Set `BACNET_BACKEND=easy_gateway` on consumers and point them at that service.

## Supervisor (`easy_aso.supervisor.app`)

- **FastAPI** app for **platform-style** configuration:
  - CRUD **devices** and **points** (SQLite).
  - **Latest values** + **per-device health** from asyncio polling.
  - **Hot reload** of poll tasks when config changes (no full restart).
- Default DB path: `SUPERVISOR_DB_PATH` (see [Supervisor workflows](SUPERVISOR_WORKFLOWS.html)).

---

## Design cue

**Operational BACnet** → diy-bacnet-server. **Application config + snapshots** → supervisor. **Control algorithms** → `EasyASO` subclasses (anywhere they can get a `BacnetClient`).
