---
layout: default
title: Supervisor OT security
nav_order: 51
---

# Supervisor security on OT / BAS networks

easy-aso is often deployed on a **building or plant LAN**, not on the public internet. The goals are **authentication** (who is calling control interfaces) and **authorization** (what they are allowed to do via your API gateway and BACnet RPC), not consumer-scale rate limiting.

## BACnet JSON-RPC (diy-bacnet-server)

When **[diy-bacnet-server](https://github.com/bbartling/diy-bacnet-server)** has **`BACNET_RPC_API_KEY`** set, JSON-RPC expects **`Authorization: Bearer <key>`** (see upstream README). easy-aso’s **`JsonRpcBacnetClient`** sends that header when you set any of:

- explicit `bearer_token=…` in code, or
- **`SUPERVISOR_BACNET_RPC_BEARER`**, or
- **`BACNET_RPC_API_KEY`** in the environment.

Use a **long random** secret and the **same** value on the BACnet RPC service and the easy-aso process (or container) that calls it.

## Supervisor HTTP API (FastAPI)

Treat the supervisor REST API like **control-plane**: bind it to **localhost** or put a **reverse proxy** (TLS + operator auth) in front and **do not** publish the Uvicorn port broadly on the LAN.

For **BAS Lite** (Docker + Caddy), see the **`vibe_code_apps_8`** stack: HTTPS with **`tls internal`**, Basic Auth at the edge, and an optional **gateway header** so only the proxy can inject the shared secret the API expects.

## Network exposure

- Prefer **segmented** VLANs or firewalls so only workstations and peers that need BACnet/IP or HTTP can reach the host.
- **BACnet UDP 47808** is inherently broadcast-oriented; securing the **IP fabric** is part of the BACnet deployment story.

This document does not replace a site **cybersecurity assessment**; it lists the hooks easy-aso and common stacks use so operators can align with site policy.
