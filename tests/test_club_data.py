"""Unit tests for openflight.club_data canonical module.

Verifies complete coverage of ClubType enum members, physical validity
of all parameters, cross-dictionary consistency, helper function fallbacks,
and guarantees prevention of numeric regression or divergence across consumers.
"""

import pytest

from openflight.ballistics import CLUB_TYPICAL_SPIN_RPM as BALLISTICS_SPIN_RPM
from openflight.club_data import (
    CLUB_BALL_SPEEDS,
    CLUB_LAUNCH,
    CLUB_LAUNCH_MODEL,
    CLUB_PROFILES,
    CLUB_SPIN,
    CLUB_SPIN_MULTIPLIERS,
    CLUB_TYPICAL_SPIN_RPM,
    OPTIMAL_LAUNCH,
    OPTIMAL_SMASH,
    ClubProfile,
    ClubType,
    get_club_launch_model,
    get_club_profile,
    get_optimal_launch,
    get_optimal_smash,
    get_spin_multiplier,
    get_typical_spin,
)
from openflight.launch_monitor import _OPTIMAL_LAUNCH as LM_OPTIMAL_LAUNCH
from openflight.rolling_buffer.monitor import (
    estimate_carry_with_spin,
    get_optimal_spin_for_ball_speed,
)
from openflight.server import (
    _CLUB_LAUNCH_MODEL as SERVER_LAUNCH_MODEL,
    _OPTIMAL_SMASH as SERVER_OPTIMAL_SMASH,
    MockLaunchMonitor,
)
from openflight.sim.resolver import (
    _OPTIMAL_LAUNCH as SIM_OPTIMAL_LAUNCH,
    SPIN_MODEL_RPM as SIM_SPIN_MODEL_RPM,
)

WOODS = [
    ClubType.DRIVER,
    ClubType.WOOD_3,
    ClubType.WOOD_5,
    ClubType.WOOD_7,
]

HYBRIDS = [
    ClubType.HYBRID_3,
    ClubType.HYBRID_5,
    ClubType.HYBRID_7,
    ClubType.HYBRID_9,
]

IRONS_AND_WEDGES = [
    ClubType.IRON_2,
    ClubType.IRON_3,
    ClubType.IRON_4,
    ClubType.IRON_5,
    ClubType.IRON_6,
    ClubType.IRON_7,
    ClubType.IRON_8,
    ClubType.IRON_9,
    ClubType.PW,
    ClubType.GW,
    ClubType.SW,
    ClubType.LW,
]

CLUB_CATEGORIES = [WOODS, HYBRIDS, IRONS_AND_WEDGES]


class TestClubDataCompleteness:
    """Verify that all enum members are defined and non-empty."""

    def test_all_club_types_in_profiles(self):
        """Every ClubType member must have a corresponding ClubProfile."""
        for club in ClubType:
            assert club in CLUB_PROFILES, f"Missing ClubProfile for {club}"
            profile = CLUB_PROFILES[club]
            assert isinstance(profile, ClubProfile)
            assert profile.club_type == club
            assert isinstance(profile.name, str) and len(profile.name) > 0

    def test_club_type_values_distinct(self):
        """All enum values must be unique non-empty strings."""
        values = [c.value for c in ClubType]
        assert len(values) == len(set(values))
        for v in values:
            assert isinstance(v, str) and len(v) > 0

    def test_profile_count_matches_enum_count(self):
        """No orphan or extra entries in CLUB_PROFILES."""
        assert len(CLUB_PROFILES) == len(ClubType)

    def test_get_club_profile_fallback(self):
        """None or unknown inputs must safely fall back to ClubType.UNKNOWN profile."""
        unknown_prof = CLUB_PROFILES[ClubType.UNKNOWN]
        assert get_club_profile(None) == unknown_prof
        assert get_club_profile(ClubType.UNKNOWN) == unknown_prof

    def test_get_club_profile_valid(self):
        """get_club_profile returns the exact profile for valid ClubType."""
        for club in ClubType:
            assert get_club_profile(club) == CLUB_PROFILES[club]


class TestClubDataRangesAndSanity:
    """Physical parameter bounds and monotonic progression tests."""

    @pytest.mark.parametrize("club", list(ClubType))
    def test_physical_ranges(self, club: ClubType):
        """Verify reasonable physical boundaries for all clubs."""
        prof = CLUB_PROFILES[club]

        # Smash factor: theoretical upper bound ~1.50 (CoR 0.83), minimum wedge ~1.15
        assert 1.15 <= prof.optimal_smash <= 1.50

        # Launch angle: driver ~11 deg, lob wedge ~35 deg
        assert 5.0 <= prof.optimal_launch_deg <= 45.0

        # Typical spin: driver ~2700 rpm, lob wedge ~10500 rpm
        assert 1500.0 <= prof.typical_spin_rpm <= 15000.0

        # Average ball speed: driver ~143 mph, lob wedge ~70 mph
        assert 50.0 <= prof.avg_ball_speed_mph <= 180.0

        # Degree deviation per mph: between 0.10 and 0.40
        assert 0.10 <= prof.deg_per_mph_deviation <= 0.40

        # Spin multiplier: driver is 1.0, wedges up to 5.0
        assert 1.0 <= prof.spin_multiplier <= 5.0

        # Statistical std deviations
        assert prof.speed_std_dev_mph > 0
        assert prof.spin_std_dev_rpm > 0
        assert prof.launch_std_dev_deg > 0

    def test_progression_smash_factor_within_categories(self):
        """Smash factor should monotonically decrease or stay flat within each club category."""
        for category in CLUB_CATEGORIES:
            for i in range(len(category) - 1):
                c_curr = category[i]
                c_next = category[i + 1]
                smash_curr = CLUB_PROFILES[c_curr].optimal_smash
                smash_next = CLUB_PROFILES[c_next].optimal_smash
                assert smash_curr >= smash_next, (
                    f"Smash factor increased from {c_curr.name} ({smash_curr}) to {c_next.name} ({smash_next})"
                )

    def test_progression_launch_angle_within_categories(self):
        """Launch angle should monotonically increase within each club category."""
        for category in CLUB_CATEGORIES:
            for i in range(len(category) - 1):
                c_curr = category[i]
                c_next = category[i + 1]
                la_curr = CLUB_PROFILES[c_curr].optimal_launch_deg
                la_next = CLUB_PROFILES[c_next].optimal_launch_deg
                assert la_curr <= la_next, (
                    f"Launch angle decreased from {c_curr.name} ({la_curr}) to {c_next.name} ({la_next})"
                )

    def test_progression_spin_within_categories(self):
        """Typical spin should monotonically increase within each club category."""
        for category in CLUB_CATEGORIES:
            for i in range(len(category) - 1):
                c_curr = category[i]
                c_next = category[i + 1]
                sp_curr = CLUB_PROFILES[c_curr].typical_spin_rpm
                sp_next = CLUB_PROFILES[c_next].typical_spin_rpm
                assert sp_curr <= sp_next, (
                    f"Spin decreased from {c_curr.name} ({sp_curr}) to {c_next.name} ({sp_next})"
                )

    def test_progression_ball_speed_within_categories(self):
        """Ball speed should monotonically decrease within each club category."""
        for category in CLUB_CATEGORIES:
            for i in range(len(category) - 1):
                c_curr = category[i]
                c_next = category[i + 1]
                bs_curr = CLUB_PROFILES[c_curr].avg_ball_speed_mph
                bs_next = CLUB_PROFILES[c_next].avg_ball_speed_mph
                assert bs_curr >= bs_next, (
                    f"Ball speed increased from {c_curr.name} ({bs_curr}) to {c_next.name} ({bs_next})"
                )

    def test_extremes_driver_vs_lob_wedge(self):
        """Driver must have highest ball speed/smash and lowest launch/spin compared to wedges."""
        driver = CLUB_PROFILES[ClubType.DRIVER]
        lw = CLUB_PROFILES[ClubType.LW]
        assert driver.optimal_smash > lw.optimal_smash
        assert driver.avg_ball_speed_mph > lw.avg_ball_speed_mph
        assert driver.optimal_launch_deg < lw.optimal_launch_deg
        assert driver.typical_spin_rpm < lw.typical_spin_rpm


class TestDerivedDictionariesAndHelpers:
    """Verify that all derived dictionaries and helper functions accurately reflect profiles."""

    @pytest.mark.parametrize("club", list(ClubType))
    def test_derived_dictionaries_match_profiles(self, club: ClubType):
        """Derived dicts must match individual profile attributes exactly."""
        prof = CLUB_PROFILES[club]

        assert OPTIMAL_SMASH[club] == prof.optimal_smash
        assert OPTIMAL_LAUNCH[club] == prof.optimal_launch_deg
        assert CLUB_TYPICAL_SPIN_RPM[club] == prof.typical_spin_rpm
        assert CLUB_SPIN_MULTIPLIERS[club] == prof.spin_multiplier
        assert CLUB_LAUNCH_MODEL[club] == (
            prof.optimal_launch_deg,
            prof.avg_ball_speed_mph,
            prof.deg_per_mph_deviation,
        )
        assert CLUB_BALL_SPEEDS[club] == (
            prof.avg_ball_speed_mph,
            prof.speed_std_dev_mph,
            prof.optimal_smash,
        )
        assert CLUB_SPIN[club] == (prof.typical_spin_rpm, prof.spin_std_dev_rpm)
        assert CLUB_LAUNCH[club] == (prof.optimal_launch_deg, prof.launch_std_dev_deg)

    def test_helper_functions_with_club(self):
        """Helper functions return exact profile fields."""
        driver_prof = CLUB_PROFILES[ClubType.DRIVER]
        assert get_optimal_smash(ClubType.DRIVER) == driver_prof.optimal_smash
        assert get_optimal_launch(ClubType.DRIVER) == driver_prof.optimal_launch_deg
        assert get_typical_spin(ClubType.DRIVER) == driver_prof.typical_spin_rpm
        assert get_spin_multiplier(ClubType.DRIVER) == driver_prof.spin_multiplier
        assert get_club_launch_model(ClubType.DRIVER) == (
            driver_prof.optimal_launch_deg,
            driver_prof.avg_ball_speed_mph,
            driver_prof.deg_per_mph_deviation,
        )

    def test_helper_functions_with_none(self):
        """Helper functions with None default to UNKNOWN club profile."""
        unk_prof = CLUB_PROFILES[ClubType.UNKNOWN]
        assert get_optimal_smash(None) == unk_prof.optimal_smash
        assert get_optimal_launch(None) == unk_prof.optimal_launch_deg
        assert get_typical_spin(None) == unk_prof.typical_spin_rpm
        assert get_spin_multiplier(None) == unk_prof.spin_multiplier
        assert get_club_launch_model(None) == (
            unk_prof.optimal_launch_deg,
            unk_prof.avg_ball_speed_mph,
            unk_prof.deg_per_mph_deviation,
        )


class TestAntiDivergenceAcrossConsumers:
    """Ensure all consumers and mock models use the canonical data source."""

    def test_server_optimal_smash_is_canonical(self):
        """server._OPTIMAL_SMASH must be identical to canonical OPTIMAL_SMASH."""
        assert SERVER_OPTIMAL_SMASH is OPTIMAL_SMASH

    def test_server_launch_model_is_canonical(self):
        """server._CLUB_LAUNCH_MODEL must be identical to canonical CLUB_LAUNCH_MODEL."""
        assert SERVER_LAUNCH_MODEL is CLUB_LAUNCH_MODEL

    def test_mock_launch_monitor_tables_are_canonical(self):
        """MockLaunchMonitor tables must be identical to canonical tables."""
        assert MockLaunchMonitor._CLUB_BALL_SPEEDS is CLUB_BALL_SPEEDS
        assert MockLaunchMonitor._CLUB_SPIN is CLUB_SPIN
        assert MockLaunchMonitor._CLUB_LAUNCH is CLUB_LAUNCH

    def test_ballistics_spin_is_canonical(self):
        """ballistics.CLUB_TYPICAL_SPIN_RPM must be identical to canonical CLUB_TYPICAL_SPIN_RPM."""
        assert BALLISTICS_SPIN_RPM is CLUB_TYPICAL_SPIN_RPM

    def test_launch_monitor_optimal_launch_is_canonical(self):
        """launch_monitor._OPTIMAL_LAUNCH must be identical to canonical OPTIMAL_LAUNCH."""
        assert LM_OPTIMAL_LAUNCH is OPTIMAL_LAUNCH

    def test_sim_resolver_tables_are_canonical(self):
        """sim.resolver tables must be identical to canonical tables."""
        assert SIM_SPIN_MODEL_RPM is CLUB_TYPICAL_SPIN_RPM
        assert SIM_OPTIMAL_LAUNCH is OPTIMAL_LAUNCH

    def test_rolling_buffer_uses_canonical_spin_multiplier(self):
        """get_optimal_spin_for_ball_speed must use canonical spin multipliers."""
        driver_spin = get_optimal_spin_for_ball_speed(150.0, ClubType.DRIVER)
        iron7_spin = get_optimal_spin_for_ball_speed(150.0, ClubType.IRON_7)
        expected_ratio = CLUB_PROFILES[ClubType.IRON_7].spin_multiplier
        assert iron7_spin == pytest.approx(driver_spin * expected_ratio, rel=1e-5)

    def test_rolling_buffer_uses_canonical_optimal_smash(self):
        """estimate_carry_with_spin must use canonical optimal smash factor."""
        # 140 mph ball speed, 2700 rpm spin, driver at optimal smash 1.48
        optimal_carry = estimate_carry_with_spin(
            140.0, 2700.0, club=ClubType.DRIVER, club_speed_mph=140.0 / 1.48
        )
        # Below optimal smash: club_speed higher than needed -> lower smash factor
        suboptimal_carry = estimate_carry_with_spin(
            140.0, 2700.0, club=ClubType.DRIVER, club_speed_mph=110.0
        )
        assert suboptimal_carry < optimal_carry


class TestCanonicalNumericEvidence:
    """Assert on specific values from Issue #18 to prevent regression."""

    def test_previously_diverged_smash_values(self):
        """WOOD_7=1.42, HYBRID_5=1.38, HYBRID_7=1.37, DRIVER=1.48 across all subsystems."""
        assert OPTIMAL_SMASH[ClubType.DRIVER] == 1.48
        assert OPTIMAL_SMASH[ClubType.WOOD_7] == 1.42
        assert OPTIMAL_SMASH[ClubType.HYBRID_5] == 1.38
        assert OPTIMAL_SMASH[ClubType.HYBRID_7] == 1.37
        assert OPTIMAL_SMASH[ClubType.IRON_7] == 1.34
        assert OPTIMAL_SMASH[ClubType.PW] == 1.25

    def test_canonical_launch_angles(self):
        """Verify baseline launch angles for key clubs."""
        assert OPTIMAL_LAUNCH[ClubType.DRIVER] == 11.0
        assert OPTIMAL_LAUNCH[ClubType.IRON_7] == 20.5
        assert OPTIMAL_LAUNCH[ClubType.PW] == 28.0
        assert OPTIMAL_LAUNCH[ClubType.LW] == 35.0

    def test_canonical_spin_rates(self):
        """Verify baseline spin rates for key clubs."""
        assert CLUB_TYPICAL_SPIN_RPM[ClubType.DRIVER] == 2700.0
        assert CLUB_TYPICAL_SPIN_RPM[ClubType.IRON_7] == 6500.0
        assert CLUB_TYPICAL_SPIN_RPM[ClubType.PW] == 9000.0
        assert CLUB_TYPICAL_SPIN_RPM[ClubType.LW] == 10500.0
