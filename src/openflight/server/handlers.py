"""HTTP routes and Socket.IO event handlers for OpenFlight UI server."""

import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import Flask, Response, send_from_directory
from flask_socketio import SocketIO

from openflight import server
from openflight.club_data import ClubType
from openflight.ops243 import Direction, SpeedReading
from openflight.server.state import TRAINING_IMPLEMENT_LABELS, _react_app_dir

logger = logging.getLogger(__name__)


def _get_trigger_status() -> dict:
    """Build trigger status payload for the UI."""
    from openflight.rolling_buffer import RollingBufferMonitor
    from openflight.server.hardware import MockSwingSpeedMonitor
    from openflight.swing_speed import SwingSpeedMonitor

    monitor = getattr(server, "monitor", None)
    mock_mode = getattr(server, "mock_mode", False)
    is_rolling_buffer = isinstance(monitor, RollingBufferMonitor)
    is_swing_speed = isinstance(monitor, (SwingSpeedMonitor, MockSwingSpeedMonitor))
    session_logger = server.get_session_logger()
    stats = session_logger.stats if session_logger else {}

    if is_swing_speed:
        mode = "swing-speed"
    elif mock_mode:
        mode = "mock"
    else:
        mode = "rolling-buffer"
    trigger_type = None
    radar_port = None

    if is_rolling_buffer:
        trigger_type = monitor.trigger_type
    if is_rolling_buffer or is_swing_speed:
        if hasattr(monitor, "radar") and hasattr(monitor.radar, "port"):
            radar_port = monitor.radar.port

    return {
        "mode": mode,
        "trigger_type": trigger_type,
        "radar_connected": monitor is not None and not mock_mode,
        "radar_port": radar_port,
        "triggers_total": stats.get("triggers_total", 0),
        "triggers_accepted": stats.get("triggers_accepted", 0),
        "triggers_rejected": stats.get("triggers_rejected", 0),
    }


def _session_shots() -> list[dict]:
    """Return current session rows in the UI's shot-shaped payload format."""
    from openflight.server.hardware import MockSwingSpeedMonitor
    from openflight.swing_speed import SwingSpeedMonitor

    monitor = getattr(server, "monitor", None)
    if not monitor:
        return []
    if isinstance(monitor, (SwingSpeedMonitor, MockSwingSpeedMonitor)):
        return [server.swing_speed_to_shot_dict(event) for event in monitor.get_events()]
    return [server.shot_to_dict(shot) for shot in monitor.get_shots()]


def _delete_session_row(timestamp: str) -> bool:
    """Delete one shot or swing-speed rep by UI timestamp."""
    from openflight.server.hardware import MockSwingSpeedMonitor
    from openflight.swing_speed import SwingSpeedMonitor

    monitor = getattr(server, "monitor", None)
    if not monitor or not timestamp:
        return False

    if isinstance(monitor, (SwingSpeedMonitor, MockSwingSpeedMonitor)):
        events = getattr(monitor, "_events", None)
        if events is None:
            return False
        for index, event in enumerate(events):
            if event.timestamp.isoformat() == timestamp:
                del events[index]
                return True
        return False

    shots = getattr(monitor, "_shots", None)
    if shots is None:
        return False
    for index, shot in enumerate(shots):
        if shot.timestamp.isoformat() == timestamp:
            del shots[index]
            return True
    return False


def start_debug_logging() -> str:
    """Start logging raw readings to a file."""
    log_dir = Path.home() / "openflight_logs"
    log_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    debug_log_path = log_dir / f"debug_{timestamp}.jsonl"
    debug_log_file = open(debug_log_path, "w", encoding="utf-8")

    server.debug_log_file = debug_log_file
    server.debug_log_path = debug_log_path

    radar_logger = logging.getLogger("ops243")
    radar_raw_logger = logging.getLogger("ops243.raw")
    radar_logger.setLevel(logging.DEBUG)
    radar_raw_logger.setLevel(logging.DEBUG)

    raw_log_path = log_dir / f"radar_raw_{timestamp}.log"
    file_handler = logging.FileHandler(raw_log_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
    radar_raw_logger.addHandler(file_handler)
    radar_logger.addHandler(file_handler)

    logger.info("[DEBUG] Debug logging to: %s", debug_log_path)
    logger.info("[DEBUG] Raw radar logging to: %s", raw_log_path)
    return str(debug_log_path)


def stop_debug_logging() -> None:
    """Stop logging and close the file."""
    debug_log_file = getattr(server, "debug_log_file", None)
    debug_log_path = getattr(server, "debug_log_path", None)
    if debug_log_file:
        debug_log_file.close()
        server.debug_log_file = None
        logger.info("[DEBUG] Debug log saved: %s", debug_log_path)


def log_debug_reading(reading: SpeedReading) -> None:
    """Log a raw reading to the debug file."""
    debug_log_file = getattr(server, "debug_log_file", None)
    if debug_log_file:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "reading",
            "speed": reading.speed,
            "direction": reading.direction.value,
            "magnitude": reading.magnitude,
            "unit": reading.unit,
        }
        debug_log_file.write(json.dumps(entry) + "\n")
        debug_log_file.flush()
        logger.info(
            "[RADAR] %.1f mph %s (mag=%s)",
            reading.speed,
            reading.direction.value,
            reading.magnitude,
        )


def on_live_reading(reading: SpeedReading) -> None:
    """Callback for live radar readings - used in debug mode."""
    if getattr(server, "debug_mode", False):
        server.log_debug_reading(reading)
        server.socketio.emit(
            "debug_reading",
            {
                "speed": reading.speed,
                "direction": reading.direction.value,
                "magnitude": reading.magnitude,
                "timestamp": datetime.now().isoformat(),
                "filtered": reading.direction != Direction.OUTBOUND,
            },
        )


def on_shot_processing(state: str) -> None:
    """Forward the rolling-buffer processing lifecycle to the UI."""
    server.socketio.emit("shot_processing", {"state": state})


# Route handlers
def index() -> Response:
    """Serve the React app."""
    return send_from_directory(_react_app_dir(server.app.static_folder), "index.html")


def display() -> Response:
    """Serve the React app for TV display mode."""
    return send_from_directory(_react_app_dir(server.app.static_folder), "index.html")


def static_files(path: str) -> Response:
    """Serve static files."""
    return send_from_directory(server.app.static_folder, path)


def api_shutdown() -> tuple[dict[str, str], int]:
    """Cleanly shut down the server via REST API."""
    logger.info("[SERVER] Shutdown requested via REST API")
    threading.Thread(target=server._shutdown_process_after_delay, daemon=True).start()
    return {"status": "shutting_down"}, 200


def camera_stream() -> Any:
    """MJPEG stream endpoint."""
    camera_enabled = getattr(server, "camera_enabled", False)
    camera_streaming = getattr(server, "camera_streaming", False)
    if not camera_enabled or not camera_streaming:
        return "Camera not available", 503

    from openflight.server.hardware import generate_mjpeg

    return Response(generate_mjpeg(), mimetype="multipart/x-mixed-replace; boundary=frame")


# Socket.IO event handlers
def handle_connect() -> None:
    """Handle client connection."""
    logger.info("[SERVER] Client connected")
    server._emit_sim_snapshot()
    power_monitor = getattr(server, "power_monitor", None)
    if power_monitor and power_monitor.status:
        server.socketio.emit("power_status", power_monitor.status.to_dict())
    monitor = getattr(server, "monitor", None)
    if monitor:
        stats = monitor.get_session_stats()
        server.socketio.emit(
            "session_state",
            {
                "stats": stats,
                "shots": server._session_shots(),
                "mock_mode": getattr(server, "mock_mode", False),
                "debug_mode": getattr(server, "debug_mode", False),
                "camera_available": getattr(server, "camera", None) is not None,
                "camera_enabled": getattr(server, "camera_enabled", False),
                "camera_streaming": getattr(server, "camera_streaming", False),
                "ball_detected": getattr(server, "ball_detected", False),
                "player_name": getattr(server, "current_player_name", "Player 1"),
            },
        )
        server.socketio.emit("trigger_status", server._get_trigger_status())


def handle_disconnect() -> None:
    """Handle client disconnection."""
    logger.info("[SERVER] Client disconnected")


def handle_get_trigger_status() -> None:
    """Get current trigger/mode status for debug UI."""
    server.socketio.emit("trigger_status", server._get_trigger_status())


def handle_set_club(data: dict) -> None:
    """Handle club selection change."""
    club_name = data.get("club", "driver") if isinstance(data, dict) else "driver"
    try:
        club = ClubType(club_name)
        monitor = getattr(server, "monitor", None)
        if monitor:
            monitor.set_club(club)
        server.socketio.emit("club_changed", {"club": club.value})
    except ValueError:
        pass


def handle_set_player(data: Any) -> None:
    """Handle active player selection changes."""
    raw_name = data.get("player_name", "Player 1") if isinstance(data, dict) else "Player 1"
    player_name = str(raw_name).strip()[:40] or "Player 1"
    server.current_player_name = player_name
    server.socketio.emit("player_changed", {"player_name": player_name})


def handle_set_training_implement(data: Any) -> None:
    """Handle swing speed training implement selection."""
    implement = data.get("implement", "driver") if isinstance(data, dict) else "driver"
    label = TRAINING_IMPLEMENT_LABELS.get(implement)
    if not label:
        server.socketio.emit("training_implement_error", {"error": "Unknown training implement"})
        return

    monitor = getattr(server, "monitor", None)
    if monitor and hasattr(monitor, "set_training_implement"):
        monitor.set_training_implement(implement, label)
    server.socketio.emit(
        "training_implement_changed",
        {"implement": implement, "label": label},
    )


def handle_clear_session() -> None:
    """Clear all recorded shots."""
    monitor = getattr(server, "monitor", None)
    if monitor:
        monitor.clear_session()
        server.socketio.emit("session_cleared")


def handle_upload_cloud() -> None:
    """Manually trigger upload of completed session logs."""
    threading.Thread(target=server._run_cloud_push_for_ui, daemon=True).start()


def handle_get_session() -> None:
    """Get current session data."""
    monitor = getattr(server, "monitor", None)
    if monitor:
        stats = monitor.get_session_stats()
        server.socketio.emit(
            "session_state",
            {
                "stats": stats,
                "shots": server._session_shots(),
                "player_name": getattr(server, "current_player_name", "Player 1"),
            },
        )


def handle_delete_shot(data: Any) -> None:
    """Delete one recorded shot or swing-speed rep from the current session."""
    timestamp = data.get("timestamp") if isinstance(data, dict) else None
    deleted = server._delete_session_row(timestamp)

    if not deleted:
        server.socketio.emit("delete_shot_error", {"error": "Shot not found"})
        return

    monitor = getattr(server, "monitor", None)
    stats = monitor.get_session_stats() if monitor else {}
    server.socketio.emit(
        "session_state",
        {
            "stats": stats,
            "shots": server._session_shots(),
            "player_name": getattr(server, "current_player_name", "Player 1"),
        },
    )


def handle_simulate_shot() -> None:
    """Simulate a shot (only works in mock mode)."""
    from openflight.server.hardware import MockLaunchMonitor, MockSwingSpeedMonitor

    monitor = getattr(server, "monitor", None)
    if monitor and isinstance(monitor, (MockLaunchMonitor, MockSwingSpeedMonitor)):
        monitor.simulate_shot()


def handle_toggle_debug() -> None:
    """Toggle debug mode on/off."""
    server.debug_mode = not getattr(server, "debug_mode", False)
    if server.debug_mode:
        log_path = server.start_debug_logging()
        server.socketio.emit("debug_toggled", {"enabled": True, "log_path": log_path})
        logger.info("[DEBUG] Debug mode ENABLED")
    else:
        server.stop_debug_logging()
        server.socketio.emit("debug_toggled", {"enabled": False})
        logger.info("[DEBUG] Debug mode DISABLED")


def handle_get_debug_status() -> None:
    """Get current debug mode status."""
    debug_log_path = getattr(server, "debug_log_path", None)
    server.socketio.emit(
        "debug_status",
        {
            "enabled": getattr(server, "debug_mode", False),
            "log_path": str(debug_log_path) if debug_log_path else None,
        },
    )


def handle_get_radar_config() -> None:
    """Get current radar configuration."""
    server.socketio.emit("radar_config", getattr(server, "radar_config", {}))


def handle_set_radar_config(data: dict) -> None:
    """Update radar configuration."""
    monitor = getattr(server, "monitor", None)
    mock_mode = getattr(server, "mock_mode", False)
    mock_swing_speed_mode = getattr(server, "mock_swing_speed_mode", False)

    if not monitor or (mock_mode and not mock_swing_speed_mode):
        server.log_session_error(
            "Radar config update rejected: radar not connected",
            component="server",
            context={"stage": "set_radar_config", "mock_mode": mock_mode},
        )
        server.socketio.emit("radar_config_error", {"error": "Radar not connected"})
        return

    try:
        from openflight.server.hardware import MockSwingSpeedMonitor
        from openflight.swing_speed import SwingSpeedMonitor

        is_swing_speed = isinstance(monitor, (SwingSpeedMonitor, MockSwingSpeedMonitor))

        if "min_speed" in data:
            new_min = int(data["min_speed"])
            monitor.radar.set_min_speed_filter(new_min)
            if is_swing_speed:
                monitor.trigger_threshold_mph = float(new_min)
            server.radar_config["min_speed"] = new_min
            logger.info("[SERVER] Set min speed filter: %d mph", new_min)

        if "max_speed" in data:
            new_max = int(data["max_speed"])
            monitor.radar.set_max_speed_filter(new_max)
            if is_swing_speed:
                monitor.max_speed_mph = None if new_max <= 0 else float(new_max)
            server.radar_config["max_speed"] = new_max
            logger.info("[SERVER] Set max speed filter: %d mph", new_max)

        if "min_magnitude" in data:
            new_mag = int(data["min_magnitude"])
            monitor.radar.set_magnitude_filter(min_mag=new_mag)
            server.radar_config["min_magnitude"] = new_mag
            logger.info("[SERVER] Set min magnitude filter: %d", new_mag)

        if "transmit_power" in data:
            new_power = int(data["transmit_power"])
            if 0 <= new_power <= 7:
                monitor.radar.set_transmit_power(new_power)
                server.radar_config["transmit_power"] = new_power
                logger.info("[SERVER] Set transmit power: %d", new_power)

        session_logger = server.get_session_logger()
        if session_logger:
            session_logger.log_config_change(server.radar_config.copy(), source="user")

        debug_log_file = getattr(server, "debug_log_file", None)
        if getattr(server, "debug_mode", False) and debug_log_file:
            entry = {
                "timestamp": datetime.now().isoformat(),
                "type": "config_change",
                "config": server.radar_config.copy(),
            }
            debug_log_file.write(json.dumps(entry) + "\n")
            debug_log_file.flush()

        server.socketio.emit("radar_config", server.radar_config)
    except Exception as e:
        logger.warning("[SERVER] Error setting radar config: %s", e, exc_info=True)
        server.log_session_error(
            "Radar config update failed",
            component="server",
            context={"stage": "set_radar_config", "requested": data},
            exc=e,
        )
        server.socketio.emit("radar_config_error", {"error": str(e)})


def handle_shutdown() -> None:
    """Cleanly shut down the server and all hardware."""
    logger.info("[SERVER] Shutdown requested from UI (WebSocket)")
    server.socketio.emit("shutdown_ack", {"message": "Shutting down..."})
    threading.Thread(target=server._shutdown_process_after_delay, daemon=True).start()


def handle_toggle_camera() -> None:
    """Toggle camera on/off."""
    camera = getattr(server, "camera", None)
    if not camera:
        server.socketio.emit(
            "camera_status",
            {"enabled": False, "available": False, "error": "Camera not initialized"},
        )
        return

    server.camera_enabled = not getattr(server, "camera_enabled", False)
    server.socketio.emit(
        "camera_status",
        {
            "enabled": server.camera_enabled,
            "available": True,
            "streaming": getattr(server, "camera_streaming", False),
        },
    )
    logger.info("[CAMERA] Camera %s", "enabled" if server.camera_enabled else "disabled")


def handle_toggle_camera_stream() -> None:
    """Toggle camera streaming on/off."""
    camera = getattr(server, "camera", None)
    camera_enabled = getattr(server, "camera_enabled", False)
    if not camera or not camera_enabled:
        server.socketio.emit(
            "camera_status",
            {
                "enabled": camera_enabled,
                "available": camera is not None,
                "streaming": False,
                "error": "Camera not enabled",
            },
        )
        return

    server.camera_streaming = not getattr(server, "camera_streaming", False)
    server.socketio.emit(
        "camera_status",
        {
            "enabled": camera_enabled,
            "available": True,
            "streaming": server.camera_streaming,
        },
    )
    logger.info(
        "[CAMERA] Camera streaming %s",
        "started" if server.camera_streaming else "stopped",
    )


def handle_get_camera_status() -> None:
    """Get current camera status."""
    server.socketio.emit(
        "camera_status",
        {
            "enabled": getattr(server, "camera_enabled", False),
            "available": getattr(server, "camera", None) is not None,
            "streaming": getattr(server, "camera_streaming", False),
            "ball_detected": getattr(server, "ball_detected", False),
            "ball_confidence": round(getattr(server, "ball_detection_confidence", 0.0), 2),
        },
    )


def register_handlers(app: Flask, socketio: SocketIO) -> None:
    """Register all routes and event listeners on Flask and SocketIO instances."""
    app.add_url_rule("/", "index", index)
    app.add_url_rule("/display", "display", display, strict_slashes=False)
    app.add_url_rule("/<path:path>", "static_files", static_files)
    app.add_url_rule("/api/shutdown", "api_shutdown", api_shutdown, methods=["POST"])
    app.add_url_rule("/camera/stream", "camera_stream", camera_stream)

    socketio.on_event("connect", handle_connect)
    socketio.on_event("disconnect", handle_disconnect)
    socketio.on_event("get_trigger_status", handle_get_trigger_status)
    socketio.on_event("set_club", handle_set_club)
    socketio.on_event("set_player", handle_set_player)
    socketio.on_event("set_training_implement", handle_set_training_implement)
    socketio.on_event("clear_session", handle_clear_session)
    socketio.on_event("upload_cloud", handle_upload_cloud)
    socketio.on_event("get_session", handle_get_session)
    socketio.on_event("delete_shot", handle_delete_shot)
    socketio.on_event("simulate_shot", handle_simulate_shot)
    socketio.on_event("toggle_debug", handle_toggle_debug)
    socketio.on_event("get_debug_status", handle_get_debug_status)
    socketio.on_event("get_radar_config", handle_get_radar_config)
    socketio.on_event("set_radar_config", handle_set_radar_config)
    socketio.on_event("shutdown", handle_shutdown)
    socketio.on_event("toggle_camera", handle_toggle_camera)
    socketio.on_event("toggle_camera_stream", handle_toggle_camera_stream)
    socketio.on_event("get_camera_status", handle_get_camera_status)
