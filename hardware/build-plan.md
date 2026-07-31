# OpenFlight Build Plan — Phased Bring-Up

**Date:** 2026-07-30
**Principle (from upstream docs):** change one thing at a time and validate it before the next step — "doing both at once makes any failure ambiguous." Every phase below ends with a **gate**: a concrete command whose output proves the phase worked. Don't advance on a red gate.

Progress is tracked as GitHub issues on this repo (label `build`).

## Phase 0 — Bench prep (no Pi required, can start today)

- [ ] Inspect both OPS243 boards: confirm non-WiFi variant, note firmware/serial numbers, label **A** (build unit) and **B** (bench unit).
- [ ] Solder the R17 resistor (47 kΩ) on the SEN-14262. Visual gate: LED flashes on clap, does **not** stay lit. If stuck high → swap to 33 kΩ.
- [ ] Optional Windows bench check: `uv run python scripts/hardware-test/test_rolling_buffer_persist.py --setup` against a COM port if the script accepts a port override — otherwise defer OPS flash setup to Phase 2 on the Pi. (Repo targets Linux/macOS; treat Windows as read-only dev, not hardware host.)
- [ ] Read: `docs/sound-trigger-wiring.md`, `docs/PARTS.md`, `docs/iwr6843/README.md`, `docs/ops243-uart-migration.md` end-to-end.

## Phase 1 — Pi base system

- [ ] Flash Raspberry Pi OS 64-bit; boot; network up.
- [ ] `git clone https://github.com/jewbetcha/openflight.git && cd openflight && ./scripts/setup/setup.sh` (interactive; handles uv, deps, UI build, one-time hardware config prompts, auto-start).
- [ ] Display working (HMTECH via HDMI/USB touch, or Touch Display 2 via DSI).
- **Gate:** `scripts/start-kiosk.sh --mock` → UI at `http://localhost:8080` shows simulated shots.

## Phase 2 — OPS243 over USB (speed only, no trigger yet)

- [ ] Connect OPS243-A (unit A) via USB.
- [ ] One-time flash config: `uv run python scripts/hardware-test/test_rolling_buffer_persist.py --setup` → power-cycle radar (unplug, 3 s, replug) → `--test`.
- **Gate:** `--test` passes (rolling buffer persists across power cycle; HOST_INT trigger mode armed from flash).

## Phase 3 — Sound trigger

- [ ] Wire per `docs/sound-trigger-wiring.md`: SEN-14262 VCC→Pi 3.3V (pin 1), GND→Pi GND (pin 6), GATE→OPS J3 pin 3 (HOST_INT); OPS J3 pin 10 → Pi GND (shared ground). J3 pin 1 is at the **right** end of the header — confirm silkscreen, don't infer.
- [ ] `uv run python scripts/hardware-test/test_sound_trigger_hardware.py` → clap → "TRIGGER RECEIVED", 4096 I/Q samples.
- [ ] Full diagnostic: `uv run python scripts/hardware-test/diagnose.py` (checks 1–3 and 6 apply; K-LD7 checks skip).
- **Gate:** clap-triggered captures are reliable; then hit real balls → plausible ball speed, club speed, smash in UI. Log a session and skim the JSONL (`shot_detected`, `rolling_buffer_capture`, `trigger_diagnostic` rows).

**Milestone: working speed/spin launch monitor (~$400 configuration).** Useful immediately, and the MLM2 Pro can already cross-check ball speed from here.

## Phase 4 — OPS243 to GPIO UART (Layout A prerequisite for the IWR6843)

The Pi can't power both radars over USB; the validated layout moves the OPS to the GPIO header.

- [ ] Follow `docs/ops243-uart-migration.md`: OPS 5V (J3-9)→Pi pin 2/4, GND (J3-10)→Pi GND, OPS TxD (J3-7)→Pi RXD0 (pin 10), OPS RxD (J3-6)→Pi TXD0 (pin 8). TX/RX crossed.
- [ ] `raspi-config`: disable serial login shell, enable serial hardware, reboot. On Pi 5 the header UART is **`/dev/ttyAMA0`** (do NOT use `/dev/serial0` → that's the debug header).
- [ ] User in `dialout` + `gpio` groups.
- **Gate:** OPS works exactly as in Phase 3 but on `--radar-port /dev/ttyAMA0` (or `--ops-port`) — sound trigger still fires, speeds still read. Validate this alone **before** the TI board is connected.

## Phase 5 — IWR6843LEVM bring-up (when it arrives)

- [ ] Verify board variant + connector; verify checked-in firmware hash: `sha256sum firmware/releases/l3_dump_vTX2_hwa_window53_12loops_18frames_4ms_v2.bin` → `3045bb2f…e7fcb`.
- [ ] Identify CP2105 **Enhanced/UARTA** interface (usually `/dev/ttyUSB0`, by-id `…if00-port0`) — not the Standard interface.
- [ ] Flash mode (S1.1 ON, S1.2 OFF, S1.3 ON, S1.4 ON, S1.5 OFF) → `uv run python firmware/flash_iwr6843.py --probe --port /dev/ttyUSB0` → then flash the release image → functional mode (S1.1 OFF …) → RESET.
- [ ] Extend the GATE splice three ways: detector GATE → OPS HOST_INT **and** Pi BCM17 (pin 11). Soldered or lever-connector splice, not twisted wire.
- [ ] Mount behind ball, antenna face down the target line, board rotated so the vertical virtual array is vertical (TX above RX). Start ~6" (0.152 m) antenna-center height, ~10° tilt as a starting point.
- [ ] Measure geometry honestly (antenna center, common floor reference): tee slant m, net m, tilt deg (inclinometer!), radar height m, ball height m (0.021 mat / 0.040 tee).
- [ ] First run with `--debug` and explicit ports/config/geometry (see operator guide's example command).
- **Gate 1 (trigger/dump):** clap → `[IWR6843] Capture #N complete: 549542 bytes`, `rejected_by_ball_tracker` (expected for claps), firmware health `active=1 … rf_faults=0`.
- **Gate 2 (real shots):** hit balls → session shows `Angle source: radar` on trusted shots; `iwr6843_capture` entries carry `capture_path` in debug mode.
- [ ] Calibration session: `scripts/iwr6843/calibrate.py --shots 20 --club 7i …` (stop the kiosk first — it owns BCM17). Set tilt by **physical measurement**; ignore edge-of-sweep tilt candidates (known-unreliable, monotonic objective).
- [ ] If measuring club path: measure boresight-to-target-line angle and pass `--iwr6843-azimuth-offset-deg` (not optional trim — absorbs the shipped array-calibration phase offset). Right-handed only. Run the 3-session separation test (`scripts/iwr6843/club_path_report.py`).

## Phase 6 — Enclosure & permanent mounting

- [ ] Print IARC case v3 parts for the chosen display; assemble (Pi, OPS mount, sensor housing, display shell).
- [ ] Solve the IWR6843 mount (no STL in the IARC set — check upstream first; else design one honoring board rotation + antenna clearance). Candidate upstream contribution.
- [ ] Re-measure ALL geometry after enclosure/mount changes (mounting shifts = angle bias), and re-run a short calibration session.

## Phase 7 — Cross-validation & ongoing development

- [ ] Run the MLM2 Pro protocol in [validation/mlm2pro-cross-validation.md](../validation/mlm2pro-cross-validation.md).
- [ ] Feed findings into upstream issues/PRs (see project-reviews/ for the opportunity list).
- Bench unit B + saved `--debug` sessions enable offline work: `scripts/iwr6843/replay.py` (angle estimator), `scripts/analysis/replay_spin_dechirp.py` (next-gen spin), `compare_trackman.py` (comparison tooling).

## Standing rules learned from upstream docs

- Power problems masquerade as everything — intermittent USB disconnects / dual-radar failures → check power first.
- Never trust a geometry number you didn't measure *after* the last time anything moved.
- A clap is a trigger test, not a shot test; `rejected_by_ball_tracker` on claps is success.
- Session JSONLs + `--debug` dumps are the raw material for all offline analysis — hoard them, and keep notes (club, geometry, intent) per session; they're worthless without setup metadata.
