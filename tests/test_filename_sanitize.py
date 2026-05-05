"""Filename sanitization for cross-platform downloads."""
from oscillo_plasma_calc.ui.components.safe_filename import safe_filename


def test_replaces_colon_slash_backslash():
    out = safe_filename("a/b\\c:d", "md", with_timestamp=False)
    assert ":" not in out and "/" not in out and "\\" not in out
    assert out.endswith(".md")


def test_replaces_question_pipe_asterisk():
    out = safe_filename("a?b|c*d", "csv", with_timestamp=False)
    for ch in "?|*":
        assert ch not in out


def test_replaces_control_chars():
    out = safe_filename("a\x00b\x1fc", "md", with_timestamp=False)
    assert "\x00" not in out and "\x1f" not in out


def test_windows_reserved_names_get_prefix():
    for name in ("CON", "PRN", "AUX", "NUL", "COM1", "LPT9"):
        out = safe_filename(name, "md", with_timestamp=False)
        assert out.startswith("_")


def test_empty_label_falls_back_to_report():
    out = safe_filename("", "md", with_timestamp=False)
    assert out == "report.md"


def test_only_whitespace_falls_back():
    out = safe_filename("   ", "md", with_timestamp=False)
    assert out == "report.md"


def test_japanese_label_preserved():
    out = safe_filename("PW目盛1.50", "md", with_timestamp=False)
    assert "PW目盛1.50" in out


def test_trailing_dots_and_spaces_stripped():
    out = safe_filename("foo. .", "md", with_timestamp=False)
    # No leading/trailing dot before extension
    assert out == "foo.md"


def test_long_label_truncated():
    out = safe_filename("a" * 250, "md", with_timestamp=False)
    base = out.rsplit(".", 1)[0]
    assert len(base) <= 100


def test_timestamp_appended_when_requested():
    out = safe_filename("foo", "md", with_timestamp=True)
    assert out.startswith("foo_")
    assert out.endswith(".md")


def test_extension_normalized():
    assert safe_filename("foo", ".md", with_timestamp=False).endswith(".md")
    assert safe_filename("foo", "md", with_timestamp=False).endswith(".md")
