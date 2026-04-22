# Easy ASO

[![Discord](https://img.shields.io/badge/Discord-Join%20Server-5865F2.svg?logo=discord&logoColor=white)](https://discord.gg/Ta48yQF8fC)
[![CI](https://github.com/bbartling/easy-aso/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/bbartling/easy-aso/actions/workflows/ci.yml)
![MIT License](https://img.shields.io/badge/license-MIT-green.svg)
![Development Status](https://img.shields.io/badge/status-Beta-blue.svg)
![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python&logoColor=white)
[![PyPI](https://img.shields.io/pypi/v/easy-aso?label=PyPI&logo=pypi&logoColor=white&cacheSeconds=600)](https://pypi.org/project/easy-aso/)

Easy-to-follow Automated Supervisory Optimization (ASO) event-driven logic combined with an asyncio-first supervisory layer for BACnet building automation — lightweight BAS orchestration at the IoT edge with one BACnet/IP core, small agents, optional REST/JSON-RPC, and room to grow without a full platform stack. 


---

## Install from PyPI

```bash
pip install easy-aso
```

---

## Online Documentation

This application is part of a broader ecosystem that together forms the **Open FDD AFDD Stack**, enabling a fully orchestrated, edge-deployable analytics and optimization platform for building automation systems.

* 🔗 **DIY BACnet Server**
  Lightweight BACnet server with JSON-RPC and MQTT support for IoT integrations.
  [Documentation](https://bbartling.github.io/diy-bacnet-server/) · [GitHub](https://github.com/bbartling/diy-bacnet-server)

* 📖 **Open FDD AFDD Stack**
  Full AFDD framework with Docker bootstrap, API services, drivers, and React web UI.
  [Documentation](https://bbartling.github.io/open-fdd-afdd-stack/) · [GitHub](https://github.com/bbartling/open-fdd-afdd-stack)

* 📘 **Open FDD Fault Detection Engine**
  Core rules engine with `RuleRunner`, YAML-based fault logic, and pandas workflows.
  [Documentation](https://bbartling.github.io/open-fdd/) · [GitHub](https://github.com/bbartling/open-fdd) · [PyPI](https://pypi.org/project/open-fdd/)

* ⚙️ **easy-aso Framework**
  Lightweight framework for Automated Supervisory Optimization (ASO) algorithms at the IoT edge.
  [Documentation](https://bbartling.github.io/easy-aso/) · [GitHub](https://github.com/bbartling/easy-aso) · [PyPI](https://pypi.org/project/easy-aso/0.1.7/)


---

## ASO made easy

Subclass **`EasyASO`** and implement **`on_start`**, **`on_step`**, and **`on_stop`** — same pattern for reads, writes, and releasing overrides:

```python
import asyncio

from easy_aso import EasyASO


class CustomHvacAso(EasyASO):
    async def on_start(self):
        print("Custom ASO is deploying! Let's do something!")

    async def on_step(self):
        # BACnet read request
        sensor = await self.bacnet_read("192.168.0.122", "analog-input,1")

        # Custom step logic - BACnet write request
        override_valve = sensor + 5.0
        await self.bacnet_write("192.168.0.122", "analog-output,2", override_valve)

        print("Executing step actions... The system is being optimized!")
        await asyncio.sleep(60)

    async def on_stop(self):
        # Custom stop logic - BACnet release request
        await self.bacnet_write("192.168.0.122", "analog-output,2", "null")
        print("Executing stop actions... The system is released back to normal!")
```

---

## Local security bootstrap

Generate local bearer tokens (diy JSON-RPC + supervisor API):

```bash
./scripts/bootstrap-secrets.sh
set -a && . ./.env.local && set +a
```

```powershell
.\scripts\bootstrap-secrets.ps1
Get-Content .env.local | ForEach-Object { if ($_ -match '^(.*?)=(.*)$') { Set-Item -Path Env:\$($matches[1]) -Value $matches[2] } }
```

Then run your stack with:

- `BACNET_RPC_API_KEY` for outbound calls to diy-bacnet-server JSON-RPC
- `SUPERVISOR_API_KEY` for optional inbound auth on `easy_aso.supervisor.app`

---

## License

MIT
