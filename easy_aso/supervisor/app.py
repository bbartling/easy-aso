from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

import fastapi_jsonrpc as jsonrpc
from fastapi import FastAPI

from easy_aso.supervisor.auth import install_supervisor_auth_if_configured
from easy_aso.supervisor.coordinator import SupervisorCoordinator
from easy_aso.supervisor.rpc_methods import create_supervisor_rpc_entrypoint, set_supervisor_rpc_app
from easy_aso.supervisor.runtime.registry import SupervisorRuntime
from easy_aso.supervisor.store.database import open_supervisor_db
from easy_aso.supervisor.store.repository import SupervisorRepository
from easy_aso.supervisor.store.seed import ensure_seed_data

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI | jsonrpc.API) -> AsyncIterator[None]:
    db_path = os.environ.get("SUPERVISOR_DB_PATH", "data/supervisor.sqlite")
    logger.info("supervisor opening database path=%s", db_path)
    conn = await open_supervisor_db(db_path)
    repo = SupervisorRepository(conn)
    await ensure_seed_data(repo)
    runtime = SupervisorRuntime(repo)
    await runtime.start()
    coordinator = SupervisorCoordinator(repo, runtime)
    app.state.db_conn = conn
    app.state.repo = repo
    app.state.runtime = runtime
    app.state.coordinator = coordinator
    yield
    await runtime.stop()
    await conn.close()
    logger.info("supervisor shutdown complete")


def create_supervisor_app() -> jsonrpc.API:
    app = jsonrpc.API(title="easy-aso supervisor", version="0.3.0", lifespan=_lifespan)
    app.bind_entrypoint(create_supervisor_rpc_entrypoint())
    set_supervisor_rpc_app(app)

    @app.get("/health")
    async def health() -> dict:
        rt = app.state.runtime
        return {"status": "ok", "running_devices": len(rt.health_snapshot())}

    enabled = install_supervisor_auth_if_configured(app)
    if enabled:
        logger.info("supervisor bearer auth enabled via SUPERVISOR_API_KEY")
    return app


app = create_supervisor_app()
