# Where I Can Best Contribute — Ranked Opportunities

**Date:** 2026-07-30 · Companion to the [state review](2026-07-30-openflight-state-review.md) and [upstream activity review](2026-07-30-upstream-activity-review.md).

## My distinctive assets

| Asset | Why it matters upstream |
|---|---|
| **Rapsodo MLM2 Pro** | The project's #1 stated blocker, in their own words: estimator limits are "deferred pending a session paired with a reference instrument, **which this repo does not have**." All truth data so far = 3 borrowed TrackMan sessions. |
| 2× OPS243 | One build unit + one bench unit; nobody upstream does dual-OPS A/B work (UART-vs-USB, trigger latency, PR testing without touching the build) |
| IWR6843LEVM (ordered) | Puts me on the current-gen path the core team is actively developing |
| Windows dev machine | The test suite's Windows story (22 env failures, 2 genuine test bugs) is invisible to the Linux/macOS core team — I hit it natively |
| Existing trust | PR #117 merged; **PR #118 approved** and waiting only on a rebase |

## Tier 1 — do now (no hardware needed)

1. **Rebase [PR #118](https://github.com/jewbetcha/openflight/pull/118)** (SessionLogger thread safety). Already approved by jewbetcha 44 days ago; went stale during the July IWR churn. Re-run tests, resolve conflicts, push. *Effort: hours. Payoff: merged PR + re-established presence.*
2. **Windows test-suite fixes** — bug fixes with tests, their top-priority contribution class, and uniquely mine to see:
   - `tests/test_compare_trackman.py:145` newline bug (`write_text` without `newline=""` → `\r\r\n` on Windows) — genuine bug, one-line fix.
   - Same family in `test_session_shot_report.py`.
   - `test_sim_transport.py:253` real-socket timing flake → mock socket/clock.
   - `sys.platform` skip markers for bash-only (`test_start_kiosk.py` ×17), chmod, udev tests.
   Ship as 2–3 single-scope PRs, not one omnibus.
3. **Docs-drift PR:** CLAUDE.md/README constants that no longer match code (min ball speed says 35, is 15; "CFAR SNR > 15" doesn't exist, actual `threshold_factor=8.0`; "shot timeout 0.5 s" removed; architecture diagram omits iwr6843/sim/cloud/ballistics) + the PARTS.md-vs-operator-guide contradiction on the WiFi OPS243-A. Maintainers love these; zero risk.
4. **Small verified code fixes** (each one PR + test): `_fire_cloud_push` silent `except: pass` (`server.py:2656`); hardcoded 68.0 ms capture midpoint wrong at non-30ksps (`processor.py:1700`); `tdm_sign_policy` field ignored (`iwr6843/runtime.py:38,55`); debounce docstring drift (`trigger.py:576`).

## Tier 2 — unlocked by the build (the unique value)

5. **The truth-data program** — once the rig runs, every paired MLM2 Pro session feeds concrete upstream asks:
   - **Driver ghost-track gate** (their roadmap item: reject TI tracks < ~65–70% of OPS ball speed; "needs more truth data before shipping"). Driver blocks with RPT balls are precisely the missing dataset — driver is their weak point (3.55° MAE, +3.39° bias).
   - **Two-dot relaxed-confidence lane** thresholds ("must be learned on independent truth").
   - **The three deferred estimator questions** (curvature normalization, select-vs-average, the 8° gate resting on one session).
   - **Spin scoring corpus**: `feat/spin-experiments` scores ripple/multitaper variants against TrackMan; MLM2 RPT-ball spin extends it, and the README explicitly welcomes "help validating [the dechirp estimator] against launch-monitor truth data."
   - **Ballistics/carry reality checks** for open PRs #121 (validated Cd/Cl) and #169 (altitude air density).
6. **MLM2 Pro comparison tooling upstream:** after proving the adapter privately (issue #11), PR `--source mlm2pro` support for `compare_trackman.py` + `docs/mlm2pro-test-process.md`. Gives every MLM2-owning builder a validation path — multiplies the project's truth-data supply beyond me.
7. **IWR6843LEVM mount for the IARC case** — the case predates the IWR migration (K-LD7 mounts only). Every new builder needs this; CAD PRs merge fast here (#156, #147).
8. **Answer [Discussion #161](https://github.com/jewbetcha/openflight/discussions/161)'s question with data** — "is the IWR upgrade significant?" An MLM2-referenced IWR6843 accuracy report (mine) vs the published K-LD7-era field numbers is the honest version of the comparison nobody has produced.

## Tier 3 — bigger swings (propose before building)

9. **`club_data.py` consolidation** (state review F3) — three smash/launch/spin tables, already numerically diverged. A day of work + cross-consistency tests; propose in an issue first, then PR. High acceptance odds: it's a correctness fix dressed as a refactor.
10. **CI-toolchain migration to uv** (F8) — workflows violate the repo's own rule #1, install deleted deps (incl. a git-URL package), never run ruff/vitest. Mechanical, reviewable, closes the local-vs-CI gap.
11. **Server refactor (F9/F2)** — `AppState` + staged shot pipeline. **Do not cold-PR this.** The johnragonhall lesson: this repo merges focused spec'd increments and lets 20k-line rewrites die. Write a design issue referencing the duplicated K-LD7 blocks and the 27 globals; offer to slice it.
12. **Dead camera code retirement** (F4) — ~2k LOC, provably unreachable; needs maintainer sign-off on intent (camera may return for spin).
13. Second-OPS experiments: UART-vs-USB A/B on the fresh #160 migration; trigger-latency characterization; testing PR #157 (swing-speed mode) without touching my build unit.

## House rules to respect (from CONTRIBUTING.md + observed history)

- Single-scope PRs, conventional titles (`fix(tests): …`), description sections enforced by CI (why / automated tests / manual testing).
- Source changes without test changes fail PR checks unless labeled `no-tests-needed`.
- Bug reports: failing test first (their CLAUDE.md rule).
- Batch nothing; the maintainer merges small things in days and big things never.

## Suggested sequence (first ~30 days)

| Week | Action |
|---|---|
| 1 | Rebase #118 · start Windows-fix PR #1 (newline bugs) · order remaining parts (issue #2) |
| 2 | Docs-drift PR · Windows platform-skips PR · Pi arrives → build Phases 0–3 |
| 3 | Small code-fix PRs (cloud-push swallow, capture-midpoint) · IWR arrives → Phases 4–5 |
| 4 | Interference check (issue #10) · first paired session (issue #12) · adapter script (issue #11) → first truth-data report upstream |
