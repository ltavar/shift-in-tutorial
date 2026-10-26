# snip — test strategy (v1)

Status: **target**. No tests exist yet; this is what we will be held to. It follows from the
quality ranking in `quality-characteristics.md` (correctness > performance > reliability >
security > maintainability) and the SLIs in `slis.md`.

## Principles

- **Weight effort where the traffic is.** `GET /{code}` dominates usage, so SLIs 1–3 get the most
  tests and the strictest gates.
- **Create is where input risk lives.** URL validation and the security rules (SLI 4) get dense,
  cheap, table-driven tests.
- **Stats depend on the follow path.** SLI 5 is proven through the follow path, never by poking
  the store directly.
- **Every observable behaviour change needs at least one higher-level test** (Definition of Done),
  so unit tests alone never close a story.

## Target test pyramid

| Level | What it exercises | Tooling | Weight (share of tests) |
|---|---|---|---|
| Unit | `shortener.py` code generation, URL validation rules, `store.py` operations in isolation | pytest | ~60% |
| API / integration | FastAPI app in-process: every endpoint, status codes, redirect targets, click counting, rejection of bad input | pytest + FastAPI `TestClient` | ~30% |
| System | The real running server over HTTP: end-to-end journeys and the latency gate | Robot Framework against `uvicorn` | ~10% |

Weights are a guide for the number of tests, not a quota. Within each level, **about half of the
tests should concern the follow path** (`GET /{code}`), with create/validation next and list/stats
last, mirroring the traffic and the quality ranking. If a level drifts far from its weight, say so
in the PR rather than quietly accumulating tests at the wrong level.

Coverage (pytest-cov) is reported but is **not** a proof of quality: a line can be covered without
being asserted on. That is what the mutation check below is for.

## SLI → proving test level

| # | SLI (target) | Proved at | How it is proved | CI gate |
|---|---|---|---|---|
| 1 | Redirect latency, p95 < 50 ms | System | Robot sends a fixed batch of `GET /{code}` requests to the running server and fails if measured p95 exceeds 50 ms | Yes — first gate candidate |
| 2 | Redirect availability, ≥ 99.9% valid redirect or correct 404 | API, plus production monitoring | API tests assert that every follow returns either a redirect or a 404 for unknown/invalid codes, never a 5xx. The 99.9% figure itself can only be measured in production | Behaviour: yes. Rate: no (not provable in CI) |
| 3 | Resolve correctness, 100% exact stored URL | API (unit for edge cases) | Create → follow for a table of awkward URLs (query strings, fragments, encoded characters, long URLs); assert the `Location` equals the input exactly | Yes — first gate candidate |
| 4 | Create validation, 100% rejected | Unit (rules) + API (wiring) | Table-driven: `javascript:`, `data:`, schemeless, empty, malformed and oversized URLs must be rejected with a 4xx and must not create a link. Valid `http`/`https` URLs must be accepted | Yes |
| 5 | Stats accuracy, 100% | API | Follow a code N times, then read `/api/links/{code}/stats` and assert exactly N. Include: unknown code (no phantom counts), two codes counted independently, a failed follow not counted | Yes |

Honest limits: SLI 2's availability percentage and SLI 1's behaviour under real load cannot be
fully proven by a CI run. The tests above guard the *behaviours* that feed them; production
monitoring owns the rates.

## Do the tests actually assert something? Break the code on purpose

A passing suite proves nothing if the assertions are weak. We check by **hand mutation**: change
the production code to be deliberately wrong and confirm a test fails. No mutation tool is used.

Procedure, per SLI:

1. With the suite green, make one small deliberate break in `src/snip/` that violates the SLI.
2. Run the suite. **It must fail**, and fail in a test that names that behaviour.
3. Revert the break. If the suite stayed green, the test is decorative: strengthen the assertion,
   re-run the break, and only then move on.

Minimum break per SLI (all must be caught):

| SLI | Deliberate break |
|---|---|
| 1 | Add a `time.sleep(0.06)` to the follow handler |
| 2 | Make an unknown code raise an unhandled error instead of returning 404 |
| 3 | Strip the query string or fragment from the stored or returned URL; return the URL of a different code |
| 4 | Remove the scheme check so `javascript:` is accepted |
| 5 | Remove the click increment; increment twice; count a follow of an unknown code |

Rules:

- Record each break and the test that caught it (a line in the PR description is enough).
- A break that survives is a defect in the *tests*, and is fixed before the story is Done.
- Breaks are never committed. Work on a throwaway change and revert with `git restore`.
- Repeat the relevant breaks whenever a story touches the follow path, validation or click counting,
  and add the new behaviour's own break (for link expiry: an expired link still redirects).

## Pipeline

- Unit and API tests run on every PR.
- System tests (including the latency gate) run on every PR against a freshly started server.
- At least one SLI gate (latency or correctness first) fails the build when breached; the rest
  are added as the pipeline matures.
- Tooling (pytest, pytest-cov, robotframework) is added to `pyproject.toml` with the first tests.

## Out of scope for v1

Load and soak testing beyond the p95 batch, multi-instance behaviour, and authentication (the
docs define none). Revisit when the business context changes.
