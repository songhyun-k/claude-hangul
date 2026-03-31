#!/usr/bin/env python3
from __future__ import annotations

"""Tests for the DEL splitting logic and wrapper/install integration paths."""

import os
import pty
import subprocess
import sys
import tempfile
import textwrap
import types

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
SCRIPT_PATH = os.path.join(REPO_ROOT, "claude-hangul")
INSTALL_SCRIPT = os.path.join(REPO_ROOT, "install.sh")


def load_module():
    """Load claude-hangul as a module even though it has no .py extension."""
    module = types.ModuleType("claude_hangul")
    module.__file__ = SCRIPT_PATH
    with open(SCRIPT_PATH) as f:
        exec(compile(f.read(), SCRIPT_PATH, "exec"), module.__dict__)
    return module


mod = load_module()
split = mod.split_del_sequences


def run_wrapper_with_fake_claude(fake_script: str):
    """Run the wrapper against a temporary fake claude binary."""
    with tempfile.TemporaryDirectory() as temp_dir:
        fake_claude = os.path.join(temp_dir, "claude")
        with open(fake_claude, "w") as f:
            f.write(fake_script)
        os.chmod(fake_claude, 0o755)

        driver = textwrap.dedent(
            f"""
            import sys
            import types

            path = {SCRIPT_PATH!r}
            mod = types.ModuleType("claude_hangul")
            mod.__file__ = path
            with open(path) as f:
                exec(compile(f.read(), path, "exec"), mod.__dict__)
            mod.find_claude = lambda: {fake_claude!r}
            sys.exit(mod.main())
            """
        )

        master_fd, slave_fd = pty.openpty()
        try:
            return subprocess.run(
                [sys.executable, "-c", driver],
                stdin=slave_fd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,
                timeout=5,
            )
        finally:
            os.close(slave_fd)
            os.close(master_fd)


def run_install(
    home_dir: str, shell_path: str, input_text: str | None = None, use_tty: bool = False
):
    """Run install.sh with an isolated HOME directory."""
    env = os.environ.copy()
    env["HOME"] = home_dir
    env["SHELL"] = shell_path

    if use_tty:
        master_fd, slave_fd = pty.openpty()
        try:
            proc = subprocess.Popen(
                ["bash", INSTALL_SCRIPT],
                cwd=REPO_ROOT,
                env=env,
                stdin=slave_fd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if input_text is not None:
                os.write(master_fd, input_text.encode())
            stdout, stderr = proc.communicate(timeout=5)
            return subprocess.CompletedProcess(
                proc.args, proc.returncode, stdout, stderr
            )
        finally:
            os.close(slave_fd)
            os.close(master_fd)

    return subprocess.run(
        ["bash", INSTALL_SCRIPT],
        cwd=REPO_ROOT,
        env=env,
        input=input_text,
        stdin=subprocess.DEVNULL if input_text is None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=5,
    )


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
    """가 → 간: DEL+가+DEL+간 produces 4 chunks (each DEL isolated)."""
    data = b"\x7f\xea\xb0\x80\x7f\xea\xb0\x84"
    chunks = split(data)
    assert len(chunks) == 4
    assert chunks[0] == b"\x7f"          # DEL
    assert chunks[1] == b"\xea\xb0\x80"  # 가
    assert chunks[2] == b"\x7f"          # DEL
    assert chunks[3] == b"\xea\xb0\x84"  # 간


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
    """Text before DEL+Korean: DEL is isolated from preceding text."""
    data = b"abc\x7f\xea\xb0\x80"
    chunks = split(data)
    assert chunks == [b"abc", b"\x7f", b"\xea\xb0\x80"]


def test_consecutive_dels_then_korean():
    """Two DELs then Korean: first DEL stays with preceding content, second is isolated."""
    data = b"\x7f\x7f\xea\xb0\x80"
    chunks = split(data)
    assert chunks == [b"\x7f", b"\x7f", b"\xea\xb0\x80"], chunks


def test_del_plus_bare_continuation_byte():
    """DEL + bare continuation byte (0x80, invalid UTF-8 start) still splits."""
    data = b"\x7f\x80"
    chunks = split(data)
    assert len(chunks) == 2


def test_only_non_ascii():
    """Pure Korean text without DEL."""
    data = "안녕하세요".encode()
    assert split(data) == [data]


def test_rapid_triple_composition():
    """Fast typing: 가→간→갈 three DEL+Korean pairs in one read."""
    data = b"\x7f\xea\xb0\x80\x7f\xea\xb0\x84\x7f\xea\xb0\x88"
    chunks = split(data)
    assert chunks == [
        b"\x7f", b"\xea\xb0\x80",  # DEL, 가
        b"\x7f", b"\xea\xb0\x84",  # DEL, 간
        b"\x7f", b"\xea\xb0\x88",  # DEL, 갈
    ], chunks


def test_wrapper_preserves_exit_code():
    """Proxy must preserve normal child exit codes."""
    proc = run_wrapper_with_fake_claude("#!/bin/sh\nexit 42\n")
    assert proc.returncode == 42, proc.returncode


def test_wrapper_preserves_signal_exit_code():
    """Proxy must preserve shell-style signal exit codes."""
    proc = run_wrapper_with_fake_claude("#!/bin/sh\nkill -TERM $$\n")
    assert proc.returncode == 143, proc.returncode


def test_install_noninteractive_skips_alias_prompt():
    """Non-interactive installs should succeed without prompting."""
    with tempfile.TemporaryDirectory() as home_dir:
        proc = run_install(home_dir, "/bin/zsh")
        installed = os.path.join(home_dir, ".local", "bin", "claude-hangul")

        assert proc.returncode == 0, proc.stderr
        assert os.path.isfile(installed), installed
        assert "skipped alias setup (non-interactive shell)" in proc.stdout


def test_install_creates_fish_config_dir():
    """Fish installs should create the config directory before writing alias."""
    with tempfile.TemporaryDirectory() as home_dir:
        proc = run_install(home_dir, "/bin/fish", "\n", use_tty=True)
        config_path = os.path.join(home_dir, ".config", "fish", "config.fish")

        assert proc.returncode == 0, proc.stderr
        assert os.path.isfile(config_path), config_path
        with open(config_path) as f:
            contents = f.read()
        assert "alias claude 'claude-hangul' # claude-hangul" in contents


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
