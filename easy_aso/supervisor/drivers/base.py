from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, Mapping, Sequence

from easy_aso.supervisor.store.models import Device, Point


@dataclass(slots=True)
class ReadBatchResult:
    """Point id -> decoded value or error message from one poll cycle."""

    values: Dict[str, Any] = field(default_factory=dict)
    errors: Dict[str, str] = field(default_factory=dict)


class BaseDriver(ABC):
    """Async driver: one instance per poll ownership boundary (typically per device)."""

    DRIVER_TYPE: ClassVar[str] = "base"

    @abstractmethod
    async def close(self) -> None:
        """Release network/clients."""

    @abstractmethod
    async def read_points(self, device: Device, points: Sequence[Point]) -> ReadBatchResult:
        """Read all requested points (subset may be skipped if disabled upstream)."""
