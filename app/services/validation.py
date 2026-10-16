from app.schemas.input import OptimizationRequest
from app.services.demand_profile import estimate_daily_energy_kwh, build_hourly_demand_profile
from app.services.pv_profile import build_hourly_pv_profile


def validate_request_summary(request: OptimizationRequest) -> dict:
    daily_kwh = estimate_daily_energy_kwh(request.demand)
    demand_profile = build_hourly_demand_profile(request.demand, request.project.simulation_days)
    pv_profile = build_hourly_pv_profile(request.pv, request.project.simulation_days)
    warnings: list[str] = [
        "Demand per jam adalah profil representatif yang mengulang pola harian yang dimasukkan; bukan pengukuran aktual.",
        "Profil peralatan menyebarkan rata-rata dayanya pada jendela penggunaan; belum ada pemodelan peluang beban serentak atau lonjakan start-up.",
    ]
    if request.pv.enabled:
        warnings.append(
            "Profil PV adalah kurva sintetis dari peak sun hours dan performance factor; bukan data cuaca lokasi tervalidasi."
        )
    if request.generators.unit_count > 1:
        warnings.append(
            "Jumlah genset diinput, tetapi per-unit on/off, startup cost, dan minimum up/down time belum dianggap terimplementasi oleh adapter."
        )
    return {
        "valid": True,
        "estimated_daily_energy_kwh": round(daily_kwh, 4),
        "estimated_annual_energy_kwh": round(daily_kwh * 365, 4),
        "connected_power_kw": round(
            sum(load.quantity * load.power_w for load in request.demand.loads) / 1000.0, 4
        ),
        "generated_demand_intervals": len(demand_profile),
        "generated_pv_intervals": len(pv_profile),
        "equipment_rows": len(request.demand.loads),
        "warnings": warnings,
    }
