# openflight_development

Private development companion repo for [jewbetcha/openflight](https://github.com/jewbetcha/openflight) — a DIY golf launch monitor (OPS243-A Doppler radar + TI IWR6843 mmWave angle radar).

**Owner:** Dieter Olson (dieterolson)
**Purpose:** Research the public OpenFlight repo, track my hardware build, and develop privately in support of upstream contributions. Notes, reviews, task tracking, and half-baked experiments live here — polished work goes upstream as PRs.

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
| TI IWR6843 angle radar | **On order** (confirm it is the **IWR6843LEVM** variant — see parts list) |
| SparkFun SEN-14262 sound detector | **Have** |
| Rapsodo MLM2 Pro | **Have** (reference instrument for validation) |
| Raspberry Pi 5 + display + accessories | **Need** — see [hardware/parts-list.md](hardware/parts-list.md) |

## License note

OpenFlight is AGPL-3.0-or-later. This private repo contains analysis of, and excerpts from, that codebase; anything derived from upstream code remains AGPL. Keeping this repo private is compatible with AGPL (obligations trigger on distribution / network service), but any code developed here that builds on upstream is destined for upstream anyway.
