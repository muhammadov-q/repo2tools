"""Tests for toolgym_local.py that need no ToolGym checkout."""

import pytest

from toolgym_local import patched


def test_patch_replaces_exactly_one_line():
    assert patched("a = 1\nb = 2\n", [("a = 1\n", "a = 5\n")], "file") == "a = 5\nb = 2\n"


@pytest.mark.parametrize("text", ["b = 2\n", "a = 1\na = 1\n"])
def test_patch_stops_if_the_line_is_missing_or_repeated(text):
    with pytest.raises(SystemExit, match="ToolGym has changed"):
        patched(text, [("a = 1\n", "a = 5\n")], "file")
