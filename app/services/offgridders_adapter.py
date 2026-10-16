"""Run the imported Offgridders copy in an isolated workspace for one API request."""
from __future__ import annotations

import re
import csv
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from app.schemas.input import OptimizationRequest
from app.services.demand_profile import build_hourly_demand_profile
from app.services.pv_profile import build_hourly_pv_profile
from app.services.result_mapper import parse_offgridders_summary


class OffgriddersAdapterError(RuntimeError):
    """An expected integration/runtime problem, safe to return as API error."""


class OffgriddersAdapterNotConfigured(OffgriddersAdapterError):
    pass


class OffgriddersRunError(OffgriddersAdapterError):
    pass


SCENARIO_CASES = {
    "diesel_only": "diesel_mg",
    "pv_diesel": "pv-diesel-mg",
    "pv_diesel_battery": "pv-diesel-storage-mg",
}

def _apply_stability_warnings(
    result_rows: list[Any],
    log_text: str,
) -> list[str]:
    warnings_by_case: dict[str, str] = {}
    current_case: str | None = None

    for line in log_text.splitlines():
        match = re.search(
            r"Starting simulation of case\s+([A-Za-z0-9_-]+)",
            line,
            re.IGNORECASE,
        )
        if match:
            current_case = match.group(1)

        if "stability criterion is strictly not fullfilled" in line.casefold():
            if current_case:
                warnings_by_case[current_case] = (
                    "Engine melaporkan kriteria stabilitas tidak terpenuhi "
                    "secara ketat; hasil perlu diperiksa sebelum digunakan "
                    "sebagai desain final."
                )

    global_warnings: list[str] = []
    mapped_cases: set[str] = set()

    for result in result_rows:
        native_case = SCENARIO_CASES.get(result.scenario_id)
        message = warnings_by_case.get(native_case)

        if not message or native_case is None:
            continue

        mapped_cases.add(native_case)
        warning = f"Skenario {result.scenario_id}: {message}"

        if warning not in result.validation.warnings:
            result.validation.warnings.append(warning)

        if result.status != "error":
            result.status = "feasible"

        global_warnings.append(warning)

    for native_case, message in warnings_by_case.items():
        if native_case not in mapped_cases:
            global_warnings.append(
                f"Warning stabilitas untuk kasus native '{native_case}' "
                f"tidak berhasil dipetakan ke skenario API. Detail: {message}"
            )

    return global_warnings


def _find_key_row(ws, key: str, key_col: int = 1, start_row: int = 1) -> int:
    wanted = key.strip().casefold()
    for r in range(start_row, ws.max_row + 1):
        value = ws.cell(r, key_col).value
        if isinstance(value, str) and value.strip().casefold() == wanted:
            return r
    raise OffgriddersRunError(f"Parameter '{key}' tidak ditemukan pada sheet '{ws.title}'.")


def _set_parameter(ws, key: str, value: Any, key_col: int = 1, value_col: int = 2, start_row: int = 1) -> None:
    r = _find_key_row(ws, key, key_col=key_col, start_row=start_row)
    ws.cell(r, value_col).value = value


def _set_or_append_constant(
    ws,
    key: str,
    value: Any,
    unit: str,
    key_col: int = 1,
    value_col: int = 2,
    unit_col: int = 3,
    start_row: int = 7,
) -> None:
    """Update a constant or append a DesaNyala-specific constant."""
    try:
        row = _find_key_row(
            ws,
            key,
            key_col=key_col,
            start_row=start_row,
        )
    except OffgriddersRunError:
        row = ws.max_row + 1
        while ws.cell(row, key_col).value is not None:
            row += 1

        ws.cell(row, key_col).value = key
        ws.cell(row, unit_col).value = unit

    ws.cell(row, value_col).value = value


def _set_setting(ws, key: str, value: Any) -> None:
    _set_parameter(ws, key, value, key_col=2, value_col=3, start_row=11)


def _case_column(ws, native_case: str) -> int:
    for c in range(2, ws.max_column + 1):
        if str(ws.cell(17, c).value or "").strip() == native_case:
            return c
    raise OffgriddersRunError(f"Case '{native_case}' tidak ditemukan pada case_definitions.")


def _set_case_value(ws, native_case: str, parameter: str, value: Any) -> None:
    r = _find_key_row(ws, parameter, key_col=1, start_row=18)
    c = _case_column(ws, native_case)
    ws.cell(r, c).value = value


def _template_path(engine_root: Path, backend_root: Path) -> Path:
    candidates = [
        engine_root / "inputs" / "test_input_template.xlsx",
        engine_root / "inputs" / "input_template_excel.xlsx",
        backend_root / "templates" / "offgridders_input_template.xlsx",
    ]
    for path in candidates:
        if path.is_file():
            return path
    raise OffgriddersAdapterNotConfigured(
        "Template Excel tidak ditemukan di engine/inputs atau backend/templates."
    )


def _write_profiles(run_dir: Path, request: OptimizationRequest) -> Path:
    timeseries_dir = run_dir / "inputs" / "timeseries"
    timeseries_dir.mkdir(parents=True, exist_ok=True)
    demand = build_hourly_demand_profile(request.demand, request.project.simulation_days)
    pv_yield = build_hourly_pv_profile(request.pv, request.project.simulation_days)
    if len(demand) != len(pv_yield):
        raise OffgriddersRunError("Panjang profil Demand dan PV tidak sama.")
    target = timeseries_dir / "desanyala_profile.csv"
    # The template's separator is semicolon and uses per-kWp PV yield.
    with target.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=";", lineterminator="\n")
        writer.writerow(["Demand", "SolarGen", "Wind"])
        for d, p in zip(demand, pv_yield):
            writer.writerow([f"{d:.8f}", f"{p if request.pv.enabled else 0.0:.8f}", "0.00000000"])
    return target


def _configure_workbook(template: Path, workbook_path: Path, run_dir: Path, request: OptimizationRequest) -> None:
    wb = load_workbook(template)
    required = {"settings", "input_constant", "input_sensitivity", "project_sites", "case_definitions"}
    missing = required.difference(wb.sheetnames)
    if missing:
        wb.close()
        raise OffgriddersRunError(f"Template kehilangan sheet wajib: {', '.join(sorted(missing))}")

    settings_ws = wb["settings"]
    _set_setting(settings_ws, "allow_shortage", "True" if request.reliability.shortage_policy == "bounded" else "False")
    _set_setting(settings_ws, "evaluated_days", request.project.simulation_days)
    _set_setting(settings_ws, "time_frequency", "H")
    _set_setting(settings_ws, "input_folder_timeseries", "./inputs/timeseries")
    _set_setting(settings_ws, "output_folder", "outputs")
    _set_setting(settings_ws, "output_file", "results")
    _set_setting(settings_ws, "perform_multicriteria_analysis", "False")
    _set_setting(settings_ws, "save_lp_file", "False")
    _set_setting(settings_ws, "save_oemofresults", "False")
    _set_setting(settings_ws, "save_to_csv_flows_storage", "True")
    _set_setting(settings_ws, "save_to_csv_flows_electricity_mg", "True")
    _set_setting(settings_ws, "save_to_png_flows_storage", "False")
    _set_setting(settings_ws, "save_to_png_flows_electricity_mg", "False")
    _set_setting(settings_ws, "results_demand_characteristics", "True")
    _set_setting(settings_ws, "results_blackout_characteristics", "True")
    _set_setting(settings_ws, "results_annuities", "True")
    _set_setting(settings_ws, "results_costs", "True")
    _set_setting(
        settings_ws,
        "include_shortage_penalty_costs_in_lcoe",
        "True",
    )

    constants = wb["input_constant"]
    const_map = {
        "project_lifetime": request.project.project_lifetime_years,
        "wacc": request.economics.discount_rate,
        "project_cost_investment": request.economics.additional_project_cost,
        "fuel_price": request.generators.fuel_price_per_liter,
        "fuel_price_change_annual": 0.0,
        "genset_cost_investment": request.generators.capex_per_kw,
        "genset_cost_opex": request.generators.opex_annual_per_unit / max(request.generators.rated_power_each_kw, 1.0),
        "genset_efficiency": request.generators.efficiency_fraction,
        "genset_lifetime": request.generators.lifetime_years,
        "genset_min_loading": request.generators.min_loading_fraction,
        "genset_max_loading": request.generators.max_loading_fraction,
        "pv_cost_investment": request.pv.capex_per_kwp,
        "pv_cost_opex": request.pv.opex_annual_per_kwp,
        "pv_lifetime": request.pv.lifetime_years,
        "storage_capacity_cost_investment": request.battery.capex_per_kwh,
        "storage_capacity_cost_opex": request.battery.opex_annual_per_kwh,
        "storage_power_cost_investment": request.battery.power_capex_per_kw,
        "storage_power_cost_opex": request.battery.power_opex_annual_per_kw,
        "storage_efficiency_charge": request.battery.charge_efficiency,
        "storage_efficiency_discharge": request.battery.discharge_efficiency,
        "storage_soc_min": request.battery.soc_min_fraction,
        "storage_soc_max": request.battery.soc_max_fraction,
        "storage_soc_initial": request.battery.soc_initial_fraction,
        "storage_Crate_charge": (request.battery.power_max_kw / request.battery.capacity_max_kwh) if request.battery.capacity_max_kwh > 0 else 0.0,
        "storage_Crate_discharge": (request.battery.power_max_kw / request.battery.capacity_max_kwh) if request.battery.capacity_max_kwh > 0 else 0.0,
        "shortage_max_allowed": request.reliability.max_unmet_energy_fraction if request.reliability.shortage_policy == "bounded" else 0.0,
        "shortage_max_timestep": request.reliability.max_unmet_energy_fraction if request.reliability.shortage_policy == "bounded" else 0.0,
        "shortage_penalty_costs": 0.0,
        "fuel_co2_emission_factor": 2.68,
    }
    for key, value in const_map.items():
        _set_parameter(constants, key, value, key_col=1, value_col=2, start_row=6)

    
    # DesaNyala optimization bounds, forwarded to the native engine.
    custom_bounds = [
        (
            "desanyala_reserve_margin_fraction",
            request.reliability.reserve_margin_fraction,
            "fraction",
        ),
        ("desanyala_pv_capacity_min_kwp", request.pv.capacity_min_kwp, "kWp"),
        ("desanyala_pv_capacity_max_kwp", request.pv.capacity_max_kwp, "kWp"),
        (
            "desanyala_battery_capacity_min_kwh",
            request.battery.capacity_min_kwh,
            "kWh",
        ),
        (
            "desanyala_battery_capacity_max_kwh",
            request.battery.capacity_max_kwh,
            "kWh",
        ),
        (
            "desanyala_battery_power_max_kw",
            request.battery.power_max_kw,
            "kW",
        ),
    ]

    for key, value, unit in custom_bounds:
        _set_or_append_constant(constants, key, value, unit)

    # Upstream sensitivity values override constant values. Keep one fixed experiment
    # at the values supplied in the cards, rather than accidentally leaving 1000/20.
    sensitivity = wb["input_sensitivity"]
    for key, value in (("pv_cost_investment", request.pv.capex_per_kwp), ("pv_lifetime", request.pv.lifetime_years)):
        try:
            r = _find_key_row(sensitivity, key, key_col=1, start_row=11)
            sensitivity.cell(r, 2).value = value
            sensitivity.cell(r, 3).value = value
            # Step needs to be positive even for a fixed single-point range.
            sensitivity.cell(r, 4).value = max(1, value)
        except OffgriddersRunError:
            # If no sensitivity rows exist in this upstream version, constants suffice.
            pass

    # Project site rows are table-like: headers are on row 14 in the supplied template.
    sites = wb["project_sites"]
    header_row = 14
    headers = {str(sites.cell(header_row, c).value).strip(): c for c in range(1, sites.max_column + 1) if sites.cell(header_row, c).value is not None}
    data_row = 15
    if "project_site_name" not in headers:
        wb.close()
        raise OffgriddersRunError("Kolom project_site_name tidak ada pada project_sites.")
    sites.cell(data_row, headers["project_site_name"]).value = "desanyala_site"
    sites.cell(data_row, headers["timeseries_file"]).value = "desanyala_profile.csv"
    sites.cell(data_row, headers["title_time"]).value = "None"
    # The provided template's fourth column is title_demand_ac; the parser treats it as demand.
    demand_header = "title_demand_ac" if "title_demand_ac" in headers else "title_demand"
    sites.cell(data_row, headers[demand_header]).value = "Demand"
    if "title_demand_dc" in headers:
        sites.cell(data_row, headers["title_demand_dc"]).value = "None"
    if "title_pv" in headers:
        sites.cell(data_row, headers["title_pv"]).value = "SolarGen" if request.pv.enabled else "None"
    if "title_wind" in headers:
        sites.cell(data_row, headers["title_wind"]).value = "Wind"  # generated zero column; no wind scenario is run
    if "title_grid_availability" in headers:
        sites.cell(data_row, headers["title_grid_availability"]).value = "None"
    if "seperator" in headers:
        sites.cell(data_row, headers["seperator"]).value = ";"

    cases = wb["case_definitions"]
    enabled = set(request.optimization.scenarios)
    # Explicitly disable every native case not represented in DesaNyala's contract,
    # including the upstream wind case. Do not rely on template defaults.
    supported_native_cases = set(SCENARIO_CASES.values())
    for c in range(2, cases.max_column + 1):
        native_name = str(cases.cell(17, c).value or "").strip()
        if not native_name:
            continue
        if native_name not in supported_native_cases:
            r = _find_key_row(cases, "perform_simulation", key_col=1, start_row=18)
            cases.cell(r, c).value = "False"
            try:
                wr = _find_key_row(cases, "capacity_wind_kW", key_col=1, start_row=18)
                cases.cell(wr, c).value = "None"
            except OffgriddersRunError:
                pass
    for scenario_id, native_case in SCENARIO_CASES.items():
        run_this = scenario_id in enabled
        _set_case_value(cases, native_case, "perform_simulation", "True" if run_this else "False")
        _set_case_value(cases, native_case, "capacity_wind_kW", "None")
        _set_case_value(cases, native_case, "number_of_equal_generators", str(request.generators.unit_count))
        _set_case_value(cases, native_case, "allow_shortage", "True" if request.reliability.shortage_policy == "bounded" else "False")
        max_shortage = request.reliability.max_unmet_energy_fraction if request.reliability.shortage_policy == "bounded" else 0.0
        _set_case_value(cases, native_case, "max_shortage", max_shortage)
        _set_case_value(cases, native_case, "capacity_genset_kW", "oem" if request.generators.mode == "new" else request.generators.rated_power_each_kw)

        if scenario_id == "diesel_only":
            _set_case_value(cases, native_case, "capacity_pv_kWp", "None")
            _set_case_value(cases, native_case, "capacity_storage_kWh", "None")
        elif scenario_id == "pv_diesel":
            if request.pv.capacity_mode == "fixed":
                pv_cap: Any = request.pv.fixed_capacity_kwp
            else:
                pv_cap = "oem"
            _set_case_value(cases, native_case, "capacity_pv_kWp", pv_cap if request.pv.enabled else "None")
            _set_case_value(cases, native_case, "capacity_storage_kWh", "None")
        else:
            if request.pv.capacity_mode == "fixed":
                pv_cap = request.pv.fixed_capacity_kwp
            else:
                pv_cap = "oem"
            _set_case_value(cases, native_case, "capacity_pv_kWp", pv_cap if request.pv.enabled else "None")
            _set_case_value(cases, native_case, "capacity_storage_kWh", "oem" if request.battery.enabled else "None")
        # Avoid making battery scenario depend on a case omitted from the request.
        _set_case_value(cases, native_case, "based_on_case", "True" if scenario_id == "pv_diesel_battery" and "pv_diesel" in enabled else "False")
        if request.reliability.shortage_policy == "forbid":
            _set_case_value(cases, native_case, "allow_shortage", "False")
            _set_case_value(cases, native_case, "max_shortage", 0.0)

    workbook_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(workbook_path)
    wb.close()


class OffgriddersAdapter:
    """Configure, run, and normalize an embedded Offgridders source checkout."""

    def __init__(self, offgridders_root: str | Path, python_executable: str | None = None, timeout_seconds: int = 1200):
        self.root = Path(offgridders_root).resolve()
        self.python_executable = python_executable or sys.executable
        self.timeout_seconds = timeout_seconds
        self.backend_root = Path(__file__).resolve().parents[2]

    def validate_installation(self) -> None:
        if not (self.root / "Offgridders.py").is_file() or not (self.root / "src").is_dir():
            raise OffgriddersAdapterNotConfigured(
                f"Source Offgridders belum diimpor ke '{self.root}'. Jalankan scripts/import_offgridders.ps1."
            )
        if not any((self.root / name).is_file() for name in ("LICENSE", "LICENSE.txt", "COPYING", "UPSTREAM_LICENSE_NOTICE.txt")):
            raise OffgriddersAdapterNotConfigured("File lisensi upstream tidak ditemukan; import ulang dengan lisensi sumber.")
        if not Path(self.python_executable).is_file() and self.python_executable != sys.executable:
            raise OffgriddersAdapterNotConfigured(f"Python Offgridders tidak ditemukan: {self.python_executable}")

    def run(self, request: OptimizationRequest, run_dir: Path) -> dict:
        self.validate_installation()
        if request.economics.fuel_price_escalation_annual != 0:
            raise OffgriddersRunError(
                "Offgridders memberi peringatan bahwa fuel_price_change_annual nonzero masih bermasalah. "
                "Set fuel_price_escalation_annual=0 sampai perhitungannya diperbaiki dan divalidasi."
            )
        if request.optimization.objective != "annualized_cost":
            raise OffgriddersRunError(
                "Objektif fuel_consumption belum dipetakan ke fungsi objektif native. Untuk saat ini pilih annualized_cost."
            )
        if request.generators.fuel_model == "curve":
            raise OffgriddersRunError(
                "Kurva konsumsi bahan bakar per beban belum dipetakan ke workbook native. Gunakan efisiensi konstan sampai model kurva diimplementasikan."
            )
        if request.generators.unit_commitment_model == "multi_unit" and request.generators.unit_count > 1:
            raise OffgriddersRunError(
                "Per-unit on/off commitment, startup cost, dan minimum up/down time belum divalidasi di adapter ini. "
                "Gunakan aggregate sementara; jangan menampilkan jadwal on/off per unit sebagai hasil model."
            )

        run_dir.mkdir(parents=True, exist_ok=True)
        template = _template_path(self.root, self.backend_root)
        workbook_path = run_dir / "config" / "desanyala_input.xlsx"
        _configure_workbook(template, workbook_path, run_dir, request)
        _write_profiles(run_dir, request)
        output_dir = run_dir / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)
        command = [self.python_executable, str(self.root / "Offgridders.py"), str(workbook_path)]
        try:
            proc = subprocess.run(
                command,
                cwd=str(run_dir),
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
                env=os.environ.copy(),
            )
        except subprocess.TimeoutExpired as exc:
            (run_dir / "stdout.log").write_text(str(exc.stdout or ""), encoding="utf-8")
            (run_dir / "stderr.log").write_text(str(exc.stderr or ""), encoding="utf-8")
            raise OffgriddersRunError(f"Offgridders melewati timeout {self.timeout_seconds} detik; log tersimpan di {run_dir}.") from exc
        (run_dir / "stdout.log").write_text(proc.stdout or "", encoding="utf-8")
        (run_dir / "stderr.log").write_text(proc.stderr or "", encoding="utf-8")
        if proc.returncode != 0:
            tail = (proc.stderr or proc.stdout or "")[-5000:]
            raise OffgriddersRunError(
                f"Offgridders exit code {proc.returncode}. Detail log ada di {run_dir}. Tail: {tail}"
            )
        summary_csv = output_dir / "results.csv"
        if not summary_csv.is_file():
            # The upstream CLI may append the configured output_file extension/name differently.
            candidates = list(output_dir.glob("*.csv"))
            summary_csv = candidates[0] if candidates else summary_csv
        if not summary_csv.is_file():
            raise OffgriddersRunError(
                f"Proses selesai tetapi summary CSV tidak ditemukan di {output_dir}. Lihat stdout.log/stderr.log."
            )
        log_text = (proc.stdout or "") + "\n" + (proc.stderr or "")
        warnings: list[str] = [
            "Profil beban diulang dari satu hari representatif; belum memodelkan variasi hari kerja/akhir pekan atau variasi musiman.",
            "Profil peralatan menyebarkan rata-rata daya pada jendela penggunaan; belum memodelkan probabilitas beban serentak atau lonjakan start-up.",
            "Profil PV adalah kurva sintetis dari peak sun hours dan performance factor, bukan data cuaca lokasi yang tervalidasi.",
            "Parameter shortage, dispatch, dan kapasitas harus divalidasi terhadap file hasil dan asumsi model.",
        ]
        engine_run_warnings: list[str] = []
        if (
            request.generators.mode == "existing"
            and request.reliability.reserve_margin_fraction > 0
        ):
            warnings.append(
                "Mode genset existing menggunakan kapasitas tetap; "
                "reserve margin diperiksa setelah solusi dan tidak "
                "dapat dipenuhi dengan menambah kapasitas lewat optimizer."
            )
        if any(load.critical for load in request.demand.loads):
            warnings.append("Flag beban kritis belum diterapkan sebagai prioritas pemenuhan terpisah di model native; semua beban dijumlahkan menjadi satu profil Demand.")
        if request.generators.mode == "new":
            warnings.append("Pada mode genset baru, ukuran genset dipilih oleh Offgridders; rated_power_each_kw dari kartu UI bukan batas maksimum kapasitas native.")
        if request.generators.unit_count > 1:
            warnings.append("number_of_equal_generators diteruskan ke model native, tetapi status on/off individual dan batas waktu hidup/mati belum divalidasi.")

        if "fuel_price_change_annual" in log_text and "faulty" in log_text.lower():
            engine_run_warnings.append(
                "Log gabungan proses engine memberi peringatan pada kalkulasi "
                "perubahan harga bahan bakar tahunan. Log yang tersedia belum "
                "mengidentifikasi skenario terkait."
            )
        result_rows = parse_offgridders_summary(
            summary_csv,
            output_dir,
            currency=request.project.currency,
            generator_unit_count=request.generators.unit_count,
            expected_scenarios=request.optimization.scenarios,
            extra_warnings=warnings,
        )

        # Map native stability warnings to the case that produced them.
        native_log_path = output_dir / "micro_grid_design_logfile.log"
        scoped_log_text = log_text

        if native_log_path.is_file():
            scoped_log_text += "\n" + native_log_path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        engine_run_warnings.extend(
            _apply_stability_warnings(result_rows, scoped_log_text)
        )

        # The workbook's baseline does not encode min/max capacity cards as native
        # decision-variable bounds. Check the returned solution and explicitly flag
        # any result outside the UI constraints instead of presenting it as accepted.
        for scenario_result in result_rows:
            capacity_errors: list[str] = []
            if scenario_result.status not in ("error",) and scenario_result.capacities.pv_kwp is not None:
                actual_pv = scenario_result.capacities.pv_kwp
                if (
                    request.pv.enabled
                    and scenario_result.scenario_id
                    in {"pv_diesel", "pv_diesel_battery"}
                ):
                    if actual_pv < request.pv.capacity_min_kwp - 1e-4 or actual_pv > request.pv.capacity_max_kwp + 1e-4:
                        capacity_errors.append(
                            f"Kapasitas PV hasil ({actual_pv:.4f} kWp) berada di luar rentang UI "
                            f"[{request.pv.capacity_min_kwp}, {request.pv.capacity_max_kwp}] kWp."
                        )
                    if request.pv.capacity_mode == "fixed" and request.pv.fixed_capacity_kwp is not None and abs(actual_pv - request.pv.fixed_capacity_kwp) > 1e-3:
                        capacity_errors.append("Kapasitas PV hasil tidak sama dengan kapasitas tetap yang diminta.")
            if request.reliability.reserve_margin_fraction > 0 and scenario_result.capacities.genset_kw is not None and scenario_result.metrics.peak_demand_kw is not None:
                required_dispatchable_capacity = scenario_result.metrics.peak_demand_kw * (1 + request.reliability.reserve_margin_fraction)
                if scenario_result.capacities.genset_kw + 1e-4 < required_dispatchable_capacity:
                    capacity_errors.append(
                        f"Kapasitas genset hasil ({scenario_result.capacities.genset_kw:.4f} kW) belum memenuhi pemeriksaan pascasolusi untuk cadangan {request.reliability.reserve_margin_fraction:.1%}; target pemeriksaan {required_dispatchable_capacity:.4f} kW. Ini bukan kendala yang ditegakkan oleh optimizer native."
                    )
            if (
                scenario_result.scenario_id == "pv_diesel_battery"
                and request.battery.enabled
            ):
                actual_batt = scenario_result.capacities.battery_kwh or 0.0
                actual_batt_power = scenario_result.capacities.battery_power_kw or 0.0
                if actual_batt < request.battery.capacity_min_kwh - 1e-4 or actual_batt > request.battery.capacity_max_kwh + 1e-4:
                    capacity_errors.append(
                        f"Kapasitas baterai hasil ({actual_batt:.4f} kWh) berada di luar rentang UI "
                        f"[{request.battery.capacity_min_kwh}, {request.battery.capacity_max_kwh}] kWh."
                    )
                if actual_batt_power > request.battery.power_max_kw + 1e-4:
                    capacity_errors.append(
                        f"Daya baterai hasil ({actual_batt_power:.4f} kW) melebihi batas UI {request.battery.power_max_kw} kW."
                    )
            if capacity_errors:
                scenario_result.status = "feasible"
                scenario_result.validation.capacity_constraints_passed = False
                scenario_result.validation.warnings.extend(capacity_errors)
            elif scenario_result.status != "error":
                scenario_result.validation.capacity_constraints_passed = True
        statuses = {r.status for r in result_rows}
        overall = "error" if "error" in statuses else ("feasible" if "feasible" in statuses else "optimal")
        return {
            "summary_csv": str(summary_csv),
            "output_dir": str(output_dir),
            "stdout_log": str(run_dir / "stdout.log"),
            "stderr_log": str(run_dir / "stderr.log"),
            "scenarios": result_rows,
            "status": overall,
            "warnings": warnings + engine_run_warnings,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
