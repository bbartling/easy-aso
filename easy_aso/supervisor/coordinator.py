from __future__ import annotations

import logging
from typing import Any, List, Optional

from easy_aso.supervisor.runtime.registry import SupervisorRuntime
from easy_aso.supervisor.store.models import Device, Point
from easy_aso.supervisor.store.repository import SupervisorRepository

logger = logging.getLogger(__name__)


class SupervisorCoordinator:
    """Application service: CRUD + hot reload hooks into the runtime."""

    def __init__(self, repo: SupervisorRepository, runtime: SupervisorRuntime) -> None:
        self._repo = repo
        self._runtime = runtime

    @property
    def repository(self) -> SupervisorRepository:
        return self._repo

    @property
    def runtime(self) -> SupervisorRuntime:
        return self._runtime

    async def create_device(
        self,
        *,
        name: str,
        driver_type: str,
        device_address: str,
        rpc_base_url: Optional[str] = None,
        rpc_entrypoint: Optional[str] = None,
        scrape_interval_seconds: float = 5.0,
        enabled: bool = False,
        device_id: Optional[str] = None,
    ) -> Device:
        d = await self._repo.create_device(
            name=name,
            driver_type=driver_type,
            device_address=device_address,
            rpc_base_url=rpc_base_url,
            rpc_entrypoint=rpc_entrypoint,
            scrape_interval_seconds=scrape_interval_seconds,
            enabled=enabled,
            device_id=device_id,
        )
        logger.info("device created id=%s name=%s enabled=%s", d.id, d.name, d.enabled)
        await self._runtime.reload_device(d.id)
        return d

    async def update_device_fields(self, device_id: str, fields: dict[str, Any]) -> Optional[Device]:
        d = await self._repo.update_device_fields(device_id, fields)
        if d is None:
            logger.warning("device update skipped: not found id=%s", device_id)
            return None
        logger.info("device updated id=%s enabled=%s interval=%s", d.id, d.enabled, d.scrape_interval_seconds)
        await self._runtime.reload_device(device_id)
        return d

    async def delete_device(self, device_id: str) -> bool:
        await self._runtime.cancel_device(device_id)
        ok = await self._repo.delete_device(device_id)
        logger.info("device deleted id=%s ok=%s", device_id, ok)
        return ok

    async def create_point(
        self,
        device_id: str,
        *,
        name: str = "",
        object_identifier: str,
        property_identifier: str = "present-value",
        enabled: bool = True,
        point_id: Optional[str] = None,
    ) -> Point:
        p = await self._repo.create_point(
            device_id,
            name=name,
            object_identifier=object_identifier,
            property_identifier=property_identifier,
            enabled=enabled,
            point_id=point_id,
        )
        logger.info("point created id=%s device_id=%s", p.id, device_id)
        await self._runtime.reload_device(device_id)
        return p

    async def update_point_fields(self, point_id: str, fields: dict[str, Any]) -> Optional[Point]:
        cur = await self._repo.get_point(point_id)
        if cur is None:
            logger.warning("point update skipped: not found id=%s", point_id)
            return None
        p = await self._repo.update_point_fields(point_id, fields)
        logger.info("point updated id=%s device_id=%s", point_id, cur.device_id)
        await self._runtime.reload_device(cur.device_id)
        return p

    async def delete_point(self, point_id: str) -> bool:
        cur = await self._repo.get_point(point_id)
        ok = await self._repo.delete_point(point_id)
        if cur is not None:
            logger.info("point deleted id=%s device_id=%s ok=%s", point_id, cur.device_id, ok)
            await self._runtime.reload_device(cur.device_id)
        return ok

    async def list_devices(self, *, enabled_only: bool = False) -> List[Device]:
        return await self._repo.list_devices(enabled_only=enabled_only)

    async def get_device(self, device_id: str) -> Optional[Device]:
        return await self._repo.get_device(device_id)

    async def list_points(self, device_id: str, *, enabled_only: bool = False) -> List[Point]:
        return await self._repo.list_points(device_id, enabled_only=enabled_only)

    async def get_point(self, point_id: str) -> Optional[Point]:
        return await self._repo.get_point(point_id)
