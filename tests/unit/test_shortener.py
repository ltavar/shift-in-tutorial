"""shortener.py: the logic behind the follow path (SLIs 2, 3, 5) and create.

Each test's docstring names the SLI it serves.
"""

import pytest

from snip import shortener
from snip.store import LinkNotFound

URL = "https://example.com/a/b?c=1&d=2#frag"


# --- SLI 2: follow returns a redirect target or a *clean* not-found --------

def test_resolve_unknown_code_raises_link_not_found():
    """SLI 2: unknown code is a LinkNotFound (mapped to 404), never a bare KeyError."""
    with pytest.raises(LinkNotFound):
        shortener.resolve("nope12")


def test_stats_unknown_code_raises_link_not_found():
    """SLI 2: stats for an unknown code is a clean not-found too."""
    with pytest.raises(LinkNotFound):
        shortener.stats("nope12")


# --- SLI 3: a code resolves to the exact URL it was created for ------------

@pytest.mark.parametrize(
    "url",
    [
        URL,
        "http://example.com",
        "https://example.com/path%20with%20encoded?q=%7Bx%7D",
        "https://example.com/?a=1&a=2&b=",
        "https://example.com/#only-fragment",
        "https://example.com/" + "a" * 1500,
    ],
    ids=["query+fragment", "bare-host", "encoded", "repeated-params", "fragment", "long"],
)
def test_resolve_returns_exact_stored_url(url):
    """SLI 3: create then resolve gives back the URL byte-for-byte."""
    record = shortener.create_link(url)
    assert shortener.resolve(record.code).url == url


def test_each_code_resolves_to_its_own_url():
    """SLI 3: two links never get each other's URL."""
    a = shortener.create_link("https://a.example/")
    b = shortener.create_link("https://b.example/")
    assert a.code != b.code
    assert shortener.resolve(a.code).url == "https://a.example/"
    assert shortener.resolve(b.code).url == "https://b.example/"


def test_collision_does_not_overwrite_existing_link(monkeypatch):
    """SLI 3 (and 5): a forced code collision must not replace the first link."""
    codes = iter(["AAAAAA", "AAAAAA", "BBBBBB"])
    monkeypatch.setattr(shortener, "generate_code", lambda: next(codes))

    first = shortener.create_link("https://first.example/")
    shortener.create_link("https://second.example/")

    assert shortener.stats(first.code).url == "https://first.example/"


def test_collision_keeps_first_links_clicks(monkeypatch):
    """SLI 5: a collision must not reset the existing link's click count."""
    codes = iter(["AAAAAA", "AAAAAA", "BBBBBB"])
    monkeypatch.setattr(shortener, "generate_code", lambda: next(codes))

    first = shortener.create_link("https://first.example/")
    shortener.resolve(first.code)
    shortener.resolve(first.code)
    shortener.create_link("https://second.example/")

    assert shortener.stats(first.code).clicks == 2


def test_collision_retries_until_a_free_code(monkeypatch):
    """SLI 3: repeated collisions keep retrying and the new link gets the first free code."""
    codes = iter(["AAAAAA", "AAAAAA", "AAAAAA", "AAAAAA", "CCCCCC"])
    monkeypatch.setattr(shortener, "generate_code", lambda: next(codes))

    shortener.create_link("https://first.example/")
    second = shortener.create_link("https://second.example/")

    assert second.code == "CCCCCC"


def test_generated_code_is_routable():
    """SLI 3: codes are 6 chars of [A-Za-z0-9], so GET /{code} can always address them."""
    for _ in range(200):
        code = shortener.generate_code()
        assert len(code) == 6
        assert code.isascii() and code.isalnum()


# --- SLI 5: recorded clicks equal actual follows ---------------------------

def test_new_link_starts_with_zero_clicks():
    """SLI 5: a link nobody followed has zero clicks."""
    assert shortener.create_link(URL).clicks == 0


def test_each_follow_counts_exactly_once():
    """SLI 5: N follows give exactly N clicks (not N-1, not 2N)."""
    code = shortener.create_link(URL).code
    for expected in range(1, 6):
        shortener.resolve(code)
        assert shortener.stats(code).clicks == expected


def test_stats_and_list_do_not_count_as_follows():
    """SLI 5: reading stats or listing links never changes a click count."""
    code = shortener.create_link(URL).code
    shortener.resolve(code)
    shortener.stats(code)
    shortener.stats(code)
    shortener.list_links()
    assert shortener.stats(code).clicks == 1


def test_clicks_are_counted_per_code():
    """SLI 5: two codes are counted independently."""
    a = shortener.create_link("https://a.example/").code
    b = shortener.create_link("https://b.example/").code
    shortener.resolve(a)
    shortener.resolve(a)
    shortener.resolve(b)
    assert shortener.stats(a).clicks == 2
    assert shortener.stats(b).clicks == 1


def test_failed_follow_creates_no_phantom_clicks():
    """SLI 5: following an unknown code records nothing anywhere."""
    code = shortener.create_link(URL).code
    with pytest.raises(LinkNotFound):
        shortener.resolve("nope12")
    assert shortener.stats(code).clicks == 0
    assert [r.code for r in shortener.list_links()] == [code]


# --- create / list (no SLI of their own) -----------------------------------

def test_list_links_returns_every_created_link():
    """No SLI: list shows all created links (supports SLI 5 by exposing clicks)."""
    codes = {shortener.create_link(f"https://x.example/{i}").code for i in range(3)}
    assert {r.code for r in shortener.list_links()} == codes
