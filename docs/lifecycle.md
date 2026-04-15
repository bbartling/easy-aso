---
layout: default
title: Lifecycle & events
nav_order: 4
---

# Lifecycle & events

`EasyASO` is an **asyncio** control skeleton: your building logic runs as a cooperative task with a predictable rhythm.

## The three hooks

| Hook | When | Typical work |
|------|------|----------------|
| `on_start` | Once at startup | Connect resources, seed setpoints, log commissioning context |
| `on_step` | Loop | Read sensors, evaluate control law, write overrides at a chosen priority |
| `on_stop` | Shutdown / signal | **Release** overrides (`null` write at same priority), flush state |

That maps cleanly to **event-driven** thinking: each `on_step` tick is an opportunity to react to **BACnet present-value**, **schedules**, **tariffs**, or **external APIs** — without blocking the event loop (keep I/O async).

---

## Kill switch & safety

The framework exposes an **optimization-enabled** commandable binary value. `get_optimization_enabled_status()` lets you **short-circuit** optimization (release overrides, hold, or run in shadow mode) before touching field hardware.

Pair that with **explicit `bacnet_write(..., 'null', priority)`** on stop so the BAS never inherits stale priorities.

---

## Scaling out

Run **multiple** `EasyASO` subclasses with `asyncio.gather` in one process, or **one container per strategy** under Compose — same code, different packaging. Telemetry (MQTT, HTTP) slots in as another asyncio task.

---

## Relation to the supervisor

The **supervisor** service (optional) continuously **polls configured points** and stores snapshots in SQLite — a natural feed for future “algorithm containers” that read **last value** instead of hammering BACnet every cycle. See [Supervisor workflows](SUPERVISOR_WORKFLOWS.html).
