# Upstream Activity Review — jewbetcha/openflight

**Date:** 2026-07-30 · **Local clone:** at `9b61f0a` = origin/main HEAD (fully current)
**Method:** gh CLI queries of PRs/issues/discussions/branches + git history analysis.

## Vitals

| Metric | Value |
|--------|-------|
| Age / activity | Created 2025-12-08 (~8 months); last push 2026-07-29 — active daily |
| Stars / forks / watchers | 774 / 85 / 37 |
| License | AGPL-3.0-or-later (changed Apr 2026) |
| Open PRs / open issues | 17 (14 human + 3 dependabot) / 7 |
| Releases / tags | **None** — no versioning yet; CHANGELOG all `[Unreleased]` |
| Community surfaces | Discussions (14 threads) + wiki enabled; openflight.dev cloud ("FlightWeb") |

## Cadence & who does the work

889 commits on main since launch. Monthly: Dec 85 → Jan 108 → Feb 66 → Mar 77 → **Apr 265 (K-LD7 RADC peak)** → May 89 → Jun 157 → Jul 42 (fewer but much larger commits — the IWR6843 integration alone was +11,845 lines squashed).

**Two-tier structure:** a genuine two-person core — **jewbetcha (Coleman Rollins, 621 contributions; 142 commits in the last 3 months)** and **johnpacino (John Pacino, ~99 commits, #2 committer)** — does all radar/DSP/firmware work. Around them, a recurring community bench: JedS (CAD/docs), Reillybags (UI features + community support), Elkhunder/mkneuffer (docs), HuggeK (CAD), clschnei (tooling). Outside-the-core algorithm contributions are rare and the K-LD7-era ones went stale when that hardware was deprecated.

**My standing:** dieterolson has 1 merged contribution — [PR #117](https://github.com/jewbetcha/openflight/pull/117) (K-LD7 ring-buffer thread-safety fix, merged 06-16) — and one open PR, [#118](https://github.com/jewbetcha/openflight/pull/118) (SessionLogger write thread-safety, +161/−8), which **jewbetcha approved** but which has gone stale/conflicting during the July IWR churn. Rebasing #118 is the single fastest path back onto the contributor list.

**Maintainer responsiveness:** good. Hardware questions answered same/next day; hardware asks get closed by actual merged CAD/docs PRs; dependabot batched; community docs/CAD PRs merge within days. All 15 recently closed issues were closed COMPLETED (none wontfix/stale). Caveat: big unsolicited feature waves stall — see below.

## The headline event: IWR6843 migration (July)

The K-LD7 angle radars were formally deprecated 07-20; the TI IWR6843LEVM is the angle radar now:

- **[PR #155](https://github.com/jewbetcha/openflight/pull/155)** (johnpacino, merged 07-26): full integration — `src/openflight/iwr6843/` (17 modules incl. the LCMF launch-angle estimator, DoA, tracking, club path), **custom C firmware** (`l3_dump.c`, 1,941 lines) with a validated prebuilt image, Pi-based ROM-bootloader flasher, calibration tooling, 15+ test files.
- **[PR #160](https://github.com/jewbetcha/openflight/pull/160)** (jewbetcha, merged 07-26): OPS243 moved USB → Pi GPIO UART (frees USB power for the TI board), plus club-path estimator gates.
- **[PR #159](https://github.com/jewbetcha/openflight/pull/159)** (johnpacino, merged 07-25): experimental multitaper spin estimator, live in UI.
- **[PR #158](https://github.com/jewbetcha/openflight/pull/158)** (merged 07-25): OPS serial deadlock fix (system froze after first real shot — recent, load-bearing bug class).

**Measured performance** (docs/iwr6843_field_report_2026-07.html, 3 TrackMan sessions): irons/wedges **0.83° MAE, 87.4% coverage, −0.04° bias** (best session ~0.68° MAE). **Driver is the weak point: 3.55° MAE, +3.39° bias**, dominated by false-accepted slow "ghost" tracks (TI locking onto 55–57 mph movers while OPS measured 152–158 mph balls). Club path: fixture-validated ±0.3° across ±12°, ships experimental, right-handed only.

**In flight now:** [PR #168](https://github.com/jewbetcha/openflight/pull/168) (RF temperature telemetry in dumps, opened 07-30) and branch `feat/club-path-iwr` (v3 25-frame firmware + Docker firmware build env, 07-27, no PR yet). `feat/spin-experiments` (18 commits, Jul 24–25) scores "ripple" spin variants against TrackMan.

## Open PRs worth knowing about

| PR | What | State |
|----|------|-------|
| [#169](https://github.com/jewbetcha/openflight/pull/169) | session_logger coverage 75%→90%, trigger tests, altitude air-density in ballistics | new, unreviewed |
| [#168](https://github.com/jewbetcha/openflight/pull/168) | IWR6843 temperature telemetry | new |
| [#165](https://github.com/jewbetcha/openflight/pull/165)/[#164](https://github.com/jewbetcha/openflight/pull/164)/[#157](https://github.com/jewbetcha/openflight/pull/157) | Reillybags: cloud-upload hygiene, ball picker, swing-speed training mode (air swings, no trigger) | #157 conflicting |
| [#147](https://github.com/jewbetcha/openflight/pull/147) | Touch Display 2 shell STL (draft, needs fit testing) | conflicting |
| [#120](https://github.com/jewbetcha/openflight/pull/120)–[#127](https://github.com/jewbetcha/openflight/pull/127) | johnragonhall's June wave: UI redesign (+20k lines), i18n, BLE, security hardening, validated ballistics ([#121](https://github.com/jewbetcha/openflight/pull/121) has real maintainer discussion) | all stalled/conflicting |
| **[#118](https://github.com/jewbetcha/openflight/pull/118)** | **mine — SessionLogger thread safety, APPROVED, needs rebase** | conflicting |

Lesson from the johnragonhall stack: this project merges focused, spec'd, tested increments quickly and lets giant unsolicited rewrites sit. Match the house style: single-scope PRs.

## Issues & discussions

Only 7 open issues — all from **ggubs** (radar-domain expert), all filed on day 2 of the project, functioning as a standing radar-engineering review backlog (link budget, energy-detector thresholds, triggering parameters, debug tools). Unclaimed. Support traffic flows through Discussions instead; community members increasingly answer each other.

Live demand signal: [Discussion #161](https://github.com/jewbetcha/openflight/discussions/161) — a builder finishing a K-LD7 build asks whether upgrading to the IWR6843 is worth it ("if it's significant"). Nobody has published a K-LD7 vs IWR6843 comparison.

## The de-facto roadmap (no ROADMAP file; assembled from field report + operator guide + specs)

1. **Two-dot relaxed-confidence lane** for strict-LCMF no-reads (~5–8 recovered reads/session at ~1.0–1.1° MAE) — thresholds "must be learned on independent truth."
2. **Driver ghost-track guardrail** — reject TI tracks below ~65–70% of OPS ball speed; then OPS-guided fast-track recovery (offline replay recovered 3 of 4 bad driver shots at ~2.6° MAE) — "needs more truth data before shipping."
3. Three launch-angle estimator limits **"deferred pending a session paired with a reference instrument, which this repo does not have"**: non-scale-normalized curvature selection, select-vs-average policy, the 8° agreement gate resting on one session.
4. Tilt self-calibration is broken by design (monotonic sweep) — physical measurement required; deliberate tilt A/B runs wanted.
5. Dump latency (7.6 s UART drain) — on-chip compression/range-gating planned.
6. TX2 horizontal aim, shank classification, attack-angle research, left-handed club path.
7. Setup hardening: radar-assisted tee-distance modes, net-distance A/B, ball-marking RCS tests.

Items 1–3 all share one bottleneck: **independent truth data** — which is exactly what a Rapsodo MLM2 Pro rig provides. See the contribution-opportunities review.

## Housekeeping observations (low-stakes PR fodder)

- 5 dead/stale branches (`feat/sim-connectors` fully merged, `fix/kld7-ring-buffer-thread-safety` fully merged, `feat/gspro-integration` superseded, K-LD7-era branches orphaned by deprecation).
- 3 dependabot PRs (#142–144) superseded by newer merged bumps.
- Zero releases/tags despite a maintained CHANGELOG — a v0.1 cut is an obvious gap (maintainer's call).
- PARTS.md vs IWR operator guide tension on the WiFi OPS243-A variant (PARTS.md: "not compatible"; operator guide: allowed via powered hub Layout B) — worth a docs clarification PR.
