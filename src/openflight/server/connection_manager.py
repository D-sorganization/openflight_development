"""Connection and simulator lifecycle management for OpenFlight server."""

import logging
from pathlib import Path
from typing import Any

from openflight import server
from openflight.launch_monitor import Shot
from openflight.power import PowerMonitor, PowerStatus
from openflight.sim import (
    IncompleteShotError,
    PlayerUpdate,
    ShotAck,
    SimError,
    resolve_shot,
)

logger = logging.getLogger(__name__)


def _forward_shot_to_simulators(shot: Shot) -> None:
    """Resolve a shot once and fan it out to every connected simulator."""
    sim_connectors = getattr(server, "sim_connectors", [])
    if not any(c.is_connected() for c in sim_connectors):
        return
    try:
        resolved = resolve_shot(shot, server.sim_player_state)
    except IncompleteShotError as e:
        logger.warning("[sim] shot not sendable: %s", e)
        server.socketio.emit("sim_shot_dropped", {"reason": str(e)})
        return

    values = resolved.as_values()
    for connector in sim_connectors:
        if not connector.is_connected():
            continue
        try:
            connector.send_shot(resolved)
        except OSError as e:
            logger.warning("[sim] %s send failed: %s", connector.name, e)
            server.socketio.emit("sim_send_failed", {"target": connector.name, "reason": str(e)})
            continue
        sl = server.get_session_logger()
        if sl:
            sl.log_sim_send(
                target=connector.name,
                shot_number=resolved.shot_number,
                provenance=resolved.provenance,
                values=values,
            )
        server.socketio.emit(
            "sim_shot",
            {
                "target": connector.name,
                "shot_number": resolved.shot_number,
                "fields": connector.codec.fields_for_target(),
                "values": values,
                "provenance": resolved.provenance,
            },
        )
        if getattr(server, "debug_mode", False):
            measured = sum(1 for p in resolved.provenance.values() if p == "measured")
            estimated = len(resolved.provenance) - measured
            logger.info(
                "[sim] → %s shot #%d: ball=%.1f vla=%.1f hla=%.1f spin=%.0f axis=%.1f "
                "carry=%.1f (%dM/%dE)",
                connector.name,
                resolved.shot_number,
                resolved.ball_speed_mph,
                resolved.vla,
                resolved.hla,
                resolved.total_spin_rpm,
                resolved.spin_axis_deg,
                resolved.carry_yards,
                measured,
                estimated,
            )


def _sim_on_status(target: str, event: Any) -> None:
    """Relay a connector status change to the UI and session log."""
    state = event.state.value
    if state == "connected":
        logger.info("[sim] %s connected (%s:%s)", target, event.host, event.port)
    elif state == "reconnecting":
        logger.info(
            "[sim] %s reconnecting — attempt %s, retry in %.0fs",
            target,
            event.attempt,
            event.next_retry_in_s,
        )
    elif state == "error":
        logger.warning("[sim] %s error: %s", target, event.message)
    elif getattr(server, "debug_mode", False):
        logger.info("[sim] %s %s", target, state)
    server.socketio.emit(
        "sim_status",
        {
            "target": target,
            "state": event.state.value,
            "host": event.host,
            "port": event.port,
            "attempt": event.attempt,
            "next_retry_in_s": event.next_retry_in_s,
            "message": event.message,
        },
    )
    sl = server.get_session_logger()
    if sl:
        sl.log_sim_status(
            target=target,
            state=event.state.value,
            host=event.host,
            port=event.port,
            message=event.message,
            attempt=event.attempt,
            next_retry_in_s=event.next_retry_in_s,
        )


def _sim_on_inbound(target: str, event: Any) -> None:
    """Apply an inbound simulator event (player/club update, error, ack)."""
    if isinstance(event, PlayerUpdate):
        server.sim_player_state.apply(event)
        club_value = server.sim_player_state.club.value
        logger.info("[sim] ← %s player update: club=%s", target, club_value)
        server.socketio.emit(
            "sim_player",
            {
                "target": target,
                "handed": server.sim_player_state.handed,
                "club": club_value,
            },
        )
        sl = server.get_session_logger()
        if sl:
            sl.log_sim_player(target=target, handed=server.sim_player_state.handed, club=club_value)
        if getattr(server, "monitor", None) is not None:
            try:
                server.monitor.set_club(server.sim_player_state.club)
            except Exception:
                logger.exception("[sim] monitor.set_club failed")
        server.socketio.emit("club_changed", {"club": club_value})
    elif isinstance(event, SimError):
        logger.warning("[sim] ← %s error: %s", target, event.message)
        server.socketio.emit(
            "sim_status", {"target": target, "state": "error", "message": event.message}
        )
    elif isinstance(event, ShotAck):
        if not event.ok:
            logger.info(
                "[sim] ← %s rejected shot %s: %s",
                target,
                event.shot_number,
                event.message,
            )
        elif getattr(server, "debug_mode", False):
            logger.info("[sim] ← %s ack: shot %s ok", target, event.shot_number)


def _emit_sim_snapshot() -> None:
    """Emit the current status of every configured simulator connector."""
    sim_connectors = getattr(server, "sim_connectors", [])
    for connector in sim_connectors:
        server.socketio.emit(
            "sim_status",
            {
                "target": connector.name,
                "state": connector.state.value,
                "host": connector.host,
                "port": connector.port,
            },
        )


def _on_power_status(status: PowerStatus) -> None:
    """Publish one battery reading to connected UI clients."""
    server.socketio.emit("power_status", status.to_dict())


def _log_power_status(status: PowerStatus) -> None:
    """Write throttled battery telemetry into the active session log."""
    session_log = server.get_session_logger()
    if session_log:
        session_log.log_power_status(status.to_dict())


def start_power_monitor(provider: str) -> None:
    """Start optional battery monitoring without blocking server startup."""
    power_monitor = PowerMonitor(
        provider=provider,
        on_status=server._on_power_status,
        on_log=server._log_power_status,
    )
    server.power_monitor = power_monitor
    power_monitor.start()
    logger.info("[POWER] Battery monitoring enabled with provider=%s", provider)


def _fire_cloud_push(session_logger: Any) -> None:
    """Best-effort, non-blocking cloud push on session end."""
    try:
        from openflight.cloud.config import load_config
        from openflight.cloud.trigger import fire_push_async

        config = load_config()
        if config is None or not config.is_active():
            return
        log_dir = getattr(session_logger, "log_dir", None)
        if log_dir is not None:
            fire_push_async(config, log_dir=log_dir)
    except Exception as exc:
        logger.debug("Cloud push failed: %s", exc, exc_info=True)


def _run_cloud_push_for_ui() -> None:
    """Run a manual cloud push and report the result to connected UI clients."""
    server.socketio.emit("cloud_upload_status", {"state": "running", "message": "Uploading..."})
    try:
        from openflight.cloud import commands
        from openflight.cloud.client import CloudClient
        from openflight.cloud.config import CloudConfig, load_config

        config = load_config() or CloudConfig()
        session_logger = server.get_session_logger()
        log_dir = getattr(session_logger, "log_dir", None)
        if log_dir is None:
            log_dir = getattr(session_logger, "DEFAULT_LOG_DIR", None) if session_logger else None
        if log_dir is None:
            log_dir = Path.home() / "openflight_sessions"

        messages = []
        summary = commands.cmd_push(
            config,
            Path(log_dir),
            CloudClient(config.endpoint, token=config.device_token or None),
            out=messages.append,
        )

        if summary.get("needs_relink"):
            state = "error"
            message = "Cloud token rejected. Re-link this Pi."
        elif summary.get("skipped") == "inactive":
            state = "error"
            message = "Cloud uploader is not linked."
        elif summary.get("offline"):
            state = "error"
            message = "Cloud unreachable."
        elif summary.get("uploaded", 0) > 0:
            state = "complete"
            message = f"Uploaded {summary['uploaded']} session(s)."
        elif messages:
            state = "complete"
            message = messages[-1]
        else:
            state = "complete"
            message = "Nothing to upload."

        server.socketio.emit(
            "cloud_upload_status",
            {"state": state, "message": message, "summary": summary},
        )
    except Exception as exc:
        logger.warning("[SERVER] Manual cloud upload failed: %s", exc, exc_info=True)
        server.socketio.emit(
            "cloud_upload_status",
            {"state": "error", "message": str(exc)},
        )
