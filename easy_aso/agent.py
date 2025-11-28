"""
Agent base classes and management for the easy‑aso framework.

Inspired by the VOLTTRON agent model, this module defines an
asynchronous base class for control agents and an agent manager to
coordinate their lifecycle.  Agents encapsulate a single piece of
control logic and interact with a BACnet client to read and write
properties.  Each agent implements three lifecycle hooks:

* ``on_start()`` – called once before the agent begins its update loop
* ``on_update()`` – called repeatedly at a fixed interval
* ``on_stop()`` – called once when the agent is shutting down

Agents run in their own asyncio tasks and may perform arbitrary
asynchronous I/O.  The agent manager can run multiple agents
concurrently.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Awaitable, Callable, Iterable, List, Optional


class Agent(ABC):
    """Abstract base class for easy‑aso control agents.

    Subclasses must implement the asynchronous lifecycle methods
    ``on_start``, ``on_update`` and ``on_stop``.  The default
    ``run()`` method will call ``on_start()``, then repeatedly call
    ``on_update()`` every ``update_interval`` seconds until the agent
    is cancelled, and finally call ``on_stop()`` to release any
    resources.
    """

    def __init__(self, update_interval: float = 60.0) -> None:
        self.update_interval = update_interval
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None

    @abstractmethod
    async def on_start(self) -> None:
        """Hook called once before updates begin."""
        raise NotImplementedError

    @abstractmethod
    async def on_update(self) -> None:
        """Hook called at each update interval."""
        raise NotImplementedError

    @abstractmethod
    async def on_stop(self) -> None:
        """Hook called once when the agent is stopping."""
        raise NotImplementedError

    async def run(self) -> None:
        """Run the agent until cancelled.

        This method wraps the lifecycle hooks and schedules periodic
        execution of ``on_update()``.  It may be scheduled as an
        asyncio task by the agent manager.
        """
        self._running = True
        try:
            await self.on_start()
            while self._running:
                await self.on_update()
                await asyncio.sleep(self.update_interval)
        except asyncio.CancelledError:
            # Propagate cancellations to allow graceful shutdown
            raise
        finally:
            self._running = False
            await self.on_stop()

    def stop(self) -> None:
        """Request the agent to stop and cancel the update loop."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()


class AgentManager:
    """Coordinator for managing the lifecycle of multiple agents.

    The agent manager accepts a collection of agent instances and
    schedules them to run concurrently.  It exposes asynchronous
    methods to start all agents and to stop them.  Agents are
    cancelled when the manager is stopped.
    """

    def __init__(self, agents: Iterable[Agent]) -> None:
        self.agents: List[Agent] = list(agents)
        self._tasks: List[asyncio.Task] = []

    async def start_all(self) -> None:
        """Start all agents concurrently.

        Schedules the ``run()`` coroutine of each agent as an asyncio
        task.  Returns when all agents have been started.
        """
        for agent in self.agents:
            task = asyncio.create_task(agent.run())
            agent._task = task  # expose the task on the agent for control
            self._tasks.append(task)

    async def stop_all(self) -> None:
        """Stop all agents and wait for their tasks to finish."""
        for agent in self.agents:
            agent.stop()
        # Wait for all tasks to finish
        await asyncio.gather(*self._tasks, return_exceptions=True)

    async def run_forever(self) -> None:
        """Run all agents until cancelled.

        This convenience method starts all agents and awaits the
        completion of their tasks.  It will exit when all agents have
        stopped or when cancelled via ``asyncio.CancelledError``.
        """
        await self.start_all()
        try:
            await asyncio.gather(*self._tasks)
        except asyncio.CancelledError:
            # Stop agents gracefully on cancellation
            await self.stop_all()
            raise