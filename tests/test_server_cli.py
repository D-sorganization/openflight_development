"""Unit tests for server CLI argument parsing and validation."""

import pytest

from openflight.server import build_parser, validate_args


class TestServerCLIParser:
    """Tests for build_parser() and validate_args() without running the server."""

    def test_build_parser_returns_argument_parser(self):
        """build_parser() returns a valid ArgumentParser instance."""
        parser = build_parser()
        assert parser is not None
        assert parser.description == "OpenFlight UI Server"

    def test_default_cli_arguments(self):
        """Default arguments match production defaults."""
        parser = build_parser()
        args = parser.parse_args([])
        assert args.host == "0.0.0.0"
        assert args.web_port == 8080
        assert args.mock is False
        assert args.swing_speed is False
        assert args.ballistics is True
        assert args.iwr6843 is False
        assert args.kld7 is False
        assert args.kld7_horizontal is False
        assert args.sample_rate == 30
        assert args.trigger == "polling"

    def test_kld7_requires_mount_tilt(self):
        """--kld7 without --kld7-mount-tilt fails validation."""
        parser = build_parser()
        args = parser.parse_args(["--kld7"])
        with pytest.raises(SystemExit):
            validate_args(args, parser)

    def test_kld7_with_mount_tilt_passes_validation(self):
        """--kld7 with --kld7-mount-tilt passes validation."""
        parser = build_parser()
        args = parser.parse_args(["--kld7", "--kld7-mount-tilt", "18.0"])
        validate_args(args, parser)
        assert args.kld7 is True
        assert args.kld7_mount_tilt == 18.0

    def test_iwr6843_and_kld7_mutual_exclusion(self):
        """--iwr6843 and --kld7 cannot both be active."""
        parser = build_parser()
        args = parser.parse_args(["--iwr6843", "--kld7", "--kld7-mount-tilt", "18.0"])
        with pytest.raises(SystemExit):
            validate_args(args, parser)

    def test_inclinometer_requires_iwr6843(self):
        """--inclinometer without --iwr6843 fails validation."""
        parser = build_parser()
        args = parser.parse_args(["--inclinometer"])
        with pytest.raises(SystemExit):
            validate_args(args, parser)

    def test_mock_swing_speed_sets_both_modes(self):
        """--mock-swing-speed enables mock and swing_speed modes."""
        parser = build_parser()
        args = parser.parse_args(["--mock-swing-speed"])
        validate_args(args, parser)
        assert args.mock is True
        assert args.swing_speed is True

    def test_unsupported_ops_baud_rejected(self):
        """Unsupported ops baud is rejected."""
        parser = build_parser()
        args = parser.parse_args(["--ops-baud", "999999"])
        with pytest.raises(SystemExit):
            validate_args(args, parser)
