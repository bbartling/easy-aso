from __future__ import annotations

from typing import Any, List

from fastapi import APIRouter, HTTPException, Request

from easy_aso.supervisor.api import schemas
from easy_aso.supervisor.coordinator import SupervisorCoordinator
from easy_aso.supervisor.runtime.registry import DeviceHealth

router = APIRouter(tags=["supervisor"])


def _coord(request: Request) -> SupervisorCoordinator:
    return request.app.state.coordinator


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


@router.get("/health")
async def supervisor_health(request: Request) -> dict:
    rt = request.app.state.runtime
    return {"status": "ok", "running_devices": len(rt.health_snapshot())}


@router.get("/devices", response_model=List[dict])
async def list_devices(request: Request, enabled_only: bool = False) -> List[dict]:
    devices = await _coord(request).list_devices(enabled_only=enabled_only)
    return [_device_to_dict(d) for d in devices]


@router.post("/devices", response_model=dict)
async def create_device(request: Request, body: schemas.DeviceCreate) -> dict:
    d = await _coord(request).create_device(**body.model_dump())
    return _device_to_dict(d)


@router.get("/devices/{device_id}", response_model=dict)
async def get_device(request: Request, device_id: str) -> dict:
    d = await _coord(request).get_device(device_id)
    if d is None:
        raise HTTPException(status_code=404, detail="device not found")
    return _device_to_dict(d)


@router.patch("/devices/{device_id}", response_model=dict)
async def patch_device(request: Request, device_id: str, body: schemas.DeviceUpdate) -> dict:
    payload = {k: v for k, v in body.model_dump(exclude_unset=True).items()}
    if not payload:
        d = await _coord(request).get_device(device_id)
        if d is None:
            raise HTTPException(status_code=404, detail="device not found")
        return _device_to_dict(d)
    d = await _coord(request).update_device_fields(device_id, payload)
    if d is None:
        raise HTTPException(status_code=404, detail="device not found")
    return _device_to_dict(d)


@router.delete("/devices/{device_id}")
async def delete_device(request: Request, device_id: str) -> dict:
    ok = await _coord(request).delete_device(device_id)
    if not ok:
        raise HTTPException(status_code=404, detail="device not found")
    return {"deleted": True, "id": device_id}


@router.get("/devices/{device_id}/points", response_model=List[dict])
async def list_points(
    request: Request,
    device_id: str,
    enabled_only: bool = False,
) -> List[dict]:
    if await _coord(request).get_device(device_id) is None:
        raise HTTPException(status_code=404, detail="device not found")
    pts = await _coord(request).list_points(device_id, enabled_only=enabled_only)
    return [_point_to_dict(p) for p in pts]


@router.post("/devices/{device_id}/points", response_model=dict)
async def create_point(request: Request, device_id: str, body: schemas.PointCreate) -> dict:
    if await _coord(request).get_device(device_id) is None:
        raise HTTPException(status_code=404, detail="device not found")
    p = await _coord(request).create_point(device_id, **body.model_dump())
    return _point_to_dict(p)


@router.patch("/points/{point_id}", response_model=dict)
async def patch_point(request: Request, point_id: str, body: schemas.PointUpdate) -> dict:
    payload = {k: v for k, v in body.model_dump(exclude_unset=True).items()}
    if not payload:
        p = await _coord(request).get_point(point_id)
        if p is None:
            raise HTTPException(status_code=404, detail="point not found")
        return _point_to_dict(p)
    p = await _coord(request).update_point_fields(point_id, payload)
    if p is None:
        raise HTTPException(status_code=404, detail="point not found")
    return _point_to_dict(p)


@router.delete("/points/{point_id}")
async def delete_point(request: Request, point_id: str) -> dict:
    ok = await _coord(request).delete_point(point_id)
    if not ok:
        raise HTTPException(status_code=404, detail="point not found")
    return {"deleted": True, "id": point_id}


@router.get("/devices/{device_id}/health", response_model=schemas.DeviceHealthOut)
async def device_health(request: Request, device_id: str) -> schemas.DeviceHealthOut:
    h: DeviceHealth | None = request.app.state.runtime.device_health(device_id)
    if h is None:
        # device may exist but be disabled / never polled
        d = await _coord(request).get_device(device_id)
        if d is None:
            raise HTTPException(status_code=404, detail="device not found")
        return schemas.DeviceHealthOut(device_id=device_id, status="idle", last_poll_at=None, last_error=None)
    return schemas.DeviceHealthOut(
        device_id=h.device_id,
        status=h.status,
        last_poll_at=h.last_poll_at,
        last_error=h.last_error,
    )


@router.get("/devices/{device_id}/latest-values", response_model=List[schemas.PointLatestOut])
async def latest_values(request: Request, device_id: str) -> List[schemas.PointLatestOut]:
    if await _coord(request).get_device(device_id) is None:
        raise HTTPException(status_code=404, detail="device not found")
    pts = await _coord(request).list_points(device_id, enabled_only=False)
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


@router.get("/points/{point_id}/latest", response_model=schemas.PointLatestOut)
async def point_latest(request: Request, point_id: str) -> schemas.PointLatestOut:
    p = await _coord(request).get_point(point_id)
    if p is None:
        raise HTTPException(status_code=404, detail="point not found")
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
