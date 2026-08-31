"""Unit tests for modular server subsystems (handlers, shot_processor, connection_manager)."""

from datetime import datetime

from openflight.club_data import ClubType
from openflight.launch_monitor import Shot
from openflight.server import connection_manager, handlers, shot_processor


class TestModularSubsystemsArchitecture:
    """Tests verifying Law of Demeter and modular isolation of server subsystems."""

    def test_shot_processor_estimate_launch_angle(self):
        """shot_processor handles angle estimation independently."""
        angle, conf = shot_processor.estimate_launch_angle(ClubType.DRIVER, 150.0, 100.0)
        assert isinstance(angle, float)
        assert isinstance(conf, float)
        assert angle > 0.0
        assert 0.0 <= conf <= 1.0

    def test_shot_processor_radar_launch_is_plausible(self):
        """shot_processor performs plausibility filtering."""
        plausible, details = shot_processor.radar_launch_is_plausible(14.0, ClubType.DRIVER, 150.0)
        assert plausible is True
        assert details["skipped"] is False

    def test_shot_processor_shot_to_dict_structure(self):
        """shot_processor serializes shots cleanly."""
        shot = Shot(
            ball_speed_mph=120.5,
            club_speed_mph=85.0,
            timestamp=datetime.now(),
            club=ClubType.IRON_7,
            launch_angle_vertical=18.0,
            launch_angle_horizontal=1.2,
        )
        d = shot_processor.shot_to_dict(shot)
        assert d["ball_speed_mph"] == 120.5
        assert d["club"] == "7-iron"
        assert d["launch_angle_vertical"] == 18.0
        assert d["launch_angle_horizontal"] == 1.2

    def test_handlers_session_shots_empty_when_no_monitor(self, monkeypatch):
        """handlers._session_shots handles absent monitor without throwing."""
        import openflight.server as srv

        monkeypatch.setattr(srv, "monitor", None)
        assert handlers._session_shots() == []

    def test_handlers_delete_session_row_nonexistent_returns_false(self, monkeypatch):
        """handlers._delete_session_row returns False for unknown timestamp."""
        import openflight.server as srv

        monkeypatch.setattr(srv, "monitor", None)
        assert handlers._delete_session_row("nonexistent") is False

    def test_connection_manager_forward_shot_skips_when_no_active_sims(self, monkeypatch):
        """connection_manager._forward_shot_to_simulators skips when no sim is connected."""
        import openflight.server as srv

        monkeypatch.setattr(srv, "sim_connectors", [])
        shot = Shot(ball_speed_mph=100.0, timestamp=datetime.now(), club=ClubType.IRON_7)
        connection_manager._forward_shot_to_simulators(shot)
