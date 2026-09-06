# Draft Backlog — Archived, Not Tracked

**Archived:** 2026-09-06 · **Status:** documentation only

This directory holds the former GitHub issue backlog of this repository, converted
into **draft** issues and epics. Nothing in here is a filed, tracked, or scheduled
work item.

## Why this repo no longer carries an issue tracker

`D-sorganization/openflight_development` is a *companion* to
[`jewbetcha/openflight`](https://github.com/jewbetcha/openflight). Its `README.md`,
`src/`, `docs/`, `ui/`, `firmware/` and `cad/` are a snapshot of upstream; only
`hardware/`, `validation/`, `project-reviews/`, `notes/` and this `backlog/`
directory are original to it.

That split is the whole problem. Carrying a live issue tracker here produced two
kinds of harm:

1. **Divergence from the actual main project.** Software work planned against a
   snapshot goes stale the moment upstream moves. Six of the eight upstream-facing
   issues closed here were re-audited on 2026-08-13 and found *still valid* against
   upstream `80a7bd6` — the tracker was describing a tree that no longer existed.
2. **Backlog noise.** These items are personal bench-and-build work on an
   AGPL hobby project. They competed for attention in fleet-wide issue sweeps,
   readiness audits and remediation waves alongside production repositories, which
   is not what any of those instruments are for.

## The policy from here

- **Software development happens upstream.** File issues and open PRs against
  `jewbetcha/openflight` directly, following its `CONTRIBUTING.md` house rules
  (single-scope PRs, conventional titles, failing-test-first for bugs).
- **This repo stays a companion.** Reviews, measurements, hardware notes, validation
  write-ups and the mirror snapshot. Prose, not tickets.
- **No GitHub issues are filed here.** When something firms up, it graduates to
  `project-reviews/` or to an upstream issue/PR — not to a tracker on this repo.
- **These drafts are a menu, not a commitment.** Pick from them when you sit down at
  the bench. Nothing here is owed to anyone or measured against a date.

## What is in here

| File | Contents |
|---|---|
| [`draft-epics.md`](draft-epics.md) | The three former milestones as draft epics, with all 11 former open issues preserved verbatim: the phased hardware bring-up and the MLM2 Pro validation program. |
| [`upstream-contribution-queue.md`](upstream-contribution-queue.md) | Software work that belongs upstream, including six items closed here in August while still unfinished. |

The living source documents these drafts were derived from remain authoritative and
are still maintained:

- [`hardware/build-plan.md`](../hardware/build-plan.md) — the phased bring-up with gates
- [`hardware/parts-list.md`](../hardware/parts-list.md) — what to buy
- [`validation/mlm2pro-cross-validation.md`](../validation/mlm2pro-cross-validation.md) — the paired-session protocol
- [`project-reviews/2026-07-30-contribution-opportunities.md`](../project-reviews/2026-07-30-contribution-opportunities.md) — ranked contribution analysis

If a draft here and a source document disagree, the source document wins. These
drafts are a point-in-time snapshot of 2026-09-06 and are not maintained.
