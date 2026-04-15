"""Minimal :class:`RpcDockedEasyASO` sample used by :func:`~easy_aso.runtime.runner.run_agent_class` defaults."""

from __future__ import annotations

import asyncio
import logging
import os

from easy_aso.runtime.rpc_docked import RpcDockedEasyASO

LOG = logging.getLogger("easy_aso.sample_agent")


class SampleAgent(RpcDockedEasyASO):
    """Sleeps between steps; optional demo read via ``EASY_ASO_DEMO_READ_DEVICE`` / ``EASY_ASO_DEMO_READ_OBJECT``."""

    async def on_start(self) -> None:
        LOG.info("SampleAgent on_start")

    async def on_step(self) -> None:
        sec = float(os.environ.get("EASY_ASO_STEP_SEC", "30"))
        addr = os.environ.get("EASY_ASO_DEMO_READ_DEVICE", "").strip()
        obj = os.environ.get("EASY_ASO_DEMO_READ_OBJECT", "").strip()
        if addr and obj:
            val = await self.bacnet_read(addr, obj)
            LOG.info("demo read %s %s -> %s", addr, obj, val)
        # Lower bound keeps tests responsive when EASY_ASO_STEP_SEC is small.
        await asyncio.sleep(max(0.05, sec))

    async def on_stop(self) -> None:
        LOG.info("SampleAgent on_stop")
        await self.close_rpc_dock()
