from __future__ import annotations

from typing import Any, List

import fastapi_jsonrpc as jsonrpc
from pydantic import BaseModel

from easy_aso.supervisor.api import schemas
from easy_aso.supervisor.coordinator import SupervisorCoordinator
from easy_aso.supervisor.runtime.registry import DeviceHealth

_APP = None


def set_supervisor_rpc_app(app) -> None:
    global _APP
    _APP = app


def _coord() -> SupervisorCoordinator:
    if _APP is None:
        raise RuntimeError("supervisor rpc app is not initialized")
    return _APP.state.coordinator


def _runtime():
    if _APP is None:
        raise RuntimeError("supervisor rpc app is not initialized")
    return _APP.state.runtime


def _device_to_dict(d: Any) -> dict:
    return {
        "id": d.id,
        "name": d.name,
        "driver_type": d.driver_type,
        "device_address": d.device_address,
        "rpc_base_url": d.rpc_base_url,
        "rpc_entrypoint": d.rpc_entrypoint,
        "scrape_interval_seconds": d.scrape_interval_seconds,
        "enabled": d.enabled,
        "created_at": d.created_at,
        "updated_at": d.updated_at,
    }


def _point_to_dict(p: Any) -> dict:
    return {
        "id": p.id,
        "device_id": p.device_id,
        "name": p.name,
        "object_identifier": p.object_identifier,
        "property_identifier": p.property_identifier,
        "enabled": p.enabled,
        "last_value": p.decoded_value(),
        "last_polled_at": p.last_polled_at,
        "last_error": p.last_error,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
    }


class DeviceById(BaseModel):
    device_id: str


class PointById(BaseModel):
    point_id: str


class DeviceListQuery(BaseModel):
    enabled_only: bool = False


class DeviceGet(BaseModel):
    device_id: str


class DevicePatch(BaseModel):
    device_id: str
    payload: schemas.DeviceUpdate


class DeviceDelete(BaseModel):
    device_id: str


class PointListQuery(BaseModel):
    device_id: str
    enabled_only: bool = False


class PointCreateReq(BaseModel):
    device_id: str
    payload: schemas.PointCreate


class PointPatchReq(BaseModel):
    point_id: str
    payload: schemas.PointUpdate


class PointDeleteReq(BaseModel):
    point_id: str


def create_supervisor_rpc_entrypoint() -> jsonrpc.Entrypoint:
    rpc = jsonrpc.Entrypoint("/api")

    @rpc.method()
    def server_hello() -> dict:
        return {"message": "easy-aso supervisor JSON-RPC API ready. Use /docs to test."}

    @rpc.method()
    async def supervisor_list_devices(query: DeviceListQuery) -> List[dict]:
        devices = await _coord().list_devices(enabled_only=query.enabled_only)
        return [_device_to_dict(d) for d in devices]

    @rpc.method()
    async def supervisor_create_device(payload: schemas.DeviceCreate) -> dict:
        d = await _coord().create_device(**payload.model_dump())
        return _device_to_dict(d)

    @rpc.method()
    async def supervisor_get_device(req: DeviceGet) -> dict:
        d = await _coord().get_device(req.device_id)
        if d is None:
            raise ValueError("device not found")
        return _device_to_dict(d)

    @rpc.method()
    async def supervisor_patch_device(req: DevicePatch) -> dict:
        payload = {k: v for k, v in req.payload.model_dump(exclude_unset=True).items()}
        if not payload:
            d = await _coord().get_device(req.device_id)
            if d is None:
                raise ValueError("device not found")
            return _device_to_dict(d)
        d = await _coord().update_device_fields(req.device_id, payload)
        if d is None:
            raise ValueError("device not found")
        return _device_to_dict(d)

    @rpc.method()
    async def supervisor_delete_device(req: DeviceDelete) -> dict:
        ok = await _coord().delete_device(req.device_id)
        if not ok:
            raise ValueError("device not found")
        return {"deleted": True, "id": req.device_id}

    @rpc.method()
    async def supervisor_list_points(query: PointListQuery) -> List[dict]:
        if await _coord().get_device(query.device_id) is None:
            raise ValueError("device not found")
        pts = await _coord().list_points(query.device_id, enabled_only=query.enabled_only)
        return [_point_to_dict(p) for p in pts]

    @rpc.method()
    async def supervisor_create_point(req: PointCreateReq) -> dict:
        if await _coord().get_device(req.device_id) is None:
            raise ValueError("device not found")
        p = await _coord().create_point(req.device_id, **req.payload.model_dump())
        return _point_to_dict(p)

    @rpc.method()
    async def supervisor_patch_point(req: PointPatchReq) -> dict:
        payload = {k: v for k, v in req.payload.model_dump(exclude_unset=True).items()}
        if not payload:
            p = await _coord().get_point(req.point_id)
            if p is None:
                raise ValueError("point not found")
            return _point_to_dict(p)
        p = await _coord().update_point_fields(req.point_id, payload)
        if p is None:
            raise ValueError("point not found")
        return _point_to_dict(p)

    @rpc.method()
    async def supervisor_delete_point(req: PointDeleteReq) -> dict:
        ok = await _coord().delete_point(req.point_id)
        if not ok:
            raise ValueError("point not found")
        return {"deleted": True, "id": req.point_id}

    @rpc.method()
    async def supervisor_device_health(req: DeviceById) -> schemas.DeviceHealthOut:
        h: DeviceHealth | None = _runtime().device_health(req.device_id)
        if h is None:
            d = await _coord().get_device(req.device_id)
            if d is None:
                raise ValueError("device not found")
            return schemas.DeviceHealthOut(device_id=req.device_id, status="idle", last_poll_at=None, last_error=None)
        return schemas.DeviceHealthOut(
            device_id=h.device_id,
            status=h.status,
            last_poll_at=h.last_poll_at,
            last_error=h.last_error,
        )

    @rpc.method()
    async def supervisor_latest_values(req: DeviceById) -> List[schemas.PointLatestOut]:
        if await _coord().get_device(req.device_id) is None:
            raise ValueError("device not found")
        pts = await _coord().list_points(req.device_id, enabled_only=False)
        out: List[schemas.PointLatestOut] = []
        for p in pts:
            out.append(
                schemas.PointLatestOut(
                    point_id=p.id,
                    device_id=p.device_id,
                    name=p.name,
                    object_identifier=p.object_identifier,
                    property_identifier=p.property_identifier,
                    enabled=p.enabled,
                    last_value=p.decoded_value(),
                    last_polled_at=p.last_polled_at,
                    last_error=p.last_error,
                )
            )
        return out

    @rpc.method()
    async def supervisor_point_latest(req: PointById) -> schemas.PointLatestOut:
        p = await _coord().get_point(req.point_id)
        if p is None:
            raise ValueError("point not found")
        return schemas.PointLatestOut(
            point_id=p.id,
            device_id=p.device_id,
            name=p.name,
            object_identifier=p.object_identifier,
            property_identifier=p.property_identifier,
            enabled=p.enabled,
            last_value=p.decoded_value(),
            last_polled_at=p.last_polled_at,
            last_error=p.last_error,
        )

    return rpc
