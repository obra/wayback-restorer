import subprocess
import sys


def test_cli_help_lists_expected_subcommands() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "sp_recovery.cli", "--help"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    for command in ("discover", "recover", "report", "run"):
        assert command in result.stdout
