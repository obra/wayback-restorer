"""Command line entrypoint for mirror recovery operations."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from sp_recovery.config import (
    DEFAULT_DOMAIN,
    DEFAULT_FROM_DATE,
    DEFAULT_MODERN_CUTOFF_DATE,
    DEFAULT_TO_DATE,
    RecoveryConfig,
    default_equivalent_hosts,
    load_missing_urls_from_gap_csv,
    normalize_equivalent_hosts,
)
from sp_recovery.discovery import capture_from_dict, capture_to_dict
from sp_recovery.io_utils import read_jsonl, write_jsonl
from sp_recovery.pipeline import (
    discover_phase,
    recover_phase,
    run_pipeline,
    run_report_only,
)
from sp_recovery.rewrite import rewrite_recovered_html_files
from sp_recovery.url_utils import canonical_identity_key


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--domain", default=DEFAULT_DOMAIN)
    parser.add_argument("--from-date", default=DEFAULT_FROM_DATE)
    parser.add_argument("--to-date", default=DEFAULT_TO_DATE)
    parser.add_argument(
        "--modern-cutoff-date",
        default=DEFAULT_MODERN_CUTOFF_DATE,
        help="Exclude captures on/after this date (YYYY-MM-DD).",
    )
    parser.add_argument("--output-root", default="output/mirror")
    parser.add_argument("--max-canonical", type=int, default=0)
    parser.add_argument("--request-interval-seconds", type=float, default=2.0)
    parser.add_argument(
        "--canonical-host",
        default=None,
        help="Canonical host to use in mirror paths and rewritten internal URLs.",
    )
    parser.add_argument(
        "--equivalent-host",
        action="append",
        default=[],
        help="Additional host to treat as equivalent to canonical host (repeatable).",
    )
    parser.add_argument(
        "--only-missing-from",
        type=Path,
        default=None,
        help="CSV file with original_url column (typically gap_register.csv)",
    )


def _config_from_args(args: argparse.Namespace) -> RecoveryConfig:
    canonical_host = args.canonical_host or args.domain
    if args.equivalent_host:
        equivalent_hosts = normalize_equivalent_hosts(args.equivalent_host)
    else:
        equivalent_hosts = default_equivalent_hosts(canonical_host)

    return RecoveryConfig(
        domain=args.domain,
        from_date=args.from_date,
        to_date=args.to_date,
        modern_cutoff_date=args.modern_cutoff_date,
        output_root=Path(args.output_root),
        max_canonical=max(args.max_canonical, 0),
        request_interval_seconds=max(args.request_interval_seconds, 0.0),
        only_missing_urls=load_missing_urls_from_gap_csv(args.only_missing_from),
        canonical_host=canonical_host,
        equivalent_hosts=equivalent_hosts,
    )


def _discover_command(args: argparse.Namespace) -> int:
    config = _config_from_args(args)
    discovered, canonical = discover_phase(config)

    state_dir = config.output_root / "state"
    write_jsonl(state_dir / "discovered_captures.jsonl", [capture_to_dict(row) for row in discovered])
    write_jsonl(state_dir / "canonical_urls.jsonl", [capture_to_dict(row) for row in canonical])

    print(f"Discovered captures: {len(discovered)}")
    print(f"Canonical URLs: {len(canonical)}")
    return 0


def _recover_command(args: argparse.Namespace) -> int:
    config = _config_from_args(args)
    state_dir = config.output_root / "state"

    canonical_rows = read_jsonl(state_dir / "canonical_urls.jsonl")
    canonical_records = [capture_from_dict(row) for row in canonical_rows]
    if config.only_missing_urls:
        missing_keys = {
            canonical_identity_key(
                url,
                canonical_host=config.canonical_host,
                equivalent_hosts=config.equivalent_hosts,
            )
            for url in config.only_missing_urls
        }
        canonical_records = [
            row
            for row in canonical_records
            if canonical_identity_key(
                row.original,
                canonical_host=config.canonical_host,
                equivalent_hosts=config.equivalent_hosts,
            )
            in missing_keys
        ]

    recovered = recover_phase(config, canonical_records)
    write_jsonl(state_dir / "provenance.jsonl", [row.as_dict() for row in recovered])

    rewrite_recovered_html_files(
        config.output_root,
        recovered,
        unresolved_csv_path=state_dir / "unresolved_links.csv",
        canonical_host=config.canonical_host,
        equivalent_hosts=config.equivalent_hosts,
    )

    print(f"Recovered artifacts: {len(recovered)}")
    return 0


def _report_command(args: argparse.Namespace) -> int:
    config = _config_from_args(args)
    run_report_only(config)
    print("Reports written")
    return 0


def _run_command(args: argparse.Namespace) -> int:
    config = _config_from_args(args)
    result = run_pipeline(config)

    print(f"Discovered captures: {result.discovered_count}")
    print(f"Canonical URLs selected: {result.canonical_count}")
    print(f"Recovered artifacts: {result.recovered_count}")
    return 0


def _add_subcommands(parser: argparse.ArgumentParser) -> None:
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True

    discover = subparsers.add_parser("discover")
    _add_common_args(discover)
    discover.set_defaults(handler=_discover_command)

    recover = subparsers.add_parser("recover")
    _add_common_args(recover)
    recover.set_defaults(handler=_recover_command)

    report = subparsers.add_parser("report")
    _add_common_args(report)
    report.set_defaults(handler=_report_command)

    run = subparsers.add_parser("run")
    _add_common_args(run)
    run.set_defaults(handler=_run_command)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sp-recovery")
    _add_subcommands(parser)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
