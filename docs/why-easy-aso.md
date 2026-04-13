---
layout: default
title: Why Easy ASO?
nav_order: 15
description: "Edge-first BACnet supervision, event-driven agents, and the optional supervisor."
---

# Why Easy ASO?

This page expands the ideas that used to live in the repo `README` — the **short story** on the [home page](index.html) is enough for newcomers; read on if you want the positioning.

---

## Edge-first

Docker Compose brings up a singleton **BACnet core** (UDP `47808`) plus independent **algorithm containers** — a slimmed-down mental model similar to a lightweight VOLTTRON-style deployment, tuned for gateways and Raspberry Pi–class hardware.

---

## Event-driven control

Subclass `EasyASO` and implement `on_start` → `on_step` → `on_stop` for read/write cycles, kill-switch behavior, and clean override release.

---

## Platform driver (supervisor)

SQLite-backed devices/points, asyncio polling, hot reload, and a **FastAPI** surface — inspired by a *platform driver* mental model, without pretending to be VOLTTRON. See [Supervisor workflows](SUPERVISOR_WORKFLOWS.html).

---

## Docker quick start (repo clone)

BACnet/IP and discovery (Who-Is, RPM, read/write, priority array, point discovery, etc.) are implemented by **[diy-bacnet-server](https://github.com/bbartling/diy-bacnet-server)** — this repo **vendors** it under `vendor/diy-bacnet-server/` and talks to it over **JSON-RPC** by default.

```bash
git clone https://github.com/bbartling/easy-aso.git
cd easy-aso
docker compose up -d --build
```

- **Swagger (BACnet core):** `http://localhost:8080/docs`
- Tune `BACNET_CORE_ARGS`, `DEVICE_INSTANCE`, and agent env vars in `docker-compose.yml` for your site.

Agents use `BACNET_BACKEND=diy_jsonrpc` and `DIY_BACNET_URL` (see [BACnet edge](bacnet-edge.html)).

---

## Local development (clone)

```bash
pip install -e ".[dev]"
pytest tests/test_abc.py tests/test_supervisor.py -v
```

Optional Docker integration test (two simulated BACnet peers):

```bash
pytest tests/test_bacnet.py -v
```

For a guided path (venv, supervisor service, building docs locally), see [Getting started](getting-started.html).
