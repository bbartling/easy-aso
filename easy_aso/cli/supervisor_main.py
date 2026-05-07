"""``easy-aso-supervisor`` CLI: run supervisor with Open-FDD-safe defaults."""

from __future__ import annotations

import argparse
import os
import sys


def main(argv: list[str] | None = None) -> None:
    argv = argv if argv is not None else sys.argv[1:]
    default_port = int(os.environ.get("SUPERVISOR_PORT", "18090"))
    parser = argparse.ArgumentParser(
        prog="easy-aso-supervisor",
        description="Run easy-aso supervisor JSON-RPC API.",
    )
    parser.add_argument("--host", default=os.environ.get("SUPERVISOR_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=default_port)
    parser.add_argument("--reload", action="store_true", help="Enable uvicorn autoreload.")
    parser.add_argument(
        "--log-level",
        default=os.environ.get("SUPERVISOR_LOG_LEVEL", "info"),
        choices=["critical", "error", "warning", "info", "debug", "trace"],
    )
    args = parser.parse_args(argv)

    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover - user environment issue
        raise SystemExit(
            "uvicorn is required for easy-aso-supervisor. Install easy-aso with platform extras: "
            "pip install 'easy-aso[platform]'",
        ) from exc

    uvicorn.run(
        "easy_aso.supervisor.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    main()
