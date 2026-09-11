# Development Log — openflight_development

State table for every feature in flight in this repository. Update
entries **in place**; never append dated sections. One entry per
feature, from proposal to ship. See the `development-logs` section of
`AGENTS.md` for the binding rules and
`shared_scripts/development_log.py` for the validator.

- **Portfolio:** personal
- **WIP limit:** 2
- **Last audited:** 2026-09-11 by bootstrap

## States

`proposed` → `in_progress` → `in_review` → `shipped`, with `parked`
reachable from any live state and `abandoned` from `parked`.
`shipped` never returns to `in_progress`; open a new entry instead.

## Active

### DL-0001 · Chore Ci Uv Migration

- **State:** parked
- **Owner:** unassigned
- **PR:** not created
- **Paths:** `.` — scope not yet narrowed; set real globs when
  this entry is reactivated.
- **Started:** 2026-09-11
- **Last verified:** 2026-09-11 (`ef0664a`)
- **Summary:** Seeded from local branch `chore/ci-uv-migration`, which is
  2 commit(s) ahead of the default branch with no
  development-log entry.
- **Parked:** 2026-09-11 — seeded during fleet rollout. Assign a
  governing issue and set `Paths` before moving this to a live
  state; a live entry without a real issue is orphaned by
  definition.

### DL-0002 · Docs 22 Iwr6843 Accuracy Comparison

- **State:** parked
- **Owner:** unassigned
- **PR:** not created
- **Paths:** `.` — scope not yet narrowed; set real globs when
  this entry is reactivated.
- **Started:** 2026-09-11
- **Last verified:** 2026-09-11 (`bf3b4fb`)
- **Summary:** Seeded from local branch `docs/22-iwr6843-accuracy-comparison`, which is
  2 commit(s) ahead of the default branch with no
  development-log entry.
- **Parked:** 2026-09-11 — seeded during fleet rollout. Assign a
  governing issue and set `Paths` before moving this to a live
  state; a live entry without a real issue is orphaned by
  definition.

### DL-0003 · Docs Face Path Weighting Correction

- **State:** parked
- **Owner:** unassigned
- **PR:** not created
- **Paths:** `.` — scope not yet narrowed; set real globs when
  this entry is reactivated.
- **Started:** 2026-09-11
- **Last verified:** 2026-09-11 (`de270f6`)
- **Summary:** Seeded from local branch `docs/face-path-weighting-correction`, which is
  2 commit(s) ahead of the default branch with no
  development-log entry.
- **Parked:** 2026-09-11 — seeded during fleet rollout. Assign a
  governing issue and set `Paths` before moving this to a live
  state; a live entry without a real issue is orphaned by
  definition.

### DL-0004 · Docs Genericise Launch Monitor Reference

- **State:** parked
- **Owner:** unassigned
- **PR:** not created
- **Paths:** `.` — scope not yet narrowed; set real globs when
  this entry is reactivated.
- **Started:** 2026-09-11
- **Last verified:** 2026-09-11 (`7f6c953`)
- **Summary:** Seeded from local branch `docs/genericise-launch-monitor-reference`, which is
  2 commit(s) ahead of the default branch with no
  development-log entry.
- **Parked:** 2026-09-11 — seeded during fleet rollout. Assign a
  governing issue and set `Paths` before moving this to a live
  state; a live entry without a real issue is orphaned by
  definition.

### DL-0005 · Docs Upstream Docs Drift Cleanup

- **State:** parked
- **Owner:** unassigned
- **PR:** not created
- **Paths:** `.` — scope not yet narrowed; set real globs when
  this entry is reactivated.
- **Started:** 2026-09-11
- **Last verified:** 2026-09-11 (`b7fa2a1`)
- **Summary:** Seeded from local branch `docs/upstream-docs-drift-cleanup`, which is
  1 commit(s) ahead of the default branch with no
  development-log entry.
- **Parked:** 2026-09-11 — seeded during fleet rollout. Assign a
  governing issue and set `Paths` before moving this to a live
  state; a live entry without a real issue is orphaned by
  definition.

### DL-0006 · Feat Club Data Consolidation

- **State:** parked
- **Owner:** unassigned
- **PR:** not created
- **Paths:** `.` — scope not yet narrowed; set real globs when
  this entry is reactivated.
- **Started:** 2026-09-11
- **Last verified:** 2026-09-11 (`03b99d2`)
- **Summary:** Seeded from local branch `feat/club-data-consolidation`, which is
  1 commit(s) ahead of the default branch with no
  development-log entry.
- **Parked:** 2026-09-11 — seeded during fleet rollout. Assign a
  governing issue and set `Paths` before moving this to a live
  state; a live entry without a real issue is orphaned by
  definition.

### DL-0007 · Feat Mlm2Pro Adapter

- **State:** parked
- **Owner:** unassigned
- **PR:** not created
- **Paths:** `.` — scope not yet narrowed; set real globs when
  this entry is reactivated.
- **Started:** 2026-09-11
- **Last verified:** 2026-09-11 (`0bfb9e8`)
- **Summary:** Seeded from local branch `feat/mlm2pro-adapter`, which is
  1 commit(s) ahead of the default branch with no
  development-log entry.
- **Parked:** 2026-09-11 — seeded during fleet rollout. Assign a
  governing issue and set `Paths` before moving this to a live
  state; a live entry without a real issue is orphaned by
  definition.

### DL-0008 · Fix Security And Logging Standards

- **State:** parked
- **Owner:** unassigned
- **PR:** not created
- **Paths:** `.` — scope not yet narrowed; set real globs when
  this entry is reactivated.
- **Started:** 2026-09-11
- **Last verified:** 2026-09-11 (`ca83330`)
- **Summary:** Seeded from local branch `fix/security-and-logging-standards`, which is
  1 commit(s) ahead of the default branch with no
  development-log entry.
- **Parked:** 2026-09-11 — seeded during fleet rollout. Assign a
  governing issue and set `Paths` before moving this to a live
  state; a live entry without a real issue is orphaned by
  definition.

### DL-0009 · Fix Windows Test And Code Fixes

- **State:** parked
- **Owner:** unassigned
- **PR:** not created
- **Paths:** `.` — scope not yet narrowed; set real globs when
  this entry is reactivated.
- **Started:** 2026-09-11
- **Last verified:** 2026-09-11 (`6b36c15`)
- **Summary:** Seeded from local branch `fix/windows-test-and-code-fixes`, which is
  1 commit(s) ahead of the default branch with no
  development-log entry.
- **Parked:** 2026-09-11 — seeded during fleet rollout. Assign a
  governing issue and set `Paths` before moving this to a live
  state; a live entry without a real issue is orphaned by
  definition.

### DL-0010 · Refactor 42 Modular Server Architecture

- **State:** parked
- **Owner:** unassigned
- **PR:** not created
- **Paths:** `.` — scope not yet narrowed; set real globs when
  this entry is reactivated.
- **Started:** 2026-09-11
- **Last verified:** 2026-09-11 (`b5fb641`)
- **Summary:** Seeded from local branch `refactor/42-modular-server-architecture`, which is
  2 commit(s) ahead of the default branch with no
  development-log entry.
- **Parked:** 2026-09-11 — seeded during fleet rollout. Assign a
  governing issue and set `Paths` before moving this to a live
  state; a live entry without a real issue is orphaned by
  definition.

## Shipped (Last 90 Days)

Entries stay here for 90 days after merge, then move to the archive.

## Archive

Older entries live in `DEVELOPMENT_LOG_ARCHIVE_<year>.md`.
