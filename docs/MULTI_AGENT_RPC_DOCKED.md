---
layout: default
title: Multi-agent (RPC-docked)
nav_order: 45
description: Run many EasyASO workers beside one BACnet gateway using JSON-RPC.
---

# Multi-agent deployments (RPC-docked `EasyASO`)

When you run **more than one** supervisory loop, keep **one** BACnet/IP listener on **UDP 47808** (typically **diy-bacnet-server** in Docker) and run each custom algorithm in its **own process or container**.

This package ships:

| Piece | Location |
|-------|----------|
| RPC-docked base class | `easy_aso.runtime.rpc_docked.RpcDockedEasyASO` |
| Env → config helper | `easy_aso.runtime.env.load_rpc_config_from_env`, `BacnetRpcConfig` |
| Programmatic runner | `easy_aso.runtime.runner.run_agent_class` |
| Console entry point | **`easy-aso-agent run`** (see `--help`) |
| Default sample agent | `easy_aso.runtime.sample_agent.SampleAgent` |

## Why not plain `EasyASO.run()` in every container?

`EasyASO` with a local BACnet stack calls `Application.from_args` and expects to participate on the wire. On a single host, **only one** process should bind **47808**. RPC-docked agents call **`JsonRpcBacnetClient`** instead so all I/O goes through the gateway’s JSON-RPC surface.

## Environment variables

Same names as the supervisor and common demo stacks:

| Variable | Role |
|----------|------|
| `SUPERVISOR_BACNET_RPC_URL` | Base URL (default `http://127.0.0.1:8080`) |
| `SUPERVISOR_BACNET_RPC_ENTRYPOINT` | Path prefix (default `/api`) |
| `BACNET_RPC_API_KEY` | Optional Bearer token for RPC |

Agent runner (`easy-aso-agent run` or `run_agent_class`):

| Variable | Role |
|----------|------|
| `EASY_ASO_AGENT_MODULE` | Dotted import path (default `easy_aso.runtime.sample_agent`) |
| `EASY_ASO_AGENT_CLASS` | Class name (default `SampleAgent`) |
| `EASY_ASO_STEP_SEC` | Sleep between steps in the bundled sample (seconds; minimum sleep clamp in sample is **0.05** s) |
| `EASY_ASO_DEMO_READ_DEVICE` / `EASY_ASO_DEMO_READ_OBJECT` | Optional demo read each step |

## `JsonRpcBacnetClient` addressing

For **diy-bacnet-server**, the `address` argument to read/write/RPM is a **device instance** string (see the client docstring), not necessarily an IP address.

## Example Docker `CMD`

```dockerfile
CMD ["easy-aso-agent", "run"]
```

Override module/class via `EASY_ASO_AGENT_MODULE` and `EASY_ASO_AGENT_CLASS` in the container environment.

## See also

- [Platform driver architecture](PLATFORM_DRIVER_ARCHITECTURE.html) — supervisor vs edge agents
- [BACnet edge](bacnet-edge.html) — who owns UDP 47808
- [Supervisor OT security](SUPERVISOR_OT_SECURITY.html) — RPC secrets on OT LANs
