# Platform driver architecture (easy-aso supervisor)

This document describes where the VOLTTRON-inspired **platform driver** (dynamic devices/points, polling, config store) fits into easy-aso, and how components interact. It is intentionally smaller than a full BAS stack: **asyncio-first**, **SQLite** for configuration, **in-process** polling tasks, and **pluggable drivers** (BACnet first).

## Current codebase (anchors)

| Area | Location | Role today |
|------|----------|------------|
| BACnet abstraction | `easy_aso/bacnet_client/` (`BacnetClient`, `JsonRpcBacnetClient`) | Read/write/RPM against diy-bacnet-server or direct bacpypes |
| HTTP gateway (BACnet socket owner) | `easy_aso/gateway/app.py` | Legacy REST shim around `BacpypesClient` |
| Agent loops | `easy_aso/agents/*.py` | Example long-running consumers using env + factory |
| Core ASO lifecycle | `easy_aso/easy_aso.py` | User subclasses `EasyASO` for algorithms |

The supervisor **does not replace** `EasyASO`; it **feeds** future algorithms and MQTT publishers with a **normalized point cache** and **CRUD configuration**.

## Target package layout

New top-level package: **`easy_aso/supervisor/`** (keeps gateway and agents unchanged).

```
easy_aso/supervisor/
  app.py                 # FastAPI app + lifespan (starts/stops runtime)
  api/schemas.py         # Pydantic request/response models
  api/routes.py          # CRUD + health + latest values
  store/
    schema.py            # DDL + PRAGMA user_version (simple migrations)
    database.py          # aiosqlite connection helper
    repository.py        # Async CRUD for devices + points + reading snapshots
    seed.py              # Example rows (disabled by default where appropriate)
  runtime/
    registry.py          # SupervisorRuntime: task map, start/stop/reload
    poller.py            # Per-device asyncio loop: sleep → driver.read_points → persist
  drivers/
    base.py              # BaseDriver protocol/ABC
    bacnet_jsonrpc.py    # Uses JsonRpcBacnetClient + RPM batching
```

## Insertion points (by concern)

### Persistent config storage

- **SQLite** via `aiosqlite` under `supervisor/store/`.
- **Single schema file** (`schema.py`) applied idempotently on open (`CREATE TABLE IF NOT EXISTS`, bump `PRAGMA user_version`).
- **Repository** is the only layer that runs SQL (keeps FastAPI routes thin).

### Runtime device registry

- **`SupervisorRuntime`** in `supervisor/runtime/registry.py` holds:
  - `dict[device_id, asyncio.Task]` for active poll loops
  - `asyncio.Lock` for structural changes (add/cancel/replace task)
  - In-memory **health** (`last_poll_at`, `last_error`, `status`) keyed by device

### Polling task manager

- **`poller.py`** implements one coroutine per **enabled** device: cancel-aware sleep, call driver, write results + timestamps through repository, update health.
- **Per-device scrape interval** stored on the device row (`scrape_interval_seconds`).

### BACnet driver abstraction

- **`drivers/base.py`**: `BaseDriver` with `DRIVER_TYPE` and `read_points(...)`.
- **`drivers/bacnet_jsonrpc.py`**: constructs `JsonRpcBacnetClient` from device/env; batches reads with **`rpm`** (object id + property pairs) when multiple points exist.

### FastAPI / future web UI

- **`supervisor/app.py`**: dedicated app (`uvicorn easy_aso.supervisor.app:app`) with **lifespan** (not legacy startup events) to own the runtime lifecycle.
- **Routers** in `api/routes.py` depend on `app.state.runtime` and `app.state.repository`.
- A future static UI can call the same JSON API; no UI in initial phases.

## Data flow

1. **Lifespan startup**: open DB → migrate schema → seed if empty → `SupervisorRuntime.start()` loads enabled devices and spawns poll tasks.
2. **Poll loop**: for each device → driver reads enabled points → repository updates `last_value`, `last_polled_at`, `last_error` per point → runtime updates device health.
3. **Config change (API)**: repository mutates SQLite → `runtime.reload_device(device_id)` cancels prior task and starts a fresh loop from DB (hot reload, not full process restart).

## MQTT (future)

Publishers subscribe to an internal **async callback queue** or poll latest values from SQLite on an interval. The repository already holds **last_value** snapshots suitable for fan-out without coupling drivers to MQTT.

## Docker / Raspberry Pi

- Supervisor is **optional**: default images keep working without the new app.
- **Python 3.14** base images for easy-aso Dockerfiles; SQLite file on a **volume** for persistence on Pi.

## Testing strategy

- **In-memory SQLite** (`:memory:`) + **mock driver** for lifecycle and CRUD/reload tests (no BACnet network).
- **Optional integration** later: compose stack + real RPC (out of scope for default CI).
