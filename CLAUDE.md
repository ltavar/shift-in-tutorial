# CLAUDE.md — snip

snip is an internal URL shortener: employees paste long links into chat, docs and slides, and snip
returns a short code and counts how often it is followed. Source in `src/snip/`
(`main.py`, `models.py`, `shortener.py`, `store.py`). Details: `docs/business-context.md`,
`docs/quality-characteristics.md`, `docs/slis.md`. Test approach: `docs/test-strategy.md`.

## Who we serve (priority order)

1. **Recipients following short links** — highest volume by far; the redirect path is the hot path.
2. **Employees creating links** — lower volume, but where validation and security risk live.
3. **Link owners checking click stats** — depends on the follow path counting reliably.

When trade-offs arise, the follow path wins over create, and create wins over list/stats.

## Quality bar (highest priority first)

1. **Functional correctness** — a code always resolves to the exact URL it was created for; click
   counts are accurate.
2. **Performance efficiency** — following a link must be fast.
3. **Reliability** — the redirect path stays up; create may tolerate brief degradation.
4. **Security** — accept only safe, well-formed URLs; no open redirect, no script-scheme abuse
   (e.g. `javascript:`).
5. **Maintainability** — the whole service is four small modules; keep it small enough that an
   agent and a human can each hold all of it in their head, and prove it with tests rather than
   comments.

## SLIs (the target, not a description of current code)

| # | SLI | Target |
|---|-----|--------|
| 1 | Redirect latency: p95 server time for `GET /{code}` | < 50 ms |
| 2 | Redirect availability: `GET /{code}` returns a valid redirect or a correct 404 | ≥ 99.9% |
| 3 | Resolve correctness: follows redirecting to the exact stored URL | 100% |
| 4 | Create validation: invalid/unsafe URLs correctly rejected | 100% |
| 5 | Stats accuracy: recorded clicks equal actual follows | 100% |

SLIs 1–3 are the redirect hot path; weight test effort there. SLIs 4–5 cover create and stats. At
least one SLI (latency or correctness first) is enforced as a CI gate.

## Working agreements

- **Ready:** before building, the request must say which of SLIs 1–5 it affects (or that none are)
  and have acceptance criteria agreed by the Three Amigos. If the SLI impact is unknown, ask.
- **Done:** SLI-affecting changes are reflected in the CI gates, and any observable behaviour
  change is covered by at least one API- or system-level test, not only unit tests.
- State the SLI impact (which of 1–5, or none) in every PR description.
- SLIs 3, 4 and 5 are 100% targets with no tolerance: a failing test there is a defect to fix,
  never a threshold to loosen or a test to skip. The same goes for the 50 ms p95 in SLI 1.
- Changes to the follow handler, URL validation or click counting are proven by hand mutation, per
  `docs/test-strategy.md`: break the code on purpose and show the named test fails.
- Known roadmap item: **link expiry** (owners want links that stop working after a chosen time).
  Build it via Example Mapping, with SLI impact in the acceptance criteria.

## Stack conventions

- Python 3.11+, FastAPI, uvicorn. Source layout is `src/snip/`, packaged with hatchling.
- Run: `uvicorn snip.main:app --reload --app-dir src` (inside a venv, after `pip install -e .`).
- API surface: `POST /api/links`, `GET /api/links`, `GET /api/links/{code}/stats`, `GET /{code}`.
  Keep the `/api` prefix for management endpoints; the bare `/{code}` path is reserved for follows.
- Test tooling (pytest, pytest-cov, robotframework) is not yet in `pyproject.toml`; add it when
  tests are introduced.
- Click counting happens on the follow path and nowhere else; the stats endpoint only reads it
  (SLI 5 depends on this). Don't add a second place that increments.
