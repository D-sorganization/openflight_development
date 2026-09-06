# Draft Epics — Hardware Bring-Up and Validation

**Archived:** 2026-09-06 · **Draft only — not filed, not tracked.**

The three former milestones of this repository, preserved as draft epics. Every
former open issue is reproduced below **verbatim**, under the epic it belonged to.
Issue numbers are retained only so that older references and the closure comments
on GitHub still resolve; the issues themselves are closed and will not be reopened.

The bodies are unedited, so they still say `jewbetcha/openflight`; that repo was
renamed and now redirects to [`open-flight/openflight`](https://github.com/open-flight/openflight).

## The dependency chain

This backlog is almost entirely serial, because it is physical work. That is the
single most useful thing to know about it — there is no parallel lane to pick up
when the current step is blocked on a part in the mail.

```
Build chain
  D1 bench prep ─┐
                 ├─► D4 Pi base ─► D5 OPS bring-up ─► D6 sound trigger ─► [M1]
  D2 procure ────┘
                 [M1] ─► D7 GPIO UART ─► D8 IWR6843 ─► D9 case + mount ─► [M2]

Validation chain
  [M1] ─► D10 interference A/B/AB ─┐
                                   ├─► D12 paired session ─► D21 driver truth data ─► [M3]
  [M2] ────────────────────────────┘
```

`D1` (bench prep) and `D2` (procurement) are the only two that can start
concurrently, and `D1` needs no Pi at all. `D10` (the interference A/B/AB) only
needs the ~$400 speed monitor from `D6`, so it is available well before the angle
radar arrives — and it must be settled before `D12`, or any later disagreement can
be blamed on OPS243/MLM2 cross-talk rather than on the instrument.

## Gate discipline

Every phase ends in a gate: a concrete command whose output proves the phase
worked. This mirrors the upstream principle that doing two things at once makes
any failure ambiguous. If a gate is red, the next phase is not started — that rule
is worth more than the issue tracker ever was.

---

## Draft Epic A — M1: A working speed monitor (~$400)

**Outcome:** an OPS243-A + Raspberry Pi 5 + sound-trigger rig that reports
plausible ball speed, club speed and smash factor on real shots, with a reliable
clap trigger and rolling-buffer capture that survives a power cycle.

**Why this epic is the one that matters.** It is genuinely useful on its own — no
angle radar required — and it is the point at which MLM2 Pro ball-speed spot checks
become possible, which is the entire premise of the contribution strategy. Nothing
downstream is reachable without it.

**Known traps captured in the drafts below.** The OPS243 WiFi (`-W`) variant locks
serial to 19200 baud and is incompatible with I/Q transfer, so the variant check in
`D1` is not a formality. The SEN-14262 needs an R17 gain resistor for 3.3 V
operation, and its LED behaviour is the gate. Rolling-buffer mode must persist
across a power cycle because upstream documents a firmware bug where the HOST_INT
pin mode switches on runtime mode transitions.

**Draft issues:** `D1`, `D2`, `D4`, `D5`, `D6`

<details>
<summary><b>D1 — Phase 0: Bench prep - verify OPS243 variants, solder R17</b></summary>

> Archived from closed issue #1 · labels: `build`

From [hardware/build-plan.md](https://github.com/D-sorganization/openflight_development/blob/main/hardware/build-plan.md) Phase 0 - no Pi required, can start now.

- [ ] Inspect both OPS243 boards: confirm neither is the WiFi `-W` variant (WiFi locks serial to 19200 baud - incompatible with I/Q transfer per upstream PARTS.md). Note serial numbers, label unit A (build) and unit B (bench).
- [ ] Solder 47 kOhm through-hole resistor into R17 on the SEN-14262 (gain fix for 3.3 V operation). Gate: LED flashes on clap, does not stick on. Fallback: 33 kOhm.
- [ ] Read upstream docs end-to-end: sound-trigger-wiring.md, PARTS.md, iwr6843/README.md, ops243-uart-migration.md.

**Exit gate:** both radars identified and labeled; SEN-14262 modded and LED behavior verified.

</details>

<details>
<summary><b>D2 — Procure core parts (Pi 5, display, PSU, SD, cables, resistors, RPT balls)</b></summary>

> Archived from closed issue #2 · labels: `procurement`

Buy the core block from [hardware/parts-list.md](https://github.com/D-sorganization/openflight_development/blob/main/hardware/parts-list.md) (~$220-235):

- [ ] Raspberry Pi 5 (4 GB+)
- [ ] Display - DECIDE FIRST: HMTECH 7" 1024x600 vs Raspberry Pi Touch Display 2 (IARC case parts differ per display; pick before printing)
- [ ] Official 27 W USB-C PSU
- [ ] microSD 64 GB
- [ ] USB-A to micro-USB data cable (OPS243)
- [ ] Data-capable USB cable for IWR6843LEVM (confirm connector when board arrives)
- [ ] Dupont F-F jumper pack (need 8+)
- [ ] 47 kOhm and 33 kOhm through-hole resistors
- [ ] RPT balls (Callaway Chrome Soft X RPT 3-pack) - spin ground truth for validation
- [ ] Decide: powered USB hub needed? (only if an OPS is WiFi variant or Layout B chosen)

</details>

<details>
<summary><b>D4 — Phase 1: Pi base system + mock-mode smoke test</b></summary>

> Archived from closed issue #4 · labels: `build`

From [hardware/build-plan.md](https://github.com/D-sorganization/openflight_development/blob/main/hardware/build-plan.md) Phase 1.

- [ ] Flash Raspberry Pi OS 64-bit, boot, network
- [ ] Clone jewbetcha/openflight and run `./scripts/setup/setup.sh` (interactive: uv, deps, UI build, auto-start prompts)
- [ ] Display working (per display choice)

**Exit gate:** `scripts/start-kiosk.sh --mock` shows simulated shots in the UI at http://localhost:8080.

</details>

<details>
<summary><b>D5 — Phase 2: OPS243 USB bring-up + rolling-buffer flash persistence</b></summary>

> Archived from closed issue #5 · labels: `build`

From [hardware/build-plan.md](https://github.com/D-sorganization/openflight_development/blob/main/hardware/build-plan.md) Phase 2.

- [ ] Connect OPS243 unit A over USB
- [ ] One-time flash config: `uv run python scripts/hardware-test/test_rolling_buffer_persist.py --setup`
- [ ] Power-cycle radar (unplug, wait 3 s, replug)

**Exit gate:** `test_rolling_buffer_persist.py --test` passes - rolling buffer mode persists across power cycle (required for HOST_INT hardware triggers; upstream documents a firmware bug where HOST_INT pin mode switches on runtime mode transitions).

</details>

<details>
<summary><b>D6 — Phase 3: Sound trigger wiring + first real shots</b></summary>

> Archived from closed issue #6 · labels: `build`

From [hardware/build-plan.md](https://github.com/D-sorganization/openflight_development/blob/main/hardware/build-plan.md) Phase 3, following upstream docs/sound-trigger-wiring.md.

- [ ] Wire: SEN-14262 VCC to Pi 3.3V (pin 1); GND to Pi GND (pin 6); GATE to OPS J3 pin 3 (HOST_INT); OPS J3 pin 10 to Pi GND (shared rail). J3 pin 1 is at the RIGHT end - confirm silkscreen.
- [ ] `uv run python scripts/hardware-test/test_sound_trigger_hardware.py` then clap: expect TRIGGER RECEIVED with 4096 I/Q samples
- [ ] Full diagnostic: `uv run python scripts/hardware-test/diagnose.py` (K-LD7 checks will skip)
- [ ] Hit real balls; skim session JSONL (`shot_detected`, `rolling_buffer_capture`, `trigger_diagnostic`)

**Exit gate:** reliable clap triggers AND plausible ball/club speed + smash on real shots. This is the ~$400 working-speed-monitor milestone - MLM2 Pro ball-speed spot checks become possible here.

</details>

---

## Draft Epic B — M2: Full unit with the IWR6843 angle radar

**Outcome:** measured launch angle (and experimental club path) from a
TI IWR6843LEVM mounted in a printed IARC case, with geometry measured rather than
guessed and a calibration session on record.

**The ordering constraint is hard.** The Pi cannot power both radars over USB, so
the OPS243 must move to the GPIO UART header *and be re-validated alone* before the
TI board is connected. On a Pi 5 the header UART is `/dev/ttyAMA0`; `/dev/serial0`
is the debug-header UART and will silently fail to be the thing you meant.

**The open design problem.** The IARC case STL set predates the IWR6843 migration
and carries K-LD7 mounts only — there is no LEVM mount. That gap has to be solved
by anyone building this, which makes a finished mount design the highest-value CAD
contribution available upstream (see `D9`). CAD PRs have historically merged fast
there.

**Geometry is the accuracy budget.** Tilt, tee slant range, net distance, radar
height and ball height are all measured from the antenna centre against a common
floor reference. Wrong values bias the result instead of producing an obvious
startup error, and small mount shifts appear as angle bias — so the mount must be
rigid and the geometry re-measured after any reassembly.

**Draft issues:** `D7`, `D8`, `D9`

<details>
<summary><b>D7 — Phase 4: Migrate OPS243 to Pi GPIO UART (Layout A)</b></summary>

> Archived from closed issue #7 · labels: `build`

From [hardware/build-plan.md](https://github.com/D-sorganization/openflight_development/blob/main/hardware/build-plan.md) Phase 4, following upstream docs/ops243-uart-migration.md. Required before the IWR6843 (the Pi cannot power both radars over USB).

- [ ] Wire OPS 5V (J3-9) to Pi pin 2/4; GND (J3-10) to Pi GND; OPS TxD (J3-7) to Pi RXD0 (pin 10); OPS RxD (J3-6) to Pi TXD0 (pin 8). TX/RX crossed.
- [ ] raspi-config: disable serial login shell, enable serial hardware, reboot
- [ ] Use `/dev/ttyAMA0` on Pi 5 (NOT `/dev/serial0` - that is the debug-header UART)
- [ ] Confirm user in `dialout` and `gpio` groups

**Exit gate:** everything from Phase 3 works identically on `--radar-port /dev/ttyAMA0`, validated BEFORE the TI board is connected (upstream: doing both at once makes any failure ambiguous).

</details>

<details>
<summary><b>D8 — Phase 5: IWR6843LEVM firmware flash + bring-up + calibration</b></summary>

> Archived from closed issue #8 · labels: `build`

From [hardware/build-plan.md](https://github.com/D-sorganization/openflight_development/blob/main/hardware/build-plan.md) Phase 5, following the upstream IWR6843 Operator Guide (docs/iwr6843/README.md).

Board confirmed ordered 2026-07: Digi-Key 296-IWR6843LEVM-ND (TI IWR6843LEVM) - correct variant (#3, closed).

- [ ] On arrival: verify silkscreen says IWR6843LEVM; identify USB connector type and confirm a data-capable cable is on hand; confirm boot-mode switch S1 and RESET button are accessible
- [ ] Verify firmware image hash: sha256 `3045bb2f087b40c228bf1dd5190cf3fac6dbde50682c7927e86714314b0e7fcb`
- [ ] Identify CP2105 Enhanced/UARTA interface (usually /dev/ttyUSB0, by-id ...if00-port0)
- [ ] Flash-mode switches; `firmware/flash_iwr6843.py --probe`; flash release image; functional-mode switches; RESET
- [ ] Three-way GATE splice: detector GATE to OPS HOST_INT AND Pi BCM17 (pin 11), soldered or lever connector
- [ ] Mount: antenna face down target line, vertical array vertical (TX above RX), ~0.152 m height, ~10 deg tilt starting point
- [ ] Measure geometry from antenna center and a common floor reference: tee-m (slant), net-m, tilt-deg (inclinometer), radar-height-m, ball-height-m (0.021 mat / 0.040 tee)
- [ ] First run with `--debug` and explicit ports/config/geometry
- [ ] Calibration session: `scripts/iwr6843/calibrate.py --shots 20 --club 7i ...` (stop kiosk first - it owns BCM17). Set tilt by PHYSICAL measurement; ignore edge-of-sweep tilt candidates (known unreliable upstream).
- [ ] If using club path: measure and pass `--iwr6843-azimuth-offset-deg`; run the 3-session separation test (`scripts/iwr6843/club_path_report.py`). Right-handed only for now.

**Exit gates:** clap gives `Capture complete: 549542 bytes` with `rf_faults=0`; real shots log `Angle source: radar` on trusted shots.

</details>

<details>
<summary><b>D9 — Phase 6: IARC case print + solve IWR6843 mount gap</b></summary>

> Archived from closed issue #9 · labels: `build`, `upstream`

From [hardware/build-plan.md](https://github.com/D-sorganization/openflight_development/blob/main/hardware/build-plan.md) Phase 6.

- [ ] Print IARC case v3 parts for the chosen display (`cad/IARC_case/` - `monitor_shell.stl` vs `Touch_Display2_*.stl` variants). Note upstream PR #147 / merged #156 reworked Touch Display 2 parts.
- [ ] Assemble: Pi, OPS mount, sensor housing, display shell, feet
- [ ] **Solve the IWR6843 mount gap:** the IARC case STL set predates the IWR6843 (K-LD7 mounts only, no LEVM mount). Check upstream cad/ and issues first; if absent, design one. Constraints from the operator guide: board rotated so the vertical virtual array is physically vertical, antenna face unobstructed, rigid mount (small shifts appear as angle bias).
- [ ] Re-measure ALL geometry after mounting; re-run a short calibration session

A finished IWR6843LEVM mount design is a strong upstream contribution - every new builder will need one.

</details>

---

## Draft Epic C — M3: Cross-validated against the MLM2 Pro

**Outcome:** a paired dataset that says, with numbers, how this rig compares
to a commercial reference instrument — and specifically a driver dataset that
upstream has asked for and does not have.

**This is the distinctive contribution.** Upstream's own words are that estimator
limits are "deferred pending a session paired with a reference instrument, which
this repo does not have." All of their truth data to date is three borrowed
TrackMan sessions. An MLM2 Pro plus RPT balls closes that gap.

**The specific upstream ask.** Driver is their weak point: 3.55° MAE and +3.39°
bias in the July 2026 field report, dominated by false-accepted slow "ghost" tracks
— the TI radar locking onto 55–57 mph movers while the OPS measured 152–158 mph
balls. Their proposed fix (reject TI tracks below ~65–70% of OPS ball speed, then
OPS-guided fast-track recovery) recovered 3 of 4 bad driver shots at ~2.6° MAE in
offline replay, and is explicitly blocked on more truth data. Driver blocks with
RPT balls are exactly that dataset.

**Settle interference first.** `D10` is not optional politeness. The MLM2 Pro radar
plausibly shares the OPS243's K-band neighbourhood (24.125 GHz CW); the IWR6843 at
60 GHz is unaffected. If cross-talk is not characterised before the paired session,
a maintainer can reasonably attribute any disagreement to cross-talk rather than to
the instrument, and the finding becomes contestable.

**Run with `--debug`.** The `.l3dump` captures are what make offline replay possible
(`scripts/iwr6843/replay.py`), and replay is how a dataset becomes a proposed fix
rather than just a complaint.

**Draft issues:** `D10`, `D12`, `D21`

<details>
<summary><b>D10 — Radar interference check: MLM2 Pro + OPS243 (A/B/AB protocol)</b></summary>

> Archived from closed issue #10 · labels: `validation`, `research`

From [validation/mlm2pro-cross-validation.md](https://github.com/D-sorganization/openflight_development/blob/main/validation/mlm2pro-cross-validation.md).

The MLM2 Pro radar likely operates in the same K-band neighborhood as the OPS243 (24.125 GHz CW). Interference is an open question to TEST, not assume away. (IWR6843 is 60 GHz - unaffected.)

Protocol:
- [ ] A: 10 shots OpenFlight only - record spin read rate, spin_snr, ball-speed spread
- [ ] B: 10 shots MLM2 Pro only - confirm normal behavior
- [ ] AB: 10 shots both running - compare OpenFlight spin_snr / read rate / trigger behavior vs A, and MLM2 readings vs B
- [ ] If degraded: try lateral separation, then alternating-shot capture as fallback
- [ ] Write up result in notes/ - publishable upstream (other MLM2 Pro owners will ask)

</details>

<details>
<summary><b>D12 — First full paired validation session (driver/7i/wedge, RPT balls)</b></summary>

> Archived from closed issue #12 · labels: `validation`

From [validation/mlm2pro-cross-validation.md](https://github.com/D-sorganization/openflight_development/blob/main/validation/mlm2pro-cross-validation.md). Prereqs: build at M2, interference check done, adapter script working.

- [ ] Session header: date, location, net distance, full OpenFlight geometry flags, commit SHA, MLM2 app version, ball type per block
- [ ] Run with `--debug --session-location mlm2-validation`
- [ ] Blocks: driver 10-15 (RPT), 7i 10-15 (RPT), PW/SW 10-15 (RPT), optional 5-10 range balls
- [ ] Select matching club in UI per block; log shot order
- [ ] Export MLM2 CSV; pair by sequence + timestamp; count device-only shots (detection-rate asymmetry is a finding)
- [ ] Report: detection rate, ball-speed bias/std, launch V/H bias/RMSE split by angle_source, spin read rate + accepted-delta + rejection histogram, club speed (with MLM2 caveat), carry labeled model-vs-model
- [ ] Autopsy the 2-3 worst disagreements via JSONL diagnostics and .l3dump replay

Driver block matters most upstream: the IWR6843 driver ghost-track problem (3.55 deg MAE, +3.39 deg bias in the July field report) needs driver truth data.

</details>

<details>
<summary><b>D21 — Truth-data program: driver ghost-track gate dataset for upstream</b></summary>

> Archived from closed issue #21 · labels: `validation`, `upstream`

**Tier 2 - the unique-value contribution** ([contribution opportunities](https://github.com/D-sorganization/openflight_development/blob/main/project-reviews/2026-07-30-contribution-opportunities.md) item 5).

Upstream's driver accuracy is their weak point: 3.55 deg MAE, +3.39 deg bias, dominated by false-accepted slow "ghost" tracks (TI locked onto 55-57 mph movers while OPS measured 152-158 mph balls). Their roadmap fix - reject TI tracks below ~65-70% of OPS ball speed, then OPS-guided fast-track recovery (offline replay recovered 3 of 4 bad driver shots at ~2.6 deg MAE) - explicitly "needs more truth data before shipping."

- [ ] After M2+M3 prereqs: dedicated driver blocks (10-15 shots, RPT balls) in every paired MLM2 session
- [ ] Log with `--debug` so .l3dump captures replay offline (`scripts/iwr6843/replay.py`)
- [ ] Deliver paired dataset + replay results to upstream (issue first, offer the data)
- [ ] Also feeds: two-dot relaxed-confidence thresholds, the 8-deg agreement gate, select-vs-average - all "deferred pending a session paired with a reference instrument"

</details>

---

## What was deliberately not carried forward

- **The milestones themselves.** `M1`, `M2` and `M3` were closed along with the
  issues. The three epics above replace them as prose.
- **Issue #11** (MLM2 Pro CSV adapter for `compare_trackman.py`) — completed and
  closed on its own merits before this archive; the script exists. Upstreaming it as
  `--source mlm2pro` support is carried in
  [`upstream-contribution-queue.md`](upstream-contribution-queue.md).
- **Issue #3** (verify the IWR6843 order is the LEVM variant) — resolved 2026-07;
  Digi-Key 296-IWR6843LEVM-ND is the correct variant. The on-arrival silkscreen
  check survives inside `D8`.
