"""Load an ``EasyASO`` subclass by module/name and run ``asyncio.run(agent.run())``."""

from __future__ import annotations

import asyncio
import importlib
import os
import sys
from typing import Optional


def run_agent_class(
    module: Optional[str] = None,
    class_name: Optional[str] = None,
    *,
    no_bacnet_server: bool = True,
) -> None:
    """
    Instantiate ``class_name`` from ``module`` and run the standard ``EasyASO`` lifecycle.

    If ``module`` / ``class_name`` are omitted, reads ``EASY_ASO_AGENT_MODULE`` and
    ``EASY_ASO_AGENT_CLASS`` from the environment (defaults: ``easy_aso.runtime.sample_agent``,
    ``SampleAgent``).

    When ``no_bacnet_server`` is true (default), ``sys.argv`` is forced to include
    ``--no-bacnet-server`` so :class:`~easy_aso.easy_aso.EasyASO` does not start a local BACnet server.
    """
    if no_bacnet_server:
        sys.argv = [sys.argv[0], "--no-bacnet-server"]

    mod_name = (module or os.environ.get("EASY_ASO_AGENT_MODULE", "easy_aso.runtime.sample_agent")).strip()
    cls_name = (class_name or os.environ.get("EASY_ASO_AGENT_CLASS", "SampleAgent")).strip()
    mod = importlib.import_module(mod_name)
    cls = getattr(mod, cls_name)
    agent = cls()
    asyncio.run(agent.run())
