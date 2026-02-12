import subprocess
import sys

from sp_recovery.cli import _config_from_args, build_parser


def test_cli_help_lists_expected_subcommands() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "sp_recovery.cli", "--help"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    for command in ("discover", "recover", "report", "run"):
        assert command in result.stdout


def test_cli_host_equivalence_defaults_follow_domain() -> None:
    parser = build_parser()
    args = parser.parse_args(["run", "--domain", "example.org"])
    config = _config_from_args(args)

    assert config.canonical_host == "example.org"
    assert config.equivalent_hosts == frozenset({"example.org", "www.example.org"})


def test_cli_host_equivalence_can_be_set_explicitly() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "run",
            "--domain",
            "example.org",
            "--canonical-host",
            "mirror.example.org",
            "--equivalent-host",
            "example.org",
            "--equivalent-host",
            "www.example.org",
        ]
    )
    config = _config_from_args(args)

    assert config.canonical_host == "mirror.example.org"
    assert config.equivalent_hosts == frozenset(
        {"mirror.example.org", "example.org", "www.example.org"}
    )
