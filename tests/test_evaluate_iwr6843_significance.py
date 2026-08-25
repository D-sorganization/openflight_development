"""Unit tests for evaluate_iwr6843_significance script."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

_script_path = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "analysis"
    / "evaluate_iwr6843_significance.py"
)
_spec = importlib.util.spec_from_file_location(
    "evaluate_iwr6843_significance", _script_path
)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Could not load module from {_script_path}")
evaluate_iwr6843_significance = importlib.util.module_from_spec(_spec)
sys.modules["evaluate_iwr6843_significance"] = evaluate_iwr6843_significance
_spec.loader.exec_module(evaluate_iwr6843_significance)

AccuracyBenchmark = evaluate_iwr6843_significance.AccuracyBenchmark
AngleSourceSplit = evaluate_iwr6843_significance.AngleSourceSplit
ClubAccuracyMetric = evaluate_iwr6843_significance.ClubAccuracyMetric
RadarComparisonReport = evaluate_iwr6843_significance.RadarComparisonReport
RadarTechSpecs = evaluate_iwr6843_significance.RadarTechSpecs
draft_discussion_161_response = (
    evaluate_iwr6843_significance.draft_discussion_161_response
)
format_markdown_report = evaluate_iwr6843_significance.format_markdown_report
generate_comparison_report = evaluate_iwr6843_significance.generate_comparison_report
get_iwr6843_accuracy = evaluate_iwr6843_significance.get_iwr6843_accuracy
get_iwr6843_specs = evaluate_iwr6843_significance.get_iwr6843_specs
get_kld7_accuracy = evaluate_iwr6843_significance.get_kld7_accuracy
get_kld7_specs = evaluate_iwr6843_significance.get_kld7_specs


class TestRadarSpecifications:
    """Test hardware and physical RF specs."""

    def test_kld7_specs(self) -> None:
        specs = get_kld7_specs()
        assert specs.rf_frequency_ghz == 24.125
        assert specs.rx_antennas == 2
        assert specs.tx_antennas == 1
        assert specs.hardware_units_needed == 2
        assert "Same 24 GHz" in specs.ops243_rf_interference_risk

    def test_iwr6843_specs(self) -> None:
        specs = get_iwr6843_specs()
        assert specs.rf_frequency_ghz == 60.0
        assert specs.rx_antennas == 4
        assert specs.tx_antennas == 3
        assert specs.virtual_channels == 12
        assert specs.hardware_units_needed == 1
        assert "Zero cross-talk" in specs.ops243_rf_interference_risk


class TestAccuracyBenchmarks:
    """Test accuracy numbers, club breakdowns, and improvement factors."""

    def test_iron_accuracy_improvement(self) -> None:
        kld7_acc = get_kld7_accuracy()
        iwr_acc = get_iwr6843_accuracy()

        assert iwr_acc.iron_launch_angle_mae_deg < 1.0
        assert iwr_acc.iron_launch_angle_mae_deg < kld7_acc.iron_launch_angle_mae_deg
        assert iwr_acc.club_path_supported is True
        assert kld7_acc.club_path_supported is False

    def test_per_club_breakdown_metrics(self) -> None:
        iwr_acc = get_iwr6843_accuracy()
        assert len(iwr_acc.per_club_breakdown) >= 5

        sw = next(c for c in iwr_acc.per_club_breakdown if c.club_name == "Sand Wedge")
        assert sw.mae_deg == 0.67
        assert sw.coverage_pct > 85.0

        d_gated = next(
            c
            for c in iwr_acc.per_club_breakdown
            if c.club_name == "Driver (Speed-Gated)"
        )
        assert d_gated.mae_deg == 1.42
        assert d_gated.mae_deg < iwr_acc.driver_launch_angle_mae_deg

    def test_angle_source_splits(self) -> None:
        iwr_acc = get_iwr6843_accuracy()
        assert len(iwr_acc.angle_source_splits) >= 4

        strict = next(
            s for s in iwr_acc.angle_source_splits if "Strict LCMF-v1" in s.mode_name
        )
        assert strict.coverage_pct >= 85.0
        assert strict.mae_deg <= 0.85
        assert "3 dots" in strict.ui_indicator

    def test_comparison_report_generation(self) -> None:
        report = generate_comparison_report()
        assert report.iron_accuracy_improvement_factor >= 2.0
        assert report.driver_accuracy_improvement_factor >= 3.0
        assert report.is_upgrade_recommended is True
        assert len(report.key_findings) >= 5
        assert len(report.drafted_discussion_response) > 100


class TestDraftedDiscussionResponse:
    """Test drafted upstream discussion response content."""

    def test_discussion_response_contains_key_data(self) -> None:
        report = generate_comparison_report()
        resp = report.drafted_discussion_response

        assert "TI IWR6843" in resp
        assert "0.83°" in resp
        assert "2.14°" in resp
        assert "60 GHz" in resp
        assert "Sand Wedge" in resp
        assert "Driver (Speed-Gated)" in resp
        assert "Practical Recommendation" in resp


class TestReportFormattingAndCli:
    """Test formatting and CLI execution."""

    def test_markdown_report_formatting(self) -> None:
        report = generate_comparison_report()
        md = format_markdown_report(report)
        assert "# Technical Evaluation: TI IWR6843 (60 GHz) vs K-LD7 (24 GHz)" in md
        assert "Discussion #161" in md
        assert "Hardware & RF Physical Comparison" in md
        assert "Empirical Accuracy & Field Benchmark Data" in md
        assert "Per-Club Accuracy Breakdown" in md
        assert "Angle Source & Confidence Tier Split" in md
        assert "Drafted Response for Upstream Discussion #161" in md

    def test_cli_execution_markdown_and_json(self, monkeypatch) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_md = Path(tmpdir) / "comp.md"
            out_json = Path(tmpdir) / "comp.json"

            # Test Markdown output
            monkeypatch.setattr(
                "sys.argv",
                [
                    "evaluate_iwr6843_significance.py",
                    "--output",
                    str(out_md),
                    "--format",
                    "markdown",
                ],
            )
            evaluate_iwr6843_significance.main()
            assert out_md.exists()
            assert "TI IWR6843" in out_md.read_text(encoding="utf-8")

            # Test JSON output
            monkeypatch.setattr(
                "sys.argv",
                [
                    "evaluate_iwr6843_significance.py",
                    "--output",
                    str(out_json),
                    "--format",
                    "json",
                ],
            )
            evaluate_iwr6843_significance.main()
            assert out_json.exists()
            data = json.loads(out_json.read_text(encoding="utf-8"))
            assert data["is_upgrade_recommended"] is True
            assert "iwr6843_specs" in data
            assert len(data["iwr6843_accuracy"]["per_club_breakdown"]) >= 5
