from __future__ import annotations

from datetime import datetime, timezone

from easy_aso.supervisor.drivers.base import BaseDriver, ReadBatchResult
from easy_aso.supervisor.store.models import Device, Point
from easy_aso.supervisor.store.repository import SupervisorRepository


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def persist_poll_results(
    repo: SupervisorRepository,
    points: list[Point],
    batch: ReadBatchResult,
) -> None:
    """Write RPM/read batch results to the points table."""
    now = _utc_iso()
    for p in points:
        if p.id in batch.errors:
            await repo.update_point_reading(p.id, value=None, polled_at=now, error=batch.errors[p.id])
        elif p.id in batch.values:
            await repo.update_point_reading(p.id, value=batch.values[p.id], polled_at=now, error=None)
        else:
            await repo.update_point_reading(
                p.id, value=None, polled_at=now, error="no reading returned for this point"
            )


async def run_one_poll(
    repo: SupervisorRepository,
    device: Device,
    driver: BaseDriver,
) -> tuple[ReadBatchResult, list[Point]]:
    points = await repo.list_points(device.id, enabled_only=True)
    if not points:
        return ReadBatchResult(), []
    batch = await driver.read_points(device, points)
    await persist_poll_results(repo, list(points), batch)
    return batch, list(points)
