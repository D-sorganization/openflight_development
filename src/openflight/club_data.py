"""Canonical golf club physics data, profiles, and baseline statistics.

Consolidates all club-physics tables (optimal smash factor, launch angles,
typical spin rates, ball speeds, spin multipliers, and mock simulation
distributions) into a single canonical source of truth, preventing numeric
drift across subsystems.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Tuple


class ClubType(Enum):
    """Golf club types for distance estimation, ballistics, and telemetry."""

    DRIVER = "driver"
    WOOD_3 = "3-wood"
    WOOD_5 = "5-wood"
    WOOD_7 = "7-wood"
    HYBRID_3 = "3-hybrid"
    HYBRID_5 = "5-hybrid"
    HYBRID_7 = "7-hybrid"
    HYBRID_9 = "9-hybrid"
    IRON_2 = "2-iron"
    IRON_3 = "3-iron"
    IRON_4 = "4-iron"
    IRON_5 = "5-iron"
    IRON_6 = "6-iron"
    IRON_7 = "7-iron"
    IRON_8 = "8-iron"
    IRON_9 = "9-iron"
    PW = "pw"
    GW = "gw"
    SW = "sw"
    LW = "lw"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ClubProfile:
    """Unified physical and statistical baseline profile for a club type.

    Attributes:
        club_type: ClubType enumeration value.
        name: Human-readable club name.
        optimal_smash: Canonical optimal smash factor (ball_speed / club_speed).
        optimal_launch_deg: Optimal / average vertical launch angle in degrees.
        typical_spin_rpm: TrackMan PGA Tour average spin rate in RPM.
        avg_ball_speed_mph: Baseline ball speed for amateur / typical golfer in mph.
        deg_per_mph_deviation: Degrees of launch angle shift per mph ball-speed deviation.
        spin_multiplier: Club-specific spin scaling multiplier relative to driver.
        speed_std_dev_mph: Standard deviation of ball speed for mock shot generation.
        spin_std_dev_rpm: Standard deviation of spin rate for mock shot generation.
        launch_std_dev_deg: Standard deviation of launch angle for mock shot generation.
    """

    club_type: ClubType
    name: str
    optimal_smash: float
    optimal_launch_deg: float
    typical_spin_rpm: float
    avg_ball_speed_mph: float
    deg_per_mph_deviation: float
    spin_multiplier: float
    speed_std_dev_mph: float = 10.0
    spin_std_dev_rpm: float = 500.0
    launch_std_dev_deg: float = 2.0


CLUB_PROFILES: Dict[ClubType, ClubProfile] = {
    ClubType.DRIVER: ClubProfile(
        club_type=ClubType.DRIVER,
        name="Driver",
        optimal_smash=1.48,
        optimal_launch_deg=11.0,
        typical_spin_rpm=2700.0,
        avg_ball_speed_mph=143.0,
        deg_per_mph_deviation=0.15,
        spin_multiplier=1.0,
        speed_std_dev_mph=12.0,
        spin_std_dev_rpm=400.0,
        launch_std_dev_deg=2.0,
    ),
    ClubType.WOOD_3: ClubProfile(
        club_type=ClubType.WOOD_3,
        name="3-Wood",
        optimal_smash=1.44,
        optimal_launch_deg=12.5,
        typical_spin_rpm=3500.0,
        avg_ball_speed_mph=135.0,
        deg_per_mph_deviation=0.18,
        spin_multiplier=1.15,
        speed_std_dev_mph=10.0,
        spin_std_dev_rpm=400.0,
        launch_std_dev_deg=2.0,
    ),
    ClubType.WOOD_5: ClubProfile(
        club_type=ClubType.WOOD_5,
        name="5-Wood",
        optimal_smash=1.42,
        optimal_launch_deg=14.0,
        typical_spin_rpm=4200.0,
        avg_ball_speed_mph=128.0,
        deg_per_mph_deviation=0.20,
        spin_multiplier=1.25,
        speed_std_dev_mph=10.0,
        spin_std_dev_rpm=400.0,
        launch_std_dev_deg=2.0,
    ),
    ClubType.WOOD_7: ClubProfile(
        club_type=ClubType.WOOD_7,
        name="7-Wood",
        optimal_smash=1.42,
        optimal_launch_deg=15.5,
        typical_spin_rpm=4800.0,
        avg_ball_speed_mph=122.0,
        deg_per_mph_deviation=0.20,
        spin_multiplier=1.32,
        speed_std_dev_mph=9.0,
        spin_std_dev_rpm=500.0,
        launch_std_dev_deg=2.0,
    ),
    ClubType.HYBRID_3: ClubProfile(
        club_type=ClubType.HYBRID_3,
        name="3-Hybrid",
        optimal_smash=1.39,
        optimal_launch_deg=13.5,
        typical_spin_rpm=4400.0,
        avg_ball_speed_mph=123.0,
        deg_per_mph_deviation=0.22,
        spin_multiplier=1.45,
        speed_std_dev_mph=9.0,
        spin_std_dev_rpm=400.0,
        launch_std_dev_deg=2.0,
    ),
    ClubType.HYBRID_5: ClubProfile(
        club_type=ClubType.HYBRID_5,
        name="5-Hybrid",
        optimal_smash=1.38,
        optimal_launch_deg=15.0,
        typical_spin_rpm=4900.0,
        avg_ball_speed_mph=118.0,
        deg_per_mph_deviation=0.22,
        spin_multiplier=1.55,
        speed_std_dev_mph=9.0,
        spin_std_dev_rpm=500.0,
        launch_std_dev_deg=2.0,
    ),
    ClubType.HYBRID_7: ClubProfile(
        club_type=ClubType.HYBRID_7,
        name="7-Hybrid",
        optimal_smash=1.37,
        optimal_launch_deg=16.5,
        typical_spin_rpm=5300.0,
        avg_ball_speed_mph=112.0,
        deg_per_mph_deviation=0.25,
        spin_multiplier=1.65,
        speed_std_dev_mph=8.0,
        spin_std_dev_rpm=500.0,
        launch_std_dev_deg=2.0,
    ),
    ClubType.HYBRID_9: ClubProfile(
        club_type=ClubType.HYBRID_9,
        name="9-Hybrid",
        optimal_smash=1.36,
        optimal_launch_deg=18.0,
        typical_spin_rpm=5800.0,
        avg_ball_speed_mph=106.0,
        deg_per_mph_deviation=0.25,
        spin_multiplier=1.75,
        speed_std_dev_mph=8.0,
        spin_std_dev_rpm=500.0,
        launch_std_dev_deg=2.5,
    ),
    ClubType.IRON_2: ClubProfile(
        club_type=ClubType.IRON_2,
        name="2-Iron",
        optimal_smash=1.37,
        optimal_launch_deg=13.0,
        typical_spin_rpm=4000.0,
        avg_ball_speed_mph=120.0,
        deg_per_mph_deviation=0.25,
        spin_multiplier=1.50,
        speed_std_dev_mph=9.0,
        spin_std_dev_rpm=400.0,
        launch_std_dev_deg=2.0,
    ),
    ClubType.IRON_3: ClubProfile(
        club_type=ClubType.IRON_3,
        name="3-Iron",
        optimal_smash=1.36,
        optimal_launch_deg=14.5,
        typical_spin_rpm=4500.0,
        avg_ball_speed_mph=118.0,
        deg_per_mph_deviation=0.25,
        spin_multiplier=1.60,
        speed_std_dev_mph=9.0,
        spin_std_dev_rpm=400.0,
        launch_std_dev_deg=2.0,
    ),
    ClubType.IRON_4: ClubProfile(
        club_type=ClubType.IRON_4,
        name="4-Iron",
        optimal_smash=1.35,
        optimal_launch_deg=16.0,
        typical_spin_rpm=5000.0,
        avg_ball_speed_mph=114.0,
        deg_per_mph_deviation=0.28,
        spin_multiplier=1.80,
        speed_std_dev_mph=8.0,
        spin_std_dev_rpm=500.0,
        launch_std_dev_deg=2.0,
    ),
    ClubType.IRON_5: ClubProfile(
        club_type=ClubType.IRON_5,
        name="5-Iron",
        optimal_smash=1.35,
        optimal_launch_deg=17.5,
        typical_spin_rpm=5400.0,
        avg_ball_speed_mph=110.0,
        deg_per_mph_deviation=0.28,
        spin_multiplier=2.00,
        speed_std_dev_mph=8.0,
        spin_std_dev_rpm=500.0,
        launch_std_dev_deg=2.0,
    ),
    ClubType.IRON_6: ClubProfile(
        club_type=ClubType.IRON_6,
        name="6-Iron",
        optimal_smash=1.34,
        optimal_launch_deg=19.0,
        typical_spin_rpm=6000.0,
        avg_ball_speed_mph=105.0,
        deg_per_mph_deviation=0.30,
        spin_multiplier=2.20,
        speed_std_dev_mph=7.0,
        spin_std_dev_rpm=600.0,
        launch_std_dev_deg=2.5,
    ),
    ClubType.IRON_7: ClubProfile(
        club_type=ClubType.IRON_7,
        name="7-Iron",
        optimal_smash=1.34,
        optimal_launch_deg=20.5,
        typical_spin_rpm=6500.0,
        avg_ball_speed_mph=100.0,
        deg_per_mph_deviation=0.30,
        spin_multiplier=2.50,
        speed_std_dev_mph=7.0,
        spin_std_dev_rpm=600.0,
        launch_std_dev_deg=2.5,
    ),
    ClubType.IRON_8: ClubProfile(
        club_type=ClubType.IRON_8,
        name="8-Iron",
        optimal_smash=1.33,
        optimal_launch_deg=23.0,
        typical_spin_rpm=7500.0,
        avg_ball_speed_mph=94.0,
        deg_per_mph_deviation=0.30,
        spin_multiplier=2.80,
        speed_std_dev_mph=6.0,
        spin_std_dev_rpm=700.0,
        launch_std_dev_deg=3.0,
    ),
    ClubType.IRON_9: ClubProfile(
        club_type=ClubType.IRON_9,
        name="9-Iron",
        optimal_smash=1.33,
        optimal_launch_deg=25.5,
        typical_spin_rpm=8500.0,
        avg_ball_speed_mph=88.0,
        deg_per_mph_deviation=0.30,
        spin_multiplier=3.20,
        speed_std_dev_mph=6.0,
        spin_std_dev_rpm=800.0,
        launch_std_dev_deg=3.0,
    ),
    ClubType.PW: ClubProfile(
        club_type=ClubType.PW,
        name="Pitching Wedge",
        optimal_smash=1.25,
        optimal_launch_deg=28.0,
        typical_spin_rpm=9000.0,
        avg_ball_speed_mph=82.0,
        deg_per_mph_deviation=0.30,
        spin_multiplier=3.60,
        speed_std_dev_mph=5.0,
        spin_std_dev_rpm=800.0,
        launch_std_dev_deg=3.0,
    ),
    ClubType.GW: ClubProfile(
        club_type=ClubType.GW,
        name="Gap Wedge",
        optimal_smash=1.23,
        optimal_launch_deg=30.0,
        typical_spin_rpm=9500.0,
        avg_ball_speed_mph=76.0,
        deg_per_mph_deviation=0.30,
        spin_multiplier=4.10,
        speed_std_dev_mph=5.0,
        spin_std_dev_rpm=900.0,
        launch_std_dev_deg=3.5,
    ),
    ClubType.SW: ClubProfile(
        club_type=ClubType.SW,
        name="Sand Wedge",
        optimal_smash=1.22,
        optimal_launch_deg=32.0,
        typical_spin_rpm=10000.0,
        avg_ball_speed_mph=73.0,
        deg_per_mph_deviation=0.30,
        spin_multiplier=4.30,
        speed_std_dev_mph=5.0,
        spin_std_dev_rpm=1000.0,
        launch_std_dev_deg=4.0,
    ),
    ClubType.LW: ClubProfile(
        club_type=ClubType.LW,
        name="Lob Wedge",
        optimal_smash=1.20,
        optimal_launch_deg=35.0,
        typical_spin_rpm=10500.0,
        avg_ball_speed_mph=70.0,
        deg_per_mph_deviation=0.30,
        spin_multiplier=4.60,
        speed_std_dev_mph=5.0,
        spin_std_dev_rpm=1000.0,
        launch_std_dev_deg=4.0,
    ),
    ClubType.UNKNOWN: ClubProfile(
        club_type=ClubType.UNKNOWN,
        name="Unknown",
        optimal_smash=1.35,
        optimal_launch_deg=18.0,
        typical_spin_rpm=5000.0,
        avg_ball_speed_mph=120.0,
        deg_per_mph_deviation=0.25,
        spin_multiplier=1.0,
        speed_std_dev_mph=15.0,
        spin_std_dev_rpm=800.0,
        launch_std_dev_deg=3.0,
    ),
}

# Derived canonical dictionaries for fast lookup and backward compatibility
OPTIMAL_SMASH: Dict[ClubType, float] = {k: v.optimal_smash for k, v in CLUB_PROFILES.items()}
OPTIMAL_LAUNCH: Dict[ClubType, float] = {k: v.optimal_launch_deg for k, v in CLUB_PROFILES.items()}
CLUB_TYPICAL_SPIN_RPM: Dict[ClubType, float] = {
    k: v.typical_spin_rpm for k, v in CLUB_PROFILES.items()
}
CLUB_LAUNCH_MODEL: Dict[ClubType, Tuple[float, float, float]] = {
    k: (v.optimal_launch_deg, v.avg_ball_speed_mph, v.deg_per_mph_deviation)
    for k, v in CLUB_PROFILES.items()
}
CLUB_SPIN_MULTIPLIERS: Dict[ClubType, float] = {
    k: v.spin_multiplier for k, v in CLUB_PROFILES.items()
}
CLUB_BALL_SPEEDS: Dict[ClubType, Tuple[float, float, float]] = {
    k: (v.avg_ball_speed_mph, v.speed_std_dev_mph, v.optimal_smash)
    for k, v in CLUB_PROFILES.items()
}
CLUB_SPIN: Dict[ClubType, Tuple[float, float]] = {
    k: (v.typical_spin_rpm, v.spin_std_dev_rpm) for k, v in CLUB_PROFILES.items()
}
CLUB_LAUNCH: Dict[ClubType, Tuple[float, float]] = {
    k: (v.optimal_launch_deg, v.launch_std_dev_deg) for k, v in CLUB_PROFILES.items()
}

# Backward-compatibility aliases with underscore prefixes
_OPTIMAL_SMASH = OPTIMAL_SMASH
_OPTIMAL_LAUNCH = OPTIMAL_LAUNCH
_CLUB_TYPICAL_SPIN_RPM = CLUB_TYPICAL_SPIN_RPM
_CLUB_LAUNCH_MODEL = CLUB_LAUNCH_MODEL
_CLUB_BALL_SPEEDS = CLUB_BALL_SPEEDS
_CLUB_SPIN = CLUB_SPIN
_CLUB_LAUNCH = CLUB_LAUNCH


def get_club_profile(club: Optional[ClubType] = None) -> ClubProfile:
    """Return the ClubProfile for the given ClubType, defaulting to UNKNOWN."""
    if club is None:
        return CLUB_PROFILES[ClubType.UNKNOWN]
    return CLUB_PROFILES.get(club, CLUB_PROFILES[ClubType.UNKNOWN])


def get_optimal_smash(club: Optional[ClubType] = None) -> float:
    """Return the optimal smash factor for a club (default 1.35)."""
    return get_club_profile(club).optimal_smash


def get_optimal_launch(club: Optional[ClubType] = None) -> float:
    """Return the optimal launch angle in degrees for a club (default 18.0)."""
    return get_club_profile(club).optimal_launch_deg


def get_typical_spin(club: Optional[ClubType] = None) -> float:
    """Return the typical spin rate in RPM for a club (default 5000.0)."""
    return get_club_profile(club).typical_spin_rpm


def get_spin_multiplier(club: Optional[ClubType] = None) -> float:
    """Return the spin multiplier for a club relative to driver (default 1.0)."""
    return get_club_profile(club).spin_multiplier


def get_club_launch_model(
    club: Optional[ClubType] = None,
) -> Tuple[float, float, float]:
    """Return (optimal_launch_deg, avg_ball_speed_mph, deg_per_mph) for a club."""
    profile = get_club_profile(club)
    return (
        profile.optimal_launch_deg,
        profile.avg_ball_speed_mph,
        profile.deg_per_mph_deviation,
    )
