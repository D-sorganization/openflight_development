"""Unit tests for the Rapsodo MLM2 Pro CSV adapter and compare_trackman integration."""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "analysis"))

import compare_trackman as ct  # noqa: E402
import mlm2pro_adapter as adapter  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_csv(path: Path, headers: list[str], rows: list[dict[str, str]]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def _write_openflight_jsonl(path: Path, shots: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for shot in shots:
            fh.write(
                json.dumps(
                    {
                        "type": "shot_detected",
                        "timestamp": shot["timestamp"],
                        "data": {k: v for k, v in shot.items() if k != "timestamp"},
                    }
                )
                + "\n"
            )


# ---------------------------------------------------------------------------
# Header Mapping & Detection
# ---------------------------------------------------------------------------


class TestHeaderMapping:
    def test_standard_mlm2pro_headers_resolve(self):
        headers = [
            "Shot Number",
            "Date/Time",
            "Club Type",
            "Ball Speed (mph)",
            "Club Speed (mph)",
            "Launch Angle (deg)",
            "Launch Direction (deg)",
            "Total Spin (rpm)",
            "Spin Axis (deg)",
            "Carry Distance (yds)",
            "Total Distance (yds)",
            "Apex (ft)",
            "Descent Angle (deg)",
            "Side Carry (yds)",
            "Smash Factor",
        ]
        col_map = adapter.build_column_map(headers)
        assert col_map["shot_number"] == "Shot Number"
        assert col_map["timestamp"] == "Date/Time"
        assert col_map["club"] == "Club Type"
        assert col_map["ball_speed"] == "Ball Speed (mph)"
        assert col_map["club_speed"] == "Club Speed (mph)"
        assert col_map["launch_angle_vertical"] == "Launch Angle (deg)"
        assert col_map["launch_angle_horizontal"] == "Launch Direction (deg)"
        assert col_map["total_spin"] == "Total Spin (rpm)"
        assert col_map["spin_axis"] == "Spin Axis (deg)"
        assert col_map["carry_distance"] == "Carry Distance (yds)"
        assert col_map["total_distance"] == "Total Distance (yds)"
        assert col_map["apex"] == "Apex (ft)"
        assert col_map["descent_angle"] == "Descent Angle (deg)"
        assert col_map["side_carry"] == "Side Carry (yds)"
        assert col_map["smash_factor"] == "Smash Factor"

    def test_alternate_headers_resolve(self):
        headers = [
            "Shot #",
            "DateTime",
            "Club",
            "BallSpeed",
            "ClubHeadSpeed",
            "Vertical Launch Angle",
            "Horizontal Launch Angle",
            "Spin Rate",
            "Tilt Angle",
            "Estimated Carry",
            "Smash Ratio",
            "Max Height",
            "Lateral",
        ]
        col_map = adapter.build_column_map(headers)
        assert col_map["shot_number"] == "Shot #"
        assert col_map["timestamp"] == "DateTime"
        assert col_map["club"] == "Club"
        assert col_map["ball_speed"] == "BallSpeed"
        assert col_map["club_speed"] == "ClubHeadSpeed"
        assert col_map["launch_angle_vertical"] == "Vertical Launch Angle"
        assert col_map["launch_angle_horizontal"] == "Horizontal Launch Angle"
        assert col_map["total_spin"] == "Spin Rate"
        assert col_map["spin_axis"] == "Tilt Angle"
        assert col_map["carry_distance"] == "Estimated Carry"
        assert col_map["smash_factor"] == "Smash Ratio"
        assert col_map["apex"] == "Max Height"
        assert col_map["side_carry"] == "Lateral"

    def test_unit_detection_mps_and_meters(self):
        headers = ["Ball Speed (m/s)", "Club Speed (m/s)", "Carry Distance (m)", "Apex (m)"]
        units = adapter.detect_units(headers)
        assert units["ball_speed"] == "mps"
        assert units["club_speed"] == "mps"
        assert units["carry"] == "meters"
        assert units["apex"] == "meters"

    def test_unit_detection_kph(self):
        headers = ["Ball Speed (km/h)", "Club Speed (kph)", "Carry (yds)"]
        units = adapter.detect_units(headers)
        assert units["ball_speed"] == "kph"
        assert units["club_speed"] == "kph"
        assert units["carry"] == "yards"


# ---------------------------------------------------------------------------
# Club Name Normalization
# ---------------------------------------------------------------------------


class TestNormalizeClub:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("7 Iron", "7-iron"),
            ("7-Iron", "7-iron"),
            ("7i", "7-iron"),
            ("Iron 7", "7-iron"),
            ("Driver", "driver"),
            ("DRV", "driver"),
            ("1W", "driver"),
            ("1 Wood", "driver"),
            ("3 Wood", "3-wood"),
            ("3W", "3-wood"),
            ("4 Hybrid", "4-hybrid"),
            ("4H", "4-hybrid"),
            ("PW", "pw"),
            ("Pitching Wedge", "pw"),
            ("GW", "gw"),
            ("Gap Wedge", "gw"),
            ("AW", "gw"),
            ("Approach Wedge", "gw"),
            ("SW", "sw"),
            ("Sand Wedge", "sw"),
            ("LW", "lw"),
            ("Lob Wedge", "lw"),
        ],
    )
    def test_normalize_club_aliases(self, raw, expected):
        assert adapter.normalize_club(raw) == expected

    def test_normalize_club_empty(self):
        assert adapter.normalize_club("") == ""
        assert adapter.normalize_club(None) == ""


# ---------------------------------------------------------------------------
# Directional Angle & Numeric Parsing
# ---------------------------------------------------------------------------


class TestAngleAndValueParsing:
    @pytest.mark.parametrize(
        "val,expected",
        [
            ("2.5 R", 2.5),
            ("R 2.5", 2.5),
            ("+2.5", 2.5),
            ("2.5° R", 2.5),
            ("1.8 L", -1.8),
            ("L 1.8", -1.8),
            ("-1.8", -1.8),
            ("1.8° L", -1.8),
            ("15.3", 15.3),
            ("15.3°", 15.3),
            ("15.3 deg", 15.3),
            ("0", 0.0),
            ("0.0", 0.0),
            ("Straight", 0.0),
            ("", None),
            (None, None),
            ("-", None),
            ("--", None),
            ("N/A", None),
            ("NaN", None),
            ("invalid", None),
        ],
    )
    def test_parse_directional_angle(self, val, expected):
        if expected is None:
            assert adapter.parse_directional_angle(val) is None
        else:
            assert adapter.parse_directional_angle(val) == pytest.approx(expected)

    def test_parse_timestamp_formats(self):
        assert adapter.parse_timestamp("2026-05-06 10:30:00") == datetime(2026, 5, 6, 10, 30, 0)
        assert adapter.parse_timestamp("2026-05-06T10:30:00") == datetime(2026, 5, 6, 10, 30, 0)
        assert adapter.parse_timestamp("5/6/2026 6:58:02 PM") == datetime(2026, 5, 6, 18, 58, 2)
        assert adapter.parse_timestamp("05/06/2026 18:58:02") == datetime(2026, 5, 6, 18, 58, 2)
        assert adapter.parse_timestamp("") is None
        assert adapter.parse_timestamp("N/A") is None


# ---------------------------------------------------------------------------
# Unit Conversions & Missing Metric Guards
# ---------------------------------------------------------------------------


class TestLoadMlm2pro:
    def test_basic_load_and_conversion(self, tmp_path):
        path = tmp_path / "mlm2pro.csv"
        _write_csv(
            path,
            [
                "Shot Number",
                "Date/Time",
                "Club Type",
                "Ball Speed (mph)",
                "Club Speed (mph)",
                "Launch Angle (deg)",
                "Launch Direction (deg)",
                "Total Spin (rpm)",
                "Spin Axis (deg)",
                "Carry Distance (yds)",
                "Total Distance (yds)",
                "Apex (ft)",
                "Smash Factor",
            ],
            [
                {
                    "Shot Number": "1",
                    "Date/Time": "2026-05-06 10:00:00",
                    "Club Type": "7 Iron",
                    "Ball Speed (mph)": "120.5",
                    "Club Speed (mph)": "85.0",
                    "Launch Angle (deg)": "17.5",
                    "Launch Direction (deg)": "1.2 R",
                    "Total Spin (rpm)": "6,800",
                    "Spin Axis (deg)": "2.4 R",
                    "Carry Distance (yds)": "165.3",
                    "Total Distance (yds)": "175.0",
                    "Apex (ft)": "88.0",
                    "Smash Factor": "1.418",
                }
            ],
        )

        shots = adapter.load_mlm2pro(path)
        assert len(shots) == 1
        s = shots[0]
        assert s.shot_number == 1
        assert s.club == "7-iron"
        assert s.ball_speed_mph == pytest.approx(120.5)
        assert s.club_speed_mph == pytest.approx(85.0)
        assert s.launch_angle_vertical == pytest.approx(17.5)
        assert s.launch_angle_horizontal == pytest.approx(1.2)
        assert s.spin_rpm == pytest.approx(6800.0)
        assert s.spin_axis_deg == pytest.approx(2.4)
        assert s.carry_yards == pytest.approx(165.3)
        assert s.total_yards == pytest.approx(175.0)
        assert s.apex_feet == pytest.approx(88.0)
        assert s.smash_factor == pytest.approx(1.418)

    def test_metric_conversions_mps_and_meters(self, tmp_path):
        path = tmp_path / "mlm2pro_metric.csv"
        _write_csv(
            path,
            [
                "Shot Number",
                "Date/Time",
                "Club",
                "Ball Speed (m/s)",
                "Club Speed (m/s)",
                "Carry Distance (m)",
                "Total Distance (m)",
                "Apex (m)",
            ],
            [
                {
                    "Shot Number": "1",
                    "Date/Time": "2026-05-06 10:00:00",
                    "Club": "Driver",
                    "Ball Speed (m/s)": "70.0",  # 70 m/s * 2.236936 = 156.5855 mph
                    "Club Speed (m/s)": "48.0",  # 48 m/s * 2.236936 = 107.3729 mph
                    "Carry Distance (m)": "220.0",  # 220 m * 1.093613 = 240.595 yards
                    "Total Distance (m)": "240.0",
                    "Apex (m)": "30.0",  # 30 m * 3.28084 = 98.425 ft
                }
            ],
        )

        shots = adapter.load_mlm2pro(path)
        assert len(shots) == 1
        s = shots[0]
        assert s.ball_speed_mph == pytest.approx(156.5855, abs=0.01)
        assert s.club_speed_mph == pytest.approx(107.3729, abs=0.01)
        assert s.carry_yards == pytest.approx(240.595, abs=0.01)
        assert s.apex_feet == pytest.approx(98.425, abs=0.05)
        # Smash factor computed automatically from converted speeds
        assert s.smash_factor == pytest.approx(156.5855 / 107.3729, abs=0.01)

    def test_missing_and_unmeasured_metrics_graceful(self, tmp_path):
        path = tmp_path / "mlm2pro_missing.csv"
        _write_csv(
            path,
            [
                "Shot Number",
                "Club",
                "Ball Speed",
                "Club Speed",
                "Launch Angle",
                "Launch Direction",
                "Total Spin",
                "Spin Axis",
                "Carry Distance",
                "Smash Factor",
            ],
            [
                {
                    "Shot Number": "",  # missing shot number -> auto-assigned 1
                    "Club": "",  # missing club -> default fallback
                    "Ball Speed": "118.0",
                    "Club Speed": "80.0",
                    "Launch Angle": "16.0",
                    "Launch Direction": "-",  # unmeasured -> None
                    "Total Spin": "N/A",  # unmeasured -> None
                    "Spin Axis": "NaN",  # unmeasured -> None
                    "Carry Distance": "",  # missing -> None
                    "Smash Factor": "",  # missing -> auto computed
                },
                {
                    "Shot Number": "",  # auto-assigned 2
                    "Club": "Driver",
                    "Ball Speed": "160.0",
                    "Club Speed": "",  # missing -> smash factor None
                    "Launch Angle": "11.0",
                    "Launch Direction": "0.5 L",
                    "Total Spin": "2600",
                    "Spin Axis": "-1.5",
                    "Carry Distance": "250.0",
                    "Smash Factor": "",
                },
            ],
        )

        shots = adapter.load_mlm2pro(path, default_club="7-iron")
        assert len(shots) == 2

        s1 = shots[0]
        assert s1.shot_number == 1
        assert s1.club == "7-iron"
        assert s1.ball_speed_mph == pytest.approx(118.0)
        assert s1.launch_angle_horizontal is None
        assert s1.spin_rpm is None
        assert s1.spin_axis_deg is None
        assert s1.carry_yards is None
        assert s1.smash_factor == pytest.approx(118.0 / 80.0, abs=0.001)

        s2 = shots[1]
        assert s2.shot_number == 2
        assert s2.club == "driver"
        assert s2.launch_angle_horizontal == pytest.approx(-0.5)
        assert s2.spin_rpm == pytest.approx(2600.0)
        assert s2.spin_axis_deg == pytest.approx(-1.5)
        assert s2.smash_factor is None

    def test_handles_bom_preamble_and_summary_rows(self, tmp_path):
        path = tmp_path / "mlm2pro_with_meta.csv"
        content = (
            "\ufeff\ufeffsep=,\r\n"
            "Session: 2026-05-06 R-Cloud Session\r\n"
            "Player: Test Golfer\r\n"
            "Shot,Date,Time,Club,Ball Speed (mph),Club Speed (mph),Total Spin,Carry\r\n"
            "1,2026-05-06,10:00:01,7 Iron,120.0,84.0,6500,165.0\r\n"
            "2,2026-05-06,10:01:02,7 Iron,122.0,85.0,6600,168.0\r\n"
            "Average,,,7 Iron,121.0,84.5,6550,166.5\r\n"
            "Std Dev,,,7 Iron,1.4,0.7,70,2.1\r\n"
        )
        path.write_text(content, encoding="utf-8", newline="")

        shots = adapter.load_mlm2pro(path)
        # Averages and Std Dev rows must be skipped
        assert len(shots) == 2
        assert shots[0].shot_number == 1
        assert shots[0].timestamp == datetime(2026, 5, 6, 10, 0, 1)
        assert shots[1].shot_number == 2
        assert shots[1].timestamp == datetime(2026, 5, 6, 10, 1, 2)


# ---------------------------------------------------------------------------
# TrackMan CSV Export & compare_trackman Integration
# ---------------------------------------------------------------------------


class TestTrackManExportAndCompareIntegration:
    def test_convert_mlm2pro_csv_to_trackman(self, tmp_path):
        mlm_path = tmp_path / "mlm2pro_session.csv"
        tm_path = tmp_path / "trackman_converted.csv"

        _write_csv(
            mlm_path,
            [
                "Shot Number",
                "Date/Time",
                "Club Type",
                "Ball Speed (mph)",
                "Club Speed (mph)",
                "Launch Angle (deg)",
                "Launch Direction (deg)",
                "Total Spin (rpm)",
                "Spin Axis (deg)",
                "Carry Distance (yds)",
            ],
            [
                {
                    "Shot Number": "1",
                    "Date/Time": "2026-05-06 10:00:00",
                    "Club Type": "7 Iron",
                    "Ball Speed (mph)": "120.0",
                    "Club Speed (mph)": "85.0",
                    "Launch Angle (deg)": "18.0",
                    "Launch Direction (deg)": "0.5 R",
                    "Total Spin (rpm)": "6500",
                    "Spin Axis (deg)": "1.5 R",
                    "Carry Distance (yds)": "162.0",
                },
                {
                    "Shot Number": "2",
                    "Date/Time": "2026-05-06 10:01:00",
                    "Club Type": "Driver",
                    "Ball Speed (mph)": "165.0",
                    "Club Speed (mph)": "110.0",
                    "Launch Angle (deg)": "12.0",
                    "Launch Direction (deg)": "1.0 L",
                    "Total Spin (rpm)": "2800",
                    "Spin Axis (deg)": "2.0 L",
                    "Carry Distance (yds)": "250.0",
                },
            ],
        )

        shots = adapter.convert_mlm2pro_csv_to_trackman(mlm_path, tm_path)
        assert len(shots) == 2
        assert tm_path.exists()

        # Check that TrackMan CSV headers and values match expectations
        with open(tm_path, encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        assert len(rows) == 2
        assert rows[0]["Club"] == "7-iron"
        assert rows[0]["Ball Speed (mph)"] == "120.0"
        assert rows[0]["Launch Direction"] == "0.5"
        assert rows[1]["Club"] == "driver"
        assert rows[1]["Launch Direction"] == "-1.0"

        # Load with compare_trackman's load_trackman
        tm_loaded_shots = ct.load_trackman(tm_path)
        assert len(tm_loaded_shots) == 2
        assert tm_loaded_shots[0].club == "7-iron"
        assert tm_loaded_shots[0].ball_speed_mph == pytest.approx(120.0)
        assert tm_loaded_shots[0].launch_angle_horizontal == pytest.approx(0.5)
        assert tm_loaded_shots[1].club == "driver"
        assert tm_loaded_shots[1].ball_speed_mph == pytest.approx(165.0)
        assert tm_loaded_shots[1].launch_angle_horizontal == pytest.approx(-1.0)

    def test_compare_trackman_with_source_mlm2pro(self, tmp_path, capsys):
        of_path = tmp_path / "of_session.jsonl"
        mlm_path = tmp_path / "mlm2pro_session.csv"
        out_path = tmp_path / "comparison.csv"

        _write_openflight_jsonl(
            of_path,
            [
                {
                    "timestamp": "2026-05-06T10:00:00",
                    "shot_number": 1,
                    "club": "7-iron",
                    "ball_speed_mph": 120.0,
                    "club_speed_mph": 85.0,
                    "launch_angle_vertical": 18.0,
                    "launch_angle_horizontal": 0.5,
                    "spin_rpm": 6500.0,
                    "estimated_carry_yards": 162.0,
                },
                {
                    "timestamp": "2026-05-06T10:01:00",
                    "shot_number": 2,
                    "club": "driver",
                    "ball_speed_mph": 165.0,
                    "club_speed_mph": 110.0,
                    "launch_angle_vertical": 12.0,
                    "launch_angle_horizontal": -1.0,
                    "spin_rpm": 2800.0,
                    "estimated_carry_yards": 250.0,
                },
            ],
        )

        _write_csv(
            mlm_path,
            [
                "Shot Number",
                "Date/Time",
                "Club Type",
                "Ball Speed (mph)",
                "Club Speed (mph)",
                "Launch Angle (deg)",
                "Launch Direction (deg)",
                "Total Spin (rpm)",
                "Carry Distance (yds)",
            ],
            [
                {
                    "Shot Number": "1",
                    "Date/Time": "2026-05-06 10:00:01",
                    "Club Type": "7 Iron",
                    "Ball Speed (mph)": "120.5",
                    "Club Speed (mph)": "85.2",
                    "Launch Angle (deg)": "18.1",
                    "Launch Direction (deg)": "0.6 R",
                    "Total Spin (rpm)": "6550",
                    "Carry Distance (yds)": "163.0",
                },
                {
                    "Shot Number": "2",
                    "Date/Time": "2026-05-06 10:01:01",
                    "Club Type": "Driver",
                    "Ball Speed (mph)": "165.8",
                    "Club Speed (mph)": "110.5",
                    "Launch Angle (deg)": "11.8",
                    "Launch Direction (deg)": "0.9 L",
                    "Total Spin (rpm)": "2780",
                    "Carry Distance (yds)": "252.0",
                },
            ],
        )

        rc = ct.main(
            [
                "--openflight",
                str(of_path),
                "--trackman",
                str(mlm_path),
                "--source",
                "mlm2pro",
                "--output",
                str(out_path),
            ]
        )
        assert rc == 0
        assert out_path.exists()

        with open(out_path, encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        assert len(rows) == 2
        assert all(r["match_quality"] == "good" for r in rows)
        # Delat calculations
        assert float(rows[0]["ball_speed_delta"]) == pytest.approx(-0.8, abs=0.01)
        assert float(rows[1]["ball_speed_delta"]) == pytest.approx(-0.5, abs=0.01)

        out = capsys.readouterr().out
        assert "COMPARISON SUMMARY" in out
        assert "driver" in out
        assert "7-iron" in out

    def test_cli_adapter_execution(self, tmp_path):
        input_csv = tmp_path / "raw_mlm2.csv"
        output_csv = tmp_path / "out_trackman.csv"

        _write_csv(
            input_csv,
            ["Shot Number", "Club Type", "Ball Speed (mph)"],
            [{"Shot Number": "1", "Club Type": "Driver", "Ball Speed (mph)": "150.0"}],
        )

        rc = adapter.main(["--input", str(input_csv), "--output", str(output_csv)])
        assert rc == 0
        assert output_csv.exists()
