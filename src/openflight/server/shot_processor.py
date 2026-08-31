"""Shot detection, angle calculation, and processing pipeline for OpenFlight server."""

import json
import logging
import math
import time
from datetime import datetime
from typing import Any, Optional

from openflight import server
from openflight.club_data import ClubType
from openflight.kld7.radc import DEFAULT_RADC_HORIZONTAL_ANGLE_LIMIT_DEG
from openflight.launch_monitor import SPIN_CONFIDENCE_HIGH, Shot
from openflight.server.state import (
    _CLUB_LAUNCH_MODEL,
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
    SPIN_AXIS_MIN_CONFIDENCE,
    VERTICAL_SPREAD_FULL_CONFIDENCE_DEG,
    VERTICAL_SPREAD_ZERO_CONFIDENCE_DEG,
)
from openflight.speed_correction import correct_ball_speed
from openflight.spin_estimate import calculated_spin_rpm
from openflight.swing_speed import SwingSpeedEvent

logger = logging.getLogger(__name__)


def estimate_launch_angle(
    club: ClubType,
    ball_speed_mph: float,
    club_speed_mph: Optional[float] = None,
    spin_rpm: Optional[float] = None,
) -> tuple[float, float]:
    """Estimate launch angle from club type, ball speed, and optional smash/spin data.

    Uses TrackMan averages as baseline, then adjusts for:
    - Ball speed deviation from club average
    - Smash factor deviation from optimal (if club_speed provided)
    - Spin rate deviation from optimal (if spin_rpm provided)

    Returns (vertical_angle, confidence).
    """
    avg_launch, avg_speed, deg_per_mph = _CLUB_LAUNCH_MODEL.get(club, (18.0, 120, 0.25))

    speed_delta = ball_speed_mph - avg_speed
    adjustment = -speed_delta * deg_per_mph
    confidence = 0.2

    if club_speed_mph is not None and club_speed_mph > 0:
        smash_factor = ball_speed_mph / club_speed_mph
        optimal_smash = _OPTIMAL_SMASH.get(club, 1.35)
        smash_delta = smash_factor - optimal_smash

        if smash_delta < 0:
            smash_adj = max(_MAX_SMASH_ADJ_LOW, smash_delta * 100 * _SMASH_DEG_PER_HUNDREDTH_LOW)
        else:
            smash_adj = min(_MAX_SMASH_ADJ_HIGH, smash_delta * 100 * _SMASH_DEG_PER_HUNDREDTH_HIGH)
        adjustment += smash_adj
        confidence = 0.35

    if spin_rpm is not None and spin_rpm > 0:
        optimal_spin = server.get_optimal_spin_for_ball_speed(ball_speed_mph, club)
        spin_delta = spin_rpm - optimal_spin
        spin_adj = (spin_delta / 500.0) * _SPIN_DEG_PER_500RPM
        spin_adj = max(-_MAX_SPIN_ADJ, min(_MAX_SPIN_ADJ, spin_adj))
        adjustment += spin_adj

        if confidence >= 0.35:
            confidence = 0.5
        else:
            confidence = 0.35

    launch_angle = max(5.0, round(avg_launch + adjustment, 1))
    return (launch_angle, confidence)


def _radar_launch_base_delta_deg(club: ClubType) -> float:
    """Return a conservative club-family window for radar launch sanity checks."""
    if club in {ClubType.PW, ClubType.GW, ClubType.SW, ClubType.LW}:
        return 22.0
    if club in {ClubType.IRON_6, ClubType.IRON_7, ClubType.IRON_8, ClubType.IRON_9}:
        return 20.0
    return 18.0


def radar_launch_is_plausible(
    radar_angle_deg: Optional[float],
    club: ClubType,
    ball_speed_mph: float,
    club_speed_mph: Optional[float] = None,
    spin_rpm: Optional[float] = None,
) -> tuple[bool, dict]:
    """Check whether a radar launch angle is plausible for the shot profile."""
    if radar_angle_deg is None or club in {None, ClubType.UNKNOWN} or ball_speed_mph <= 0:
        return True, {
            "skipped": True,
            "expected_launch_deg": None,
            "allowed_delta_deg": None,
            "delta_deg": None,
        }

    expected_launch_deg, estimate_conf = server.estimate_launch_angle(
        club,
        ball_speed_mph,
        club_speed_mph=club_speed_mph,
        spin_rpm=spin_rpm,
    )
    allowed_delta_deg = (
        _radar_launch_base_delta_deg(club)
        + (1.0 - estimate_conf) * _RADAR_SANITY_LOW_CONF_BONUS_DEG
    )
    delta_deg = abs(radar_angle_deg - expected_launch_deg)
    if radar_angle_deg <= expected_launch_deg:
        plausible = 0.0 <= radar_angle_deg <= 45.0
    else:
        plausible = delta_deg <= allowed_delta_deg

    return plausible, {
        "skipped": False,
        "expected_launch_deg": round(expected_launch_deg, 1),
        "allowed_delta_deg": round(allowed_delta_deg, 1),
        "delta_deg": round(delta_deg, 1),
    }


def _vertical_soft_launch_lane_deg(club: ClubType) -> tuple[float, float]:
    """Return broad club-family lanes for low-confidence vertical radar candidates."""
    if club == ClubType.DRIVER:
        return (4.0, 22.0)
    if club in {ClubType.WOOD_3, ClubType.WOOD_5, ClubType.WOOD_7}:
        return (5.0, 24.0)
    if club in {
        ClubType.HYBRID_3,
        ClubType.HYBRID_5,
        ClubType.HYBRID_7,
        ClubType.HYBRID_9,
    }:
        return (6.0, 26.0)
    if club in {ClubType.IRON_2, ClubType.IRON_3, ClubType.IRON_4, ClubType.IRON_5}:
        return (5.0, 25.0)
    if club in {ClubType.IRON_6, ClubType.IRON_7, ClubType.IRON_8, ClubType.IRON_9}:
        return (7.0, 28.0)
    if club in {ClubType.PW, ClubType.GW, ClubType.SW, ClubType.LW}:
        return (10.0, 45.0)
    return (5.0, 35.0)


def _select_vertical_radar_launch(kld7_angle: Any, shot: Shot) -> tuple[bool, dict]:
    """Decide whether a vertical K-LD7 candidate should set the shot launch angle."""
    details = {
        "accepted": False,
        "selection_reason": "no_candidate",
        "acceptance_path": None,
        "strict_min_confidence": _MIN_VERTICAL_RADAR_CONFIDENCE,
        "soft_min_confidence": _MIN_VERTICAL_SOFT_RADAR_CONFIDENCE,
        "low_confidence_min_confidence": _MIN_VERTICAL_LOW_CONFIDENCE_RADAR_CONFIDENCE,
        "soft_allowed_delta_deg": _VERTICAL_SOFT_ESTIMATE_DELTA_DEG,
        "soft_max_frame_count": _VERTICAL_SOFT_MAX_FRAME_COUNT,
    }
    if not kld7_angle or kld7_angle.vertical_deg is None:
        return False, details

    if getattr(server, "_VERTICAL_RADAR_GATE_BYPASS", False):
        details["accepted"] = True
        details["selection_reason"] = "gate_bypassed"
        details["acceptance_path"] = "bypass"
        return True, details

    radar_angle_deg = kld7_angle.vertical_deg
    plausible, guard_details = server.radar_launch_is_plausible(
        radar_angle_deg=radar_angle_deg,
        club=shot.club,
        ball_speed_mph=shot.ball_speed_mph,
        club_speed_mph=shot.club_speed_mph,
        spin_rpm=shot.spin_rpm,
    )
    details.update(guard_details)
    if not plausible:
        details["selection_reason"] = "implausible_launch"
        return False, details

    if kld7_angle.confidence >= _MIN_VERTICAL_RADAR_CONFIDENCE:
        details["accepted"] = True
        details["selection_reason"] = "strict_accept"
        details["acceptance_path"] = "strict"
        return True, details

    if kld7_angle.confidence < _MIN_VERTICAL_LOW_CONFIDENCE_RADAR_CONFIDENCE:
        details["selection_reason"] = "low_confidence"
        return False, details

    if guard_details.get("skipped"):
        details["selection_reason"] = "soft_guard_unavailable"
        return False, details

    lane_min, lane_max = _vertical_soft_launch_lane_deg(shot.club)
    details["soft_lane_min_deg"] = lane_min
    details["soft_lane_max_deg"] = lane_max
    if radar_angle_deg < lane_min or radar_angle_deg > lane_max:
        details["accepted"] = True
        details["selection_reason"] = "marginal_accept:outside_soft_lane"
        details["acceptance_path"] = "marginal"
        return True, details

    delta_deg = guard_details.get("delta_deg")
    if delta_deg is None or delta_deg > _VERTICAL_SOFT_ESTIMATE_DELTA_DEG:
        details["accepted"] = True
        details["selection_reason"] = "marginal_accept:estimator_delta_too_large"
        details["acceptance_path"] = "marginal"
        return True, details

    if kld7_angle.num_frames <= 0:
        details["selection_reason"] = "no_candidate_frames"
        return False, details

    if (
        kld7_angle.num_frames > _VERTICAL_SOFT_MAX_FRAME_COUNT
        and delta_deg > _VERTICAL_SOFT_TIGHT_DELTA_FOR_LONG_FRAME_DEG
    ):
        details["accepted"] = True
        details["selection_reason"] = "marginal_accept:suspicious_frame_span"
        details["acceptance_path"] = "marginal"
        return True, details

    details["accepted"] = True
    if kld7_angle.confidence >= _MIN_VERTICAL_SOFT_RADAR_CONFIDENCE:
        details["selection_reason"] = "soft_accept"
        details["acceptance_path"] = "soft"
    else:
        details["selection_reason"] = "low_confidence_accept"
        details["acceptance_path"] = "low_confidence"
    return True, details


def _select_horizontal_radar_launch(kld7_angle: Any, horizontal_limit: float) -> tuple[bool, dict]:
    """Decide whether a horizontal K-LD7 candidate should set the shot angle."""
    soft_limit = min(_HORIZONTAL_SOFT_ANGLE_LIMIT_DEG, max(horizontal_limit, 0.0))
    details = {
        "accepted": False,
        "selection_reason": "no_candidate",
        "acceptance_path": None,
        "horizontal_limit_deg": horizontal_limit,
        "strict_min_confidence": _MIN_HORIZONTAL_RADAR_CONFIDENCE,
        "soft_min_confidence": _MIN_HORIZONTAL_SOFT_RADAR_CONFIDENCE,
        "soft_angle_limit_deg": soft_limit,
        "soft_max_frame_count": _HORIZONTAL_SOFT_MAX_FRAME_COUNT,
        "near_limit_min_confidence": _HORIZONTAL_NEAR_LIMIT_MIN_CONFIDENCE,
        "near_limit_max_frame_count": _HORIZONTAL_NEAR_LIMIT_MAX_FRAMES,
    }
    if not kld7_angle or kld7_angle.horizontal_deg is None:
        return False, details

    abs_angle = abs(kld7_angle.horizontal_deg)
    if abs_angle > horizontal_limit:
        details["selection_reason"] = "outside_horizontal_limit"
        return False, details

    near_limit_angle = horizontal_limit * _HORIZONTAL_NEAR_LIMIT_FRACTION
    if (
        abs_angle >= near_limit_angle
        and kld7_angle.num_frames <= _HORIZONTAL_NEAR_LIMIT_MAX_FRAMES
        and kld7_angle.confidence < _HORIZONTAL_NEAR_LIMIT_MIN_CONFIDENCE
    ):
        details["selection_reason"] = "weak_near_limit"
        details["near_limit_angle_deg"] = round(near_limit_angle, 1)
        return False, details

    if kld7_angle.confidence >= _MIN_HORIZONTAL_RADAR_CONFIDENCE:
        details["accepted"] = True
        details["selection_reason"] = "strict_accept"
        details["acceptance_path"] = "strict"
        return True, details

    if kld7_angle.confidence < _MIN_HORIZONTAL_SOFT_RADAR_CONFIDENCE:
        details["selection_reason"] = "low_confidence"
        return False, details

    if abs_angle > soft_limit:
        details["selection_reason"] = "outside_soft_lane"
        return False, details

    if kld7_angle.num_frames <= 0:
        details["selection_reason"] = "no_candidate_frames"
        return False, details

    if kld7_angle.num_frames > _HORIZONTAL_SOFT_MAX_FRAME_COUNT:
        details["selection_reason"] = "suspicious_frame_span"
        return False, details

    details["accepted"] = True
    details["selection_reason"] = "soft_accept"
    details["acceptance_path"] = "soft"
    return True, details


def _ensure_user_facing_launch_angles(shot: Shot) -> None:
    """Guarantee emitted shots have launch angles without overwriting measurements."""
    estimated: tuple[float, float] | None = None

    if shot.launch_angle_vertical is None:
        estimated = server.estimate_launch_angle(
            shot.club,
            shot.ball_speed_mph,
            club_speed_mph=shot.club_speed_mph,
            spin_rpm=shot.spin_rpm,
        )
        shot.launch_angle_vertical = estimated[0]
        shot.launch_angle_confidence = estimated[1]
        shot.launch_angle_vertical_confidence = estimated[1]
        shot.launch_angle_vertical_source = "estimated"
        shot.angle_source = "estimated"
        logger.info(
            "[SERVER] Angle source: estimated (%.1f°, conf=%.0f%%)",
            estimated[0],
            estimated[1] * 100,
        )

    if shot.launch_angle_horizontal is None:
        shot.launch_angle_horizontal = 0.0
        if shot.launch_angle_horizontal_confidence is None:
            if estimated is None:
                estimated = server.estimate_launch_angle(
                    shot.club,
                    shot.ball_speed_mph,
                    club_speed_mph=shot.club_speed_mph,
                    spin_rpm=shot.spin_rpm,
                )
            shot.launch_angle_horizontal_confidence = estimated[1]
        shot.launch_angle_horizontal_source = "estimated"
        if shot.angle_source is None:
            shot.angle_source = "estimated"
        logger.info("[SERVER] Horizontal angle source: neutral estimate (0.0°)")


def _maybe_wait_for_kld7_post_shot_frames(shot_timestamp: float) -> None:
    """Let the K-LD7 stream collect post-impact RADC frames for extraction."""
    target_time = shot_timestamp + _KLD7_POST_SHOT_CAPTURE_DELAY_S
    delay_s = target_time - server.time.time()
    if delay_s <= 0:
        return
    logger.info(
        "[SERVER] Waiting %.0fms for post-impact K-LD7 RADC frames",
        delay_s * 1000.0,
    )
    server.time.sleep(delay_s)


def _warn_if_kld7_buffer_underfilled(orientation: str, frame_count: int) -> None:
    """Log a WARNING when the K-LD7 ring-buffer snapshot is underfilled."""
    expected = int(_KLD7_FRAME_HZ * _KLD7_BUFFER_SECONDS)
    if expected <= 0 or frame_count <= 0:
        return
    if frame_count < expected * _KLD7_BUFFER_UNDERFILL_FRAC:
        logger.warning(
            "[SERVER] K-LD7 %s buffer underfilled: %d/%d frames (%.0f%%) — "
            "stream rate dropped, check USB cabling and contention.",
            orientation,
            frame_count,
            expected,
            100.0 * frame_count / expected,
        )


def _warn_if_kld7_raw_payload_missing(
    orientation: str,
    buffer_frames: list,
    *,
    raw_payload_expected: bool,
) -> None:
    """Log a WARNING when experimental replay logging lacks raw RADC bytes."""
    if not raw_payload_expected or not buffer_frames:
        return

    radc_frames = sum(
        1 for frame in buffer_frames if frame.get("has_radc") or frame.get("radc_b64")
    )
    if radc_frames == 0:
        logger.warning(
            "[SERVER] K-LD7 %s raw RADC replay payload missing: buffer has no RADC frames. "
            "TrackMan replay will fail; verify RADC streaming.",
            orientation,
        )
        return

    payload_frames = sum(1 for frame in buffer_frames if frame.get("radc_b64"))
    if payload_frames == radc_frames:
        invalid_payload_frames = sum(
            1
            for frame in buffer_frames
            if frame.get("radc_b64") and frame.get("radc_payload_valid") is False
        )
        if invalid_payload_frames:
            logger.warning(
                "[SERVER] K-LD7 %s raw RADC replay payload invalid: %d/%d payloads "
                "have the wrong byte length. TrackMan replay will fail for those frames.",
                orientation,
                invalid_payload_frames,
                payload_frames,
            )
        return

    if payload_frames == 0:
        logger.warning(
            "[SERVER] K-LD7 %s raw RADC replay payload missing: 0/%d RADC frames have radc_b64. "
            "TrackMan replay will fail; verify RADC streaming and raw payload logging.",
            orientation,
            radc_frames,
        )
        return

    logger.warning(
        "[SERVER] K-LD7 %s raw RADC replay payload incomplete: %d/%d RADC frames have radc_b64. "
        "TrackMan replay may fail for some shots.",
        orientation,
        payload_frames,
        radc_frames,
    )


def _warn_if_kld7_snapshot_lacks_post_shot_frames(
    orientation: str,
    buffer_frames: list,
    shot_timestamp: float,
    *,
    raw_payload_expected: bool,
) -> None:
    """Warn when a TrackMan replay snapshot cannot contain post-impact ball frames."""
    if not raw_payload_expected or not buffer_frames:
        return
    post_shot_frames = [
        frame
        for frame in buffer_frames
        if frame.get("timestamp") is not None and float(frame["timestamp"]) > shot_timestamp
    ]
    if post_shot_frames:
        return
    logger.warning(
        "[SERVER] K-LD7 %s snapshot has no frames after shot timestamp %.3f; "
        "angle replay may be using pre-impact clutter.",
        orientation,
        shot_timestamp,
    )


def _kld7_angle_log_payload(
    angle: Any,
    axis_field: str,
    selection_details: Optional[dict] = None,
) -> Optional[dict]:
    """Build the compact K-LD7 angle payload used in session logs."""
    if angle is None:
        return None

    payload = {
        axis_field: getattr(angle, axis_field),
        "confidence": angle.confidence,
        "detection_class": angle.detection_class,
        "magnitude": angle.magnitude,
        "num_frames": angle.num_frames,
        "frames_examined": angle.frames_examined,
        "frames_available": angle.frames_available,
        "frames_ignored_stale": angle.frames_ignored_stale,
    }
    radc_selection = getattr(angle, "radc_selection", None)
    if radc_selection:
        payload["radc_selection"] = radc_selection
    if selection_details:
        payload.update(selection_details)
    return payload


def _experimental_kld7_raw_radc_logging_enabled() -> bool:
    """Return whether K-LD7 buffers should include raw RADC payloads."""
    return bool(
        getattr(server, "experimental_kld7_raw_radc_logging", False)
        or getattr(server, "experimental_kld7_radc_tuning", False)
    )


def _process_kld7_orientation(
    tracker: Any,
    orientation: str,
    shot: Shot,
    shot_ts: float,
    session_log: Any = None,
) -> None:
    """Process a single K-LD7 tracker (vertical or horizontal) for a detected shot."""
    if not tracker:
        return

    raw_payload_expected = server._experimental_kld7_raw_radc_logging_enabled()
    if raw_payload_expected:
        raw_buffer = tracker.snapshot_buffer(include_radc_payload=True)
    else:
        raw_buffer = tracker.snapshot_buffer()

    server._warn_if_kld7_buffer_underfilled(orientation, len(raw_buffer))
    server._warn_if_kld7_raw_payload_missing(
        orientation,
        raw_buffer,
        raw_payload_expected=raw_payload_expected,
    )
    server._warn_if_kld7_snapshot_lacks_post_shot_frames(
        orientation,
        raw_buffer,
        shot_ts,
        raw_payload_expected=raw_payload_expected,
    )

    if orientation == "vertical":
        kld7_angle = tracker.get_angle_for_shot(
            shot_timestamp=shot_ts,
            ball_speed_mph=shot.ball_speed_mph,
            impact_timestamp=shot.impact_timestamp_kld7,
            club=shot.club,
        )
        vertical_selection_details = None
        if kld7_angle and kld7_angle.vertical_deg is not None:
            accepted, vertical_selection_details = server._select_vertical_radar_launch(
                kld7_angle, shot
            )
            selection_reason = vertical_selection_details["selection_reason"]
            if not accepted:
                logger.warning(
                    "[SERVER] Vertical angle %.1f° rejected: %s "
                    "(expected=%s°, delta=%s°, conf=%.0f%%)",
                    kld7_angle.vertical_deg,
                    selection_reason,
                    vertical_selection_details.get("expected_launch_deg"),
                    vertical_selection_details.get("delta_deg"),
                    kld7_angle.confidence * 100,
                )
            else:
                accepted_conf = kld7_angle.confidence
                if vertical_selection_details.get("acceptance_path") == "marginal":
                    accepted_conf = min(accepted_conf, _VERTICAL_MARGINAL_DISPLAY_CONFIDENCE)
                shot.launch_angle_vertical = kld7_angle.vertical_deg
                shot.launch_angle_confidence = accepted_conf
                shot.launch_angle_vertical_confidence = accepted_conf
                shot.launch_angle_vertical_source = "radar"
                shot.angle_source = "radar"
                logger.info(
                    "[SERVER] Vertical angle: %.1f° (conf=%.0f%%, %d frames, %s)",
                    kld7_angle.vertical_deg,
                    kld7_angle.confidence * 100,
                    kld7_angle.num_frames,
                    selection_reason,
                )

        club_angle_v = None
        if shot.club_speed_mph:
            club_angle_v = tracker.get_club_angle(
                club_speed_mph=shot.club_speed_mph,
                shot_timestamp=shot_ts,
            )
            if club_angle_v and club_angle_v.vertical_deg is not None:
                candidate_aoa = -club_angle_v.vertical_deg
                if -15.0 <= candidate_aoa <= 8.0:
                    shot.club_angle_deg = candidate_aoa
                    logger.info(
                        "[SERVER] Club AoA: %.1f° (conf=%.0f%%)",
                        shot.club_angle_deg,
                        club_angle_v.confidence * 100,
                    )
                else:
                    logger.warning(
                        "[SERVER] Club AoA rejected: %.1f° outside plausible range",
                        candidate_aoa,
                    )

        if session_log and raw_buffer:
            session_log.log_kld7_buffer(
                shot_number=session_log.stats.get("shots_detected", 0) + 1,
                shot_timestamp=shot_ts,
                orientation="vertical",
                buffer_frames=raw_buffer,
                ball_angle=server._kld7_angle_log_payload(
                    kld7_angle,
                    "vertical_deg",
                    selection_details=vertical_selection_details,
                ),
                club_angle=server._kld7_angle_log_payload(club_angle_v, "vertical_deg"),
                raw_payload_expected=raw_payload_expected,
            )

        tracker.reset()

    elif orientation == "horizontal":
        kld7_angle_h = tracker.get_angle_for_shot(
            shot_timestamp=shot_ts,
            ball_speed_mph=shot.ball_speed_mph,
        )
        horizontal_selection_details = None
        if kld7_angle_h and kld7_angle_h.horizontal_deg is not None:
            active_tuning = getattr(server, "active_kld7_radc_tuning", {})
            horizontal_limit = (
                float(
                    active_tuning.get(
                        "radc_horizontal_angle_limit_deg",
                        DEFAULT_RADC_HORIZONTAL_ANGLE_LIMIT_DEG,
                    )
                )
                if getattr(server, "experimental_kld7_radc_tuning", False)
                else DEFAULT_RADC_HORIZONTAL_ANGLE_LIMIT_DEG
            )
            accepted_h, horizontal_selection_details = server._select_horizontal_radar_launch(
                kld7_angle_h, horizontal_limit
            )
            selection_reason_h = horizontal_selection_details["selection_reason"]
            if accepted_h:
                shot.launch_angle_horizontal = kld7_angle_h.horizontal_deg
                shot.launch_angle_horizontal_confidence = kld7_angle_h.confidence
                shot.launch_angle_horizontal_source = "radar"
                if shot.angle_source is None:
                    shot.angle_source = "radar"
                if shot.launch_angle_confidence is None:
                    shot.launch_angle_confidence = kld7_angle_h.confidence
                logger.info(
                    "[SERVER] Horizontal angle: %.1f° (conf=%.0f%%, %d frames, %s)",
                    kld7_angle_h.horizontal_deg,
                    kld7_angle_h.confidence * 100,
                    kld7_angle_h.num_frames,
                    selection_reason_h,
                )
            else:
                logger.warning(
                    "[SERVER] Horizontal angle %.1f° rejected: %s (limit=±%.0f°, conf=%.0f%%)",
                    kld7_angle_h.horizontal_deg,
                    selection_reason_h,
                    horizontal_limit,
                    kld7_angle_h.confidence * 100,
                )

        club_angle_h = None
        if shot.club_speed_mph:
            club_angle_h = tracker.get_club_angle(
                club_speed_mph=shot.club_speed_mph,
                shot_timestamp=shot_ts,
            )
            if club_angle_h and club_angle_h.horizontal_deg is not None:
                shot.club_path_deg = club_angle_h.horizontal_deg
                logger.info(
                    "[SERVER] Club path: %.1f° (conf=%.0f%%)",
                    club_angle_h.horizontal_deg,
                    club_angle_h.confidence * 100,
                )

        if session_log and raw_buffer:
            session_log.log_kld7_buffer(
                shot_number=session_log.stats.get("shots_detected", 0) + 1,
                shot_timestamp=shot_ts,
                orientation="horizontal",
                buffer_frames=raw_buffer,
                ball_angle=server._kld7_angle_log_payload(
                    kld7_angle_h,
                    "horizontal_deg",
                    selection_details=horizontal_selection_details,
                ),
                club_angle=server._kld7_angle_log_payload(club_angle_h, "horizontal_deg"),
                raw_payload_expected=raw_payload_expected,
            )

        tracker.reset()


def _apply_calculated_spin(shot: Shot) -> bool:
    """Replace radar-measured spin with the kinematic estimate."""
    if shot.launch_angle_vertical is None:
        return False
    if shot.launch_angle_vertical_source not in ("radar", "camera"):
        return False
    spin_calc = calculated_spin_rpm(shot.ball_speed_mph, shot.launch_angle_vertical)
    if spin_calc is None:
        return False
    shot.spin_rpm_measured = shot.spin_rpm
    shot.spin_rpm = spin_calc
    shot.spin_confidence = SPIN_CONFIDENCE_HIGH
    shot.spin_source = "calculated"
    shot.spin_rejection_reason = None
    logger.info(
        "[SERVER] Calculated spin: %.0f rpm (v=%.1f mph, LA=%.1f deg, measured was %s)",
        spin_calc,
        shot.ball_speed_mph,
        shot.launch_angle_vertical,
        "%.0f rpm" % shot.spin_rpm_measured if shot.spin_rpm_measured else "none",
    )
    return True


def vertical_confidence(measurement: Any) -> float:
    """Vertical launch confidence from channel agreement and corroboration."""
    single_channel = getattr(measurement, "single_channel", False)
    spread = getattr(measurement, "component_std_deg", None)
    if single_channel or spread is None:
        score = 0.5
    else:
        span = VERTICAL_SPREAD_ZERO_CONFIDENCE_DEG - VERTICAL_SPREAD_FULL_CONFIDENCE_DEG
        score = 1.0 - (float(spread) - VERTICAL_SPREAD_FULL_CONFIDENCE_DEG) / span
        score = min(1.0, max(0.0, score))
    if single_channel:
        from openflight.iwr6843.lcmf import SINGLE_CHANNEL_CONFIDENCE_FACTOR

        score *= SINGLE_CHANNEL_CONFIDENCE_FACTOR
    span = ANGLE_CONFIDENCE_CEILING - ANGLE_CONFIDENCE_FLOOR
    return round(ANGLE_CONFIDENCE_FLOOR + span * score, 3)


def horizontal_confidence_from(coherence: Optional[float]) -> float:
    """Horizontal launch confidence from HLCMF-v0 coherence."""
    if coherence is None:
        return 0.0
    return round(min(ANGLE_CONFIDENCE_CEILING, max(0.0, float(coherence))), 3)


def _snapshot_inclinometer_for_shot(shot: Shot) -> None:
    """Attach the stable pre-impact enclosure orientation used by this shot."""
    inclinometer_service = getattr(server, "inclinometer_service", None)
    if inclinometer_service is None or shot.mode == "mock":
        return

    impact_timestamp = shot.impact_timestamp or time.time()
    selection = inclinometer_service.snapshot_for_impact(impact_timestamp)
    data = selection.to_dict()
    inclinometer_runtime_config = getattr(server, "inclinometer_runtime_config", {})
    data["zero_offset_deg"] = inclinometer_runtime_config.get("zero_offset_deg", 0.0)
    snapshot = selection.snapshot
    iwr6843_runtime = getattr(server, "iwr6843_runtime", None)
    if snapshot is not None and iwr6843_runtime is not None:
        configured_tilt = math.degrees(iwr6843_runtime.calibration.tilt_rad)
        effective_tilt = configured_tilt + snapshot.calibrated_pitch_deg
        data.update(
            {
                "applied": True,
                "configured_iwr_tilt_deg": round(configured_tilt, 3),
                "effective_iwr_tilt_deg": round(effective_tilt, 3),
            }
        )
        logger.info(
            "[SERVER] Inclinometer pitch: raw %+.2fdeg, calibrated %+.2fdeg, "
            "IWR tilt %.2fdeg (age %.0fms)",
            snapshot.raw_pitch_deg,
            snapshot.calibrated_pitch_deg,
            effective_tilt,
            (selection.age_s or 0.0) * 1000.0,
        )
    else:
        data["applied"] = False
        logger.warning("[SERVER] Inclinometer correction not applied: %s", selection.status)
    shot.inclinometer = data


def _process_iwr6843_angle(shot: Shot) -> Optional[float]:
    """Apply a correlated LCMF-v1 result without risking the OPS shot."""
    iwr6843_runtime = getattr(server, "iwr6843_runtime", None)
    if iwr6843_runtime is None or shot.mode == "mock":
        return None

    started = time.time()
    try:
        shot_result = iwr6843_runtime.process_shot(
            impact_timestamp=shot.impact_timestamp,
            ball_speed_mph=shot.ball_speed_mph,
            club=shot.club.value,
            club_speed_mph=shot.club_speed_mph,
            tilt_deg=(
                shot.inclinometer.get("effective_iwr_tilt_deg")
                if shot.inclinometer and shot.inclinometer.get("applied")
                else None
            ),
        )
        capture = shot_result.capture
        measurement = shot_result.measurement
        club_path = getattr(shot_result, "club_path", None)
        session_log = server.get_session_logger()
        if session_log:
            session_log.log_iwr6843_capture(
                shot_number=session_log.stats.get("shots_detected", 0) + 1,
                shot_timestamp=shot.impact_timestamp,
                trigger_timestamp=(capture.trigger_timestamp if capture is not None else None),
                capture_path=(str(capture.path) if capture and capture.path else None),
                capture_bytes=(len(capture.raw) if capture and capture.raw else 0),
                dump_duration_s=(capture.dump_duration_s if capture is not None else None),
                capture_error=(
                    capture.error
                    if capture is not None
                    else "no capture matched the OPS impact timestamp"
                ),
                ball_speed_mph=shot.ball_speed_mph,
                measurement=(measurement.to_dict() if measurement is not None else None),
                club_path=(club_path.to_dict() if club_path is not None else None),
                temperature_report=(
                    getattr(capture, "temperature_report", None) if capture is not None else None
                ),
            )

        if capture is None:
            logger.warning("[SERVER] IWR6843 capture timed out; preserving OPS shot")
            server._emit_iwr6843_trigger_status(
                shot,
                state="error",
                reason="no capture matched the OPS impact timestamp",
            )
        elif not capture.valid:
            logger.warning(
                "[SERVER] IWR6843 capture #%d failed: %s; preserving OPS shot",
                capture.sequence,
                capture.error,
            )
            server._emit_iwr6843_trigger_status(
                shot,
                state="error",
                reason=capture.error or "invalid IWR6843 capture",
            )
        elif measurement is None:
            logger.warning("[SERVER] IWR6843 capture had no LCMF measurement")
            server._emit_iwr6843_trigger_status(
                shot,
                state="rejected",
                reason="no LCMF measurement",
            )
        elif measurement.accepted:
            shot.launch_angle_vertical = measurement.angle_deg
            shot.launch_angle_vertical_source = "radar"
            derived_v_conf = server.vertical_confidence(measurement)
            shot.launch_angle_vertical_confidence = derived_v_conf
            shot.launch_angle_confidence = derived_v_conf
            shot.angle_source = "radar"
            horizontal_deg = getattr(measurement, "horizontal_deg", None)
            horizontal_confidence = getattr(measurement, "horizontal_confidence", None)
            horizontal_status = getattr(measurement, "horizontal_status", None)
            if horizontal_deg is not None:
                shot.launch_angle_horizontal = horizontal_deg
                shot.launch_angle_horizontal_confidence = server.horizontal_confidence_from(
                    horizontal_confidence
                )
                shot.launch_angle_horizontal_source = "radar"
                logger.info(
                    "[SERVER] IWR6843 TX2 horizontal proxy: %.2f° (coherence %.0f%%, status=%s)",
                    horizontal_deg,
                    (horizontal_confidence or 0.0) * 100,
                    horizontal_status,
                )
            logger.info(
                "[SERVER] IWR6843 LCMF-v1 launch: %.2f° "
                "(%d snapshots/%d frames, component std %.2f°)",
                measurement.angle_deg,
                measurement.n_snapshots,
                measurement.n_frames,
                measurement.component_std_deg,
            )
            server._emit_iwr6843_trigger_status(
                shot,
                state="accepted",
                reason="accepted",
                angle_deg=measurement.angle_deg,
            )
        else:
            logger.warning(
                "[SERVER] IWR6843 LCMF-v1 withheld angle: %s",
                measurement.status,
            )
            server._emit_iwr6843_trigger_status(
                shot,
                state="rejected",
                reason=measurement.status,
            )

        if club_path is not None and club_path.accepted:
            shot.club_path_deg = round(club_path.path_deg, 1)
            logger.info(
                "[SERVER] IWR6843 club path: %.2f° (confidence %.2f, %d frames)",
                club_path.path_deg,
                club_path.confidence or 0.0,
                club_path.n_frames,
            )
    except Exception as error:
        logger.warning("[SERVER] IWR6843 processing error: %s", error, exc_info=True)
        server.log_session_error(
            "IWR6843 shot processing failed",
            component="server",
            context={
                "stage": "iwr6843",
                "ball_speed_mph": shot.ball_speed_mph,
                "club": shot.club.value,
            },
            exc=error,
        )
        server._emit_iwr6843_trigger_status(shot, state="error", reason=str(error))
    return (time.time() - started) * 1000.0


def _emit_iwr6843_trigger_status(
    shot: Shot,
    *,
    state: str,
    reason: str,
    angle_deg: Optional[float] = None,
) -> None:
    """Enrich the existing OPS trigger row with the correlated TI result."""
    iwr_status: dict[str, Any] = {"state": state, "reason": reason}
    if angle_deg is not None:
        iwr_status["angle_deg"] = round(angle_deg, 2)
    server.socketio.emit(
        "trigger_diagnostic_update",
        {
            "timestamp": shot.timestamp.isoformat(),
            "iwr6843": iwr_status,
        },
    )


def shot_to_dict(shot: Shot) -> dict:
    """Convert Shot to JSON-serializable dict."""
    return {
        "ball_speed_mph": round(shot.ball_speed_mph, 1),
        "ball_speed_raw_mph": (
            round(shot.ball_speed_raw_mph, 1) if shot.ball_speed_raw_mph else None
        ),
        "club_speed_mph": (round(shot.club_speed_mph, 1) if shot.club_speed_mph else None),
        "smash_factor": round(shot.smash_factor, 2) if shot.smash_factor else None,
        "estimated_carry_yards": round(shot.estimated_carry_yards),
        "carry_range": [
            round(shot.estimated_carry_range[0]),
            round(shot.estimated_carry_range[1]),
        ],
        "club": shot.club.value,
        "player_name": shot.player_name,
        "timestamp": shot.timestamp.isoformat(),
        "peak_magnitude": shot.peak_magnitude,
        "launch_angle_vertical": shot.launch_angle_vertical,
        "launch_angle_horizontal": shot.launch_angle_horizontal,
        "launch_angle_confidence": shot.launch_angle_confidence,
        "launch_angle_vertical_confidence": shot.launch_angle_vertical_confidence,
        "launch_angle_horizontal_confidence": shot.launch_angle_horizontal_confidence,
        "launch_angle_vertical_source": shot.launch_angle_vertical_source,
        "launch_angle_horizontal_source": shot.launch_angle_horizontal_source,
        "angle_source": shot.angle_source,
        "club_angle_deg": shot.club_angle_deg,
        "club_path_deg": shot.club_path_deg,
        "spin_axis_deg": shot.spin_axis_deg,
        "inclinometer": shot.inclinometer,
        "spin_rpm": round(shot.spin_rpm) if shot.spin_rpm else None,
        "spin_rpm_measured": (round(shot.spin_rpm_measured) if shot.spin_rpm_measured else None),
        "spin_source": shot.spin_source,
        "spin_method": shot.spin_method,
        "spin_confidence": (round(shot.spin_confidence, 2) if shot.spin_confidence else None),
        "spin_quality": shot.spin_quality,
        "spin_multipath_fade_hz": (
            round(shot.spin_multipath_fade_hz, 2)
            if shot.spin_multipath_fade_hz is not None
            else None
        ),
        "spin_snr": round(shot.spin_snr, 2) if shot.spin_snr is not None else None,
        "spin_modulation_depth": (
            round(shot.spin_modulation_depth, 4) if shot.spin_modulation_depth is not None else None
        ),
        "spin_peak_freq_hz": (
            round(shot.spin_peak_freq_hz, 2) if shot.spin_peak_freq_hz is not None else None
        ),
        "spin_candidate_rpm": (
            round(shot.spin_peak_freq_hz * 60) if shot.spin_peak_freq_hz is not None else None
        ),
        "spin_seam_cycles": (
            round(shot.spin_seam_cycles, 2) if shot.spin_seam_cycles is not None else None
        ),
        "spin_at_lower_rail": shot.spin_at_lower_rail,
        "spin_at_upper_rail": shot.spin_at_upper_rail,
        "spin_candidates": shot.spin_candidates,
        "spin_phase_method": shot.spin_phase_method,
        "spin_phase_rpm": round(shot.spin_phase_rpm) if shot.spin_phase_rpm else None,
        "spin_phase_snr": (
            round(shot.spin_phase_snr, 2) if shot.spin_phase_snr is not None else None
        ),
        "spin_phase_agreement_pct": (
            round(shot.spin_phase_agreement_pct, 1)
            if shot.spin_phase_agreement_pct is not None
            else None
        ),
        "spin_phase_confirmed": shot.spin_phase_confirmed,
        "spin_rejection_reason": shot.spin_rejection_reason,
        "carry_spin_adjusted": (
            round(shot.carry_spin_adjusted) if shot.carry_spin_adjusted else None
        ),
    }


def swing_speed_to_dict(event: SwingSpeedEvent) -> dict:
    """Convert a swing speed training event to a UI payload."""
    return {
        "peak_speed_mph": round(event.peak_speed_mph, 1),
        "timestamp": event.timestamp.isoformat(),
        "duration_ms": round(event.duration_ms),
        "reading_count": event.reading_count,
        "trigger_speed_mph": round(event.trigger_speed_mph, 1),
        "peak_magnitude": event.peak_magnitude,
        "training_implement": event.training_implement,
        "training_implement_label": event.training_implement_label,
        "player_name": event.player_name,
        "unit": event.unit,
        "mode": event.mode,
    }


def swing_speed_to_shot_dict(event: SwingSpeedEvent) -> dict:
    """Convert a swing speed event to the existing shot UI shape."""
    peak_speed = round(event.peak_speed_mph, 1)
    return {
        "ball_speed_mph": peak_speed,
        "ball_speed_raw_mph": None,
        "club_speed_mph": peak_speed,
        "smash_factor": None,
        "estimated_carry_yards": 0,
        "carry_range": [0, 0],
        "club": event.training_implement_label,
        "player_name": event.player_name,
        "timestamp": event.timestamp.isoformat(),
        "peak_magnitude": event.peak_magnitude,
        "launch_angle_vertical": None,
        "launch_angle_horizontal": None,
        "launch_angle_confidence": None,
        "launch_angle_vertical_confidence": None,
        "launch_angle_horizontal_confidence": None,
        "launch_angle_vertical_source": None,
        "launch_angle_horizontal_source": None,
        "angle_source": None,
        "club_angle_deg": None,
        "club_path_deg": None,
        "spin_axis_deg": None,
        "spin_rpm": None,
        "spin_rpm_measured": None,
        "spin_source": None,
        "spin_confidence": None,
        "spin_quality": None,
        "spin_snr": None,
        "spin_modulation_depth": None,
        "spin_peak_freq_hz": None,
        "spin_peak_freq_rpm": None,
        "spin_seam_cycles": None,
        "spin_at_lower_rail": None,
        "spin_at_upper_rail": None,
        "spin_candidates": None,
        "spin_phase_method": None,
        "spin_phase_rpm": None,
        "spin_phase_snr": None,
        "spin_phase_agreement_pct": None,
        "spin_phase_confirmed": None,
        "spin_rejection_reason": None,
        "carry_spin_adjusted": None,
        "mode": event.mode,
        "swing_speed_duration_ms": round(event.duration_ms),
        "swing_speed_reading_count": event.reading_count,
        "swing_speed_trigger_mph": round(event.trigger_speed_mph, 1),
        "training_implement": event.training_implement,
        "training_implement_label": event.training_implement_label,
    }


def _process_shot_kld7_and_spin_axis(
    shot: Shot, shot_ts: float, session_log: Any
) -> Optional[float]:
    """Execute K-LD7 vertical and horizontal radar processing and derive spin axis."""
    if shot.mode == "mock":
        return None

    kld7_vertical = getattr(server, "kld7_vertical", None)
    kld7_horizontal = getattr(server, "kld7_horizontal", None)
    kld7_ms = None

    try:
        if kld7_vertical or kld7_horizontal:
            kld7_start = time.time()
            server._maybe_wait_for_kld7_post_shot_frames(shot_ts)

            if kld7_vertical:
                server._process_kld7_orientation(
                    kld7_vertical, "vertical", shot, shot_ts, session_log
                )

            if kld7_horizontal:
                server._process_kld7_orientation(
                    kld7_horizontal, "horizontal", shot, shot_ts, session_log
                )

            kld7_ms = (time.time() - kld7_start) * 1000
            logger.info("[SERVER] K-LD7 processing: %.1fms", kld7_ms)

        if (
            shot.launch_angle_horizontal is not None
            and shot.club_path_deg is not None
            and (shot.launch_angle_horizontal_confidence or 0.0) >= SPIN_AXIS_MIN_CONFIDENCE
        ):
            shot.spin_axis_deg = round(shot.launch_angle_horizontal - shot.club_path_deg, 1)
            logger.info(
                "[SERVER] Spin axis: %+.1f° (face=%+.1f° - path=%+.1f°)",
                shot.spin_axis_deg,
                shot.launch_angle_horizontal,
                shot.club_path_deg,
            )

        return kld7_ms
    except Exception as e:
        logger.warning("[SERVER] Angle/spin-axis post-processing error: %s", e, exc_info=True)
        server.log_session_error(
            "Angle/spin-axis post-processing failed",
            component="server",
            context={
                "stage": "angle_postprocessing",
                "ball_speed_mph": shot.ball_speed_mph,
                "club": shot.club.value,
            },
            exc=e,
        )
        return None


def _process_shot_camera(shot: Shot) -> Optional[dict]:
    """Extract camera launch angle if camera is enabled and available."""
    camera_tracker = getattr(server, "camera_tracker", None)
    camera_enabled = getattr(server, "camera_enabled", False)
    if (
        not camera_tracker
        or not camera_enabled
        or shot.mode == "mock"
        or shot.launch_angle_vertical is not None
    ):
        return None

    try:
        launch_angle = camera_tracker.calculate_launch_angle()
        camera_data = None
        if launch_angle:
            shot.launch_angle_vertical = launch_angle.vertical
            shot.launch_angle_horizontal = launch_angle.horizontal
            shot.launch_angle_confidence = launch_angle.confidence
            shot.launch_angle_vertical_confidence = launch_angle.confidence
            shot.launch_angle_horizontal_confidence = launch_angle.confidence
            shot.launch_angle_vertical_source = "camera"
            shot.launch_angle_horizontal_source = "camera"
            shot.angle_source = "camera"

            camera_data = {
                "launch_angle_vertical": launch_angle.vertical,
                "launch_angle_horizontal": launch_angle.horizontal,
                "launch_angle_confidence": launch_angle.confidence,
                "positions_tracked": len(launch_angle.positions),
                "launch_detected": camera_tracker.launch_detected,
            }
            logger.info(
                "[SERVER] Angle source: camera (%.1f° V, %.1f° H, conf=%.0f%%)",
                launch_angle.vertical,
                launch_angle.horizontal,
                launch_angle.confidence * 100,
            )

        camera_tracker.reset()
        server.ball_detected = False
        server.ball_detection_confidence = 0.0
        return camera_data
    except Exception as e:
        logger.warning("[SERVER] Camera processing error: %s", e, exc_info=True)
        server.log_session_error(
            "Camera shot processing failed",
            component="server",
            context={"stage": "camera", "ball_speed_mph": shot.ball_speed_mph},
            exc=e,
        )
        return None


def _process_shot_ballistics_and_carry(shot: Shot) -> None:
    """Calculate shot carry distance using physics simulator or carry table."""
    ballistics_enabled = getattr(server, "ballistics_enabled", True)
    if shot.carry_spin_adjusted is not None or shot.mode == "mock":
        return

    conditions = server.resolve_launch(shot) if ballistics_enabled else None
    if conditions is not None:
        trajectory = server.simulate(conditions)
        shot.carry_spin_adjusted = trajectory.carry_yards
        logger.info(
            "[SERVER] Ballistic carry: %.0f yds (spin: %.0f rpm, source: %s)",
            shot.carry_spin_adjusted,
            conditions.spin_rpm,
            conditions.spin_source,
        )
    else:
        has_reliable_spin = (
            shot.spin_rpm
            and shot.spin_rpm > 0
            and shot.spin_confidence is not None
            and shot.spin_confidence >= _MIN_RELIABLE_SPIN_CONF
        )
        spin_for_carry = (
            shot.spin_rpm
            if has_reliable_spin
            else server.get_optimal_spin_for_ball_speed(shot.ball_speed_mph, shot.club)
        )
        shot.carry_spin_adjusted = server.estimate_carry_with_spin(
            shot.ball_speed_mph,
            spin_for_carry,
            shot.club,
            club_speed_mph=shot.club_speed_mph,
        )
        reason = "ballistics disabled" if not ballistics_enabled else "no launch angle"
        logger.info(
            "[SERVER] Table carry (%s): %.0f yds (spin: %.0f rpm%s)",
            reason,
            shot.carry_spin_adjusted,
            spin_for_carry,
            "" if shot.spin_rpm and shot.spin_rpm > 0 else " avg",
        )

    if shot.spin_rejection_reason:
        logger.info(
            "[SERVER] Spin unavailable: %s (snr=%s, candidate=%s rpm)",
            shot.spin_rejection_reason,
            "%.2f" % shot.spin_snr if shot.spin_snr is not None else "N/A",
            (
                "%.0f" % (shot.spin_peak_freq_hz * 60)
                if shot.spin_peak_freq_hz is not None
                else "N/A"
            ),
        )


def _log_shot_to_session(
    shot: Shot,
    iwr6843_ms: Optional[float],
    kld7_ms: Optional[float],
) -> None:
    """Log complete shot telemetry into session log."""
    try:
        session_log = server.get_session_logger()
        if session_log:
            session_log.log_shot(
                ball_speed_mph=shot.ball_speed_mph,
                club_speed_mph=shot.club_speed_mph,
                smash_factor=shot.smash_factor,
                estimated_carry_yards=shot.estimated_carry_yards,
                club=shot.club.value,
                peak_magnitude=shot.peak_magnitude,
                readings_count=len(shot.readings),
                readings=shot.readings_data,
                spin_rpm=shot.spin_rpm,
                spin_confidence=shot.spin_confidence,
                spin_method=shot.spin_method,
                spin_quality=shot.spin_quality,
                spin_multipath_fade_hz=shot.spin_multipath_fade_hz,
                spin_snr=shot.spin_snr,
                spin_modulation_depth=shot.spin_modulation_depth,
                spin_peak_freq_hz=shot.spin_peak_freq_hz,
                spin_seam_cycles=shot.spin_seam_cycles,
                spin_at_lower_rail=shot.spin_at_lower_rail,
                spin_at_upper_rail=shot.spin_at_upper_rail,
                spin_candidates=shot.spin_candidates,
                spin_phase_method=shot.spin_phase_method,
                spin_phase_rpm=shot.spin_phase_rpm,
                spin_phase_snr=shot.spin_phase_snr,
                spin_phase_agreement_pct=shot.spin_phase_agreement_pct,
                spin_phase_confirmed=shot.spin_phase_confirmed,
                spin_rejection_reason=shot.spin_rejection_reason,
                carry_spin_adjusted=shot.carry_spin_adjusted,
                mode=shot.mode,
                launch_angle_vertical=shot.launch_angle_vertical,
                launch_angle_horizontal=shot.launch_angle_horizontal,
                launch_angle_confidence=shot.launch_angle_confidence,
                launch_angle_vertical_confidence=shot.launch_angle_vertical_confidence,
                launch_angle_horizontal_confidence=shot.launch_angle_horizontal_confidence,
                launch_angle_vertical_source=shot.launch_angle_vertical_source,
                launch_angle_horizontal_source=shot.launch_angle_horizontal_source,
                angle_source=shot.angle_source,
                club_angle_deg=shot.club_angle_deg,
                club_path_deg=shot.club_path_deg,
                spin_axis_deg=shot.spin_axis_deg,
                impact_timestamp=shot.impact_timestamp,
                player_name=shot.player_name,
                inclinometer=shot.inclinometer,
                pipeline_ms={
                    "iwr6843": (round(iwr6843_ms, 1) if iwr6843_ms is not None else None),
                    "kld7": round(kld7_ms, 1) if kld7_ms is not None else None,
                },
            )
    except Exception as e:
        logger.warning("[SERVER] Failed to log shot: %s", e, exc_info=True)
        server.log_session_error(
            "Session shot logging failed",
            component="server",
            context={
                "stage": "session_log_shot",
                "ball_speed_mph": shot.ball_speed_mph,
            },
            exc=e,
        )


def _emit_shot_to_ui(shot: Shot) -> Optional[dict]:
    """Serialize and emit shot payload over Socket.IO to connected web clients."""
    try:
        shot_data = server.shot_to_dict(shot)
        stats = server.monitor.get_session_stats() if getattr(server, "monitor", None) else {}
        server.socketio.emit("shot", {"shot": shot_data, "stats": stats})

        angle_str = ""
        if shot.launch_angle_vertical is not None:
            angle_str = ", Launch: %.1f°" % shot.launch_angle_vertical
        logger.info(
            "[SERVER] Shot: ball=%.1f mph, carry=%.0f yds%s",
            shot.ball_speed_mph,
            shot.estimated_carry_yards,
            angle_str,
        )
        return shot_data
    except Exception as e:
        logger.error("[SERVER] Failed to emit shot: %s", e, exc_info=True)
        server.log_session_error(
            "WebSocket shot emit failed",
            component="server",
            context={"stage": "emit_shot", "ball_speed_mph": shot.ball_speed_mph},
            exc=e,
        )
        return None


def _emit_shot_debug(shot_data: dict, camera_data: Optional[dict]) -> None:
    """Record shot debug entry and emit over Socket.IO."""
    try:
        debug_log_entry = {
            "type": "shot",
            "timestamp": datetime.now().isoformat(),
            "radar": {
                "ball_speed_mph": shot_data["ball_speed_mph"],
                "club_speed_mph": shot_data["club_speed_mph"],
                "smash_factor": shot_data["smash_factor"],
                "peak_magnitude": shot_data["peak_magnitude"],
            },
            "camera": camera_data,
            "club": shot_data["club"],
        }
        debug_log_file = getattr(server, "debug_log_file", None)
        if debug_log_file:
            debug_log_file.write(json.dumps(debug_log_entry) + "\n")
            debug_log_file.flush()

        server.socketio.emit("debug_shot", debug_log_entry)
    except Exception as e:
        logger.warning("[SERVER] Debug logging error: %s", e)


def on_shot_detected(shot: Shot) -> None:
    """Callback when a shot is detected - orchestrates processing and emits to clients."""
    shot.player_name = getattr(server, "current_player_name", "Player 1")
    logger.info("[SERVER] Shot callback: %.1f mph", shot.ball_speed_mph)

    server._snapshot_inclinometer_for_shot(shot)
    iwr6843_ms = server._process_iwr6843_angle(shot)
    session_log = server.get_session_logger()
    shot_ts = shot.impact_timestamp or time.time()

    kld7_ms = server._process_shot_kld7_and_spin_axis(shot, shot_ts, session_log)
    camera_data = server._process_shot_camera(shot)
    server._ensure_user_facing_launch_angles(shot)

    if (
        getattr(server, "ball_speed_correction_enabled", False)
        and shot.launch_angle_vertical is not None
    ):
        raw_speed = shot.ball_speed_mph
        shot.ball_speed_raw_mph = raw_speed
        dist_ft = getattr(server, "ball_speed_correction_distance_ft", 1.0)
        above_ft = getattr(server, "ball_speed_correction_ball_above_radar_ft", 0.0)
        shot.ball_speed_mph = correct_ball_speed(
            raw_speed,
            shot.launch_angle_vertical,
            dist_ft,
            above_ft,
        )
        logger.info(
            "[SERVER] Ball speed cosine correction: %.1f -> %.1f mph (LA %.1f)",
            raw_speed,
            shot.ball_speed_mph,
            shot.launch_angle_vertical,
        )

    if getattr(server, "calculated_spin_enabled", False):
        server._apply_calculated_spin(shot)

    server._process_shot_ballistics_and_carry(shot)
    server._log_shot_to_session(shot, iwr6843_ms, kld7_ms)
    shot_data = server._emit_shot_to_ui(shot)
    if shot_data is None:
        return

    server._forward_shot_to_simulators(shot)
    if getattr(server, "debug_mode", False):
        server._emit_shot_debug(shot_data, camera_data)


def on_swing_speed_detected(event: SwingSpeedEvent) -> None:
    """Handle swing speed training reps and emit them to connected clients."""
    event.player_name = getattr(server, "current_player_name", "Player 1")
    event_data = server.swing_speed_to_dict(event)
    shot_data = server.swing_speed_to_shot_dict(event)
    stats = server.monitor.get_session_stats() if getattr(server, "monitor", None) else {}
    server.socketio.emit("swing_speed", {"event": event_data, "stats": stats})
    server.socketio.emit("shot", {"shot": shot_data, "stats": stats})
    logger.info(
        "[SERVER] Swing speed event emitted: peak=%.1f mph, readings=%d",
        event.peak_speed_mph,
        event.reading_count,
    )
