# Upstream Contribution Queue — Draft

**Archived:** 2026-09-06 · **Draft only — not filed, not tracked.**
**Verified against** `jewbetcha/openflight` `main` = **`5dd0d0b`** (2026-09-02), fetched 2026-09-06.

Software work that belongs to [`jewbetcha/openflight`](https://github.com/jewbetcha/openflight),
not to this repository. Nothing here is filed anywhere yet — filing it means opening
an issue or PR **on the upstream repo**.

---

## First, the thing this archive exists to fix

This repository is **not a GitHub fork**. It was seeded by copying upstream's tree,
so there is **no merge base** — `git merge-base upstream/main HEAD` returns nothing.
Git cannot rebase, cherry-pick or three-way-merge anything between the two.

Since that copy, the two trees have gone in different directions:

| | This repo | Upstream `5dd0d0b` |
|---|---|---|
| Commits the other side does not have | 24 | 1,182 |
| `src/openflight/server` | 8-module package, 4,687 lines | single `server.py`, **5,964 lines** |
| `AppState` | present (`server/state.py`) | 0 occurrences |
| `club_data.py` | present | absent |
| CI toolchain | `uv` + ruff + vitest | `pip`, no ruff job |

Nine of the 24 local commits are real source changes to the mirrored tree, made
here instead of upstream. That is the drift, stated plainly: roughly nine PRs of
software work living in a snapshot that upstream has since moved 1,182 commits
past, in a repo with no ancestry link to rebase across.

**The rule going forward:** clone `jewbetcha/openflight` fresh, branch from *its*
`main`, and open the PR there. Do not develop against the snapshot in this repo.

## Disposition of the nine local source PRs

Re-checked against upstream `5dd0d0b` today. "Rebuild" means the change is still
wanted but must be re-authored against current upstream — the local diff will not
apply.

| Local PR | What it did | Upstream today | Disposition |
|---|---|---|---|
| [#35](https://github.com/D-sorganization/openflight_development/pull/35) | Windows test fixes (CRLF, platform skips) | `test_compare_trackman.py:159,178` already carry `newline=""`; `test_start_kiosk.py` guarded by PR #171 | **Mostly landed independently.** Only the `test_cloud_config` 0600 and `test_serial_latency` udev skips may remain — verify, then a tiny PR. |
| [#36](https://github.com/D-sorganization/openflight_development/pull/36) | Docs-drift fixes | `CLAUDE.md:204` now reads "Min ball speed: 15 mph"; the CFAR-SNR and shot-timeout lines are gone | **Superseded.** Re-diff before claiming any remaining drift. |
| [#37](https://github.com/D-sorganization/openflight_development/pull/37) | CI → `uv`, add ruff/vitest | upstream workflows are still `anti-slop`, `pr-checks`, `pylint`, `pytest`, `ui-build`; no `uv`, no ruff job | **Rebuild and offer.** Mechanical, high acceptance odds, closes the local-vs-CI gap that violates upstream's own rule #1. |
| [#38](https://github.com/D-sorganization/openflight_development/pull/38) | `club_data.py` consolidation | no `club_data.py` upstream | **Rebuild — highest priority.** This is a *correctness* fix dressed as a refactor: the smash/launch/spin tables were numerically diverged (DRIVER 1.48 vs 1.45, WOOD_7 1.42 vs 1.41 vs 1.40). Propose in an issue first, then PR with cross-consistency tests. |
| [#39](https://github.com/D-sorganization/openflight_development/pull/39) | MLM2 Pro CSV adapter | absent upstream | **Rebuild and offer** as `--source mlm2pro` for `compare_trackman.py` plus `docs/mlm2pro-test-process.md`. Gives every MLM2-owning builder a validation path, which multiplies upstream's truth-data supply beyond one person. |
| [#40](https://github.com/D-sorganization/openflight_development/pull/40) | `AppState` + K-LD7 orientation dedup | 0 `AppState`; `server.py` grew 3,755 → 5,964 lines | **Do not cold-PR.** See U7 below. |
| [#41](https://github.com/D-sorganization/openflight_development/pull/41) | IWR6843 accuracy write-up for Discussion #161 | n/a — this is prose | **Blocked on data**, not on code. See U9. |
| [#45](https://github.com/D-sorganization/openflight_development/pull/45) | Replace unsafe `pickle`, convert server to logging | `server.py` has 0 `pickle`, but ~10 `scripts/analysis/*` files still load pickles; 1,623 `print(` calls remain across 69 files in `src` + `scripts` | **Split and rebuild.** The pickle-load hardening in the analysis scripts is a defensible standalone security PR. The print→logging sweep is too large to land as one change. |
| [#46](https://github.com/D-sorganization/openflight_development/pull/46) | Modular server package (8 modules) | single 5,964-line file | **Do not port as-is.** See U7. |

## The queue

Ranked. Each entry is a *draft*; none is filed upstream.

### U1 — `club_data.py` consolidation · rebuild · highest value

Three smash/launch/spin tables that have already diverged numerically. Frame it as
a correctness fix, propose in an upstream issue first, then a single PR carrying
cross-consistency tests. Roughly a day of work; strong acceptance odds.

### U2 — CI toolchain migration to `uv`, plus ruff and vitest jobs

Upstream CI installs dependencies the package no longer declares and never runs
`ruff` — while the repo's own rule #1 mandates `uv`. Mechanical and reviewable.
One correction to carry over from the August draft: upstream `ui-build.yml` already
runs `npm run build`, `lint`, `format:check`, `playwright install` and `test:e2e`,
so do not claim CI is "build + eslint only."

### U3 — MLM2 Pro adapter for `compare_trackman.py`

`--source mlm2pro` plus a `docs/mlm2pro-test-process.md`. Best offered *after* the
first paired session (draft `D12`) gives it a worked example.

### U4 — IWR6843LEVM mount for the IARC case · CAD

The case STL set predates the IWR migration and ships K-LD7 mounts only. Every new
builder needs this; CAD PRs have merged fast upstream (#147, #156). Constraints:
board rotated so the vertical virtual array is physically vertical, antenna face
unobstructed, rigid mount. Pairs with draft `D9`.

### U5 — Pickle-load hardening in `scripts/analysis/`

About ten analysis scripts still `pickle.load()` capture files. A non-executable
format (or a guarded loader) is a contained security PR. Keep it separate from any
logging change.

### U6 — Residual Windows test fixes

Verify whether `test_cloud_config` (0600 permissions) and `test_serial_latency`
(udev) still fail on Windows at current upstream, and whether PR #172's utf-8 fix
actually cleared `test_session_shot_report`. Small `sys.platform` skip markers if
so; drop the item if not.

### U7 — `server.py` decomposition · propose, never cold-PR

Upstream's `server.py` is now **5,964 lines** and growing, with no `AppState`. The
local 8-module package here proves the shape works, but a 5,000-line replacement
PR will die — upstream merges focused spec'd increments and lets rewrites rot.

The only viable route is an upstream *design issue* that references the concrete
duplication (the K-LD7 orientation blocks, the `global` count) and offers to slice
it, starting with a single extraction such as `_process_kld7_orientation`. Use the
local package as evidence of feasibility, not as the patch.

### U8 — `print()` → logging · only as narrow slices

1,623 `print(` calls across 69 files. Never one PR. Pick one module with a real
diagnostic need, convert it, show the operator benefit, and see whether upstream
wants more.

### U9 — Answer Discussion #161 with data

"Is the IWR6843 upgrade significant?" An MLM2-referenced accuracy report against
the published K-LD7-era numbers is the honest version of a comparison nobody has
produced. **Physical task** — blocked on draft `D21` → `D12` → `D8`/`D10`, the
longest dependency chain in the project. The interference check (`D10`) must be
settled first or a maintainer can attribute any difference to cross-talk.

### U10 — Dead camera-code retirement

~2k LOC, provably unreachable. Needs maintainer sign-off on intent first — camera
may be intended to return for spin work. Ask before touching.

### U11 — Second-OPS experiments

Two OPS243 boards is a setup nobody upstream has: UART-vs-USB A/B on the migration,
trigger-latency characterisation, and testing other people's PRs on the bench unit
without disturbing the build unit.

## House rules to respect upstream

From upstream `CONTRIBUTING.md` and observed merge history:

- Single-scope PRs, conventional titles (`fix(tests): …`).
- Description sections are CI-enforced: why / automated tests / manual testing.
- Source changes without test changes fail PR checks unless labelled `no-tests-needed`.
- Bug reports get a failing test first — upstream's own `CLAUDE.md` rule.
- Batch nothing. Small things merge in days; big things never merge.

## Staleness

Every claim above was re-verified against `5dd0d0b` on 2026-09-06 and **will rot**.
Upstream moved 1,182 commits since this repo's snapshot; it will keep moving.
Re-verify against a freshly fetched `origin/main` before filing anything — the
August 2026 audit of this same queue found that half its items had already been
fixed or invalidated within six weeks.
