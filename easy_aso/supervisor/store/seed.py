from __future__ import annotations

from .repository import SupervisorRepository


async def ensure_seed_data(repo: SupervisorRepository) -> None:
    """Insert example device + points when the database is empty."""
    if await repo.device_count() > 0:
        return

    dev = await repo.create_device(
        name="Example VAV (disabled)",
        driver_type="stub",
        device_address="0",
        rpc_base_url=None,
        rpc_entrypoint=None,
        scrape_interval_seconds=5.0,
        enabled=False,
        device_id="seed-example-vav",
    )
    await repo.create_point(
        dev.id,
        name="Space temperature",
        object_identifier="analog-input,1",
        property_identifier="present-value",
        enabled=True,
        point_id="seed-point-space-temp",
    )
    await repo.create_point(
        dev.id,
        name="Occupancy",
        object_identifier="binary-value,1",
        property_identifier="present-value",
        enabled=True,
        point_id="seed-point-occ",
    )
