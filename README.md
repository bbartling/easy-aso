# Easy ASO

[![Discord](https://img.shields.io/badge/Discord-Join%20Server-5865F2.svg?logo=discord&logoColor=white)](https://discord.gg/Ta48yQF8fC)
[![CI](https://github.com/bbartling/easy-aso/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/bbartling/easy-aso/actions/workflows/ci.yml)
![MIT License](https://img.shields.io/badge/license-MIT-green.svg)
![Development Status](https://img.shields.io/badge/status-Beta-blue.svg)
![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python&logoColor=white)
[![PyPI](https://img.shields.io/pypi/v/easy-aso?label=PyPI&logo=pypi&logoColor=white&cacheSeconds=600)](https://pypi.org/project/easy-aso/)

Easy-to-follow Automated Supervisory Optimization (ASO) event-driven logic combined with an asyncio-first supervisory layer for BACnet building automation — lightweight BAS orchestration at the IoT edge with one BACnet/IP core, small agents, optional REST/JSON-RPC, and room to grow without a full platform stack.


**[Documentation](https://bbartling.github.io/easy-aso/)** · 

---

## Install from PyPI

```bash
pip install easy-aso
```

[documentation site](https://bbartling.github.io/easy-aso/)
[diy-bacnet-server](https://github.com/bbartling/diy-bacnet-server) (BACnet core)

## ASO Made Easy


```python
class CustomHvacAso(EasyASO):
    async def on_start(self):
        print("Custom ASO is deploying! Lets do something!")

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
        await self.bacnet_write("192.168.0.122", "analog-output,2", 'null')
        print("Executing stop actions... The system is released back to normal!")
```

---

## License

MIT — see [`LICENSE`](LICENSE).
