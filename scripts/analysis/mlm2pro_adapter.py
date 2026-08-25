"""Rapsodo MLM2 Pro CSV adapter for OpenFlight / TrackMan comparison pipeline.

Transforms Rapsodo MLM2 Pro session CSV exports into the standard TrackMan CSV layout
expected by ``compare_trackman.py``.

Usage::

    uv run python scripts/analysis/mlm2pro_adapter.py \\
        --input ~/Downloads/mlm2pro_session.csv \\
        --output ~/openflight_sessions/trackman_formatted.csv

Or within Python::

    from mlm2pro_adapter import convert_mlm2pro_csv_to_trackman, load_mlm2pro

    shots = load_mlm2pro("mlm2pro_session.csv")
    convert_mlm2pro_csv_to_trackman("mlm2pro_session.csv", "trackman_formatted.csv")
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# Constants & Unit Conversions
# ---------------------------------------------------------------------------

MPH_PER_MPS: float = 2.2369362920544
MPS_PER_MPH: float = 0.44704
KMH_PER_MPH: float = 1.609344
MPH_PER_KMH: float = 1.0 / KMH_PER_MPH

YARDS_PER_METER: float = 1.0936132983377
METERS_PER_YARD: float = 0.9144
FEET_PER_METER: float = 3.280839895
YARDS_PER_FOOT: float = 1.0 / 3.0
FEET_PER_YARD: float = 3.0

TRACKMAN_EXPORT_FIELDS: List[str] = [
    "Shot Number",
    "Date/Time",
    "Club",
    "Ball Speed (mph)",
    "Club Speed (mph)",
    "Smash Factor",
    "Launch Angle",
    "Launch Direction",
    "Spin Rate",
    "Spin Axis",
    "Carry Distance",
    "Total Distance",
    "Apex",
    "Side Carry",
]

# ---------------------------------------------------------------------------
# Header Match Rules
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HeaderAlias:
    """Header match rule for column mapping."""

    text: str
    exact: bool = False


# Aliases commonly found in Rapsodo MLM2PRO / R-Cloud web exports and app exports.
_MLM2PRO_ALIAS_CONFIG: Dict[str, List[str | HeaderAlias]] = {
    "shot_number": [
        "shot number",
        "shot #",
        "shot no",
        "shot no.",
        "shot id",
        "shotid",
        "shot_number",
        "shot_id",
        "shot",
        "number",
        HeaderAlias("#", exact=True),
    ],
    "timestamp": [
        "date/time",
        "date & time",
        "date and time",
        "date time",
        "datetime",
        "created at",
        "timestamp",
    ],
    "date_only": [
        HeaderAlias("date", exact=True),
        "session date",
    ],
    "time_only": [
        HeaderAlias("time", exact=True),
        "shot time",
    ],
    "club": [
        "club type",
        "club name",
        "club model",
        "club selected",
        "club type / name",
        "club",
    ],
    "ball_speed": [
        "ball speed",
        "ballspeed",
        "ball vel",
        "ball velocity",
    ],
    "club_speed": [
        "club speed",
        "clubspeed",
        "club head speed",
        "clubhead speed",
        "clubheadspeed",
        "chs",
    ],
    "smash_factor": [
        "smash factor",
        "smashfactor",
        "smash ratio",
        "smash",
    ],
    "launch_angle_vertical": [
        "launch angle (deg)",
        "launch angle (°)",
        "launch angle (v)",
        "launch angle v",
        "vertical launch angle",
        "vertical launch",
        "launch angle",
        "vla",
        "launch v",
    ],
    "launch_angle_horizontal": [
        "launch direction (deg)",
        "launch direction (°)",
        "launch direction",
        "launch angle (h)",
        "launch angle h",
        "horizontal launch angle",
        "horizontal launch",
        "side angle (deg)",
        "side angle (°)",
        "side angle",
        "hla",
        "launch h",
        "azimuth",
        "deviation angle",
    ],
    "total_spin": [
        "total spin (rpm)",
        "total spin",
        "spin rate (rpm)",
        "spin rate",
        "total spin rate",
        "spin (rpm)",
        "spin",
        "back spin (rpm)",
        "back spin",
        "backspin (rpm)",
        "backspin",
    ],
    "spin_axis": [
        "spin axis (deg)",
        "spin axis (°)",
        "spin axis",
        "spin tilt (deg)",
        "spin tilt",
        "tilt angle (deg)",
        "tilt angle",
        "axis (deg)",
        "axis",
    ],
    "carry_distance": [
        "carry distance (yds)",
        "carry distance (yd)",
        "carry distance (yards)",
        "carry distance (m)",
        "carry distance (meters)",
        "carry distance (metres)",
        "carry (yds)",
        "carry (yd)",
        "carry (m)",
        "carry distance",
        "carry",
        "estimated carry distance",
        "estimated carry",
    ],
    "total_distance": [
        "total distance (yds)",
        "total distance (yd)",
        "total distance (m)",
        "total distance (meters)",
        "total (yds)",
        "total (yd)",
        "total (m)",
        "total distance",
        "total",
    ],
    "apex": [
        "apex (ft)",
        "apex (m)",
        "apex (yds)",
        "apex height (ft)",
        "apex height (m)",
        "apex height",
        "apex",
        "max height (ft)",
        "max height (m)",
        "max height",
        "peak height (ft)",
        "peak height",
    ],
    "descent_angle": [
        "descent angle (deg)",
        "descent angle (°)",
        "descent angle",
        "landing angle (deg)",
        "landing angle",
        "descent",
    ],
    "side_carry": [
        "side carry (yds)",
        "side carry (m)",
        "side (yds)",
        "side (m)",
        "side carry",
        "offline (yds)",
        "offline (m)",
        "lateral (yds)",
        "lateral (m)",
        "side",
        "lateral",
    ],
}

_MLM2PRO_ALIASES: Dict[str, List[HeaderAlias]] = {
    field_name: [
        alias if isinstance(alias, HeaderAlias) else HeaderAlias(alias) for alias in aliases
    ]
    for field_name, aliases in _MLM2PRO_ALIAS_CONFIG.items()
}

# ---------------------------------------------------------------------------
# Club Name Normalization
# ---------------------------------------------------------------------------

_CLUB_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\b(driver|drv|1w|1-wood|1 wood)\b", re.IGNORECASE), "driver"),
    (re.compile(r"\b(\d)\s*-?\s*(wood|w)\b", re.IGNORECASE), r"\1-wood"),
    (re.compile(r"\b(\d)\s*-?\s*(hybrid|h|hy)\b", re.IGNORECASE), r"\1-hybrid"),
    (re.compile(r"\b(\d)\s*-?\s*(iron|i)\b", re.IGNORECASE), r"\1-iron"),
    (re.compile(r"\biron\s*-?\s*(\d)\b", re.IGNORECASE), r"\1-iron"),
    (re.compile(r"\bpitching\s*wedge\b|\bpw\b", re.IGNORECASE), "pw"),
    (re.compile(r"\bgap\s*wedge\b|\bgw\b|\bapproach\s*wedge\b|\baw\b", re.IGNORECASE), "gw"),
    (re.compile(r"\bsand\s*wedge\b|\bsw\b", re.IGNORECASE), "sw"),
    (re.compile(r"\blob\s*wedge\b|\blw\b", re.IGNORECASE), "lw"),
]


def normalize_club(raw: Optional[str]) -> str:
    """Normalize club names into canonical OpenFlight / TrackMan formats.

    Examples:
        '7 Iron', '7i', 'Iron 7', '7-iron' -> '7-iron'
        'Driver', 'DRV', '1W' -> 'driver'
        'Pitching Wedge', 'PW' -> 'pw'
        'Gap Wedge', 'AW', 'GW' -> 'gw'
    """
    if raw is None:
        return ""
    s = str(raw).strip()
    if not s:
        return ""
    for pat, repl in _CLUB_PATTERNS:
        m = pat.search(s)
        if m:
            return pat.sub(repl, m.group(0)).lower().strip()
    return s.lower()


# ---------------------------------------------------------------------------
# Value & Unit Parsers
# ---------------------------------------------------------------------------


def _canon_header(h: str) -> str:
    return h.strip().lower().replace("_", " ")


def detect_units(headers: Sequence[str]) -> Dict[str, str]:
    """Detect metric units by inspecting header suffixes.

    Returns dict mapping:
        'ball_speed': 'mph' | 'mps' | 'kph'
        'club_speed': 'mph' | 'mps' | 'kph'
        'carry': 'yards' | 'meters'
        'total': 'yards' | 'meters'
        'apex': 'feet' | 'meters' | 'yards'
        'side': 'yards' | 'meters'
    """
    units: Dict[str, str] = {
        "ball_speed": "mph",
        "club_speed": "mph",
        "carry": "yards",
        "total": "yards",
        "apex": "feet",
        "side": "yards",
    }

    for h in headers:
        ch = _canon_header(h)
        # Speed units
        if "ball speed" in ch or "ballspeed" in ch or "ball vel" in ch:
            if "m/s" in ch or "mps" in ch:
                units["ball_speed"] = "mps"
            elif "kph" in ch or "km/h" in ch or "kmh" in ch:
                units["ball_speed"] = "kph"
            elif "mph" in ch:
                units["ball_speed"] = "mph"

        if (
            "club speed" in ch
            or "clubspeed" in ch
            or "club head speed" in ch
            or "clubheadspeed" in ch
            or "chs" in ch
        ):
            if "m/s" in ch or "mps" in ch:
                units["club_speed"] = "mps"
            elif "kph" in ch or "km/h" in ch or "kmh" in ch:
                units["club_speed"] = "kph"
            elif "mph" in ch:
                units["club_speed"] = "mph"

        # Distance units
        if "carry" in ch:
            if "metre" in ch or "meter" in ch or "(m)" in ch or " m " in ch or ch.endswith(" m"):
                units["carry"] = "meters"
            elif "yd" in ch or "yard" in ch:
                units["carry"] = "yards"

        if "total" in ch and "spin" not in ch:
            if "metre" in ch or "meter" in ch or "(m)" in ch or " m " in ch or ch.endswith(" m"):
                units["total"] = "meters"
            elif "yd" in ch or "yard" in ch:
                units["total"] = "yards"

        if "apex" in ch or "height" in ch:
            if "metre" in ch or "meter" in ch or "(m)" in ch or " m " in ch:
                units["apex"] = "meters"
            elif "yd" in ch or "yard" in ch:
                units["apex"] = "yards"
            elif "ft" in ch or "feet" in ch:
                units["apex"] = "feet"

        if "side" in ch or "offline" in ch or "lateral" in ch:
            if "metre" in ch or "meter" in ch or "(m)" in ch or " m " in ch:
                units["side"] = "meters"
            elif "yd" in ch or "yard" in ch:
                units["side"] = "yards"

    return units


def build_column_map(headers: Sequence[str]) -> Dict[str, str]:
    """Map canonical field name -> actual header string from the CSV."""
    col_map: Dict[str, str] = {}
    canon = {_canon_header(h): h for h in headers}

    for field_name, aliases in _MLM2PRO_ALIASES.items():
        for alias in aliases:
            for canon_h, raw_h in canon.items():
                matches = canon_h == alias.text if alias.exact else alias.text in canon_h
                if matches and field_name not in col_map:
                    col_map[field_name] = raw_h
                    break
            if field_name in col_map:
                break
    return col_map


def _to_float(v: Any) -> Optional[float]:
    """Parse numeric float safely with NaN / fallback guards."""
    if v is None:
        return None
    s = str(v).strip()
    if not s or s.lower() in (
        "-",
        "--",
        "n/a",
        "na",
        "null",
        "none",
        "nan",
        "inf",
        "-inf",
        "invalid",
        "calc",
        "est",
    ):
        return None
    s = s.replace(",", "")
    # Check for prefix or postfix unit labels e.g. "120.5 mph"
    m = re.search(r"^[+\-]?\d+(?:\.\d+)?(?:[eE][+\-]?\d+)?", s)
    if m:
        try:
            return float(m.group(0))
        except (TypeError, ValueError):
            return None
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def _to_int(v: Any) -> Optional[int]:
    """Parse integer value safely."""
    f = _to_float(v)
    return int(round(f)) if f is not None else None


def parse_directional_angle(val: Any) -> Optional[float]:
    """Parse launch direction or spin axis angle with optional L/R sign indicators.

    In golf conventions:
        - Right / Push / Fade is positive (+)
        - Left / Pull / Draw is negative (-)
        - 'Straight' is 0.0

    Examples:
        '2.5 R', 'R 2.5', '+2.5', '2.5° R' -> +2.5
        '1.8 L', 'L 1.8', '-1.8', '1.8° L' -> -1.8
        '15.3', '15.3°', '15.3 deg' -> 15.3
        'Straight' -> 0.0
        None, '', 'N/A', '-' -> None
    """
    if val is None:
        return None
    s = str(val).strip()
    if not s or s.lower() in (
        "-",
        "--",
        "n/a",
        "na",
        "null",
        "none",
        "nan",
        "invalid",
        "calc",
        "est",
    ):
        return None
    if s.lower() == "straight":
        return 0.0

    upper = s.upper()
    is_left = False
    is_right = False

    # Check for L or R indicator
    if re.search(r"(^|\s|\d)L($|\s|°)", upper) or upper.startswith("L ") or upper.endswith(" L"):
        is_left = True
    elif re.search(r"(^|\s|\d)R($|\s|°)", upper) or upper.startswith("R ") or upper.endswith(" R"):
        is_right = True

    # Extract numeric part
    cleaned = re.sub(r"[^\d.+\-]", "", s)
    if not cleaned or cleaned in ("+", "-"):
        return None
    try:
        num = float(cleaned)
        if is_left:
            return -abs(num)
        if is_right:
            return abs(num)
        return num
    except (TypeError, ValueError):
        return None


def parse_timestamp(v: Any) -> Optional[datetime]:
    """Parse date/time string across standard ISO and launch-monitor export formats."""
    if v is None:
        return None
    s = str(v).strip()
    if not s or s.lower() in ("-", "--", "n/a", "na", "null", "none", "nan"):
        return None

    # Try ISO first
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        pass

    candidates = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %I:%M:%S %p",
        "%m/%d/%Y %I:%M %p",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %I:%M:%S %p",
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%m/%d/%Y %H:%M",
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%d/%m/%Y",
    ]
    for fmt in candidates:
        try:
            return datetime.strptime(s, fmt)
        except (ValueError, TypeError):
            continue
    return None


def _combine_date_time(date_val: Any, time_val: Any) -> Optional[datetime]:
    """Combine separate date and time strings if available."""
    if date_val and time_val:
        combined = f"{str(date_val).strip()} {str(time_val).strip()}"
        ts = parse_timestamp(combined)
        if ts is not None:
            return ts
    if date_val:
        return parse_timestamp(date_val)
    if time_val:
        return parse_timestamp(time_val)
    return None


# ---------------------------------------------------------------------------
# Data Record
# ---------------------------------------------------------------------------


@dataclass
class MLM2ProShot:
    """Canonical parsed record for an MLM2 Pro shot."""

    shot_number: Optional[int] = None
    timestamp: Optional[datetime] = None
    club: str = ""
    ball_speed_mph: Optional[float] = None
    club_speed_mph: Optional[float] = None
    smash_factor: Optional[float] = None
    launch_angle_vertical: Optional[float] = None
    launch_angle_horizontal: Optional[float] = None
    spin_rpm: Optional[float] = None
    spin_axis_deg: Optional[float] = None
    carry_yards: Optional[float] = None
    total_yards: Optional[float] = None
    apex_feet: Optional[float] = None
    descent_angle_deg: Optional[float] = None
    side_carry_yards: Optional[float] = None
    raw: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Row Filtering & Summary Detection
# ---------------------------------------------------------------------------

_SUMMARY_LABELS = {
    "average",
    "avg",
    "averages",
    "std dev",
    "stddev",
    "standard deviation",
    "total",
    "totals",
    "summary",
    "min",
    "max",
    "median",
}


def _is_summary_or_blank_row(row: Dict[str, str]) -> bool:
    """Return True if row represents a statistical summary row (Averages, etc.) or is empty."""
    values = [str(v).strip() for v in row.values() if v is not None and str(v).strip()]
    if not values:
        return True

    for v in values:
        if v.lower() in _SUMMARY_LABELS:
            return True

    return False


# ---------------------------------------------------------------------------
# CSV Loader & Transformer
# ---------------------------------------------------------------------------


def _clean_csv_stream(fh: io.TextIOBase) -> io.StringIO:
    """Strip Excel preambles (``sep=,``), multiple UTF-8 BOMs, and leading metadata rows."""
    content = fh.read()
    # Strip any leading BOM characters
    while content.startswith("\ufeff"):
        content = content[1:]

    lines = content.splitlines()
    cleaned_lines: List[str] = []
    found_header = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.lower().startswith("sep="):
            continue

        # If header not yet identified, check if line looks like a header
        if not found_header:
            lower_line = stripped.lower()
            if any(
                k in lower_line
                for k in (
                    "ball speed",
                    "club speed",
                    "launch angle",
                    "carry",
                    "spin",
                    "shot",
                    "club",
                )
            ):
                found_header = True
                cleaned_lines.append(line)
                continue
            # Skip session header / player metadata lines before CSV table
            continue

        cleaned_lines.append(line)

    if not cleaned_lines:
        return io.StringIO(content)
    return io.StringIO("\n".join(cleaned_lines))


def load_mlm2pro(
    path: Path | str,
    speed_unit: str = "auto",
    distance_unit: str = "auto",
    default_club: Optional[str] = None,
) -> List[MLM2ProShot]:
    """Load and parse an MLM2 Pro session CSV export into canonical shot records.

    Args:
        path: Path to the MLM2 Pro CSV file.
        speed_unit: Override speed unit ('auto', 'mph', 'mps', 'kph').
        distance_unit: Override distance unit ('auto', 'yards', 'meters').
        default_club: Default club name if club column is missing/blank.

    Returns:
        List of parsed MLM2ProShot dataclass records.
    """
    shots: List[MLM2ProShot] = []
    file_path = Path(path)

    with open(file_path, "r", encoding="utf-8-sig", newline="") as raw_fh:
        stream = _clean_csv_stream(raw_fh)

    reader = csv.DictReader(stream)
    if reader.fieldnames is None:
        return shots

    cleaned_headers = [h.lstrip("\ufeff").strip() for h in reader.fieldnames]
    reader.fieldnames = cleaned_headers
    col_map = build_column_map(cleaned_headers)
    detected_units = detect_units(cleaned_headers)

    # Unit resolution (CLI override beats header detection)
    ball_speed_unit = speed_unit if speed_unit != "auto" else detected_units["ball_speed"]
    club_speed_unit = speed_unit if speed_unit != "auto" else detected_units["club_speed"]
    carry_unit = distance_unit if distance_unit != "auto" else detected_units["carry"]
    total_unit = distance_unit if distance_unit != "auto" else detected_units["total"]
    side_unit = distance_unit if distance_unit != "auto" else detected_units["side"]
    apex_unit = detected_units["apex"]

    def _get(row: Dict[str, str], canon_field: str) -> Any:
        col = col_map.get(canon_field)
        return row.get(col) if col else None

    shot_counter = 1

    for row in reader:
        if _is_summary_or_blank_row(row):
            continue

        # Shot Number (fallback to sequential 1-based index)
        raw_shot_num = _to_int(_get(row, "shot_number"))
        shot_num = raw_shot_num if raw_shot_num is not None else shot_counter
        shot_counter = shot_num + 1

        # Timestamp
        date_col = col_map.get("date_only")
        time_col = col_map.get("time_only")
        if date_col and time_col and date_col != time_col:
            ts = _combine_date_time(row.get(date_col), row.get(time_col))
        else:
            ts = parse_timestamp(_get(row, "timestamp"))
            if ts is None:
                ts = _combine_date_time(_get(row, "date_only"), _get(row, "time_only"))

        # Club
        raw_club = _get(row, "club")
        club_val = normalize_club(raw_club) if raw_club else normalize_club(default_club)

        # Ball Speed -> converted to mph
        raw_ball_speed = _to_float(_get(row, "ball_speed"))
        ball_speed_mph: Optional[float] = None
        if raw_ball_speed is not None:
            if ball_speed_unit == "mps":
                ball_speed_mph = raw_ball_speed * MPH_PER_MPS
            elif ball_speed_unit == "kph":
                ball_speed_mph = raw_ball_speed * MPH_PER_KMH
            else:
                ball_speed_mph = raw_ball_speed

        # Club Speed -> converted to mph
        raw_club_speed = _to_float(_get(row, "club_speed"))
        club_speed_mph: Optional[float] = None
        if raw_club_speed is not None:
            if club_speed_unit == "mps":
                club_speed_mph = raw_club_speed * MPH_PER_MPS
            elif club_speed_unit == "kph":
                club_speed_mph = raw_club_speed * MPH_PER_KMH
            else:
                club_speed_mph = raw_club_speed

        # Smash Factor (use reported or fallback compute)
        smash_val = _to_float(_get(row, "smash_factor"))
        if smash_val is None:
            if ball_speed_mph is not None and club_speed_mph is not None and club_speed_mph > 0:
                smash_val = round(ball_speed_mph / club_speed_mph, 3)

        # Launch Angles
        launch_v = _to_float(_get(row, "launch_angle_vertical"))
        launch_h = parse_directional_angle(_get(row, "launch_angle_horizontal"))

        # Spin Rate & Spin Axis
        spin_val = _to_float(_get(row, "total_spin"))
        spin_axis_val = parse_directional_angle(_get(row, "spin_axis"))

        # Carry Distance -> converted to yards
        raw_carry = _to_float(_get(row, "carry_distance"))
        carry_yards: Optional[float] = None
        if raw_carry is not None:
            if carry_unit == "meters":
                carry_yards = raw_carry * YARDS_PER_METER
            else:
                carry_yards = raw_carry

        # Total Distance -> converted to yards
        raw_total = _to_float(_get(row, "total_distance"))
        total_yards: Optional[float] = None
        if raw_total is not None:
            if total_unit == "meters":
                total_yards = raw_total * YARDS_PER_METER
            else:
                total_yards = raw_total

        # Apex Height -> converted to feet
        raw_apex = _to_float(_get(row, "apex"))
        apex_feet: Optional[float] = None
        if raw_apex is not None:
            if apex_unit == "meters":
                apex_feet = raw_apex * FEET_PER_METER
            elif apex_unit == "yards":
                apex_feet = raw_apex * FEET_PER_YARD
            else:
                apex_feet = raw_apex

        # Descent Angle
        descent_angle = _to_float(_get(row, "descent_angle"))

        # Side Carry -> converted to yards
        raw_side = parse_directional_angle(_get(row, "side_carry"))
        side_yards: Optional[float] = None
        if raw_side is not None:
            if side_unit == "meters":
                side_yards = raw_side * YARDS_PER_METER
            else:
                side_yards = raw_side

        shots.append(
            MLM2ProShot(
                shot_number=shot_num,
                timestamp=ts,
                club=club_val,
                ball_speed_mph=ball_speed_mph,
                club_speed_mph=club_speed_mph,
                smash_factor=smash_val,
                launch_angle_vertical=launch_v,
                launch_angle_horizontal=launch_h,
                spin_rpm=spin_val,
                spin_axis_deg=spin_axis_val,
                carry_yards=carry_yards,
                total_yards=total_yards,
                apex_feet=apex_feet,
                descent_angle_deg=descent_angle,
                side_carry_yards=side_yards,
                raw=dict(row),
            )
        )

    return shots


def shot_to_trackman_row(shot: MLM2ProShot) -> Dict[str, Any]:
    """Convert an MLM2ProShot dataclass to standard TrackMan CSV dictionary row."""

    def f(val: Any, decimals: int = 2) -> Any:
        if val is None:
            return ""
        if isinstance(val, float):
            return round(val, decimals)
        return val

    ts_str = shot.timestamp.strftime("%Y-%m-%d %H:%M:%S") if shot.timestamp else ""

    return {
        "Shot Number": shot.shot_number if shot.shot_number is not None else "",
        "Date/Time": ts_str,
        "Club": shot.club,
        "Ball Speed (mph)": f(shot.ball_speed_mph, 2),
        "Club Speed (mph)": f(shot.club_speed_mph, 2),
        "Smash Factor": f(shot.smash_factor, 3),
        "Launch Angle": f(shot.launch_angle_vertical, 2),
        "Launch Direction": f(shot.launch_angle_horizontal, 2),
        "Spin Rate": f(shot.spin_rpm, 1),
        "Spin Axis": f(shot.spin_axis_deg, 2),
        "Carry Distance": f(shot.carry_yards, 2),
        "Total Distance": f(shot.total_yards, 2),
        "Apex": f(shot.apex_feet, 2),
        "Side Carry": f(shot.side_carry_yards, 2),
    }


def write_trackman_csv(shots: Sequence[MLM2ProShot], output_path: Path | str) -> None:
    """Write parsed shots into TrackMan-compatible CSV format."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=TRACKMAN_EXPORT_FIELDS)
        writer.writeheader()
        for shot in shots:
            writer.writerow(shot_to_trackman_row(shot))


def convert_mlm2pro_csv_to_trackman(
    input_path: Path | str,
    output_path: Path | str,
    speed_unit: str = "auto",
    distance_unit: str = "auto",
    default_club: Optional[str] = None,
) -> List[MLM2ProShot]:
    """Convert Rapsodo MLM2 Pro session CSV export to standard TrackMan CSV layout.

    Args:
        input_path: Path to MLM2 Pro CSV export.
        output_path: Destination path for TrackMan formatted CSV.
        speed_unit: Speed unit override ('auto', 'mph', 'mps', 'kph').
        distance_unit: Distance unit override ('auto', 'yards', 'meters').
        default_club: Fallback club string if club is missing/unspecified.

    Returns:
        List of parsed MLM2ProShot records.
    """
    shots = load_mlm2pro(
        input_path,
        speed_unit=speed_unit,
        distance_unit=distance_unit,
        default_club=default_club,
    )
    write_trackman_csv(shots, output_path)
    return shots


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Transform Rapsodo MLM2 Pro session CSV export to TrackMan format "
            "for compare_trackman.py"
        )
    )
    parser.add_argument("--input", "-i", required=True, type=Path, help="MLM2 Pro CSV export path")
    parser.add_argument(
        "--output", "-o", required=True, type=Path, help="Output TrackMan-formatted CSV path"
    )
    parser.add_argument(
        "--speed-unit",
        choices=["auto", "mph", "mps", "kph"],
        default="auto",
        help="Input speed unit (default: auto-detect from header)",
    )
    parser.add_argument(
        "--distance-unit",
        choices=["auto", "yards", "meters"],
        default="auto",
        help="Input distance unit (default: auto-detect from header)",
    )
    parser.add_argument(
        "--default-club",
        default=None,
        help="Default club name if missing from CSV (e.g. '7-iron', 'driver')",
    )

    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"Input file not found: {args.input}", file=sys.stderr)
        return 2

    shots = convert_mlm2pro_csv_to_trackman(
        input_path=args.input,
        output_path=args.output,
        speed_unit=args.speed_unit,
        distance_unit=args.distance_unit,
        default_club=args.default_club,
    )

    print(f"Successfully converted {len(shots)} MLM2 Pro shots -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
