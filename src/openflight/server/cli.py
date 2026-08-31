"""CLI parser and startup orchestrator for OpenFlight UI server."""

import argparse
import logging
import sys
from pathlib import Path

from openflight import server
from openflight.kld7.radc import DEFAULT_RADC_HORIZONTAL_ANGLE_LIMIT_DEG
from openflight.ops243 import UART_BAUD_COMMANDS, OPS243Radar, set_show_raw_readings
from openflight.power import SUPPORTED_BATTERY_PROVIDERS
from openflight.session_logger import init_session_logger
from openflight.sim import build_connectors, load_sim_config

logger = logging.getLogger(__name__)


def _add_ballistics_arguments(parser: argparse.ArgumentParser) -> None:
    """Add the preferred ballistic carry model and its explicit opt-out."""
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--ballistics",
        action="store_true",
        dest="ballistics",
        help=(
            "Use the physics-based carry simulator (drag + Magnus, RK4). "
            "This is the default; shots without a vertical launch angle "
            "fall back to the legacy table estimator."
        ),
    )
    group.add_argument(
        "--no-ballistics",
        action="store_false",
        dest="ballistics",
        help="Disable the physics simulator and use the legacy carry table for all shots.",
    )
    parser.set_defaults(ballistics=True)


def _add_battery_arguments(parser: argparse.ArgumentParser) -> None:
    """Add explicit battery-provider selection."""
    parser.add_argument(
        "--battery",
        choices=SUPPORTED_BATTERY_PROVIDERS,
        default=None,
        help="Show battery and external-power status using the selected provider",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser for OpenFlight server."""
    parser = argparse.ArgumentParser(description="OpenFlight UI Server")
    parser.add_argument("--port", "-p", help="Serial port for radar")
    parser.add_argument(
        "--ops-baud",
        type=int,
        default=None,
        help=(
            "Target UART baud for the OPS243 on the GPIO header "
            f"(default {OPS243Radar.DEFAULT_UART_BAUD}). Only meaningful when "
            "--port is a UART device such as /dev/ttyAMA0; drop to 115200 if "
            "230400 proves unreliable on your board."
        ),
    )
    parser.add_argument("--mock", "-m", action="store_true", help="Run in mock mode without radar")
    parser.add_argument(
        "--mock-swing-speed",
        action="store_true",
        help="Run swing speed training mode with simulated reps and no OPS radar",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument(
        "--web-port", type=int, default=8080, help="Web server port (default: 8080)"
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Enable verbose FFT/CFAR debug output",
    )
    parser.add_argument(
        "--radar-log",
        action="store_true",
        help="Log raw radar data to console (Python logging)",
    )
    parser.add_argument(
        "--show-raw",
        action="store_true",
        help="Show raw radar readings in console (signed values)",
    )
    parser.add_argument(
        "--no-camera",
        action="store_true",
        help="Disable camera (auto-enabled if available)",
    )
    parser.add_argument(
        "--camera-model",
        default=None,
        help="Path to YOLO model for ball detection (uses Hough by default)",
    )
    parser.add_argument(
        "--camera-imgsz",
        type=int,
        default=256,
        help="YOLO inference input size (256 for speed, 640 for accuracy)",
    )
    parser.add_argument(
        "--hough-param2",
        type=int,
        default=33,
        help="Hough accumulator threshold (lower = more sensitive, default 33)",
    )
    parser.add_argument(
        "--hough-param1",
        type=int,
        default=48,
        help="Canny edge threshold (lower = detects weaker edges, default 48)",
    )
    parser.add_argument(
        "--hough-min-radius",
        type=int,
        default=4,
        help="Min ball radius in pixels (default 4)",
    )
    parser.add_argument(
        "--hough-max-radius",
        type=int,
        default=43,
        help="Max ball radius in pixels (default 43)",
    )
    parser.add_argument(
        "--hough-min-dist",
        type=int,
        default=266,
        help="Min distance between detected circles in pixels (default 266)",
    )
    parser.add_argument(
        "--roboflow-model",
        help="Roboflow model ID (e.g., 'golfballdetector/10'). Uses Roboflow API instead of Hough.",
    )
    parser.add_argument(
        "--roboflow-api-key",
        help="Roboflow API key (can also use ROBOFLOW_API_KEY env var)",
    )
    parser.add_argument(
        "--session-location",
        "-l",
        default="range",
        help="Location identifier for session logs (e.g., 'range', 'course', 'home')",
    )
    parser.add_argument(
        "--log-dir", help="Directory for session logs (default: ~/openflight_sessions)"
    )
    parser.add_argument("--no-logging", action="store_true", help="Disable session logging")
    _add_battery_arguments(parser)
    parser.add_argument(
        "--sim",
        action="store_true",
        help="Enable simulator connectors from config/sim.json (GSPro / OpenGolfSim). Off by default.",
    )
    _add_ballistics_arguments(parser)
    parser.add_argument(
        "--trigger",
        choices=["polling", "threshold", "speed", "sound"],
        default="polling",
        help="Trigger strategy (default: polling)",
    )
    parser.add_argument(
        "--swing-speed",
        action="store_true",
        help="Run club-only swing speed training mode (no impact or ball required)",
    )
    parser.add_argument(
        "--swing-speed-threshold",
        type=float,
        default=30.0,
        help="Outbound speed threshold that starts a swing speed rep (default: 30 mph)",
    )
    parser.add_argument(
        "--swing-speed-max",
        type=float,
        default=130.0,
        help="Maximum plausible swing speed accepted from OPS reports; use 0 to disable (default: 130 mph)",
    )
    parser.add_argument(
        "--swing-speed-min-readings",
        type=int,
        default=3,
        help="Minimum qualifying radar readings required to count a swing speed rep (default: 3)",
    )
    parser.add_argument(
        "--swing-speed-single-peak",
        type=float,
        default=60.0,
        help="Peak speed that can count as a swing from one radar reading (default: 60 mph)",
    )
    parser.add_argument(
        "--swing-speed-num-reports",
        type=int,
        default=8,
        help="Number of OPS speed candidates to report per sample cycle (default: 8)",
    )
    parser.add_argument(
        "--swing-speed-end-ms",
        type=float,
        default=1000.0,
        help="Milliseconds below threshold before ending a swing speed rep (default: 1000)",
    )
    parser.add_argument(
        "--swing-speed-cooldown-ms",
        type=float,
        default=750.0,
        help="Cooldown after a swing speed rep before accepting another (default: 750)",
    )
    parser.add_argument(
        "--swing-speed-rejected-cooldown-ms",
        type=float,
        default=100.0,
        help="Cooldown after an ignored short motion before re-arming (default: 100)",
    )
    parser.add_argument(
        "--sound-pre-trigger",
        type=int,
        default=16,
        help=(
            "Pre-trigger segments S#n, 0-32 "
            "(default: 16 = 50/50 split, each segment ~4.27ms at 30ksps)"
        ),
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=30,
        help=(
            "Radar sample rate in ksps (default: 30). "
            "Lower = longer buffer but lower max speed. "
            "25=174mph/164ms, 27=187mph/152ms"
        ),
    )
    parser.add_argument(
        "--iwr6843",
        action="store_true",
        help="Enable TI IWR6843 L3 capture and LCMF-v1 vertical launch angle",
    )
    parser.add_argument(
        "--inclinometer",
        action="store_true",
        help="Enable LIS3DH enclosure pitch compensation for IWR6843 tilt",
    )
    parser.add_argument(
        "--inclinometer-zero-offset",
        type=float,
        default=0.0,
        help="Degrees added to raw LIS3DH pitch (default: 0)",
    )
    parser.add_argument(
        "--iwr6843-port", default=None, help="TI serial port (auto-detect by default)"
    )
    parser.add_argument(
        "--iwr6843-config",
        default="config/iwr6843_l3dump_wide_24f3ms_53bin_iq16.cfg",
        help="TI RF config matching the flashed L3 firmware",
    )
    parser.add_argument(
        "--iwr6843-cal",
        default="config/iwr6843_calibration_reference.json",
        help="TI complex array/range calibration JSON",
    )
    parser.add_argument(
        "--iwr6843-trigger-pin",
        type=int,
        default=17,
        help="BCM GPIO receiving the shared sound-trigger edge (default: 17)",
    )
    parser.add_argument(
        "--iwr6843-tee-m",
        type=float,
        default=1.575,
        help="Antenna-center to tee slant range in metres (default: 1.575)",
    )
    parser.add_argument(
        "--iwr6843-net-m",
        type=float,
        default=4.6,
        help="Antenna-center to net range in metres (default: 4.6)",
    )
    parser.add_argument(
        "--iwr6843-tilt-deg",
        type=float,
        default=None,
        help="Override mount tilt from the TI calibration JSON",
    )
    parser.add_argument(
        "--iwr6843-radar-height-m",
        type=float,
        default=None,
        help="Override antenna-center height from the TI calibration JSON",
    )
    parser.add_argument(
        "--iwr6843-ball-height-m",
        type=float,
        default=0.040,
        help="Ball-center height above the floor/mat (default: 0.040)",
    )
    parser.add_argument(
        "--iwr6843-tx-order",
        choices=("auto", "normal", "reversed"),
        default="auto",
        help="TI TDM chirp order; auto reads the chirp masks from the cfg",
    )
    parser.add_argument(
        "--iwr6843-capture-timeout",
        type=float,
        default=12.0,
        help="Maximum seconds an OPS shot waits for its TI UART dump (default: 12)",
    )
    parser.add_argument(
        "--iwr6843-output-dir",
        default=None,
        help="Raw TI dump directory when --debug is enabled (default: <session-log-dir>/iwr6843)",
    )
    parser.add_argument(
        "--iwr6843-azimuth-offset-deg",
        type=float,
        default=0.0,
        help=(
            "Azimuth of the radar boresight relative to the target line, in degrees. "
            "Positive means boresight points right of the target line. Added to the "
            "measured club path; 0 reports club path relative to boresight."
        ),
    )
    parser.add_argument(
        "--iwr6843-horizontal-phase-reference-rad",
        type=float,
        default=None,
        help=(
            "Static target-line phase measured by horizontal aim calibration. "
            "Subtracted from the TX2 horizontal proxy before angle conversion."
        ),
    )
    parser.add_argument(
        "--kld7",
        action="store_true",
        help="[DEPRECATED] Enable K-LD7 vertical angle radar (launch angle)",
    )
    parser.add_argument(
        "--kld7-port",
        default=None,
        help="K-LD7 vertical serial port (auto-detect if not specified)",
    )
    parser.add_argument(
        "--kld7-angle-offset",
        type=float,
        default=1.5,
        help=(
            "K-LD7 vertical boresight offset in degrees. Not user-measurable "
            "without a corner reflector; 1.5 is the calibrated default for the "
            "standard mount (default: 1.5)"
        ),
    )
    parser.add_argument(
        "--calculated-spin",
        action="store_true",
        help=(
            "Replace radar-measured spin with the kinematic estimate "
            "(170*v*sin(LA)^1.2) when the launch angle was measured. The 24 GHz "
            "OPS return carries no usable spin line (see "
            "src/openflight/spin_estimate.py); the measured value is kept in "
            "spin_rpm_measured for offline scoring"
        ),
    )
    parser.add_argument(
        "--kld7-mount-tilt",
        type=float,
        default=None,
        help=(
            "K-LD7 vertical radar mount tilt in degrees. REQUIRED with --kld7 — "
            "measure it with a phone inclinometer against the radar face; there is "
            "no default because a wrong tilt silently corrupts the launch angle"
        ),
    )
    parser.add_argument(
        "--kld7-ball-distance",
        type=float,
        default=5.0,
        help="Radar-to-tee distance in feet (default: 5.0)",
    )
    parser.add_argument(
        "--net-distance",
        dest="net_distance",
        type=float,
        default=10.0,
        help=(
            "Ball-to-net/screen distance in feet (two_ray). For nets beyond the "
            "~11ft FSK range wrap, far-flight frames are de-aliased and kept "
            "instead of dropped (default: 10.0; nets at/inside the wrap are "
            "unaffected)."
        ),
    )
    parser.add_argument(
        "--kld7-radar-height-inches",
        dest="kld7_radar_height_inches",
        type=float,
        default=4.0,
        help=(
            "K-LD7 radar height above the ball in inches, used by the ball-speed "
            "cosine correction geometry (default: 4.0)"
        ),
    )
    parser.add_argument(
        "--kld7-vertical-raw",
        dest="kld7_vertical_raw",
        action="store_true",
        help=(
            "TEST MODE: show the raw vertical launch angle for every shot the "
            "estimator produces, bypassing all display guardrails (plausibility, "
            "soft-lane, estimator-agreement, confidence floor). Default off."
        ),
    )
    parser.add_argument(
        "--kld7-horizontal",
        action="store_true",
        help="[DEPRECATED] Enable K-LD7 horizontal angle radar (club path)",
    )
    parser.add_argument("--kld7-horizontal-port", default=None, help="K-LD7 horizontal serial port")
    parser.add_argument(
        "--kld7-horizontal-offset",
        type=float,
        default=0.0,
        help="K-LD7 horizontal angle offset in degrees (default: 0.0)",
    )
    parser.add_argument(
        "--kld7-raw-logging",
        dest="experimental_kld7_raw_radc_logging",
        action="store_true",
        help=(
            "Log raw K-LD7 RADC payloads (base64) in kld7_buffer session logs for "
            "offline replay and the session reviewer, without changing live angle extraction"
        ),
    )
    parser.add_argument(
        "--experimental-kld7-radc-tuning",
        action="store_true",
        help="Enable temporary K-LD7 RADC extraction tuning parameters (off by default)",
    )
    parser.add_argument(
        "--experimental-kld7-speed-tolerance",
        type=float,
        default=10.0,
        help="Experimental K-LD7 RADC speed tolerance in mph (default: 10.0)",
    )
    parser.add_argument(
        "--experimental-kld7-centroid-floor",
        type=float,
        default=0.5,
        help="Experimental K-LD7 RADC centroid floor fraction (default: 0.5)",
    )
    parser.add_argument(
        "--experimental-kld7-spectrum-source",
        choices=("f1a", "f2a", "f1b", "sum12", "sum1b", "sumall", "min12", "geom12"),
        default="f1a",
        help=(
            "Experimental K-LD7 spectrum used for target-bin selection "
            "(default: f1a; try sum12 for F1A+F2A non-coherent selection)"
        ),
    )
    parser.add_argument(
        "--experimental-kld7-ops-bin-tol",
        type=int,
        default=25,
        help="Experimental K-LD7 RADC OPS-bin outlier tolerance (default: 25)",
    )
    parser.add_argument(
        "--experimental-kld7-ops-bin-penalty",
        type=float,
        default=10.0,
        help="Experimental K-LD7 RADC OPS-bin outlier penalty (default: 10.0)",
    )
    parser.add_argument(
        "--experimental-kld7-ops-anchored-min-snr",
        type=float,
        default=5.0,
        help="Experimental K-LD7 RADC OPS-anchored local peak minimum SNR (default: 5.0)",
    )
    parser.add_argument(
        "--experimental-kld7-vertical-impact-energy",
        type=float,
        default=3.0,
        help="Experimental vertical K-LD7 RADC impact energy threshold (default: 3.0)",
    )
    parser.add_argument(
        "--experimental-kld7-horizontal-impact-energy",
        type=float,
        default=1.85,
        help="Experimental horizontal K-LD7 RADC impact energy threshold (default: 1.85)",
    )
    parser.add_argument(
        "--experimental-kld7-horizontal-retry-impact-energy",
        type=float,
        default=0.5,
        help="Experimental horizontal K-LD7 RADC retry impact energy threshold (default: 0.5)",
    )
    parser.add_argument(
        "--experimental-kld7-horizontal-angle-limit",
        type=float,
        default=DEFAULT_RADC_HORIZONTAL_ANGLE_LIMIT_DEG,
        help="Experimental horizontal K-LD7 RADC angle acceptance limit in degrees (default: 15.0)",
    )
    return parser


def validate_args(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    """Validate argument relationships and raise parser errors if invalid."""
    if args.kld7 and args.kld7_mount_tilt is None:
        parser.error("--kld7-mount-tilt is required when --kld7 is passed")
    if args.mock_swing_speed:
        args.mock = True
        args.swing_speed = True
    elif args.swing_speed and args.mock:
        parser.error(
            "--swing-speed requires real OPS243 radar hardware; use --mock-swing-speed for UI testing"
        )

    if args.iwr6843 and args.kld7:
        parser.error("--iwr6843 and vertical --kld7 cannot both own launch angle")
    if args.iwr6843 and args.kld7_horizontal:
        parser.error("--iwr6843 and horizontal --kld7 cannot both own club path")
    if args.inclinometer and not args.iwr6843:
        parser.error("--inclinometer requires --iwr6843")
    if args.iwr6843 and args.mock:
        parser.error("--iwr6843 cannot be used with --mock")
    if args.iwr6843 and args.trigger == "sound-gpio":
        parser.error("--iwr6843 already owns BCM GPIO; use the default --trigger sound")
    if args.iwr6843 and (args.iwr6843_tee_m <= 0 or args.iwr6843_net_m <= 0):
        parser.error("--iwr6843-tee-m and --iwr6843-net-m must be positive")
    if args.ops_baud is not None and args.ops_baud not in UART_BAUD_COMMANDS:
        supported = ", ".join(str(b) for b in sorted(UART_BAUD_COMMANDS))
        parser.error(f"--ops-baud must be one of {supported} (got {args.ops_baud})")


def configure_from_args(args: argparse.Namespace) -> None:
    """Apply parsed CLI arguments to server runtime state."""
    from openflight.server.hardware import _kld7_radc_tuning_kwargs

    server.experimental_kld7_raw_radc_logging = args.experimental_kld7_raw_radc_logging
    server.experimental_kld7_radc_tuning = args.experimental_kld7_radc_tuning
    server.ball_speed_correction_enabled = args.kld7 or args.iwr6843
    server.ball_speed_correction_distance_ft = args.kld7_ball_distance
    server.ball_speed_correction_ball_above_radar_ft = -args.kld7_radar_height_inches / 12.0
    server._VERTICAL_RADAR_GATE_BYPASS = args.kld7_vertical_raw
    server.calculated_spin_enabled = args.calculated_spin
    server.ballistics_enabled = args.ballistics
    server.battery_provider = args.battery
    server.active_kld7_radc_tuning = dict(_kld7_radc_tuning_kwargs(args))


def run_server(args: argparse.Namespace) -> None:
    """Initialize hardware subsystems and launch the web server."""
    from openflight.server.connection_manager import (
        _sim_on_inbound,
        _sim_on_status,
        start_power_monitor,
    )
    from openflight.server.hardware import (
        _cleanup_hardware_for_shutdown,
        _kld7_radc_tuning_kwargs,
        init_camera,
        init_inclinometer,
        init_iwr6843,
        init_kld7,
        start_camera_thread,
        start_monitor,
    )

    parser = build_parser()
    validate_args(args, parser)
    configure_from_args(args)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logging.getLogger("openflight.rolling_buffer").setLevel(logging.INFO)
    logging.getLogger("openflight.rolling_buffer.trigger").setLevel(logging.INFO)
    logging.getLogger("openflight.rolling_buffer.monitor").setLevel(logging.INFO)

    logger.info("=" * 50)
    logger.info("  OpenFlight UI Server")
    logger.info("=" * 50)

    if not args.no_logging:
        log_dir = Path(args.log_dir) if args.log_dir else None
        init_session_logger(log_dir=log_dir, location=args.session_location, enabled=True)
        logger.info("Session logging enabled (location: %s)", args.session_location)
    else:
        init_session_logger(enabled=False)
        logger.info("Session logging DISABLED")

    if server.ballistics_enabled:
        logger.info("Ballistic carry model: ENABLED (simulator + drag/Magnus)")
    else:
        logger.info("Ballistic carry model: DISABLED (table fallback for all shots)")

    if args.radar_log:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        radar_logger = logging.getLogger("ops243")
        radar_raw_logger = logging.getLogger("ops243.raw")
        radar_logger.setLevel(logging.DEBUG)
        radar_raw_logger.setLevel(logging.DEBUG)
        logger.info("Radar raw logging ENABLED - all readings will be logged")

    if args.show_raw:
        set_show_raw_readings(True)
        logger.info("Raw radar readings display ENABLED - signed speed values will be shown")

    trigger_kwargs = {"pre_trigger_segments": args.sound_pre_trigger}
    swing_speed_kwargs = {
        "trigger_threshold_mph": args.swing_speed_threshold,
        "max_speed_mph": None if args.swing_speed_max <= 0 else args.swing_speed_max,
        "min_readings": args.swing_speed_min_readings,
        "single_reading_peak_mph": args.swing_speed_single_peak,
        "num_reports": args.swing_speed_num_reports,
        "end_quiet_ms": args.swing_speed_end_ms,
        "cooldown_ms": args.swing_speed_cooldown_ms,
        "rejected_cooldown_ms": args.swing_speed_rejected_cooldown_ms,
    }

    if not args.no_camera:
        use_hough = args.camera_model is None and args.roboflow_model is None
        if init_camera(
            model_path=args.camera_model,
            roboflow_model_id=args.roboflow_model,
            roboflow_api_key=args.roboflow_api_key,
            imgsz=args.camera_imgsz,
            use_hough=use_hough,
            hough_param2=args.hough_param2,
            hough_param1=args.hough_param1,
            hough_min_radius=args.hough_min_radius,
            hough_max_radius=args.hough_max_radius,
            hough_min_dist=args.hough_min_dist,
        ):
            start_camera_thread()
        else:
            logger.info("Camera not available - running without camera")
    else:
        logger.info("Camera disabled by --no-camera flag")

    if server.experimental_kld7_raw_radc_logging:
        logger.info("Experimental K-LD7 raw RADC payload logging enabled")
    if server.experimental_kld7_radc_tuning:
        logger.info("Experimental K-LD7 RADC tuning enabled: %s", server.active_kld7_radc_tuning)

    if args.iwr6843:
        iwr_output_dir = (
            Path(args.iwr6843_output_dir).expanduser()
            if args.iwr6843_output_dir
            else (
                Path(args.log_dir).expanduser()
                if args.log_dir
                else Path.home() / "openflight_sessions"
            )
            / "iwr6843"
        )
        if init_iwr6843(
            port=args.iwr6843_port,
            config_path=args.iwr6843_config,
            calibration_path=args.iwr6843_cal,
            output_dir=iwr_output_dir,
            trigger_pin=args.iwr6843_trigger_pin,
            tee_range_m=args.iwr6843_tee_m,
            net_range_m=args.iwr6843_net_m,
            tx_order=args.iwr6843_tx_order,
            capture_timeout_s=args.iwr6843_capture_timeout,
            tilt_deg=args.iwr6843_tilt_deg,
            radar_height_m=args.iwr6843_radar_height_m,
            ball_height_m=args.iwr6843_ball_height_m,
            azimuth_offset_deg=args.iwr6843_azimuth_offset_deg,
            horizontal_phase_reference_rad=args.iwr6843_horizontal_phase_reference_rad,
            save_dumps=args.debug,
        ):
            calibration = server.iwr6843_runtime.calibration
            server.ball_speed_correction_distance_ft = args.iwr6843_tee_m * 3.28084
            server.ball_speed_correction_ball_above_radar_ft = (
                calibration.tee_ball_height_m - calibration.radar_height_m
            ) * 3.28084
            logger.info(
                "IWR6843 enabled (LCMF-v1 launch angle, BCM%d, %s TX order)",
                args.iwr6843_trigger_pin,
                server.iwr6843_runtime.tx_order,
            )
            if args.debug:
                logger.info("IWR6843 raw dumps enabled: %s", iwr_output_dir)
        else:
            logger.error("ERROR: IWR6843 requested but failed to initialize. Exiting.")
            sys.exit(1)

    if args.inclinometer:
        if not init_inclinometer(zero_offset_deg=args.inclinometer_zero_offset):
            logger.warning(
                "WARNING: Inclinometer unavailable; continuing with configured IWR6843 tilt"
            )

    if args.kld7:
        kld7_kwargs = _kld7_radc_tuning_kwargs(args)
        if init_kld7(
            port=args.kld7_port,
            orientation="vertical",
            angle_offset_deg=args.kld7_angle_offset,
            base_freq=0,
            vertical_estimator="two_ray",
            mount_tilt_deg=args.kld7_mount_tilt,
            ball_distance_ft=args.kld7_ball_distance,
            vertical_flight_window_net_distance_ft=args.net_distance,
            **kld7_kwargs,
        ):
            offset_str = (
                f", offset: {args.kld7_angle_offset:+.1f}°" if args.kld7_angle_offset else ""
            )
            logger.info("K-LD7 vertical radar enabled (launch angle%s)", offset_str)
        else:
            logger.error("ERROR: K-LD7 vertical requested but failed to connect. Exiting.")
            sys.exit(1)

    if args.kld7_horizontal:
        kld7_kwargs = _kld7_radc_tuning_kwargs(args)
        if init_kld7(
            port=args.kld7_horizontal_port,
            orientation="horizontal",
            angle_offset_deg=args.kld7_horizontal_offset,
            base_freq=2,
            **kld7_kwargs,
        ):
            offset_str = (
                f", offset: {args.kld7_horizontal_offset:+.1f}°"
                if args.kld7_horizontal_offset
                else ""
            )
            logger.info("K-LD7 horizontal radar enabled (club path%s)", offset_str)
        else:
            logger.error("ERROR: K-LD7 horizontal requested but failed to connect. Exiting.")
            sys.exit(1)

    start_monitor(
        port=args.port,
        mock=args.mock,
        trigger_type=args.trigger,
        debug=args.debug,
        trigger_kwargs=trigger_kwargs,
        sample_rate_ksps=args.sample_rate,
        swing_speed_mode=args.swing_speed,
        swing_speed_kwargs=swing_speed_kwargs,
        ops_baud=args.ops_baud,
    )

    if server.battery_provider:
        start_power_monitor(server.battery_provider)
        logger.info("Battery monitoring: ENABLED (%s)", server.battery_provider)

    sim_cfgs = load_sim_config() if args.sim else []
    server.sim_connectors = build_connectors(
        sim_cfgs, on_status=_sim_on_status, on_inbound=_sim_on_inbound
    )
    for connector in server.sim_connectors:
        connector.start()
        logger.info(
            "Simulator connector enabled: %s -> %s:%s",
            connector.name,
            connector.host,
            connector.port,
        )
    if args.sim and not server.sim_connectors:
        logger.info("Simulator connectors enabled (--sim) but none are enabled in config/sim.json")

    if args.mock:
        logger.info("Running in MOCK mode - no radar required")
        logger.info("Simulate shots via WebSocket or API")
    if args.swing_speed:
        logger.info("Running in SWING SPEED mode - no ball impact trigger required")

    logger.info("Server starting at http://%s:%d", args.host, args.web_port)

    try:
        server.socketio.run(
            server.app,
            host=args.host,
            port=args.web_port,
            debug=False,
            allow_unsafe_werkzeug=True,
        )
    finally:
        _cleanup_hardware_for_shutdown()
