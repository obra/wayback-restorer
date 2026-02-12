"""Command line entrypoint for mirror recovery operations."""

from __future__ import annotations

import argparse
from typing import Sequence


def _add_subcommands(parser: argparse.ArgumentParser) -> None:
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True

    for name in ("discover", "recover", "report", "run"):
        subparsers.add_parser(name)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sp-recovery")
    _add_subcommands(parser)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    parser.parse_args(argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
