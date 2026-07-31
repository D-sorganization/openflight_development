# OpenFlight Repository State Review

**Date:** 2026-07-30 · **Commit reviewed:** `9b61f0a` (main, current with upstream)
**Scale:** Python src ≈ 25,700 LOC / 67 modules · tests ≈ 22,200 LOC / 68 files · UI ≈ 6,760 LOC (React 19 + TS + Vite, zustand, vitest + Playwright)
**Method:** full-code read of production paths, complete test-suite execution on Windows, doc/CI audit. Findings follow my review preferences (aggressive on DRY, tests non-negotiable, explicit > clever, engineered-enough): numbered issues, lettered options, recommendation first. Decisions are captured as GitHub issues on this repo since this review was produced asynchronously.

## Executive summary

OpenFlight is in the middle of its biggest transition — the K-LD7 angle radars were deprecated 2026-07-20 and replaced by the TI IWR6843LEVM (merged PRs #155/#160, July). The new `iwr6843/` package is the best code in the repo (frozen dataclasses, DI, validation provenance in docstrings); the deprecated `kld7/` package is the most complex (6,354 LOC, 25% of the codebase) and still sits on the default startup path. Test culture is genuinely strong (1,166 behavioral tests, replay tests against recorded hardware captures, CI-enforced test inclusion on PRs). The main liabilities are: `server.py` as a 3,495-line god-module with 27 globals; a web of duplicated club-physics tables that have **already numerically diverged**; dead camera code on the production import path; and CI that drifted from the project's own uv-based toolchain. On Windows, 22 of 1,166 tests fail — all environmental, two of them genuine test bugs. Nothing here is fatal; the codebase is healthy for its age and unusually well-instrumented for a hobby project.

## Architecture (as verified in code)

Production entry point is `server.py:main()` (~50 CLI flags), wrapped by `scripts/start-kiosk.sh` (682 lines). Shot flow:

1. Impact sound → SEN-14262 GATE → OPS243 HOST_INT; `SoundTrigger.wait_for_trigger` (`rolling_buffer/trigger.py:1016`) blocks until the radar dumps ~40.6 KB of I/Q JSON.
2. `RollingBufferMonitor._capture_loop` (own thread) → `RollingBufferProcessor.process_capture` (`processor.py:1637`): FFT mode-based ball speed, overlapping-FFT timeline, club speed, impact estimate, multitaper spin.
3. `_create_shot` builds the 45-field `Shot` dataclass.
4. **`server.on_shot_detected` (`server.py:2024–2520`) runs synchronously on the capture thread**: IWR6843 correlation → K-LD7 vertical/horizontal gating → camera fallback (dead, see F4) → estimator fallback → cosine speed correction → optional calculated spin → carry (RK4 ballistics or table) → session log → `socketio.emit("shot")` → sim-connector fan-out (GSPro/OpenGolfSim).
5. React UI: socket.io singleton → zustand stores → `ShotDisplay`.

The IWR6843 path is production-integrated but **opt-in** (`--iwr6843`); a GPIO edge on the shared trigger line queues a 768 KiB UART dump correlated by OPS impact timestamp, feeding the frozen "LCMF-v1" estimator + club path.

### Where the docs lie (verified divergences)

| Doc claim (CLAUDE.md/README) | Reality |
|---|---|
| Architecture diagram: UI→Flask→Monitor→OPS + 2×KLD7 | Omits `iwr6843/`, `sim/`, `cloud/`, `ballistics.py`, camera modules |
| "Min ball speed: 35 mph" | Validation floor is **15 mph** (`monitor.py:760`; `trigger.py:32`); 35 only in a non-default trigger (`trigger.py:420`) |
| "CFAR threshold: SNR > 15.0" | No such constant; K-LD7 OS-CFAR uses `threshold_factor=8.0` (`kld7/radc.py:295`) |
| "Shot timeout: 0.5 s" | Constant no longer exists (removed with streaming mode) |
| Carry lives in `launch_monitor.py` | Split 3 ways: base table, spin-adjusted table (`rolling_buffer/monitor.py:94`), RK4 sim (`ballistics.py:253`) |

→ Cheap, high-goodwill docs PR (see contribution doc, T1-3).

## Module health (condensed)

| Area | LOC | Health |
|---|---|---|
| `server.py` | 3,495 | God-module: 27 globals, 50 `print()`s mixed with logging, 500-line shot handler |
| `ops243.py` | 1,727 | Clean; exceptional field-debugging comments (write-timeout deadlock, drain budgets) |
| `rolling_buffer/` | 4,618 | Core path, sound; two oversized functions (`detect_spin` 466 lines; `process_capture`) |
| `kld7/` | 6,354 | Deprecated hardware, heaviest complexity; `extract_launch_angle` = 837 lines / 24 params; monkey-patches its third-party driver lib |
| `iwr6843/` | 4,243 | Newest, cleanest; validation provenance in docstrings |
| `sim/` + `gspro/` | 1,085 | Clean, well-abstracted connector framework |
| `cloud/` | 1,138 | Clean, DI, tested; `filtering.py` is an explicit tested privacy boundary |
| `camera_tracker.py` + `camera/` | 2,030 | **Dead**: cv2 deps commented out of pyproject; `CV2_AVAILABLE` always False on fresh installs |
| `session_logger.py` | 1,094 | Works; kwarg explosion (`log_shot` ~140 lines of signature-and-plumbing) |
| UI (`ui/src`) | 6,760 | Modern, tidy; typed socket singleton; 7 vitest files + Playwright e2e |

## Test suite

**1,166 collected; on Windows: 1,136 pass / 22 fail / 8 skip in 88 s.** All 22 failures are environmental: 17× `test_start_kiosk.py` (bash-only), POSIX chmod, udev, two genuine newline bugs (`test_compare_trackman.py:145` writes `\r\n` without `newline=""` → `\r\r\n`; same family in `test_session_shot_report.py`), and one real-socket timing flake (`test_sim_transport.py:253`). Assertion quality is high — physical-bounds checks against TrackMan references, ordering properties, regression tests naming the field incident they prevent (`test_sound_trigger_serial_deadlock.py`).

**Untested modules:** `camera_tracker.py` (the one the server actually imports), `iwr6843/music.py` (indirect only), `iwr6843/dump.py` (no dedicated file), `cloud/trigger.py` (light), `src/analysis/analyze_capture.py` (also misplaced under `src/` and not packaged).

## Findings (numbered; recommendation first)

**F1. `kld7/radc.py:extract_launch_angle` — 837 lines, 24 parameters** (`radc.py:1414–2251`); its 10 `radc_*` tuning kwargs are hand-plumbed across 5 sites (`server.py:114`, `:776`, `:1094`, `tracker.py:130`, `radc.py:1414`).
- **A (recommended): freeze, don't refactor.** Hardware is deprecated; wrap in a `RadcTuning` dataclass only if touched again. Effort S, risk none, stops new complexity.
- B: full stage-extraction refactor. Effort L, risk M — high-quality work on end-of-life code.
- C: do nothing. Free, but the kwarg plumb still infects `server.py`.

**F2. `on_shot_detected` — ~500 lines with near-clone vertical/horizontal K-LD7 blocks** (`server.py:2042–2143` vs `:2146–2240`: snapshot → warn-helpers → extract → gate → assign → log → reset, twice).
- **A (recommended): extract `_process_kld7_orientation(...)`** — removes ~90 duplicated lines without touching behavior. Effort S, risk L(ow), test-coverable.
- B: full pipeline-of-stages refactor of the handler. Right long-term, but should be maintainer-blessed first (see F9).
- C: do nothing — every angle feature keeps being written twice.

**F3. Club-physics tables duplicated and already diverged.** Smash factor ×3 (`server.py:214` WOOD_7=1.42 vs `rolling_buffer/monitor.py:166` WOOD_7=**1.41**; Mock DRIVER=1.45 vs 1.48 `server.py:2680`); launch-angle table ×3; club-spin table ×3 (`ballistics.py:70`, `server.py:2705`, multipliers `monitor.py:66`). Two code paths can disagree about the same shot — the exact failure mode a measurement device can't afford.
- **A (recommended): single `club_data.py` with one per-club record; all consumers import it.** Effort M (~a day + tests), risk L, kills a whole drift class. Strong upstream PR candidate — aligns with their "tests required" culture and is tuning-adjacent work golf contributors care about.
- B: leave tables, add a cross-consistency test that fails on divergence. Effort S, catches drift but keeps the DRY violation.
- C: do nothing — silent divergence continues.

**F4. ~2,030 LOC of dead camera code, one path untested but imported by the server.** `camera_tracker.py` (used by `server.py:60`, zero tests, needs cv2 which is no longer installable) vs `camera/` package (1,583 LOC, tested, used by nothing). All camera branches in server.py are unreachable on fresh installs.
- **A (recommended): propose upstream moving both to `archive/` + collapsing server camera branches behind one optional adapter.** Effort M, risk L (provably dead), −2k LOC.
- B: delete `camera/`, keep `camera_tracker.py`. Smaller, but keeps the untested one.
- C: do nothing — every reader of server.py pays the tax.

**F5. `SpinResult`/`Shot` fields hand-plumbed through 4 layers** (~25 fields × 4 sites: `monitor.py:572`, `:856`, `server.py:825`, `:2414`, plus both `session_logger.py` signatures). Adding one spin diagnostic touches 6 files.
- **A (recommended): `to_log_dict()` on `SpinResult`/`Shot`; session_logger accepts dicts.** Effort M, risk L.
- B: do nothing — friction on exactly the code (spin diagnostics) that changes most.

**F6. Hardcoded 30 ksps / threshold constants.** `processor.py:1700` falls back to `68.0` ms (capture midpoint only at 30 ksps/4096); ±15° horizontal limit appears independently ×6 (`server.py:124`, `:1108`, `:2174`, `radc.py:1252`, `:1429`, `tracker.py:142`); 15 mph floor duplicated (`monitor.py:760` vs `trigger.py:32`); docstring drift (`trigger.py:576` says debounce default 200, actual 20).
- **A (recommended): derive midpoint from `len(i_samples)/sample_rate`; name shared constants once.** Effort S each; good first-PR material with tests.
- B: do nothing — `--sample-rate 20` silently mis-times impact fallback today.

**F7. Silent exception swallowing in cloud push.** `_fire_cloud_push` ends `except Exception: pass` (`server.py:2656`) — config/import errors vanish; contrast the repo's own good pattern at `server.py:143` (`exc_info` logging).
- **A (recommended): `logger.debug(..., exc_info=True)` minimum.** Effort XS. Textbook small upstream fix with test.

**F8. CI drift from the project's own rules.** Workflows hand-list dependencies including three packages removed from pyproject (opencv, supervision, roboflow-trackers from a git URL), don't use uv (the repo's rule #1), run pylint without installing the package, pin pre-commit ruff 0.9.10 vs dev-group ≥0.16.1, and never run ruff or vitest in CI.
- **A (recommended): migrate workflows to `uv sync --group dev` + `make lint`/`make test`; add ruff + vitest jobs.** Effort S–M, risk L, closes the local-vs-CI truth gap.
- B: minimally delete the stale deps from the hand-list. Effort XS, keeps two sources of truth.

**F9. `server.py` global-state architecture.** 27 `global` statements; module "constant" `_VERTICAL_RADAR_GATE_BYPASS` reassigned at runtime (`server.py:608`, `:3285`); tests forced into monkeypatching; 50 `print()`s vs logger.
- **A (recommended): open an upstream design issue proposing `AppState` + staged shot pipeline; contribute incrementally after maintainer buy-in.** This repo's history shows big unsolicited rewrites stall — propose, then slice.
- B: do nothing — merge-conflict magnet keeps compounding (IWR, sim, correction all threaded new globals in the last 2 months).

**F10. Mock/real monitor interface mismatch** papered over with `# pylint: disable=unexpected-keyword-arg` (`server.py:2629`) and `duplicate-code` disabled repo-wide partly for the mock (`pyproject.toml:120`).
- **A (recommended): small `typing.Protocol` (`LaunchMonitorProtocol`); mock accepts+ignores `diagnostic_callback`.** Effort S, deletes suppressions and branches.
- B: do nothing.

Minor (verified): `IWR6843Runtime.process_shot` hardcodes `tdm_sign_policy="positive"` ignoring its own configurable field (`iwr6843/runtime.py:38,55`) — latent config trap; `estimate_carry_distance` rebuilds its table per call (`launch_monitor.py:101`); `session_logger` import emits a DeprecationWarning via kld7 import on every pytest run; `POST /api/shutdown` unauthenticated + `CORS(app)` wildcard + `os._exit(0)` (`server.py:918`, `:184`, `:76`) — any LAN page can kill the kiosk; low stakes but worth an upstream note.

## Tech-debt ranking (impact × likelihood)

1. **`server.py` god-module** — every contributor touches it; highest-leverage refactor (needs maintainer buy-in first).
2. **Club-data/constant duplication web** — silent numeric drift already real; cheap fix, big class of bugs removed.
3. **K-LD7: most complex code, deprecated hardware, still the default path** — decide the end-state (freeze behind shared angle-source interface vs plugin) before more accretes.
4. **Windows test experience** — 22 red tests teach contributors to ignore failures; fixes are cheap (2 newline bugs, platform skips, mock socket).
5. **CI drift** — green CI proves less than contributors think.

## Strengths worth preserving

- Field-debugging discipline: py-spy-cited comments (`ops243.py:177`), deadlock-ordering rationale (`trigger.py:1049`), regression tests named for field incidents.
- `iwr6843/`, `sim/`, `cloud/` set the current quality bar — new code should match them, not `server.py`/`kld7/`.
- PR automation enforcing description sections + test inclusion.
- Privacy boundary (`cloud/filtering.py`) explicit and tested.

## Path forward (my read)

**Near term (upstream-aligned):** rebase my approved PR #118; land small fixes (F6/F7 + Windows test bugs); docs-drift PR (CLAUDE.md constants table above). **Mid term:** club_data consolidation (F3) and CI-uv migration (F8) as standalone PRs; propose F9 as a design issue. **For my build:** none of the above blocks hardware bring-up — the OPS243+IWR6843 path is production-ready today (opt-in flag), and the validation program (see contribution-opportunities doc) is where my rig adds unique value.
