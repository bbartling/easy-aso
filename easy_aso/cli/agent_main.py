"""``easy-aso-agent`` CLI: run an EasyASO subclass from module:class or env."""

from __future__ import annotations

import argparse
import logging
import sys


def main(argv: list[str] | None = None) -> None:
    argv = argv if argv is not None else sys.argv[1:]
    epilog = (
        "Environment: EASY_ASO_AGENT_MODULE, EASY_ASO_AGENT_CLASS, "
        "SUPERVISOR_BACNET_RPC_URL, SUPERVISOR_BACNET_RPC_ENTRYPOINT, BACNET_RPC_API_KEY. "
        "See docs/MULTI_AGENT_RPC_DOCKED.md."
    )
    parser = argparse.ArgumentParser(
        prog="easy-aso-agent",
        description="Run an EasyASO agent process.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run agent lifecycle (on_start / on_step / on_stop).")
    run_p.add_argument(
        "--module",
        "-m",
        default=None,
        help="Dotted module path (default: EASY_ASO_AGENT_MODULE or easy_aso.runtime.sample_agent).",
    )
    run_p.add_argument(
        "--class",
        dest="class_name",
        default=None,
        help="Class name (default: EASY_ASO_AGENT_CLASS or SampleAgent).",
    )
    run_p.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Root logging level.",
    )

    args = parser.parse_args(argv)
    if args.command == "run":
        logging.basicConfig(
            level=getattr(logging, args.log_level),
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
        from easy_aso.runtime.runner import run_agent_class

        run_agent_class(module=args.module, class_name=args.class_name)


if __name__ == "__main__":
    main()
