"""OpenFlight - DIY Golf Launch Monitor using OPS243-A Radar."""

__version__ = "0.2.0"

from .club_data import CLUB_PROFILES, ClubProfile, ClubType, get_club_profile
from .launch_monitor import Shot, estimate_carry_distance
from .ops243 import Direction, OPS243Radar, SpeedReading, SpeedUnit

__all__ = [
    "OPS243Radar",
    "Shot",
    "ClubType",
    "ClubProfile",
    "CLUB_PROFILES",
    "get_club_profile",
    "SpeedUnit",
    "Direction",
    "SpeedReading",
    "estimate_carry_distance",
]
