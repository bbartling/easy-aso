"""easy-aso library package (install with ``pip install -e .`` from repo root)."""

from importlib.metadata import PackageNotFoundError, version

from easy_aso.easy_aso import EasyASO
from easy_aso.runtime import (
    BacnetRpcConfig,
    RpcDockedEasyASO,
    load_rpc_config_from_env,
    run_agent_class,
)

try:
    __version__ = version("easy-aso")
except PackageNotFoundError:  # pragma: no cover - editable checkout without install
    __version__ = "0.dev0"

__all__ = [
    "BacnetRpcConfig",
    "EasyASO",
    "RpcDockedEasyASO",
    "__version__",
    "load_rpc_config_from_env",
    "run_agent_class",
]
