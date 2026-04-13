# Supervisor workflows

The **supervisor** service (`easy_aso.supervisor.app`) provides CRUD for BACnet (or stub) devices/points, persists configuration in **SQLite**, and runs **asyncio** polling loops per enabled device.

## Run locally

```bash
pip install -e ".[platform]"
export SUPERVISOR_DB_PATH=./data/supervisor.sqlite
uvicorn easy_aso.supervisor.app:app --host 0.0.0.0 --port 8090
```

- Open `http://127.0.0.1:8090/docs` for interactive API.
- On first start, **seed data** creates a disabled example device (`seed-example-vav`) with two points.

## BACnet (diy-bacnet-server)

1. Run diy-bacnet-server (JSON-RPC, default `http://127.0.0.1:8080/api`).
2. Create or patch a device with `driver_type: bacnet_jsonrpc`, `device_address` set to the **device instance** (e.g. `"3456789"`), and `enabled: true`.
3. Optionally set `rpc_base_url` / `rpc_entrypoint` on the device row; otherwise the process reads:

   - `SUPERVISOR_BACNET_RPC_URL` (default `http://127.0.0.1:8080`)
   - `SUPERVISOR_BACNET_RPC_ENTRYPOINT` (default `/api`)

4. Add points with BACnet `object_identifier` / `property_identifier` pairs. Polling uses **RPM** when multiple points exist.

## Hot reload

Any **create / update / delete** of a device or its points triggers `SupervisorRuntime.reload_device` for that device: the old poll task is cancelled and a new loop is started from the database (no full process restart).

## MQTT (later)

Poll results are stored on each point (`last_value_json`, `last_polled_at`, `last_error`). A separate asyncio task or agent can read these snapshots (or subscribe to future in-memory buses) and publish to MQTT without changing drivers.
