---
layout: default
title: Home
nav_order: 1
description: "Asyncio BACnet supervisory layer for the IoT edge."
permalink: /
---

# Easy ASO

**Easy ASO** is a small, opinionated stack for **BACnet building automation at the edge**: asyncio agents, a single BACnet/IP core ([diy-bacnet-server](https://github.com/bbartling/diy-bacnet-server)), and an optional **supervisor** that feels a bit like a **VOLTTRON platform driver** — dynamic devices/points, polling, SQLite config — without the ceremony of a full distributed platform.

Use it when you want:

- **Deterministic control loops** (`on_start` / `on_step` / `on_stop`) with explicit override and release semantics.
- **Docker-first** deployment next to MQTT, EMIS, or your own services.
- **A path to optimization** (demand limits, resets, diagnostics) that stays readable as the site grows.

---

## Where to go next

| I want to… | Read |
|------------|------|
| Understand positioning (edge, agents, supervisor) | [Why Easy ASO?](why-easy-aso.html) |
| Run the stack on a gateway or Pi | [Getting started](getting-started.html) |
| Point BACnet tooling at the LAN | [BACnet edge](bacnet-edge.html) |
| Model supervisory logic as events | [Lifecycle & events](lifecycle.html) |
| Configure devices/points + REST API | [Supervisor workflows](SUPERVISOR_WORKFLOWS.html) |
| Harden supervisor + BACnet RPC on an OT LAN | [Supervisor OT security](SUPERVISOR_OT_SECURITY.html) |
| See HTTP surfaces | [API surface](api-surface.html) |
| Understand the design | [Platform driver architecture](PLATFORM_DRIVER_ARCHITECTURE.html) |
| Ship to PyPI | [PyPI publishing](pypi-publishing.html) |
| Run many agents beside one BACnet gateway | [Multi-agent (RPC-docked)](MULTI_AGENT_RPC_DOCKED.html) |

---

## Philosophy

**BACnet stays in one place.** Everyone else speaks JSON-RPC or REST over TCP — that keeps UDP `47808` sane on constrained hosts and matches how real edge integrators deploy.

**Supervision is a loop, not a framework.** You bring the physics and the sequence of operations; Easy ASO brings scheduling, BACnet plumbing, and (optionally) a config store so you can iterate without redeploying the world.
