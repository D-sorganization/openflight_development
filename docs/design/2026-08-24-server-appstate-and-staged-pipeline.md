# Upstream Design Proposal: `server.py` AppState, Staged Shot Pipeline, and Camera Retirement

**Author:** Dieter Olson  
**Date:** 2026-08-24  
**Issue:** [#20](https://github.com/D-sorganization/openflight_development/issues/20)  
**Status:** Proposed / Implemented in Slice 1  

---

## 1. Executive Summary

As OpenFlight has expanded to support TI IWR6843 mmWave radar, simulator connectors (GSPro, OpenGolfSim, E6), LIS3DH inclinometer compensation, calculated spin models, and swing-speed training modes, `src/openflight/server.py` has grown into a 4,200+ line god-module holding 29 `global` declarations, runtime mutation of configuration constants, and a ~500-line monolithic `on_shot_detected` handler.

Past experience across large refactors (e.g. PRs #120–#127) demonstrates that massive, single-shot rewrites stall in review, whereas well-specified incremental slices with automated tests merge quickly and safely.

This proposal outlines a phased architectural refactoring strategy:
1. **`AppState` Dataclass:** Encapsulate scattered module globals, hardware controllers, session state, and configuration dictionaries into a clean, typed container instantiated at startup.
2. **Staged Shot Processing Pipeline:** Decompose the monolithic `on_shot_detected` handler into distinct, testable, and isolated stages (ingestion, angle extraction, ballistics, logging, and downstream fan-out).
3. **K-LD7 Orientation Extraction (First Slice):** Extract `_process_kld7_orientation()` to deduplicate ~90 lines of duplicated vertical/horizontal radar buffer analysis and validation logic.
4. **Dead Camera Stack Retirement:** Formally deprecate and retire ~2,030 lines of unreachable computer vision code (`camera_tracker.py` and `src/openflight/camera/`) whose dependencies (`opencv-python`, `supervision`, `inference-sdk`) were removed from the base package.

---

## 2. Current Architecture & Pain Points

### 2.1 Global State Accumulation
`server.py` currently relies on 29 `global` statements across startup routines, socket events, and shot callbacks:
- Hardware handles: `monitor`, `kld7_vertical`, `kld7_horizontal`, `iwr6843_runtime`, `inclinometer_service`, `power_monitor`, `camera`, `camera_tracker`.
- Session state: `current_player_name`, `sim_player_state`, `sim_connectors`.
- Operational flags: `mock_mode`, `debug_mode`, `mock_swing_speed_mode`, `ballistics_enabled`, `battery_provider`, `ball_speed_correction_enabled`, `calculated_spin_enabled`, `_VERTICAL_RADAR_GATE_BYPASS`.
- Configuration dictionaries: `active_kld7_radc_tuning`, `iwr6843_runtime_config`, `inclinometer_runtime_config`.

**Consequences:**
- Testing requires extensive `monkeypatch.setattr(server_module, ...)` calls.
- Concurrency and lifecycle cleanup are fragile.
- Runtime state cannot be cloned or instantiated independently for headless simulations or multi-rig testing.

### 2.2 Duplication in `on_shot_detected`
The primary shot callback executes synchronously on the capture thread. Prior to this refactor, vertical (launch angle) and horizontal (club path) K-LD7 processing were duplicated line-for-line across ~200 lines:
- Ring buffer snapshotting and underfill warnings.
- RADC raw payload verification.
- Post-shot frame span validation.
- Radar angle candidate extraction and validation gating.
- Club angle extraction (angle of attack vs. club path).
- JSONL buffer session logging.
- Tracker reset.

### 2.3 Dead Vision Stack
OpenFlight previously explored Pi Camera v2 / HQ camera tracking for launch angle. However:
- Dependencies (`opencv-python`, `supervision`, `trackers@git`, `inference-sdk`) were commented out in `pyproject.toml` due to ARM64 wheel build instability and latency constraints on Raspberry Pi.
- TI IWR6843 60 GHz radar and OPS243-A Doppler radar provide superior accuracy and environmental robustness without optical lighting constraints.
- `camera_tracker.py` and `camera/` remain on disk and referenced in `server.py`, but all execution branches are unreachable on fresh installs.

---

## 3. Proposed Architecture

```
                                  ┌─────────────────────────────┐
                                  │          AppState           │
                                  │ ─────────────────────────── │
                                  │ • Hardware Adapters         │
                                  │ • Session & Player State    │
                                  │ • Config & Tuning Dicts     │
                                  │ • Operational Flags         │
                                  │ • Lifecycle & Concurrency   │
                                  └──────────────┬──────────────┘
                                                 │
                                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                   Shot Processing Pipeline                              │
├───────────────────┬───────────────────┬───────────────────┬──────────────┬──────────────┤
│ 1. Ingestion      │ 2. Angle & Path   │ 3. Ballistics &   │ 4. Session   │ 5. Client &  │
│    & Geometry     │    Resolution     │    Trajectory     │    Logging   │    Sim Fanout│
├───────────────────┼───────────────────┼───────────────────┼──────────────┼──────────────┤
│ • Inclinometer    │ • IWR6843 LCMF-v1 │ • Cosine speed    │ • JSONL      │ • WebSocket  │
│   tilt snapshot   │ • K-LD7 vertical/ │   correction      │   logging    │   "shot" emit│
│ • Impact timing   │   horizontal      │ • Calculated spin │ • Diagnostic │ • Simulators │
│   correlation     │   processing      │ • RK4 simulation/ │   provenance │   (GSPro,    │
│                   │ • Estimator/table │   table carry     │ • Error traps│   OpenGolf)  │
│                   │   fallback        │                   │              │              │
└───────────────────┴───────────────────┴───────────────────┴──────────────┴──────────────┘
```

### 3.1 `AppState` Dataclass
`AppState` unifies runtime state into a structured, type-annotated dataclass:

```python
@dataclass
class AppState:
    """Encapsulates OpenFlight server runtime state, hardware adapters, and configuration."""

    # Hardware controllers & adapters
    monitor: Any = None
    power_monitor: Optional[PowerMonitor] = None
    battery_provider: Optional[str] = None
    kld7_vertical: Any = None
    kld7_horizontal: Any = None
    iwr6843_runtime: Any = None
    inclinometer_service: Any = None
    camera: Any = None
    camera_tracker: Any = None
    sim_connectors: List[Any] = field(default_factory=list)

    # Session & player state
    current_player_name: str = "Player 1"
    sim_player_state: SimPlayerState = field(
        default_factory=lambda: SimPlayerState(shot_counter=initial_shot_counter())
    )

    # Operational flags & runtime modes
    mock_mode: bool = False
    debug_mode: bool = False
    mock_swing_speed_mode: bool = False
    ballistics_enabled: bool = True
    ball_speed_correction_enabled: bool = True
    ball_speed_correction_distance_ft: float = 1.0
    ball_speed_correction_ball_above_radar_ft: float = 0.0
    radar_gate_bypass: bool = False
    calculated_spin_enabled: bool = False
    experimental_kld7_radc_tuning: bool = False
    experimental_kld7_raw_radc_logging: bool = False

    # Dynamic tuning / config dictionaries
    active_kld7_radc_tuning: dict = field(default_factory=lambda: dict(_DEFAULT_KLD7_RADC_TUNING))
    iwr6843_runtime_config: dict = field(default_factory=lambda: {"enabled": False})
    inclinometer_runtime_config: dict = field(default_factory=lambda: {"enabled": False})

    # Debug file logging
    debug_log_file: Any = None
    debug_log_path: Optional[Path] = None

    # Camera runtime state
    camera_enabled: bool = False
    camera_streaming: bool = False
    camera_thread: Optional[threading.Thread] = None
    camera_stop_event: Optional[threading.Event] = None
    ball_detected: bool = False
    ball_detection_confidence: float = 0.0
    latest_frame: Optional[bytes] = None

    # Lifecycle synchronization
    shutdown_cleanup_started: bool = False
```

### 3.2 Staged Shot Pipeline
`on_shot_detected` is decomposed into 5 clear stages:

1. **Stage 1: Geometric Ingestion & Snapshot**
   - Captures orientation from `inclinometer_service` before blocking I/Q operations.
   - Correlates radar impact timestamps.
2. **Stage 2: Launch Angle & Path Resolution**
   - Executes `_process_iwr6843_angle()` (TI 60 GHz radar).
   - Executes `_process_kld7_orientation()` for vertical (launch angle + AoA) and horizontal (club path) tracking.
   - Derives spin axis from horizontal launch and club path.
   - Falls back to `_ensure_user_facing_launch_angles()` when radar measurements are unavailable or rejected.
3. **Stage 3: Ballistic & Trajectory Simulation**
   - Applies radial-to-true speed cosine correction.
   - Evaluates calculated spin models if enabled.
   - Resolves launch conditions and simulates 3D trajectory via RK4 numerical ballistics, falling back to spin-adjusted tables.
4. **Stage 4: Session Logging & Telemetry**
   - Records shot records, raw I/Q captures, and RADC buffer diagnostics to `SessionLogger`.
5. **Stage 5: Client Broadcast & Simulator Fan-out**
   - Emits WebSocket payload to React frontend.
   - Dispatches shot events to active simulator connectors (GSPro / OpenGolfSim).

### 3.3 First Slice Implementation: `_process_kld7_orientation()`
Extracted helper function that unifies K-LD7 vertical and horizontal buffer processing:

```python
def _process_kld7_orientation(
    tracker,
    orientation: str,
    shot: Shot,
    shot_ts: float,
    session_log=None,
) -> None:
    """Process a single K-LD7 tracker (vertical or horizontal) for a detected shot."""
```

Benefits:
- Eliminates ~90 lines of duplicate code.
- Ensures identical diagnostic warning logs and buffer retention across both axes.
- Cleanly isolated for unit testing.

### 3.4 Camera Stack Retirement Plan

| Phase | Scope | Description |
|---|---|---|
| **Phase 1 (This PR)** | Foundation & Deduplication | Define `AppState`, extract `_process_kld7_orientation()`, document proposal, maintain backwards-compatible camera stubs. |
| **Phase 2** | Code Retirement | Move `camera_tracker.py` and `camera/` to `archive/vision/` or deprecate package. Remove unused CV2 dependencies. |
| **Phase 3** | Server Cleanup | Remove dead camera branches from `server.py` startup and `on_shot_detected`. Collapse camera status routes into a clean no-op / disabled stub. |
| **Phase 4** | Pipeline Decoupling | Refactor `on_shot_detected` into standalone stage functions accepting `(shot, app_state)`. |

---

## 4. Testing & Validation Strategy

1. **Automated Unit Tests:**
   - `TestAppState`: Verify default values, custom instantiation, and immutability/field consistency.
   - `TestProcessKld7Orientation`: Verify vertical angle acceptance, low-confidence rejection, club AoA sign inversion, horizontal club path assignment, and buffer session logging.
   - Existing 1,400+ unit and replay tests in `tests/` pass with zero regressions.
2. **Backwards Compatibility:**
   - All module-level attributes in `server.py` are preserved, ensuring existing test monkeypatching and public imports remain unbroken.

---

## 5. Conclusion

This proposal establishes a clean, reviewable roadmap for modernizing `server.py`. By landing `AppState` and `_process_kld7_orientation` first, we demonstrate immediate code reduction and maintainability gains without risking system stability.
