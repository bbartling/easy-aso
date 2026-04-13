---
layout: default
title: Getting started
nav_order: 2
---

# Getting started

## Edge: Docker Compose

From the repo root:

```bash
docker compose up -d --build
```

- **BACnet core (diy-bacnet-server):** JSON-RPC + Swagger at `http://localhost:8080/docs`.
- **Agents** (`dueler_*`, `hvac_agent`, `mqtt_publisher`, …) use `BACNET_BACKEND=diy_jsonrpc` — see `docker-compose.yml`.

`network_mode: host` is used so BACnet/IP can reach the OT LAN reliably from Linux gateways (typical Pi / edge server).

---

## Laptop: local Python

```bash
git clone https://github.com/bbartling/easy-aso.git
cd easy-aso
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest tests/test_abc.py tests/test_supervisor.py -v
```

Optional full BACnet-in-Docker check:

```bash
pytest tests/test_bacnet.py -v
```

---

## Supervisor (optional service)

```bash
pip install -e ".[platform]"
export SUPERVISOR_DB_PATH=./data/supervisor.sqlite
uvicorn easy_aso.supervisor.app:app --host 0.0.0.0 --port 8090
```

Open `http://127.0.0.1:8090/docs` for CRUD on devices/points and latest polled values. Details: [Supervisor workflows](SUPERVISOR_WORKFLOWS.html).

---

## Build this documentation locally

```bash
cd docs
bundle install
bundle exec jekyll serve --livereload
```

Open `http://127.0.0.1:4000/easy-aso/`.

### Published site (GitHub Pages)

Set **Settings → Pages → Build and deployment → Source: GitHub Actions**.

Workflows (same layout as [open-fdd](https://github.com/bbartling/open-fdd/tree/master/.github/workflows)):

| Workflow | What it does |
|----------|----------------|
| [`docs-pages.yml`](https://github.com/bbartling/easy-aso/blob/main/.github/workflows/docs-pages.yml) | Jekyll → GitHub Pages when `docs/**` changes on **`main`** |
| [`docs-pdf.yml`](https://github.com/bbartling/easy-aso/blob/main/.github/workflows/docs-pdf.yml) | Regenerates `pdf/easy-aso-docs.pdf` + `.txt`, opens a **PR** |
| [`publish-pypi.yml`](https://github.com/bbartling/easy-aso/blob/main/.github/workflows/publish-pypi.yml) | Publishes the **whole** package on push tags `v*` |

Public site: **`https://bbartling.github.io/easy-aso/`**

PyPI setup for maintainers: [PyPI publishing](pypi-publishing.html).
