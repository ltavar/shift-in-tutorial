"""store.py: the lookup the follow path depends on (SLIs 2, 3, 5)."""

import pytest

from snip.store import LinkNotFound, LinkRecord, Store


def test_get_missing_code_raises_link_not_found():
    """SLI 2: a missing code is LinkNotFound, which the API maps to 404."""
    with pytest.raises(LinkNotFound):
        Store().get("nope12")


def test_link_not_found_is_still_a_keyerror():
    """SLI 2: stays a KeyError subclass so existing `except KeyError` callers keep working."""
    assert issubclass(LinkNotFound, KeyError)


def test_get_returns_the_stored_url_unchanged():
    """SLI 3: what was put is what is got, byte-for-byte."""
    s = Store()
    url = "https://example.com/a b|c?q=%7B#f"
    s.put(LinkRecord(code="abc123", url=url))
    assert s.get("abc123").url == url


def test_get_returns_the_same_record_object():
    """SLI 5: the follow path increments the record it got, so get must not return a copy."""
    s = Store()
    s.put(LinkRecord(code="abc123", url="https://example.com/"))
    s.get("abc123").clicks += 1
    assert s.get("abc123").clicks == 1


def test_exists_reflects_puts():
    """SLI 3: create_link relies on exists() to avoid overwriting a live code."""
    s = Store()
    assert not s.exists("abc123")
    s.put(LinkRecord(code="abc123", url="https://example.com/"))
    assert s.exists("abc123")
    assert not s.exists("other1")


def test_all_lists_every_record():
    """No SLI: all() returns each stored record once."""
    s = Store()
    for code in ("aaaaaa", "bbbbbb"):
        s.put(LinkRecord(code=code, url="https://example.com/"))
    assert sorted(r.code for r in s.all()) == ["aaaaaa", "bbbbbb"]
