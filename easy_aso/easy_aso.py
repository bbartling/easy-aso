"""
Legacy compatibility wrapper for EasyASO.

The original easy_aso.easy_aso module provided a monolithic EasyASO
abstract base class tightly coupled to the bacpypes3 library.  It
has been replaced by the more flexible :class:`easy_aso.agent.Agent` in
modern versions of easy‑aso.  This module simply re‑exports the
``EasyASO`` alias from ``easy_aso.__init__`` so that existing code
continues to import ``EasyASO`` from here without modification.
"""

from . import EasyASO  # type: ignore  # re-export for backwards compatibility

__all__ = ["EasyASO"]
