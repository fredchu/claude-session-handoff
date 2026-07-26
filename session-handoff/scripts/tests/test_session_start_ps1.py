import pathlib


SCRIPT = pathlib.Path(__file__).parents[3] / "hooks" / "session-start.ps1"


def test_session_start_powershell_hook_is_ascii_and_configures_utf8():
    content = SCRIPT.read_bytes()
    assert all(byte < 0x80 for byte in content)
    assert b"$LASTEXITCODE" in content
    assert b"PYTHONUTF8" in content


def test_session_start_powershell_hook_qualifies_each_candidate_before_selecting():
    text = SCRIPT.read_text(encoding="ascii")
    # Both interpreter candidates are probed inside one qualification loop, so an
    # outdated "py -3" falls through to a supported "python" instead of aborting.
    assert 'Exe = "py"; Args = @("-3")' in text
    assert 'Exe = "python"; Args = @()' in text
    assert text.index("foreach ($candidate in $candidates)") < text.index('"3.9.0"')
    assert text.count("3.9.0") == 1  # single version gate inside the loop
