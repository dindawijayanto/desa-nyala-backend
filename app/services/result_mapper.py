"""Map Offgridders CSV outputs into the stable DesaNyala response contract."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from app.schemas.results import (
    Capacities,
    DispatchPoint,
    ScenarioMetrics,
    ScenarioResult,
    ValidationReport,
)

NATIVE_TO_SCENARIO = {
    "diesel_mg": ("diesel_only", "Diesel-only"),
    "pv-diesel-mg": ("pv_diesel", "PV + diesel"),
    "pv-diesel-storage-mg": ("pv_diesel_battery", "PV + diesel + baterai"),
}


def _num(row: dict[str, Any], key: str, default: float | None = None) -> float | None:
    value = row.get(key)
    if value is None or value == "":
        return default
    try:
        number = float(value)
        return number if number == number and abs(number) != float("inf") else default
    except (TypeError, ValueError):
        return default


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _find_dispatch_csv(output_root: Path, native_case: str) -> Path | None:
    candidates = list((output_root / "electricity_mg").glob(f"{native_case}_*_electricity_mg.csv"))
    if not candidates:
        candidates = list((output_root / "electricity_mg").glob(f"{native_case}*electricity_mg.csv"))
    return sorted(candidates)[0] if candidates else None


def _dispatch_points(path: Path | None, battery_capacity_kwh: float | None) -> tuple[list[DispatchPoint], bool | None]:
    if path is None or not path.exists():
        return [], None
    rows = _read_csv(path)
    points: list[DispatchPoint] = []
    all_balanced = True
    for row in rows:
        demand = _num(row, "Demand", 0.0) or 0.0
        pv = _num(row, "PV generation", 0.0) or 0.0
        genset = _num(row, "Genset generation", 0.0) or 0.0
        charge = abs(_num(row, "Storage charge", 0.0) or 0.0)
        discharge = abs(_num(row, "Storage discharge", 0.0) or 0.0)
        shortage = abs(_num(row, "Demand shortage AC", 0.0) or 0.0) + abs(
            _num(row, "Demand shortage DC", 0.0) or 0.0
        )
        excess = abs(_num(row, "Excess generation", 0.0) or 0.0)
        soc_fraction = _num(row, "Storage SOC", None)
        soc_kwh = None
        if soc_fraction is not None and battery_capacity_kwh is not None:
            soc_kwh = soc_fraction * battery_capacity_kwh
        # Offgridders exports Storage discharge with negative sign. Convert to positive
        # delivered power, and use shortage/excess as explicit balance terms.
        reconstructed_demand = pv + genset + discharge - charge - excess + shortage
        if abs(reconstructed_demand - demand) > max(0.05, demand * 0.01):
            all_balanced = False
        points.append(
            DispatchPoint(
                timestamp=row.get("timestep", ""),
                demand_kw=demand,
                pv_kw=pv,
                generator_power_kw=genset,
                battery_charge_kw=charge,
                battery_discharge_kw=discharge,
                battery_soc_kwh=soc_kwh,
                battery_soc_fraction=soc_fraction,
                excess_power_kw=excess,
                unmet_demand_kw=shortage,
            )
        )
    return points, all_balanced


def parse_offgridders_summary(
    result_csv: Path,
    output_root: Path,
    *,
    currency: str,
    generator_unit_count: int,
    expected_scenarios: list[str],
    extra_warnings: list[str] | None = None,
) -> list[ScenarioResult]:
    if not result_csv.is_file():
        raise FileNotFoundError(f"Offgridders summary CSV was not generated: {result_csv}")
    rows = _read_csv(result_csv)
    by_native_case = {row.get("case", ""): row for row in rows}
    extra_warnings = extra_warnings or []
    response: list[ScenarioResult] = []

    scenario_map = {
        "diesel_only": "diesel_mg",
        "pv_diesel": "pv-diesel-mg",
        "pv_diesel_battery": "pv-diesel-storage-mg",
    }
    for scenario_id in expected_scenarios:
        native_case = scenario_map[scenario_id]
        row = by_native_case.get(native_case)
        if row is None:
            response.append(
                ScenarioResult(
                    scenario_id=scenario_id,
                    scenario_name=NATIVE_TO_SCENARIO[native_case][1],
                    status="error",
                    validation=ValidationReport(
                        warnings=[f"Tidak ada baris hasil untuk kasus {native_case}."]
                    ),
                )
            )
            continue

        annual_demand = _num(row, "total_demand_annual_kWh")
        annual_supplied = _num(row, "total_demand_supplied_annual_kWh")
        annual_shortage = _num(row, "total_demand_shortage_annual_kWh")
        reliability = None
        if annual_demand and annual_demand > 0 and annual_supplied is not None:
            reliability = max(0.0, min(1.0, annual_supplied / annual_demand))
        pv_cap = _num(row, "capacity_pv_kWp", 0.0)
        genset_cap = _num(row, "capacity_genset_kW", 0.0)
        battery_cap = _num(row, "capacity_storage_kWh", 0.0)
        battery_power = _num(row, "power_storage_kW", 0.0)
        dispatch_path = _find_dispatch_csv(output_root, native_case)
        dispatch, balance_pass = _dispatch_points(dispatch_path, battery_cap)
        warnings = list(extra_warnings)
        comments = row.get("comments", "") or ""
        if comments.strip():
            warnings.append(f"Catatan engine: {comments.strip()}")
        if dispatch_path is None:
            warnings.append("CSV dispatch per jam tidak ditemukan; grafik operasi tidak tersedia.")
        if balance_pass is False:
            warnings.append("Pemeriksaan keseimbangan energi pada dispatch memiliki deviasi; audit sebelum menggunakan hasil.")
        if generator_unit_count > 1:
            warnings.append(
                "Hasil kapasitas genset multi-unit perlu diverifikasi: adapter belum memastikan apakah kolom kapasitas native adalah total sistem atau per unit."
            )
        if "Stability criterion is strictly not fullfilled" in "".join(extra_warnings):
            status = "feasible"
        else:
            status = "optimal"
        response.append(
            ScenarioResult(
                scenario_id=scenario_id,
                scenario_name=NATIVE_TO_SCENARIO[native_case][1],
                status=status,
                metrics=ScenarioMetrics(
                    lcoe=_num(row, "lcoe"),
                    annualized_cost=_num(row, "annuity"),
                    npv=_num(row, "npv"),
                    annual_demand_kwh=annual_demand,
                    annual_supplied_kwh=annual_supplied,
                    annual_unmet_energy_kwh=annual_shortage,
                    supply_reliability_fraction=reliability,
                    renewable_share_fraction=_num(row, "res_share"),
                    annual_fuel_liters=_num(row, "consumption_fuel_annual_l"),
                    annual_co2_kg=_num(row, "co2_emissions_kgCO2eq"),
                    peak_demand_kw=_num(row, "demand_peak_kW"),
                    annual_pv_generation_kwh=_num(row, "total_pv_generation_kWh"),
                    annual_genset_generation_kwh=_num(row, "total_genset_generation_kWh"),
                    annual_excess_energy_kwh=_num(row, "total_excess_annual_kWh"),
                ),
                capacities=Capacities(
                    pv_kwp=pv_cap,
                    genset_kw=genset_cap,
                    battery_kwh=battery_cap,
                    battery_power_kw=battery_power,
                    genset_capacity_basis="aggregate" if generator_unit_count == 1 else "unknown",
                ),
                validation=ValidationReport(
                    energy_balance_passed=balance_pass,
                    reliability_passed=(reliability is not None and annual_shortage is not None and annual_shortage <= 1e-4),
                    capacity_constraints_passed=None,
                    solver_message="Ringkasan CSV tersedia; baca log untuk status solver dan warning numerik.",
                    warnings=warnings,
                ),
                dispatch=dispatch,
            )
        )
    return response
