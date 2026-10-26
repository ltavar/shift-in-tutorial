"""models.py: request validation (SLI 4) and response mapping (SLIs 3, 5)."""

import pytest
from pydantic import ValidationError

from snip.models import CreateLinkRequest, LinkResponse
from snip.store import LinkRecord

# --- SLI 4: invalid/unsafe URLs must be rejected ---------------------------
# CreateLinkRequest is currently a bare `url: str` (review finding #2), so the
# rejection tests are expected to fail until validation is added. strict=True
# makes the suite go red the moment validation lands, as a reminder to delete
# the marker.

NOT_YET_VALIDATED = pytest.mark.xfail(
    strict=True,
    reason="review finding #2: CreateLinkRequest does not validate URLs yet",
)

REJECTED = [
    "javascript:alert(1)",
    "JavaScript:alert(1)",
    "javascript://example.com/%0Aalert(1)",
    "data:text/html,x",
    "file:///etc/passwd",
    "ftp://example.com/x",
    "",
    "   ",
    "not a url",
    "example.com/path",
    "//evil.example",
    "http://",
]


@NOT_YET_VALIDATED
@pytest.mark.parametrize("url", REJECTED)
def test_unsafe_or_malformed_url_is_rejected(url):
    """SLI 4: the request model refuses scripts, non-http(s) schemes, schemeless and hostless URLs."""
    with pytest.raises(ValidationError):
        CreateLinkRequest(url=url)


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com",
        "https://example.com/a/b?c=1&d=2#frag",
        "https://intranet.corp.example:8443/dash?x=%20y",
    ],
)
def test_valid_http_urls_are_accepted(url):
    """SLI 4: rejecting bad input must not reject good input (and the URL is kept unchanged)."""
    assert CreateLinkRequest(url=url).url == url


# --- SLIs 3 and 5: the response reports the record faithfully --------------

def test_response_carries_exact_url_and_clicks():
    """SLI 3 + 5: the API response shows the stored URL and the recorded clicks, unaltered."""
    record = LinkRecord(code="abc123", url="https://example.com/a?b=1#c", clicks=7)
    resp = LinkResponse.from_record(record)
    assert (resp.code, resp.url, resp.clicks) == ("abc123", "https://example.com/a?b=1#c", 7)
