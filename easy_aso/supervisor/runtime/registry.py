from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional

from easy_aso.supervisor.drivers.factory import create_driver
from easy_aso.supervisor.store.repository import SupervisorRepository

from .poller import run_one_poll

logger = logging.getLogger(__name__)


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class DeviceHealth:
    device_id: str
    status: str = "idle"  # idle | running | error | stopped
    last_poll_at: Optional[str] = None
    last_error: Optional[str] = None


class SupervisorRuntime:
    """Owns per-device asyncio tasks, health, and hot reload."""

    def __init__(self, repo: SupervisorRepository) -> None:
        self._repo = repo
        self._tasks: Dict[str, asyncio.Task[None]] = {}
        self._health: Dict[str, DeviceHealth] = {}
        self._lock = asyncio.Lock()

    def health_snapshot(self) -> Dict[str, DeviceHealth]:
        return dict(self._health)

    def device_health(self, device_id: str) -> Optional[DeviceHealth]:
        return self._health.get(device_id)

    async def start(self) -> None:
        devices = await self._repo.list_devices(enabled_only=True)
        logger.info("SupervisorRuntime.start: spawning %d enabled device(s)", len(devices))
        for d in devices:
            await self.spawn_device(d.id)

    async def stop(self) -> None:
        ids = list(self._tasks.keys())
        logger.info("SupervisorRuntime.stop: cancelling %d task(s)", len(ids))
        for device_id in ids:
            await self.cancel_device(device_id)
        self._health.clear()

    async def spawn_device(self, device_id: str) -> None:
        async with self._lock:
            if device_id in self._tasks:
                logger.debug("spawn_device: task already running device_id=%s", device_id)
                return
            self._health[device_id] = DeviceHealth(device_id=device_id, status="running")
            self._tasks[device_id] = asyncio.create_task(
                self._device_task_wrapper(device_id),
                name=f"easy-aso-supervisor:{device_id}",
            )
            logger.info("spawn_device: created task device_id=%s", device_id)

    async def cancel_device(self, device_id: str) -> None:
        async with self._lock:
            task = self._tasks.pop(device_id, None)
        if task is None:
            return
        if not task.done():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        h = self._health.get(device_id)
        if h:
            h.status = "stopped"
        logger.info("cancel_device: joined task device_id=%s", device_id)

    async def reload_device(self, device_id: str) -> None:
        """Cancel and respawn a device task from DB (config hot reload)."""
        logger.info("reload_device: begin device_id=%s", device_id)
        await self.cancel_device(device_id)
        dev = await self._repo.get_device(device_id)
        if dev is not None and dev.enabled:
            await self.spawn_device(device_id)
            logger.info("reload_device: respawned enabled device_id=%s", device_id)
        else:
            self._health.pop(device_id, None)
            logger.info("reload_device: device disabled or removed device_id=%s", device_id)

    async def _device_task_wrapper(self, device_id: str) -> None:
        try:
            await self._device_poll_loop(device_id)
        finally:
            async with self._lock:
                self._tasks.pop(device_id, None)

    async def _device_poll_loop(self, device_id: str) -> None:
        try:
            while True:
                device = await self._repo.get_device(device_id)
                if device is None or not device.enabled:
                    logger.info("poll loop exit: disabled or missing device_id=%s", device_id)
                    self._health.pop(device_id, None)
                    return

                h = self._health.setdefault(device_id, DeviceHealth(device_id=device_id))
                h.status = "running"
                h.last_error = None

                driver = create_driver(device)
                try:
                    batch, points = await run_one_poll(self._repo, device, driver)
                    h.last_poll_at = _utc_iso()
                    if batch.errors:
                        h.status = "error"
                        h.last_error = "; ".join(f"{k}: {v}" for k, v in batch.errors.items())
                    else:
                        h.status = "running"
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    logger.exception("poll loop error device_id=%s", device_id)
                    h.status = "error"
                    h.last_error = str(exc)
                    h.last_poll_at = _utc_iso()
                finally:
                    await driver.close()

                device = await self._repo.get_device(device_id)
                if device is None or not device.enabled:
                    logger.info("poll loop exit after iteration: device_id=%s", device_id)
                    self._health.pop(device_id, None)
                    return
                await asyncio.sleep(max(0.5, float(device.scrape_interval_seconds)))
        except asyncio.CancelledError:
            logger.info("poll loop cancelled device_id=%s", device_id)
            raise
