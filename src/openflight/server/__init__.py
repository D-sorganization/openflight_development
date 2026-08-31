"""WebSocket server and modular subsystems for OpenFlight UI."""

import json
import logging
import math
import os
import random
import statistics
import sys
import threading
import time
from pathlib import Path
from typing import List, Optional

from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO

from openflight.ballistics import resolve_launch, simulate
from openflight.club_data import (
    CLUB_BALL_SPEEDS,
    CLUB_LAUNCH,
    CLUB_LAUNCH_MODEL,
    CLUB_SPIN,
    OPTIMAL_SMASH,
    ClubType,
)
from openflight.iwr6843 import Calibration
from openflight.kld7.radc import DEFAULT_RADC_HORIZONTAL_ANGLE_LIMIT_DEG
from openflight.kld7.types import KLD7Angle
from openflight.launch_monitor import SPIN_CONFIDENCE_HIGH, Shot
from openflight.ops243 import (
    UART_BAUD_COMMANDS,
    Direction,
    OPS243Radar,
    SpeedReading,
    set_show_raw_readings,
)
from openflight.power import (
    SUPPORTED_BATTERY_PROVIDERS,
    PowerMonitor,
    PowerState,
    PowerStatus,
)
from openflight.rolling_buffer.monitor import (
    estimate_carry_with_spin,
    get_optimal_spin_for_ball_speed,
)
from openflight.server.cli import (
    _add_ballistics_arguments,
    _add_battery_arguments,
    build_parser,
    configure_from_args,
    run_server,
    validate_args,
)
from openflight.server.connection_manager import (
    _emit_sim_snapshot,
    _fire_cloud_push,
    _forward_shot_to_simulators,
    _log_power_status,
    _on_power_status,
    _run_cloud_push_for_ui,
    _sim_on_inbound,
    _sim_on_status,
    start_power_monitor,
)
from openflight.server.handlers import (
    _delete_session_row,
    _get_trigger_status,
    _session_shots,
    api_shutdown,
    camera_stream,
    display,
    handle_clear_session,
    handle_connect,
    handle_delete_shot,
    handle_disconnect,
    handle_get_camera_status,
    handle_get_debug_status,
    handle_get_radar_config,
    handle_get_session,
    handle_get_trigger_status,
    handle_set_club,
    handle_set_player,
    handle_set_radar_config,
    handle_set_training_implement,
    handle_shutdown,
    handle_simulate_shot,
    handle_toggle_camera,
    handle_toggle_camera_stream,
    handle_toggle_debug,
    handle_upload_cloud,
    index,
    log_debug_reading,
    on_live_reading,
    on_shot_processing,
    register_handlers,
    start_debug_logging,
    static_files,
    stop_debug_logging,
)
from openflight.server.hardware import (
    MockLaunchMonitor,
    MockSwingSpeedMonitor,
    _cleanup_hardware_for_shutdown,
    _kld7_radc_tuning_kwargs,
    _MockSwingRadar,
    _run_shutdown_step,
    _session_start_config,
    _shutdown_process_after_delay,
    camera_processing_loop,
    generate_mjpeg,
    init_camera,
    init_inclinometer,
    init_iwr6843,
    init_kld7,
    start_camera_thread,
    start_monitor,
    stop_camera_thread,
    stop_monitor,
)
from openflight.server.shot_processor import (
    _apply_calculated_spin,
    _emit_iwr6843_trigger_status,
    _emit_shot_debug,
    _emit_shot_to_ui,
    _ensure_user_facing_launch_angles,
    _experimental_kld7_raw_radc_logging_enabled,
    _kld7_angle_log_payload,
    _log_shot_to_session,
    _maybe_wait_for_kld7_post_shot_frames,
    _process_iwr6843_angle,
    _process_kld7_orientation,
    _process_shot_ballistics_and_carry,
    _process_shot_camera,
    _process_shot_kld7_and_spin_axis,
    _radar_launch_base_delta_deg,
    _select_horizontal_radar_launch,
    _select_vertical_radar_launch,
    _snapshot_inclinometer_for_shot,
    _vertical_soft_launch_lane_deg,
    _warn_if_kld7_buffer_underfilled,
    _warn_if_kld7_raw_payload_missing,
    _warn_if_kld7_snapshot_lacks_post_shot_frames,
    estimate_launch_angle,
    horizontal_confidence_from,
    on_shot_detected,
    on_swing_speed_detected,
    radar_launch_is_plausible,
    shot_to_dict,
    swing_speed_to_dict,
    swing_speed_to_shot_dict,
    vertical_confidence,
)
from openflight.server.state import (
    _CLUB_LAUNCH_MODEL,
    _DEFAULT_KLD7_RADC_TUNING,
    _HORIZONTAL_NEAR_LIMIT_FRACTION,
    _HORIZONTAL_NEAR_LIMIT_MAX_FRAMES,
    _HORIZONTAL_NEAR_LIMIT_MIN_CONFIDENCE,
    _HORIZONTAL_SOFT_ANGLE_LIMIT_DEG,
    _HORIZONTAL_SOFT_MAX_FRAME_COUNT,
    _KLD7_BUFFER_SECONDS,
    _KLD7_BUFFER_UNDERFILL_FRAC,
    _KLD7_FRAME_HZ,
    _KLD7_POST_SHOT_CAPTURE_DELAY_S,
    _MAX_SMASH_ADJ_HIGH,
    _MAX_SMASH_ADJ_LOW,
    _MAX_SPIN_ADJ,
    _MIN_HORIZONTAL_RADAR_CONFIDENCE,
    _MIN_HORIZONTAL_SOFT_RADAR_CONFIDENCE,
    _MIN_RELIABLE_SPIN_CONF,
    _MIN_VERTICAL_LOW_CONFIDENCE_RADAR_CONFIDENCE,
    _MIN_VERTICAL_RADAR_CONFIDENCE,
    _MIN_VERTICAL_SOFT_RADAR_CONFIDENCE,
    _OPTIMAL_SMASH,
    _RADAR_SANITY_LOW_CONF_BONUS_DEG,
    _SMASH_DEG_PER_HUNDREDTH_HIGH,
    _SMASH_DEG_PER_HUNDREDTH_LOW,
    _SPIN_DEG_PER_500RPM,
    _VERTICAL_MARGINAL_DISPLAY_CONFIDENCE,
    _VERTICAL_SOFT_ESTIMATE_DELTA_DEG,
    _VERTICAL_SOFT_MAX_FRAME_COUNT,
    _VERTICAL_SOFT_TIGHT_DELTA_FOR_LONG_FRAME_DEG,
    ANGLE_CONFIDENCE_CEILING,
    ANGLE_CONFIDENCE_FLOOR,
    CV2_AVAILABLE,
    FRONTEND_DIST_DIR,
    FRONTEND_SOURCE_DIR,
    PICAMERA_AVAILABLE,
    REPO_ROOT,
    SPIN_AXIS_MIN_CONFIDENCE,
    TRAINING_IMPLEMENT_LABELS,
    VERTICAL_SPREAD_FULL_CONFIDENCE_DEG,
    VERTICAL_SPREAD_ZERO_CONFIDENCE_DEG,
    AppState,
    _react_app_dir,
)
from openflight.session_logger import (
    get_session_logger,
    init_session_logger,
    log_session_error,
)
from openflight.sim import (
    IncompleteShotError,
    PlayerState as SimPlayerState,
    PlayerUpdate,
    ShotAck,
    SimError,
    build_connectors,
    initial_shot_counter,
    load_sim_config,
    resolve_shot,
)
from openflight.speed_correction import correct_ball_speed
from openflight.spin_estimate import calculated_spin_rpm
from openflight.swing_speed import SwingSpeedEvent

logger = logging.getLogger(__name__)

# Flask application & SocketIO instance
app = Flask(__name__, static_folder=str(FRONTEND_DIST_DIR), static_url_path="")
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# AppState container
app_state = AppState()

# Global runtime state
monitor = None
power_monitor: Optional[PowerMonitor] = None
battery_provider: Optional[str] = None
mock_mode: bool = False
debug_mode: bool = False
mock_swing_speed_mode: bool = False
debug_log_file = None
debug_log_path: Optional[Path] = None
current_player_name: str = "Player 1"

# Radars and hardware adapters
kld7_vertical = None
kld7_horizontal = None
experimental_kld7_radc_tuning: bool = False
experimental_kld7_raw_radc_logging: bool = False

iwr6843_runtime = None
iwr6843_runtime_config: dict = {"enabled": False}

inclinometer_service = None
inclinometer_runtime_config: dict = {"enabled": False}

ballistics_enabled: bool = True
sim_connectors: List = []
sim_player_state = SimPlayerState(shot_counter=initial_shot_counter())

active_kld7_radc_tuning: dict = dict(_DEFAULT_KLD7_RADC_TUNING)

# Camera state
camera = None
camera_tracker = None
camera_enabled: bool = False
camera_streaming: bool = False
camera_thread: Optional[threading.Thread] = None
camera_stop_event: Optional[threading.Event] = None
ball_detected: bool = False
ball_detection_confidence: float = 0.0
latest_frame: Optional[bytes] = None
frame_lock = threading.Lock()
shutdown_lock = threading.Lock()
shutdown_cleanup_started = False

ball_speed_correction_enabled = False
ball_speed_correction_distance_ft = 5.5
ball_speed_correction_ball_above_radar_ft = -4.0 / 12.0
_VERTICAL_RADAR_GATE_BYPASS = False
calculated_spin_enabled = False

# Radar tuning configuration
radar_config = {
    "min_speed": 10,
    "max_speed": 220,
    "min_magnitude": 0,
    "transmit_power": 0,
}

# Register HTTP and Socket.IO handlers
register_handlers(app, socketio)


def main() -> None:
    """Run the server CLI."""
    parser = build_parser()
    args = parser.parse_args()
    run_server(args)


__all__ = [
    "ANGLE_CONFIDENCE_CEILING",
    "ANGLE_CONFIDENCE_FLOOR",
    "AppState",
    "Calibration",
    "CLUB_BALL_SPEEDS",
    "CLUB_LAUNCH",
    "CLUB_LAUNCH_MODEL",
    "CLUB_SPIN",
    "ClubType",
    "CORS",
    "CV2_AVAILABLE",
    "DEFAULT_RADC_HORIZONTAL_ANGLE_LIMIT_DEG",
    "Direction",
    "Flask",
    "FRONTEND_DIST_DIR",
    "FRONTEND_SOURCE_DIR",
    "IncompleteShotError",
    "KLD7Angle",
    "MockLaunchMonitor",
    "MockSwingSpeedMonitor",
    "OPS243Radar",
    "OPTIMAL_SMASH",
    "PICAMERA_AVAILABLE",
    "PlayerUpdate",
    "PowerMonitor",
    "PowerState",
    "PowerStatus",
    "REPO_ROOT",
    "SPIN_AXIS_MIN_CONFIDENCE",
    "SPIN_CONFIDENCE_HIGH",
    "Shot",
    "ShotAck",
    "SimError",
    "SimPlayerState",
    "SocketIO",
    "SpeedReading",
    "SUPPORTED_BATTERY_PROVIDERS",
    "SwingSpeedEvent",
    "TRAINING_IMPLEMENT_LABELS",
    "UART_BAUD_COMMANDS",
    "VERTICAL_SPREAD_FULL_CONFIDENCE_DEG",
    "VERTICAL_SPREAD_ZERO_CONFIDENCE_DEG",
    "_CLUB_LAUNCH_MODEL",
    "_DEFAULT_KLD7_RADC_TUNING",
    "_HORIZONTAL_NEAR_LIMIT_FRACTION",
    "_HORIZONTAL_NEAR_LIMIT_MAX_FRAMES",
    "_HORIZONTAL_NEAR_LIMIT_MIN_CONFIDENCE",
    "_HORIZONTAL_SOFT_ANGLE_LIMIT_DEG",
    "_HORIZONTAL_SOFT_MAX_FRAME_COUNT",
    "_KLD7_BUFFER_SECONDS",
    "_KLD7_BUFFER_UNDERFILL_FRAC",
    "_KLD7_FRAME_HZ",
    "_KLD7_POST_SHOT_CAPTURE_DELAY_S",
    "_MAX_SMASH_ADJ_HIGH",
    "_MAX_SMASH_ADJ_LOW",
    "_MAX_SPIN_ADJ",
    "_MIN_HORIZONTAL_RADAR_CONFIDENCE",
    "_MIN_HORIZONTAL_SOFT_RADAR_CONFIDENCE",
    "_MIN_RELIABLE_SPIN_CONF",
    "_MIN_VERTICAL_LOW_CONFIDENCE_RADAR_CONFIDENCE",
    "_MIN_VERTICAL_RADAR_CONFIDENCE",
    "_MIN_VERTICAL_SOFT_RADAR_CONFIDENCE",
    "_MockSwingRadar",
    "_OPTIMAL_SMASH",
    "_RADAR_SANITY_LOW_CONF_BONUS_DEG",
    "_SMASH_DEG_PER_HUNDREDTH_HIGH",
    "_SMASH_DEG_PER_HUNDREDTH_LOW",
    "_SPIN_DEG_PER_500RPM",
    "_VERTICAL_MARGINAL_DISPLAY_CONFIDENCE",
    "_VERTICAL_SOFT_ESTIMATE_DELTA_DEG",
    "_VERTICAL_SOFT_MAX_FRAME_COUNT",
    "_VERTICAL_SOFT_TIGHT_DELTA_FOR_LONG_FRAME_DEG",
    "_add_ballistics_arguments",
    "_add_battery_arguments",
    "_apply_calculated_spin",
    "_cleanup_hardware_for_shutdown",
    "_delete_session_row",
    "_emit_iwr6843_trigger_status",
    "_emit_shot_debug",
    "_emit_shot_to_ui",
    "_emit_sim_snapshot",
    "_ensure_user_facing_launch_angles",
    "_experimental_kld7_raw_radc_logging_enabled",
    "_fire_cloud_push",
    "_forward_shot_to_simulators",
    "_get_trigger_status",
    "_kld7_angle_log_payload",
    "_kld7_radc_tuning_kwargs",
    "_log_power_status",
    "_log_shot_to_session",
    "_maybe_wait_for_kld7_post_shot_frames",
    "_on_power_status",
    "_process_iwr6843_angle",
    "_process_kld7_orientation",
    "_process_shot_ballistics_and_carry",
    "_process_shot_camera",
    "_process_shot_kld7_and_spin_axis",
    "_radar_launch_base_delta_deg",
    "_react_app_dir",
    "_run_cloud_push_for_ui",
    "_run_shutdown_step",
    "_select_horizontal_radar_launch",
    "_select_vertical_radar_launch",
    "_session_shots",
    "_session_start_config",
    "_shutdown_process_after_delay",
    "_sim_on_inbound",
    "_sim_on_status",
    "_snapshot_inclinometer_for_shot",
    "_vertical_soft_launch_lane_deg",
    "_warn_if_kld7_buffer_underfilled",
    "_warn_if_kld7_raw_payload_missing",
    "_warn_if_kld7_snapshot_lacks_post_shot_frames",
    "api_shutdown",
    "app",
    "app_state",
    "build_connectors",
    "build_parser",
    "calculated_spin_rpm",
    "camera_processing_loop",
    "camera_stream",
    "configure_from_args",
    "correct_ball_speed",
    "display",
    "estimate_carry_with_spin",
    "estimate_launch_angle",
    "generate_mjpeg",
    "get_optimal_spin_for_ball_speed",
    "get_session_logger",
    "handle_clear_session",
    "handle_connect",
    "handle_delete_shot",
    "handle_disconnect",
    "handle_get_camera_status",
    "handle_get_debug_status",
    "handle_get_radar_config",
    "handle_get_session",
    "handle_get_trigger_status",
    "handle_set_club",
    "handle_set_player",
    "handle_set_radar_config",
    "handle_set_training_implement",
    "handle_shutdown",
    "handle_simulate_shot",
    "handle_toggle_camera",
    "handle_toggle_camera_stream",
    "handle_toggle_debug",
    "handle_upload_cloud",
    "horizontal_confidence_from",
    "index",
    "init_camera",
    "init_inclinometer",
    "init_iwr6843",
    "init_kld7",
    "init_session_logger",
    "initial_shot_counter",
    "json",
    "load_sim_config",
    "log_debug_reading",
    "log_session_error",
    "logging",
    "main",
    "math",
    "on_live_reading",
    "on_shot_detected",
    "on_shot_processing",
    "on_swing_speed_detected",
    "os",
    "radar_launch_is_plausible",
    "random",
    "register_handlers",
    "resolve_launch",
    "resolve_shot",
    "run_server",
    "set_show_raw_readings",
    "shot_to_dict",
    "simulate",
    "socketio",
    "start_camera_thread",
    "start_debug_logging",
    "start_monitor",
    "start_power_monitor",
    "static_files",
    "statistics",
    "stop_camera_thread",
    "stop_debug_logging",
    "stop_monitor",
    "swing_speed_to_dict",
    "swing_speed_to_shot_dict",
    "sys",
    "threading",
    "time",
    "validate_args",
    "vertical_confidence",
]
