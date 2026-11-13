"""Tests for the `repo2tools` command: every command leads to a module with a main()."""

import importlib

import pytest

from repo2tools import __version__, cli


@pytest.mark.parametrize("command, module", sorted(cli.MODULES.items()))
def test_every_command_has_a_main(command, module):
    assert callable(importlib.import_module(module).main)


def test_help_lists_every_command(capsys):
    cli.main([])
    shown = capsys.readouterr().out
    assert all(f"  {command} " in shown for command in cli.MODULES)


def test_version(capsys):
    cli.main(["--version"])
    assert capsys.readouterr().out.strip() == f"repo2tools {__version__}"


def test_unknown_command_is_refused():
    with pytest.raises(SystemExit) as stopped:
        cli.main(["no-such-command"])
    assert "unknown command 'no-such-command'" in str(stopped.value)


def test_a_command_gets_the_rest_of_the_arguments(monkeypatch, capsys):
    with pytest.raises(SystemExit) as stopped:  # argparse leaves after --help
        cli.main(["compare-runs", "--help"])
    assert stopped.value.code == 0 and "usage: repo2tools compare-runs" in capsys.readouterr().out
