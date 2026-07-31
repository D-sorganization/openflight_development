# MLM2 Pro Cross-Validation Protocol

**Date:** 2026-07-30
**Instrument:** Rapsodo MLM2 Pro (dual camera + radar), owned.
**Adapted from:** upstream `docs/trackman-test-process.md` — the project's established methodology with TrackMan as truth. This doc maps that process onto the MLM2 Pro.

## Why this matters upstream (not just for my build)

The public repo repeatedly names its biggest gap — a reference instrument:

- README: *"help validating [the dechirped spin estimator] against launch-monitor truth data is especially welcome."*
- IWR6843 Operator Guide, estimator limitations: three known-unresolved issues (curvature criterion not scale-normalised, select-vs-average policy, the 8° agreement gate resting on one session) are *"deferred pending a session paired with a reference instrument, which this repo does not have."*
- `compare_trackman.py` exists but TrackMan access is rare; a repeatable consumer-reference workflow would let more contributors produce comparison data.

A well-run MLM2 Pro protocol + published datasets is likely the **highest-leverage contribution I can make** with hardware I already own.

## Know your reference instrument (honest error bars)

The MLM2 Pro is a consumer unit, not a TrackMan. Treat it as a **reference for bias/trend detection**, not absolute truth.

| Metric | MLM2 Pro basis | Trust level for validation |
|--------|----------------|---------------------------|
| Ball speed | Radar, measured | **High** — primary anchor metric |
| Launch angle (vertical) | Camera (Shot Vision), measured | **Good** — key for IWR6843 comparison |
| Launch direction (horizontal) | Camera, measured | **Good** |
| Spin rate / spin axis | **Measured only with RPT-marked balls** (Callaway Chrome Soft X RPT); otherwise algorithmically estimated | **Good with RPT balls; near-worthless without** |
| Club speed | Radar-derived; consumer reviews note it's less reliable than ball data | **Medium** — compare, but don't tune OpenFlight club speed against it alone |
| Carry / total | Simulated from launch conditions (especially indoors into a net) | **Low as truth** — both devices model carry; compare models, don't calibrate to it |

Rules that follow:

1. **RPT balls are mandatory for spin sessions.** Log ball type per shot block.
2. Indoors, compare **launch conditions** (speed, angles, spin), not outcomes (carry) — both units model carry from conditions, so carry agreement only tests whose ballistics model is which.
3. Log the MLM2 Pro app/firmware version each session; consumer devices change behavior across updates.

## Physical setup & interference check

Both units sit **behind the ball**: MLM2 Pro at its specified distance (~6–8 ft per Rapsodo setup guidance), OpenFlight at 3–5 ft. Side-by-side or stacked placement must not block either unit's view/beam.

⚠️ **Radar interference is an open question to test, not assume away.** The MLM2 Pro's radar operates in K-band (same neighborhood as the OPS243's 24.125 GHz CW). The IWR6843 is at 60 GHz (no conflict). Before trusting joint sessions, run the A/B/AB check:

1. **A:** 10 shots, OpenFlight only → note spin read rate, spin SNR (`spin_snr`), ball-speed spread.
2. **B:** 10 shots, MLM2 Pro only → note its readings behave normally.
3. **AB:** 10 shots, both running → compare OpenFlight `spin_snr` / read rate / trigger behavior vs session A, and MLM2 readings vs session B.

If AB degrades OpenFlight spin SNR or MLM2 readings, try greater lateral separation, then alternating-shot capture as the fallback (worse: no shot-paired data). Record the outcome in `notes/` — this result is itself useful to upstream (others will ask).

## Session protocol

**Fixed per session (record in a session header note):**

- Date, location, indoor/outdoor, net distance
- OpenFlight geometry actually passed on the command line (tee-m, net-m, tilt-deg, radar-height-m, ball-height-m, azimuth-offset-deg)
- OpenFlight commit SHA; MLM2 app version; ball type (RPT or not); mat vs tee per block
- Club per block; any intentional shot shaping (low/high, push/pull, cuts)

**Command:** run with `--debug` (keeps IWR `.l3dump` captures for replay) and a session location tag, e.g.:

```bash
scripts/start-kiosk.sh --debug --session-location mlm2-validation [geometry flags…]
```

**Shot matrix (target per full session):**

| Block | Club | Shots | Ball | Purpose |
|-------|------|-------|------|---------|
| 1 | Driver | 10–15 | RPT | High speed, low spin — spin lower-rail behavior (≤~3100 RPM reduced-confidence zone) |
| 2 | 7-iron | 10–15 | RPT | Mid speed/spin — the plausibility-gating club class |
| 3 | PW or SW | 10–15 | RPT | High spin — upper-rail behavior (~12000 RPM rejection zone) |
| 4 (optional) | Any | 5–10 | range balls | Spin estimator behavior on unmarked balls |

Select the matching club in the OpenFlight UI per block (drives fallbacks and spin rail filtering). Keep shot order logged — pairing is by sequence + timestamp.

## Data collection & pairing

- **OpenFlight:** session JSONL from `~/openflight_sessions/` (rows: `shot_detected`, `rolling_buffer_capture`, `iwr6843_capture`, `trigger_diagnostic`), plus `.l3dump` files (debug mode).
- **MLM2 Pro:** export session CSV from the Rapsodo app (premium feature); if export is unavailable, transcribe per-shot from the app immediately after the session (tedious but workable for 30–45 shots).
- **Pairing:** shot index + wall-clock. Flag and exclude shots only one device saw — but *count* them: detection-rate asymmetry is a finding, not noise (upstream's first question: "Did OpenFlight detect the same shot the reference saw?").

## Analysis

Upstream already ships `scripts/analysis/compare_trackman.py` (per-club bias + row-level deltas for ball speed, club speed, smash, vertical/horizontal launch, spin, carry, plus OpenFlight spin diagnostics columns). Two options:

1. **Adapter script** that reshapes an MLM2 Pro CSV export into the TrackMan CSV column layout `compare_trackman.py` expects → zero upstream changes, works today. Start here, in this repo.
2. **Upstream contribution:** `--source mlm2pro` (or a generic `--source` column-mapping) for `compare_trackman.py` + a `docs/mlm2pro-test-process.md`. Do this after the adapter is proven on 2–3 real sessions.

**Per session, report (mirroring upstream's post-session checklist):**

- Detection rate: shots seen by both / OpenFlight-only / MLM2-only
- Ball speed: bias, stddev of deltas (expect tight agreement — if not, something is wrong with setup, not physics)
- Launch angle V/H: bias, RMSE; split by `angle_source` (radar vs estimated) — only `Angle source: radar` shots validate the IWR estimator
- Spin: read rate, delta on accepted readings, rejection reasons histogram (`spin_rejection_reason`), rail flags — do **not** advocate loosening guardrails to raise read rate unless accepted candidates prove accurate (explicit upstream rule)
- Club speed: bias with the MLM2 caveat noted
- Carry: report deltas for curiosity, labeled "model vs model"
- Per-shot outlier autopsies: for the 2–3 worst disagreements, pull the JSONL diagnostics (spin SNR, track RMS, inlier count, rejection reasons) and the `.l3dump` replay

**Statistics:** with n≈10–15 per club, stick to mean bias ± stddev and Bland-Altman-style plots per metric; resist significance theater. Trends across sessions matter more than any single session.

## Deliverables ladder (each rung is upstream-useful)

1. First joint session ran + interference check documented → `notes/`
2. MLM2→TrackMan-format adapter script + first comparison CSV → this repo
3. 3+ sessions of paired data with per-club bias summary → shareable dataset
4. Upstream PR: `compare_trackman.py` MLM2 Pro source support + process doc
5. Upstream issue-quality data: IWR estimator behavior vs reference on the exact open questions (8° gate placement, select-vs-average on disagreeing-but-healthy channels), and dechirp spin estimator truth pairs
