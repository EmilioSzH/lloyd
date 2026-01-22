"""Tests for the Lloyd CLI."""

from click.testing import CliRunner

from lloyd.main import cli


def test_cli_without_command() -> None:
    """Test that CLI runs without a command and shows welcome message."""
    runner = CliRunner()
    result = runner.invoke(cli)
    assert result.exit_code == 0
    assert "Lloyd" in result.output
    assert "initialized" in result.output


def test_cli_version() -> None:
    """Test that CLI shows version."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_cli_status() -> None:
    """Test the status command."""
    runner = CliRunner()
    result = runner.invoke(cli, ["status"])
    # Should work even without a prd.json (will show warning)
    assert result.exit_code == 0


def test_cli_init() -> None:
    """Test the init command."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["init"])
        assert result.exit_code == 0
        assert "initialized successfully" in result.output


def test_cli_help() -> None:
    """Test the help command."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Lloyd" in result.output
    assert "idea" in result.output
    assert "status" in result.output
