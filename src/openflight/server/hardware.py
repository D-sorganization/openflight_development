"""Hardware controllers, lifecycle adapters, and mock monitors for OpenFlight server."""

import logging
import math
import os
import random
import statistics
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

from openflight import server
from openflight.club_data import CLUB_BALL_SPEEDS, CLUB_LAUNCH, CLUB_SPIN, ClubType
from openflight.launch_monitor import Shot
from openflight.server.state import (
    _DEFAULT_KLD7_RADC_TUNING,
    CV2_AVAILABLE,
    PICAMERA_AVAILABLE,
)
from openflight.swing_speed import SwingSpeedEvent

logger = logging.getLogger(__name__)


def _run_shutdown_step(name: str, callback: Any) -> None:
    """Run one shutdown step without preventing later hardware cleanup."""
    started = time.monotonic()
    try:
        callback()
    except Exception:
        logger.warning("[SERVER] Shutdown cleanup failed during %s", name, exc_info=True)
    finally:
        elapsed_ms = (time.monotonic() - started) * 1000
        logger.info("[SERVER] Shutdown step %s completed in %.1fms", name, elapsed_ms)


def _cleanup_hardware_for_shutdown() -> bool:
    """Stop hardware resources and report whether this caller owned cleanup."""
    with server.shutdown_lock:
        if getattr(server, "shutdown_cleanup_started", False):
            logger.info("[SERVER] Shutdown cleanup already started")
            return False
        server.shutdown_cleanup_started = True

    kld7_vertical = getattr(server, "kld7_vertical", None)
    if kld7_vertical:
        server._run_shutdown_step("K-LD7 vertical stop", kld7_vertical.stop)

    kld7_horizontal = getattr(server, "kld7_horizontal", None)
    if kld7_horizontal:
        server._run_shutdown_step("K-LD7 horizontal stop", kld7_horizontal.stop)

    inclinometer_service = getattr(server, "inclinometer_service", None)
    if inclinometer_service:
        server._run_shutdown_step("inclinometer stop", inclinometer_service.stop)

    iwr6843_runtime = getattr(server, "iwr6843_runtime", None)
    if iwr6843_runtime:
        server._run_shutdown_step("IWR6843 stop", iwr6843_runtime.stop)

    power_monitor = getattr(server, "power_monitor", None)
    if power_monitor:
        server._run_shutdown_step("battery monitor stop", power_monitor.stop)

    server._run_shutdown_step(
        "camera thread stop", getattr(server, "stop_camera_thread", stop_camera_thread)
    )

    camera = getattr(server, "camera", None)
    if camera:
        server._run_shutdown_step("camera stop", camera.stop)
        server._run_shutdown_step("camera close", camera.close)

    server._run_shutdown_step("launch monitor stop", getattr(server, "stop_monitor", stop_monitor))

    sim_connectors = getattr(server, "sim_connectors", [])
    for connector in sim_connectors:
        server._run_shutdown_step(f"simulator connector stop ({connector.name})", connector.stop)

    return True


def _shutdown_process_after_delay(delay_s: float = 0.5) -> None:
    """Give the HTTP/WebSocket response time to flush, then clean up and exit."""
    time.sleep(delay_s)
    cleanup_func = getattr(server, "_cleanup_hardware_for_shutdown", _cleanup_hardware_for_shutdown)
    if not cleanup_func():
        return
    logger.info("[SERVER] Goodbye")
    server.os._exit(0)


def init_camera(
    model_path: Optional[str] = None,
    roboflow_model_id: Optional[str] = None,
    roboflow_api_key: Optional[str] = None,
    imgsz: int = 256,
    use_hough: bool = True,
    hough_param2: int = 33,
    hough_param1: int = 48,
    hough_min_radius: int = 4,
    hough_max_radius: int = 43,
    hough_min_dist: int = 266,
) -> bool:
    """Initialize camera and ball tracker (Hough, YOLO, or Roboflow)."""
    if not CV2_AVAILABLE:
        logger.info("OpenCV not available - camera disabled")
        return False

    if not PICAMERA_AVAILABLE:
        logger.info("picamera2 not available - camera disabled")
        return False

    try:
        from picamera2 import Picamera2

        from openflight.camera_tracker import CameraTracker

        cam = Picamera2()
        config = cam.create_video_configuration(
            main={"size": (640, 480), "format": "RGB888"},
            buffer_count=2,
            controls={"FrameRate": 60},
        )
        cam.configure(config)
        cam.start()
        time.sleep(0.5)

        if roboflow_model_id:
            tracker = CameraTracker(
                roboflow_model_id=roboflow_model_id,
                roboflow_api_key=roboflow_api_key,
                imgsz=imgsz,
                use_hough=False,
            )
        elif not use_hough and model_path and os.path.exists(model_path):
            tracker = CameraTracker(
                model_path=model_path,
                imgsz=imgsz,
                use_hough=False,
            )
        else:
            tracker = CameraTracker(
                use_hough=True,
                hough_param2=hough_param2,
                hough_param1=hough_param1,
                hough_min_radius=hough_min_radius,
                hough_max_radius=hough_max_radius,
                hough_min_dist=hough_min_dist,
            )

        server.camera = cam
        server.camera_tracker = tracker
        server.camera_enabled = True
        return True
    except Exception as e:
        logger.warning("Failed to initialize camera: %s", e, exc_info=True)
        server.camera = None
        server.camera_tracker = None
        return False


def init_iwr6843(
    *,
    port: Optional[str],
    config_path: str,
    calibration_path: str,
    output_dir: str | Path,
    trigger_pin: int,
    tee_range_m: float,
    net_range_m: Optional[float],
    tx_order: str,
    capture_timeout_s: float,
    tilt_deg: Optional[float] = None,
    radar_height_m: Optional[float] = None,
    ball_height_m: float = 0.04,
    azimuth_offset_deg: float = 0.0,
    horizontal_phase_reference_rad: Optional[float] = None,
    save_dumps: bool = False,
) -> bool:
    """Initialize GPIO-triggered TI capture and the frozen LCMF-v1 estimator."""
    try:
        from openflight.iwr6843 import Calibration
        from openflight.iwr6843.monitor import (
            IWR6843CaptureMonitor,
            tx_order_from_config,
        )
        from openflight.iwr6843.runtime import IWR6843Runtime

        configured_order = tx_order_from_config(config_path)
        resolved_order = configured_order if tx_order == "auto" else tx_order
        if resolved_order != configured_order:
            raise ValueError(
                f"--iwr6843-tx-order {resolved_order} conflicts with "
                f"{Path(config_path).name} ({configured_order})"
            )

        calibration = Calibration.load(calibration_path)
        calibration.tee_range_m = tee_range_m
        calibration.tee_ball_height_m = ball_height_m
        if tilt_deg is not None:
            calibration.tilt_rad = math.radians(tilt_deg)
        if radar_height_m is not None:
            calibration.meta["radar_height_m"] = radar_height_m

        capture_monitor = IWR6843CaptureMonitor(
            config_path=config_path,
            output_dir=output_dir,
            port=port,
            gpio_pin=trigger_pin,
            save_dumps=save_dumps,
        )
        capture_monitor.start(armed=False)
        runtime = IWR6843Runtime(
            capture_monitor=capture_monitor,
            calibration=calibration,
            net_range_m=net_range_m,
            tx_order=resolved_order,
            capture_timeout_s=capture_timeout_s,
            azimuth_offset_deg=azimuth_offset_deg,
            horizontal_phase_reference_rad=horizontal_phase_reference_rad,
            tdm_sign_policy="positive",
        )
        server.iwr6843_runtime = runtime
        server.iwr6843_runtime_config = {
            "enabled": True,
            "estimator": "lcmf_v1",
            "port": capture_monitor.port,
            "config": str(config_path),
            "calibration": str(calibration_path),
            "trigger_pin_bcm": trigger_pin,
            "tee_slant_range_m": tee_range_m,
            "net_range_m": net_range_m,
            "tx_order": resolved_order,
            "tdm_sign_policy": runtime.tdm_sign_policy,
            "tilt_deg": math.degrees(calibration.tilt_rad),
            "radar_height_m": calibration.radar_height_m,
            "ball_height_m": calibration.tee_ball_height_m,
            "azimuth_offset_deg": azimuth_offset_deg,
            "horizontal_phase_reference_rad": horizontal_phase_reference_rad,
            "capture_timeout_s": capture_timeout_s,
            "freeze_delay_ms": 0.0,
            "raw_dump_saved": save_dumps,
            "output_dir": str(Path(output_dir).expanduser()),
        }
        logger.info(
            "[SERVER] IWR6843 initialized "
            "(port=%s, BCM%d, estimator=LCMF-v1, firmware boundary freeze)",
            capture_monitor.port,
            trigger_pin,
        )
        return True
    except Exception as error:
        logger.warning("[SERVER] IWR6843 initialization failed: %s", error, exc_info=True)
        server.log_session_error(
            "IWR6843 initialization failed",
            component="iwr6843",
            context={"config": config_path, "port": port or "auto"},
            exc=error,
        )
        server.iwr6843_runtime = None
        server.iwr6843_runtime_config = {"enabled": False, "error": str(error)}
        return False


def init_inclinometer(*, zero_offset_deg: float, bus_number: int = 1, address: int = 0x18) -> bool:
    """Start the optional LIS3DH service without risking radar availability."""
    service = None
    try:
        from openflight.inclinometer import LIS3DH, InclinometerService

        service = InclinometerService(
            LIS3DH(bus_number=bus_number, address=address),
            zero_offset_deg=zero_offset_deg,
        )
        service.start()
        startup = service.wait_for_stable(timeout_s=2.0)
        server.inclinometer_service = service
        server.inclinometer_runtime_config = {
            "enabled": True,
            "sensor": "lis3dh",
            "i2c_bus": bus_number,
            "i2c_address": f"0x{address:02x}",
            "sample_hz": service.sample_hz,
            "zero_offset_deg": zero_offset_deg,
            "startup": startup.to_dict(),
        }
        if startup.snapshot is None:
            logger.warning(
                "[SERVER] LIS3DH initialized but has no stable startup reading (%s)",
                startup.status,
            )
            logger.info(
                "Inclinometer enabled, waiting for a stable reading (%s)",
                startup.status,
            )
            return True

        snapshot = startup.snapshot
        logger.info(
            "Inclinometer enabled (raw pitch %+.2fdeg, calibrated %+.2fdeg)",
            snapshot.raw_pitch_deg,
            snapshot.calibrated_pitch_deg,
        )
        iwr6843_runtime = getattr(server, "iwr6843_runtime", None)
        if iwr6843_runtime is not None:
            configured_tilt = math.degrees(iwr6843_runtime.calibration.tilt_rad)
            effective_tilt = configured_tilt + snapshot.calibrated_pitch_deg
            logger.info(
                "IWR6843 tilt: configured %.2fdeg, effective %.2fdeg",
                configured_tilt,
                effective_tilt,
            )
        return True
    except Exception as error:
        if service is not None:
            try:
                service.stop()
            except Exception:
                logger.debug("Failed to close LIS3DH after initialization error", exc_info=True)
        logger.warning("[SERVER] Inclinometer initialization failed: %s", error, exc_info=True)
        server.log_session_error(
            "Inclinometer initialization failed",
            component="inclinometer",
            context={"i2c_bus": bus_number, "i2c_address": f"0x{address:02x}"},
            exc=error,
        )
        server.inclinometer_service = None
        server.inclinometer_runtime_config = {
            "enabled": False,
            "requested": True,
            "sensor": "lis3dh",
            "i2c_bus": bus_number,
            "i2c_address": f"0x{address:02x}",
            "zero_offset_deg": zero_offset_deg,
            "error": str(error),
        }
        return False


def init_kld7(
    port: Optional[str] = None,
    orientation: str = "vertical",
    angle_offset_deg: float = 0.0,
    base_freq: int = 0,
    radc_speed_tolerance_mph: float = 10.0,
    radc_centroid_floor_frac: float = 0.5,
    radc_spectrum_source: str = "f1a",
    radc_ops_bin_outlier_tol: int = 25,
    radc_ops_bin_outlier_penalty: float = 10.0,
    radc_ops_anchored_peak_min_snr: float = 5.0,
    radc_vertical_impact_energy_threshold: float = 3.0,
    radc_horizontal_impact_energy_threshold: float = 1.85,
    radc_horizontal_retry_impact_energy_threshold: float = 0.5,
    radc_horizontal_angle_limit_deg: float = 15.0,
    vertical_estimator: str = "naive",
    mount_tilt_deg: float = 18.0,
    ball_distance_ft: float = 5.5,
    vertical_flight_window_net_distance_ft: float = 10.0,
) -> bool:
    """Initialize a single K-LD7 angle radar tracker."""
    try:
        from openflight.kld7 import KLD7Tracker

        tracker = KLD7Tracker(
            port=port,
            orientation=orientation,
            angle_offset_deg=angle_offset_deg,
            base_freq=base_freq,
            buffer_seconds=6.0,
            radc_speed_tolerance_mph=radc_speed_tolerance_mph,
            radc_centroid_floor_frac=radc_centroid_floor_frac,
            radc_spectrum_source=radc_spectrum_source,
            radc_ops_bin_outlier_tol=radc_ops_bin_outlier_tol,
            radc_ops_bin_outlier_penalty=radc_ops_bin_outlier_penalty,
            radc_ops_anchored_peak_min_snr=radc_ops_anchored_peak_min_snr,
            radc_vertical_impact_energy_threshold=radc_vertical_impact_energy_threshold,
            radc_horizontal_impact_energy_threshold=radc_horizontal_impact_energy_threshold,
            radc_horizontal_retry_impact_energy_threshold=radc_horizontal_retry_impact_energy_threshold,
            radc_horizontal_angle_limit_deg=radc_horizontal_angle_limit_deg,
            vertical_estimator=vertical_estimator,
            mount_tilt_deg=mount_tilt_deg,
            ball_distance_ft=ball_distance_ft,
            vertical_flight_window_net_distance_ft=vertical_flight_window_net_distance_ft,
        )
        if tracker.connect():
            tracker.start()
            logger.info(
                "[SERVER] K-LD7 %s initialized (port=%s, offset=%.1f°, RBFR=%d)",
                orientation,
                port or "auto",
                angle_offset_deg,
                base_freq,
            )
            session_log = server.get_session_logger()
            if session_log:
                session_log.log_connection(
                    device=f"kld7_{orientation}",
                    port=tracker.port or "auto",
                    baud=3000000,
                    radc_available=True,
                    base_freq=base_freq,
                )
            if orientation == "vertical":
                server.kld7_vertical = tracker
            else:
                server.kld7_horizontal = tracker
            return True
        return False
    except Exception as e:
        logger.warning("[SERVER] K-LD7 %s initialization failed: %s", orientation, e, exc_info=True)
        server.log_session_error(
            "K-LD7 initialization failed",
            component="kld7",
            context={"orientation": orientation},
            exc=e,
        )
        return False


def camera_processing_loop() -> None:
    """Background thread for camera processing."""
    import cv2

    while not server.camera_stop_event.is_set():
        if not getattr(server, "camera", None) or not getattr(server, "camera_enabled", False):
            time.sleep(0.1)
            continue

        try:
            frame = server.camera.capture_array()

            if getattr(server, "camera_tracker", None):
                detection = server.camera_tracker.process_frame(frame)
                new_detected = detection is not None
                new_confidence = detection.confidence if detection else 0.0

                if (
                    new_detected != getattr(server, "ball_detected", False)
                    or abs(new_confidence - getattr(server, "ball_detection_confidence", 0.0))
                    > 0.05
                ):
                    server.ball_detected = new_detected
                    server.ball_detection_confidence = new_confidence
                    server.socketio.emit(
                        "ball_detection",
                        {
                            "detected": server.ball_detected,
                            "confidence": round(server.ball_detection_confidence, 2),
                        },
                    )

                if getattr(server, "camera_streaming", False):
                    frame = server.camera_tracker.get_debug_frame(frame)

            if getattr(server, "camera_streaming", False):
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                _, jpeg = cv2.imencode(".jpg", frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 70])
                with server.frame_lock:
                    server.latest_frame = jpeg.tobytes()

        except Exception as e:
            logger.warning("Camera processing error: %s", e)
            time.sleep(0.1)


def start_camera_thread() -> None:
    """Start the camera processing thread."""
    if getattr(server, "camera_thread", None) and server.camera_thread.is_alive():
        return

    server.camera_stop_event = threading.Event()
    server.camera_thread = threading.Thread(target=server.camera_processing_loop, daemon=True)
    server.camera_thread.start()
    logger.info("Camera processing thread started")


def stop_camera_thread() -> None:
    """Stop the camera processing thread."""
    if getattr(server, "camera_stop_event", None):
        server.camera_stop_event.set()
    if getattr(server, "camera_thread", None):
        server.camera_thread.join(timeout=2.0)
        server.camera_thread = None


def generate_mjpeg() -> Any:
    """Generator for MJPEG stream."""
    while True:
        if not getattr(server, "camera_streaming", False):
            break

        with server.frame_lock:
            frame = getattr(server, "latest_frame", None)

        if frame:
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
        else:
            time.sleep(0.03)


def _kld7_radc_tuning_kwargs(args: Any) -> dict[str, Any]:
    """Return K-LD7 RADC extraction parameters for startup."""
    if not getattr(args, "experimental_kld7_radc_tuning", False):
        return dict(_DEFAULT_KLD7_RADC_TUNING)

    return {
        "radc_speed_tolerance_mph": args.experimental_kld7_speed_tolerance,
        "radc_centroid_floor_frac": args.experimental_kld7_centroid_floor,
        "radc_spectrum_source": args.experimental_kld7_spectrum_source,
        "radc_ops_bin_outlier_tol": args.experimental_kld7_ops_bin_tol,
        "radc_ops_bin_outlier_penalty": args.experimental_kld7_ops_bin_penalty,
        "radc_ops_anchored_peak_min_snr": args.experimental_kld7_ops_anchored_min_snr,
        "radc_vertical_impact_energy_threshold": args.experimental_kld7_vertical_impact_energy,
        "radc_horizontal_impact_energy_threshold": args.experimental_kld7_horizontal_impact_energy,
        "radc_horizontal_retry_impact_energy_threshold": (
            args.experimental_kld7_horizontal_retry_impact_energy
        ),
        "radc_horizontal_angle_limit_deg": args.experimental_kld7_horizontal_angle_limit,
    }


def _session_start_config() -> dict[str, Any]:
    """Return session-start config including experimental K-LD7 provenance."""
    config = server.radar_config.copy()
    config["kld7_experiments"] = {
        "trackman_calibration_enabled": False,
        "trackman_calibration_model": None,
        "raw_radc_payload_logging_enabled": server._experimental_kld7_raw_radc_logging_enabled(),
        "raw_radc_payload_logging_requested": getattr(
            server, "experimental_kld7_raw_radc_logging", False
        ),
        "radc_tuning_enabled": getattr(server, "experimental_kld7_radc_tuning", False),
        "radc_tuning_params": dict(getattr(server, "active_kld7_radc_tuning", {})),
    }
    config["iwr6843"] = dict(getattr(server, "iwr6843_runtime_config", {}))
    config["inclinometer"] = dict(getattr(server, "inclinometer_runtime_config", {}))
    config["power"] = {
        "enabled": getattr(server, "battery_provider", None) is not None,
        "provider": getattr(server, "battery_provider", None),
    }
    return config


def start_monitor(
    port: Optional[str] = None,
    mock: bool = False,
    trigger_type: str = "polling",
    debug: bool = False,
    trigger_kwargs: Optional[dict] = None,
    sample_rate_ksps: int = 30,
    swing_speed_mode: bool = False,
    swing_speed_kwargs: Optional[dict] = None,
    ops_baud: Optional[int] = None,
) -> None:
    """Start the monitor in launch monitor or swing speed mode."""
    if getattr(server, "monitor", None) is not None:
        logger.info("[MONITOR] Stopping existing monitor before starting new one")
        server.stop_monitor()

    server.mock_mode = mock
    server.mock_swing_speed_mode = mock and swing_speed_mode

    if server.mock_swing_speed_mode:
        monitor = MockSwingSpeedMonitor(**(swing_speed_kwargs or {}))
        logger.info("[MODE] Mock swing speed training mode")
    elif mock:
        monitor = MockLaunchMonitor()
    elif swing_speed_mode:
        from openflight.swing_speed import SwingSpeedMonitor

        monitor = SwingSpeedMonitor(
            port=port,
            **(swing_speed_kwargs or {}),
        )
        logger.info("[MODE] Swing speed training mode")
    else:
        from openflight.rolling_buffer import RollingBufferMonitor

        monitor = RollingBufferMonitor(
            port=port,
            trigger_type=trigger_type,
            sample_rate_ksps=sample_rate_ksps,
            ops_baud=ops_baud,
            **(trigger_kwargs or {}),
        )
        logger.info(
            "[MODE] Rolling buffer mode (trigger: %s, sample_rate: %dksps)",
            trigger_type,
            sample_rate_ksps,
        )

    server.monitor = monitor
    monitor.connect()

    if swing_speed_mode:
        swing_config = swing_speed_kwargs or {}
        server.radar_config = {
            **server.radar_config,
            "min_speed": int(swing_config.get("trigger_threshold_mph", 30)),
            "max_speed": int(swing_config.get("max_speed_mph") or 0),
        }

    logger.info(
        "[SERVER] Starting monitor: mode=%s, trigger=%s, sample_rate=%dksps",
        "swing-speed" if swing_speed_mode else ("mock" if mock else "rolling-buffer"),
        trigger_type,
        sample_rate_ksps,
    )

    session_logger = server.get_session_logger()
    if session_logger:
        radar_info = monitor.get_radar_info() if not mock else {}
        session_logger.start_session(
            radar_port=port if not mock else "mock",
            firmware_version=radar_info.get("Version"),
            camera_enabled=getattr(server, "camera", None) is not None,
            camera_model=(
                "hough"
                if (getattr(server, "camera_tracker", None) and server.camera_tracker.use_hough)
                else None
            ),
            config=server._session_start_config(),
            mode=("swing-speed" if swing_speed_mode else ("mock" if mock else "rolling-buffer")),
            trigger_type=None if swing_speed_mode or mock else trigger_type,
        )
        if not mock and radar_info:
            session_logger.log_connection(
                device="ops243",
                port=port or "auto",
                baud=(getattr(monitor.radar, "baud", 0) if hasattr(monitor, "radar") else 0),
                firmware=radar_info.get("Version"),
            )
            radar = getattr(monitor, "radar", None)
            if not swing_speed_mode and radar is not None and hasattr(radar, "read_clock_sync"):
                try:
                    clock_sync = radar.read_clock_sync()
                    session_logger.log_clock_sync(
                        device="ops243",
                        port=port or "auto",
                        summary=clock_sync,
                    )
                except Exception:
                    logger.warning("[SERVER] OPS clock sync read failed", exc_info=True)
        if not mock and getattr(server, "iwr6843_runtime", None) is not None:
            session_logger.log_connection(
                device="iwr6843",
                port=server.iwr6843_runtime.capture_monitor.port,
                baud=getattr(server.iwr6843_runtime.capture_monitor.radar, "baud", 1_041_667),
                firmware="custom-l3-dump",
                estimator="lcmf_v1",
                trigger_pin_bcm=server.iwr6843_runtime_config.get("trigger_pin_bcm"),
            )
        if not mock and getattr(server, "inclinometer_service", None) is not None:
            session_logger.log_connection(
                device="lis3dh",
                port=f"i2c-{server.inclinometer_runtime_config.get('i2c_bus', 1)}",
                baud=0,
                address=server.inclinometer_runtime_config.get("i2c_address", "0x18"),
                sample_hz=server.inclinometer_runtime_config.get("sample_hz", 10.0),
            )

    if swing_speed_mode:
        monitor.start(
            event_callback=server.on_swing_speed_detected,
            live_callback=getattr(server, "on_live_reading", None),
        )
    elif not mock:

        def on_trigger_diagnostic(data: dict):
            server.socketio.emit("trigger_diagnostic", data)

        monitor.start(
            shot_callback=server.on_shot_detected,
            live_callback=getattr(server, "on_live_reading", None),
            diagnostic_callback=on_trigger_diagnostic,
            processing_callback=getattr(server, "on_shot_processing", None),
        )
        if getattr(server, "iwr6843_runtime", None) is not None:
            server.iwr6843_runtime.capture_monitor.arm()
    else:
        monitor.start(
            shot_callback=server.on_shot_detected,
            live_callback=getattr(server, "on_live_reading", None),
        )


def stop_monitor() -> None:
    """Stop the launch monitor."""
    session_logger = server.get_session_logger()
    if session_logger:
        session_logger.end_session()
        server._fire_cloud_push(session_logger)

    monitor = getattr(server, "monitor", None)
    if monitor:
        monitor.stop()
        monitor.disconnect()
        server.monitor = None
    server.mock_swing_speed_mode = False


class MockLaunchMonitor:
    """Mock launch monitor for UI development without radar hardware."""

    _CLUB_BALL_SPEEDS = CLUB_BALL_SPEEDS
    _CLUB_SPIN = CLUB_SPIN
    _CLUB_LAUNCH = CLUB_LAUNCH

    def __init__(self):
        self._shots: List[Shot] = []
        self._running = False
        self._shot_callback = None
        self._current_club = ClubType.DRIVER

    def connect(self) -> bool:
        return True

    def disconnect(self) -> None:
        self.stop()

    def start(self, shot_callback=None, live_callback=None) -> None:
        self._shot_callback = shot_callback
        self._running = True
        logger.info("Mock monitor started - simulate shots via WebSocket")

    def stop(self) -> None:
        self._running = False

    def simulate_shot(self, ball_speed: Optional[float] = None) -> Shot:
        avg_speed, std_dev, smash = self._CLUB_BALL_SPEEDS.get(self._current_club, (120, 15, 1.35))
        if ball_speed is None:
            ball_speed = max(50, min(200, random.gauss(avg_speed, std_dev)))

        smash_factor = smash + random.uniform(-0.03, 0.03)
        club_speed = ball_speed / smash_factor

        avg_spin, spin_std = self._CLUB_SPIN.get(self._current_club, (5000, 800))
        spin_rpm = max(1000, random.gauss(avg_spin, spin_std))

        avg_launch, launch_std = self._CLUB_LAUNCH.get(self._current_club, (18.0, 3.0))
        launch_v = max(5.0, random.gauss(avg_launch, launch_std))
        launch_h = random.gauss(0, 2.0)
        launch_confidence = round(random.uniform(0.5, 0.95), 2)
        club_aoa = round(random.gauss(-4.0, 2.5), 1)

        shot = Shot(
            ball_speed_mph=ball_speed,
            club_speed_mph=club_speed,
            timestamp=datetime.now(),
            club=self._current_club,
            spin_rpm=spin_rpm,
            spin_confidence=random.choice([0.3, 0.6, 0.7, 0.9]),
            launch_angle_vertical=round(launch_v, 1),
            launch_angle_horizontal=round(launch_h, 1),
            launch_angle_confidence=launch_confidence,
            launch_angle_vertical_confidence=launch_confidence,
            launch_angle_horizontal_confidence=launch_confidence,
            launch_angle_vertical_source="mock",
            launch_angle_horizontal_source="mock",
            angle_source="mock",
            club_angle_deg=club_aoa,
            club_path_deg=round(random.uniform(-5.0, 5.0), 1),
            spin_axis_deg=round(launch_h - random.uniform(-5.0, 5.0), 1),
            mode="mock",
        )

        self._shots.append(shot)
        if self._shot_callback:
            self._shot_callback(shot)
        return shot

    def get_shots(self) -> List[Shot]:
        return self._shots.copy()

    def get_session_stats(self) -> dict[str, Any]:
        if not self._shots:
            return {
                "shot_count": 0,
                "avg_ball_speed": 0,
                "max_ball_speed": 0,
                "min_ball_speed": 0,
                "avg_club_speed": None,
                "avg_smash_factor": None,
                "avg_carry_est": 0,
            }

        ball_speeds = [s.ball_speed_mph for s in self._shots]
        club_speeds = [s.club_speed_mph for s in self._shots if s.club_speed_mph]
        smash_factors = [s.smash_factor for s in self._shots if s.smash_factor]

        return {
            "shot_count": len(self._shots),
            "avg_ball_speed": statistics.mean(ball_speeds),
            "max_ball_speed": max(ball_speeds),
            "min_ball_speed": min(ball_speeds),
            "std_dev": statistics.stdev(ball_speeds) if len(ball_speeds) > 1 else 0,
            "avg_club_speed": statistics.mean(club_speeds) if club_speeds else None,
            "avg_smash_factor": (statistics.mean(smash_factors) if smash_factors else None),
            "avg_carry_est": statistics.mean([s.estimated_carry_yards for s in self._shots]),
        }

    def clear_session(self) -> None:
        self._shots = []

    def set_club(self, club: ClubType) -> None:
        self._current_club = club


class _MockSwingRadar:
    """Tiny radar facade so UI tuning can exercise the swing speed controls."""

    port = "mock"
    baud = 0

    def set_min_speed_filter(self, value: int) -> None:
        pass

    def set_max_speed_filter(self, value: int) -> None:
        pass

    def set_magnitude_filter(self, min_mag: int = 0, max_mag: int = 0) -> None:
        pass

    def set_transmit_power(self, level: int) -> None:
        pass


class MockSwingSpeedMonitor:
    """Mock swing speed monitor for UI development without OPS hardware."""

    def __init__(
        self,
        trigger_threshold_mph: float = 30.0,
        max_speed_mph: Optional[float] = 130.0,
        min_readings: int = 3,
        single_reading_peak_mph: float = 60.0,
        **kwargs: Any,
    ):
        self.trigger_threshold_mph = float(trigger_threshold_mph)
        self.max_speed_mph = None if max_speed_mph is None else float(max_speed_mph)
        self.min_readings = int(min_readings)
        self.single_reading_peak_mph = float(single_reading_peak_mph)
        self.radar = _MockSwingRadar()
        self._events: List[SwingSpeedEvent] = []
        self._running = False
        self._event_callback = None
        self.training_implement = "driver"
        self.training_implement_label = "Driver"

    def connect(self) -> bool:
        return True

    def disconnect(self) -> None:
        self.stop()

    def start(self, event_callback=None, live_callback=None) -> None:
        self._event_callback = event_callback
        self._running = True
        logger.info("Mock swing speed monitor started - simulate swings via WebSocket")

    def stop(self) -> None:
        self._running = False

    def get_radar_info(self) -> dict[str, str]:
        return {"Version": "mock-swing-speed"}

    def simulate_shot(self, peak_speed: Optional[float] = None) -> SwingSpeedEvent:
        lower = max(20.0, float(self.trigger_threshold_mph))
        upper = float(self.max_speed_mph) if self.max_speed_mph is not None else 130.0
        upper = max(lower + 1.0, upper)

        if peak_speed is None:
            center = min(max(lower + 35.0, 95.0), upper - 4.0)
            peak_speed = random.gauss(center, 6.0)

        peak_speed = max(lower, min(upper, float(peak_speed)))
        trigger_speed = max(lower, min(peak_speed, peak_speed - random.uniform(12.0, 24.0)))
        reading_count = random.randint(max(1, self.min_readings), max(self.min_readings + 3, 8))

        event = SwingSpeedEvent(
            peak_speed_mph=peak_speed,
            timestamp=datetime.now(),
            duration_ms=random.uniform(850.0, 1800.0),
            reading_count=reading_count,
            trigger_speed_mph=trigger_speed,
            peak_magnitude=random.uniform(80.0, 450.0),
            training_implement=self.training_implement,
            training_implement_label=self.training_implement_label,
        )
        self._events.append(event)

        if self._event_callback:
            self._event_callback(event)
        return event

    def get_shots(self) -> List[Shot]:
        return []

    def get_events(self) -> List[SwingSpeedEvent]:
        return list(self._events)

    def get_session_stats(self) -> dict[str, Any]:
        if not self._events:
            return {
                "shot_count": 0,
                "avg_ball_speed": 0,
                "max_ball_speed": 0,
                "min_ball_speed": 0,
                "avg_club_speed": None,
                "avg_smash_factor": None,
                "avg_carry_est": 0,
            }

        speeds = [event.peak_speed_mph for event in self._events]
        return {
            "shot_count": len(self._events),
            "avg_ball_speed": statistics.mean(speeds),
            "max_ball_speed": max(speeds),
            "min_ball_speed": min(speeds),
            "std_dev": statistics.stdev(speeds) if len(speeds) > 1 else 0,
            "avg_club_speed": statistics.mean(speeds),
            "avg_smash_factor": None,
            "avg_carry_est": 0,
        }

    def clear_session(self) -> None:
        self._events = []

    def set_club(self, club: ClubType) -> None:
        pass

    def set_training_implement(
        self, implement: str, label: Optional[str] = None
    ) -> None:
        self.training_implement = implement
        self.training_implement_label = label or getattr(
            server, "TRAINING_IMPLEMENT_LABELS", {}
        ).get(implement, implement.title())
