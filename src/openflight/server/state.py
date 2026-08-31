"""State and configuration definitions for the OpenFlight server."""

import importlib.util
import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional

from openflight.club_data import CLUB_LAUNCH_MODEL, OPTIMAL_SMASH
from openflight.kld7.radc import DEFAULT_RADC_HORIZONTAL_ANGLE_LIMIT_DEG
from openflight.power import PowerMonitor
from openflight.sim import PlayerState as SimPlayerState, initial_shot_counter

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
FRONTEND_DIST_DIR = REPO_ROOT / "ui" / "dist"
FRONTEND_SOURCE_DIR = REPO_ROOT / "ui"

# Optional camera dependencies
CV2_AVAILABLE = importlib.util.find_spec("cv2") is not None
PICAMERA_AVAILABLE = importlib.util.find_spec("picamera2") is not None

# Re-exported constants for launch and angle sanity models
_CLUB_LAUNCH_MODEL = CLUB_LAUNCH_MODEL
_OPTIMAL_SMASH = OPTIMAL_SMASH
_MAX_SMASH_ADJ_LOW = -2.0
_MAX_SMASH_ADJ_HIGH = 2.0
_SMASH_DEG_PER_HUNDREDTH_LOW = 0.2
_SMASH_DEG_PER_HUNDREDTH_HIGH = 0.2
_SPIN_DEG_PER_500RPM = 1.0
_MAX_SPIN_ADJ = 2.0
_RADAR_SANITY_LOW_CONF_BONUS_DEG = 4.0

_KLD7_FRAME_HZ = 34.0
_KLD7_BUFFER_SECONDS = 6.0
_KLD7_BUFFER_UNDERFILL_FRAC = 0.5
_KLD7_POST_SHOT_CAPTURE_DELAY_S = 0.18
_MIN_VERTICAL_RADAR_CONFIDENCE = 0.80
_MIN_VERTICAL_SOFT_RADAR_CONFIDENCE = 0.68
_MIN_VERTICAL_LOW_CONFIDENCE_RADAR_CONFIDENCE = 0.65
_VERTICAL_MARGINAL_DISPLAY_CONFIDENCE = 0.38
_VERTICAL_SOFT_ESTIMATE_DELTA_DEG = 4.5
_VERTICAL_SOFT_MAX_FRAME_COUNT = 40
_VERTICAL_SOFT_TIGHT_DELTA_FOR_LONG_FRAME_DEG = 2.0
_MIN_HORIZONTAL_RADAR_CONFIDENCE = 0.40
_MIN_HORIZONTAL_SOFT_RADAR_CONFIDENCE = 0.30
_HORIZONTAL_SOFT_ANGLE_LIMIT_DEG = 5.0
_HORIZONTAL_SOFT_MAX_FRAME_COUNT = 40
_HORIZONTAL_NEAR_LIMIT_FRACTION = 0.80
_HORIZONTAL_NEAR_LIMIT_MAX_FRAMES = 2
_HORIZONTAL_NEAR_LIMIT_MIN_CONFIDENCE = 0.80

VERTICAL_SPREAD_FULL_CONFIDENCE_DEG = 2.0
VERTICAL_SPREAD_ZERO_CONFIDENCE_DEG = 6.0
ANGLE_CONFIDENCE_FLOOR = 0.30
ANGLE_CONFIDENCE_CEILING = 0.95
SPIN_AXIS_MIN_CONFIDENCE = 0.40
_MIN_RELIABLE_SPIN_CONF = 0.4

_DEFAULT_KLD7_RADC_TUNING = {
    "radc_speed_tolerance_mph": 10.0,
    "radc_centroid_floor_frac": 0.5,
    "radc_spectrum_source": "f1a",
    "radc_ops_bin_outlier_tol": 25,
    "radc_ops_bin_outlier_penalty": 10.0,
    "radc_ops_anchored_peak_min_snr": 5.0,
    "radc_vertical_impact_energy_threshold": 3.0,
    "radc_horizontal_impact_energy_threshold": 1.85,
    "radc_horizontal_retry_impact_energy_threshold": 0.5,
    "radc_horizontal_angle_limit_deg": DEFAULT_RADC_HORIZONTAL_ANGLE_LIMIT_DEG,
}

TRAINING_IMPLEMENT_LABELS = {
    "driver": "Driver",
    "superspeed-light": "SuperSpeed Light",
    "superspeed-medium": "SuperSpeed Medium",
    "superspeed-heavy": "SuperSpeed Heavy",
    "speed-stick-light": "SuperSpeed Light",
    "speed-stick-medium": "SuperSpeed Medium",
    "speed-stick-heavy": "SuperSpeed Heavy",
    "stack": "Stack",
    "stack-0g": "Stack 0g",
    "stack-60g": "Stack 60g",
    "stack-100g": "Stack 100g",
    "stack-120g": "Stack 120g",
    "stack-160g": "Stack 160g",
    "stack-180g": "Stack 180g",
    "stack-200g": "Stack 200g",
    "stack-220g": "Stack 220g",
    "stack-240g": "Stack 240g",
    "stack-260g": "Stack 260g",
    "stack-280g": "Stack 280g",
    "stack-300g": "Stack 300g",
    "rypstick": "Rypstick",
    "rypstick-0w": "Rypstick 0 Weights",
    "rypstick-1w": "Rypstick 1 Weight",
    "rypstick-2w": "Rypstick 2 Weights",
    "rypstick-3w": "Rypstick 3 Weights",
    "rypstick-3w-cw": "Rypstick 3 Weights + Counterweight",
    "custom": "Custom",
}


def _react_app_dir(static_folder: Optional[str]) -> Path:
    """Resolve directory containing index.html."""
    if static_folder:
        dist_index = Path(static_folder) / "index.html"
        if dist_index.exists():
            return Path(static_folder)

    source_index = FRONTEND_SOURCE_DIR / "index.html"
    if source_index.exists():
        return FRONTEND_SOURCE_DIR

    raise RuntimeError(
        "OpenFlight React frontend not found. Expected built assets in "
        f"{FRONTEND_DIST_DIR} or index.html in {FRONTEND_SOURCE_DIR}."
    )


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
    frame_lock: threading.Lock = field(default_factory=threading.Lock)
    shutdown_lock: threading.Lock = field(default_factory=threading.Lock)
    shutdown_cleanup_started: bool = False

    _VERTICAL_RADAR_GATE_BYPASS: bool = False

    radar_config: dict = field(
        default_factory=lambda: {
            "min_speed": 10,
            "max_speed": 220,
            "min_magnitude": 0,
            "transmit_power": 0,
        }
    )
