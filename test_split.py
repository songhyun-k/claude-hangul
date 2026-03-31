#!/usr/bin/env python3
"""Unit tests for the DEL-sequence splitting logic."""

import os
import sys
import types

# Load claude-hangul as a module (it has no .py extension)
_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "claude-hangul")
mod = types.ModuleType("claude_hangul")
with open(_path) as f:
    exec(compile(f.read(), _path, "exec"), mod.__dict__)
split = mod.split_del_sequences


def test_del_plus_korean():
    """DEL + 가 (U+AC00) must be split."""
    data = b"\x7f\xea\xb0\x80"
    chunks = split(data)
    assert chunks == [b"\x7f", b"\xea\xb0\x80"], chunks


def test_del_alone():
    """Standalone DEL (normal backspace) must NOT be split."""
    assert split(b"\x7f") == [b"\x7f"]


def test_del_plus_ascii():
    """DEL + ASCII must NOT be split (Issue #1853 compat)."""
    assert split(b"\x7fhello") == [b"\x7fhello"]


def test_multi_composition():
    """가 → 간: DEL+가+DEL+간 produces 3 chunks."""
    data = b"\x7f\xea\xb0\x80\x7f\xea\xb0\x84"
    chunks = split(data)
    assert len(chunks) == 3
    assert chunks[0] == b"\x7f"
    assert chunks[1] == b"\xea\xb0\x80\x7f"  # 가 + next DEL
    assert chunks[2] == b"\xea\xb0\x84"  # 간


def test_pure_text():
    """Plain text must pass through unsplit."""
    data = "hello 세계".encode()
    assert split(data) == [data]


def test_del_at_end():
    """Trailing DEL (no following byte) must NOT be split."""
    assert split(b"abc\x7f") == [b"abc\x7f"]


def test_japanese():
    """DEL + Japanese hiragana あ (U+3042) must be split."""
    data = b"\x7f\xe3\x81\x82"
    chunks = split(data)
    assert chunks == [b"\x7f", b"\xe3\x81\x82"]


def test_chinese():
    """DEL + Chinese 中 (U+4E2D) must be split."""
    data = b"\x7f\xe4\xb8\xad"
    chunks = split(data)
    assert chunks == [b"\x7f", b"\xe4\xb8\xad"]


def test_empty():
    """Empty input."""
    assert split(b"") == [b""]


def test_prefix_text_then_del_korean():
    """Text before DEL+Korean: split only at the DEL boundary."""
    data = b"abc\x7f\xea\xb0\x80"
    chunks = split(data)
    assert chunks == [b"abc\x7f", b"\xea\xb0\x80"]


if __name__ == "__main__":
    passed = 0
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS  {name}")
                passed += 1
            except AssertionError as e:
                print(f"  FAIL  {name}: {e}")
                failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
