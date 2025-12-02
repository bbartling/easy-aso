# Easy ASO 🤖🕹️⚡

Welcome to Easy ASO, the ultimate command tool for Automated Supervisory Optimization (ASO) of BACnet systems in EMIS applications. 
Built on a seamless Python asyncio framework, Easy ASO comes with a fully integrated BACnet asyncio stack for convenience, making BACnet—the default protocol in the HVAC industry—effortless to use. 
Other protocols can also be implemented during the development process, offering flexibility and extensibility.

---

## The Skeleton of ASO 🦾🎮🏢
Control BACnet systems on a simple `on_start`, `on_step`, and `on_stop` structure:

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

## Current BACnet Services Supported 💼

- [x] Read
- [x] Write
- [ ] Read Multiple
- [ ] Write Multiple
- [ ] Whois
- [ ] Read Priority Array
- [ ] Anything else? 🤔

---

## Exploring Remote BACnet Sites with `tester.py` 🔍

The `tester.py` script, located in the scripts directory, provides a utility for exploring a remote BACnet site via the bacpypes3 console.  
This tool is designed to assist in the setup and configuration of the `easy-aso` project, streamlining the integration process.  

For detailed information and instructions on using the `Tester.py` script, please refer to the `setup_scripts` directory [README](https://github.com/bbartling/easy-aso/tree/develop/setup_scripts) for more information.

- [x] Read Property (`read_property`)
- [x] Write Property (`write_property`)
- [x] Read Property Multiple (`read_property_multiple`)
- [x] Read Priority Array (`read_property` with `priority-array`)
- [x] Device Discovery (`who-is`)
- [x] Object Discovery (`who-has`)
- [x] Read All Points (`do_point_discovery`)
- [x] Router Discovery (`who_is_router_to_network`)

---

### Step 1: Clone the Repository 📂
First, clone the `easy-aso` repository to your local machine:
```bash
git clone https://github.com/bbartling/easy-aso
```

### Step 2: Install the Package Locally 🖥️
Navigate into the project directory and install it using `pip`. This will make the `easy-aso` package available in your Python environment.
```bash
cd easy-aso
pip install .
```

---

## 📜 License

Everything here is **MIT Licensed** — free, open source, and made for the BAS community.  
Use it, remix it, or improve it — just share it forward so others can benefit too. 🥰🌍


【MIT License】

Copyright 2025 Ben Bartling

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
