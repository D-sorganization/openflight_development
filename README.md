# openflight_development

Development companion repo for [jewbetcha/openflight](https://github.com/jewbetcha/openflight) — a DIY golf launch monitor (OPS243-A Doppler radar + TI IWR6843 mmWave angle radar).

**Owner:** Dieter Olson (dieterolson)
**Purpose:** Research the public OpenFlight repo, track my hardware build, and develop in support of upstream contributions. Notes, reviews, task tracking, and half-baked experiments live here — polished work goes upstream as PRs.

This is a working repo, not a released product. Expect notes mid-thought and
experiments that went nowhere.

The launch-monitor technology review and its companion screw-theory outline —
previously `tech-review/` and `notes/screw-theory-research-outline.md` — now
live in [AffineDrift](https://github.com/D-sorganization/AffineDrift), vendored
here as `vendor/affinedrift` (a git submodule), the same way the fleet's other
repos vendor shared content. All the golf articles are kept in one place so
they share one CI and release path. See
`vendor/affinedrift/articles/Launch_Monitor_Technology_Review/`.

## How this repo is used

1. **Research** — periodic reviews of the public repo's state and upstream activity land in `project-reviews/`.
2. **Build** — my unit build is tracked via the parts list, build plan, and GitHub Issues on this repo.
3. **Validate** — my Rapsodo MLM2 Pro serves as a reference instrument; protocols and results live in `validation/`.
4. **Contribute** — findings graduate into upstream PRs against jewbetcha/openflight, following their [CONTRIBUTING.md](https://github.com/jewbetcha/openflight/blob/main/CONTRIBUTING.md) (single-scope PRs, tests required, manual testing documented, conventional commit titles).

## Directory map

| Path | Contents |
|------|----------|
| `project-reviews/` | Dated reviews: repo state, upstream activity, contribution opportunities |
| `hardware/` | Parts list (with have/ordered/need status) and the phased build plan |
| `validation/` | MLM2 Pro cross-validation protocol and session results |
| `notes/` | Working notes, experiment logs, scratch analysis |
| `vendor/affinedrift/` | Submodule: the launch-monitor technology review and its screw-theory outline, maintained in AffineDrift |

## Task management

Tasks are tracked as **GitHub Issues on this repo**, derived from the project reviews. Labels:

- `build` — hardware assembly and bring-up tasks
- `procurement` — parts to buy/verify
- `validation` — MLM2 Pro comparison work
- `upstream` — contribution candidates for jewbetcha/openflight
- `research` — things to investigate before acting

## My hardware inventory (2026-07-30)

| Item | Status |
|------|--------|
| OPS243 Doppler radar ×2 | **Have** (verify neither is the WiFi `-W` variant — see parts list) |
| TI IWR6843LEVM angle radar | **On order** — ✅ variant confirmed 2026-07-31 (Digi-Key 296-IWR6843LEVM-ND) |
| SparkFun SEN-14262 sound detector | **Have** |
| Rapsodo MLM2 Pro | **Have** (reference instrument for validation) |
| Raspberry Pi 5 + display + accessories | **Need** — see [hardware/parts-list.md](hardware/parts-list.md) |

## License note

OpenFlight is AGPL-3.0-or-later. This repo is public, so the earlier reasoning
that privacy deferred any AGPL obligation no longer applies — but nothing here
triggers one either: the contents are prose, notes, and a build script, with no
upstream source vendored or excerpted at length. Any code developed here that
builds on upstream remains AGPL and is destined for upstream anyway.

The technology review's license status travels with it; see AffineDrift for
the current terms, if any have been added since the move.
