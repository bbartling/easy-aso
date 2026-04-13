# Easy ASO

**Asyncio-first supervisory layer for BACnet building automation** — think lightweight BAS orchestration at the IoT edge: one BACnet/IP core, many small agents, optional REST/JSON-RPC, and room to grow toward MQTT and optimization loops without the weight of a full platform stack.

**[Documentation](https://bbartling.github.io/easy-aso/)** · [diy-bacnet-server](https://github.com/bbartling/diy-bacnet-server) (BACnet core & discovery) · MIT License

---

## Why Easy ASO?

- **Edge-first:** Docker Compose brings up a singleton **BACnet core** (UDP `47808`) plus independent **algorithm containers** — same idea as a slimmed-down VOLTTRON-style deployment, tuned for gateways and Raspberry Pi–class hardware.
- **Event-driven control:** Subclass `EasyASO` and implement `on_start` → `on_step` → `on_stop` for read/write cycles, kill-switch behavior, and clean override release.
- **Platform driver (supervisor):** SQLite-backed devices/points, asyncio polling, hot reload, and a **FastAPI** surface — inspired by a *platform driver* mental model, without pretending to be VOLTTRON. See [Supervisor workflows](https://bbartling.github.io/easy-aso/SUPERVISOR_WORKFLOWS.html).

---

## Quick start (Docker, IoT edge)

BACnet/IP and discovery (Who-Is, RPM, read/write, priority array, point discovery, etc.) are implemented by **[diy-bacnet-server](https://github.com/bbartling/diy-bacnet-server)** — this repo **vendors** it under `vendor/diy-bacnet-server/` and talks to it over **JSON-RPC** by default.

```bash
git clone https://github.com/bbartling/easy-aso.git
cd easy-aso
docker compose up -d --build
```

- **Swagger (BACnet core):** `http://localhost:8080/docs`  
- Tune `BACNET_CORE_ARGS`, `DEVICE_INSTANCE`, and agent env vars in `docker-compose.yml` for your site.

Agents use `BACNET_BACKEND=diy_jsonrpc` and `DIY_BACNET_URL` (see [BACnet edge](https://bbartling.github.io/easy-aso/bacnet-edge.html)).

---

## Local development

```bash
pip install -e ".[dev]"
pytest tests/test_abc.py tests/test_supervisor.py -v
```

Optional Docker integration test (two simulated BACnet peers):

```bash
pytest tests/test_bacnet.py -v
```

---

## Documentation site

Full guides (architecture, supervisor API, lifecycle patterns, BACnet integration) live in **`docs/`**. Pushes to **`main`** trigger **GitHub Actions** (`.github/workflows/pages.yml`) to build Jekyll and publish **GitHub Pages** at the link in the header above.

Build locally (Ruby + Bundler):

```bash
cd docs
bundle install
bundle exec jekyll serve --livereload
```

Browse `http://127.0.0.1:4000/easy-aso/`.

---

## License

MIT — see [`LICENSE`](LICENSE).
