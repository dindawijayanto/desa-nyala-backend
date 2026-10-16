from types import SimpleNamespace

from app.services.offgridders_adapter import _apply_stability_warnings


def _scenario(scenario_id: str):
    return SimpleNamespace(
        scenario_id=scenario_id,
        status="optimal",
        validation=SimpleNamespace(warnings=[]),
    )


def test_stability_warning_only_downgrades_native_case():
    rows = [
        _scenario("diesel_only"),
        _scenario("pv_diesel"),
        _scenario("pv_diesel_battery"),
    ]
    native_log = """
INFO - cli - Starting simulation of case diesel_mg, project site desanyala_site, experiment no. 1/3...
DEBUG - G2b_constraints_custom - Stability criterion is fullfilled.
INFO - cli - Starting simulation of case pv-diesel-mg, project site desanyala_site, experiment no. 2/3...
DEBUG - G2b_constraints_custom - Stability criterion is fullfilled.
INFO - cli - Starting simulation of case pv-diesel-storage-mg, project site desanyala_site, experiment no. 3/3...
WARNING - G2b_constraints_custom - Stability criterion is strictly not fullfilled, but deviation is less then e6.
"""

    global_warnings = _apply_stability_warnings(rows, native_log)
    by_id = {row.scenario_id: row for row in rows}

    assert by_id["diesel_only"].status == "optimal"
    assert by_id["pv_diesel"].status == "optimal"
    assert by_id["pv_diesel_battery"].status == "feasible"
    assert not any("stabilitas" in w.lower() for w in by_id["diesel_only"].validation.warnings)
    assert not any("stabilitas" in w.lower() for w in by_id["pv_diesel"].validation.warnings)
    assert any("stabilitas" in w.lower() for w in by_id["pv_diesel_battery"].validation.warnings)
    assert len(global_warnings) == 1


def test_unmapped_stability_warning_is_reported_globally():
    rows = [_scenario("diesel_only")]
    native_log = """
INFO - cli - Starting simulation of case unknown-case, project site site, experiment no. 1/1...
WARNING - G2b_constraints_custom - Stability criterion is strictly not fullfilled, but deviation is less then e6.
"""

    global_warnings = _apply_stability_warnings(rows, native_log)

    assert rows[0].status == "optimal"
    assert len(global_warnings) == 1
    assert "tidak berhasil dipetakan" in global_warnings[0]
