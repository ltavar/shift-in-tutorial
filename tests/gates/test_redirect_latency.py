"""CI gate for SLI 1 (docs/slis.md): redirect latency, p95 of GET /{code} < 50 ms.

Starts a real uvicorn server, creates one link, follows it REQUESTS times over a
single keep-alive connection and checks the 95th percentile.

What is measured: the client-observed time from sending the request to reading
the full response over loopback. That includes a little client and socket
overhead, so it is a slight over-estimate of server time and never an
under-estimate; a pass is therefore a safe pass.
"""

import http.client
import json
import math
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

SLO_P95_MS = 50  # docs/slis.md, SLI 1: p95 server time to answer GET /{code} < 50 ms
REQUESTS = 200
WARMUP_REQUESTS = 20
STARTUP_TIMEOUT_S = 15

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_until_up(port: int, server: subprocess.Popen) -> None:
    deadline = time.monotonic() + STARTUP_TIMEOUT_S
    while time.monotonic() < deadline:
        if server.poll() is not None:
            raise RuntimeError(f"uvicorn exited early with code {server.returncode}")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(f"uvicorn not accepting connections after {STARTUP_TIMEOUT_S}s")


@pytest.fixture(scope="module")
def server_port():
    port = _free_port()
    server = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "snip.main:app",
            "--app-dir", "src", "--host", "127.0.0.1", "--port", str(port),
            "--log-level", "warning",
        ],
        cwd=PROJECT_ROOT,
    )
    try:
        _wait_until_up(port, server)
        yield port
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()


def p95(samples_ms: list[float]) -> float:
    """Nearest-rank 95th percentile."""
    ordered = sorted(samples_ms)
    return ordered[math.ceil(0.95 * len(ordered)) - 1]


def test_redirect_p95_is_under_slo(server_port, capsys):
    conn = http.client.HTTPConnection("127.0.0.1", server_port, timeout=5)

    body = json.dumps({"url": "https://example.com/some/long/path?a=1&b=2"})
    conn.request("POST", "/api/links", body, {"Content-Type": "application/json"})
    created = conn.getresponse()
    assert created.status == 201
    code = json.loads(created.read())["code"]

    def follow() -> float:
        start = time.perf_counter()
        conn.request("GET", f"/{code}")
        response = conn.getresponse()
        response.read()
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert response.status == 307
        return elapsed_ms

    for _ in range(WARMUP_REQUESTS):
        follow()
    samples = [follow() for _ in range(REQUESTS)]
    conn.close()

    measured = p95(samples)
    with capsys.disabled():
        print(
            f"\n[SLI 1 gate] redirect latency over {REQUESTS} follows "
            f"(after {WARMUP_REQUESTS} warm-up): "
            f"p50={sorted(samples)[len(samples) // 2]:.2f} ms  "
            f"p95={measured:.2f} ms  max={max(samples):.2f} ms  "
            f"SLO p95 < {SLO_P95_MS} ms  margin={SLO_P95_MS - measured:.2f} ms"
        )

    assert measured < SLO_P95_MS, (
        f"p95 {measured:.2f} ms is not under the {SLO_P95_MS} ms SLO (docs/slis.md SLI 1)"
    )
