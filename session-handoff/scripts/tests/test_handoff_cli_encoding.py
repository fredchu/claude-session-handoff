import os
import pathlib
import subprocess
import sys

import pytest

from markdown_storage import write_shard

SCRIPT = pathlib.Path(__file__).parent.parent / "handoff_cli.py"
UPDATED = "2026-07-26T10:00:00+08:00"
BODY = "跨平台交接成功 🚀"


def utf8_hostile_env():
    env = os.environ.copy()
    env.update({
        "LC_ALL": "C",
        "PYTHONUTF8": "0",
        "PYTHONCOERCECLOCALE": "0",
    })
    return env


@pytest.mark.parametrize("command", ["write", "archive"])
def test_utf8_body_round_trips_with_ascii_locale(tmp_path, command):
    root = tmp_path / "store"
    body_file = tmp_path / "body.md"
    body_file.write_text(BODY, encoding="utf-8")
    args = [
        sys.executable,
        str(SCRIPT),
        command,
        "--root",
        str(root),
        "--agent",
        "Main",
        "--body-file",
        str(body_file),
        "--updated-at",
        UPDATED,
    ]
    if command == "write":
        args.extend(["--kind", "active"])
    else:
        args.extend(["--session-id", "encoding-test", "--slug", "encoding"])

    result = subprocess.run(
        args,
        capture_output=True,
        encoding="utf-8",
        env=utf8_hostile_env(),
    )

    assert result.returncode == 0, result.stderr
    shard = next(root.rglob("*.md"))
    assert "跨平台交接成功" in shard.read_text(encoding="utf-8")


def test_session_start_writes_utf8_with_ascii_locale(tmp_path):
    root = tmp_path / "store"
    write_shard(root, "active", "Main", "Main", BODY, UPDATED)

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "session-start",
            "--root",
            str(root),
            "--agent",
            "Main",
        ],
        capture_output=True,
        encoding="utf-8",
        env=utf8_hostile_env(),
    )

    assert result.returncode == 0, result.stderr
    assert "跨平台交接成功" in result.stdout
