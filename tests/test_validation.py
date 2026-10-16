from app.schemas.input import OptimizationRequest
from app.services.validation import validate_request_summary


def sample_payload():
    return {
        "schema_version": "1.0.0",
        "project": {
            "name": "Desa Demo",
            "location": "Kabupaten Contoh, Indonesia",
            "households": 150,
            "electrification_status": "unserved",
            "simulation_days": 365,
            "time_step_hours": 1,
            "project_lifetime_years": 20,
            "currency": "IDR",
        },
        "demand": {
            "profile_source": "equipment_estimate",
            "loads": [
                {
                    "category": "Rumah tangga",
                    "device": "Lampu LED",
                    "quantity": 150,
                    "power_w": 10,
                    "hours_per_day": 6,
                    "usage_period": "evening",
                    "critical": False,
                }
            ],
        },
        "pv": {
            "enabled": True,
            "resource_location": "Kabupaten Contoh, Indonesia",
            "peak_sun_hours_estimate": 4.5,
            "system_performance_factor": 0.8,
            "capacity_mode": "optimize",
            "fixed_capacity_kwp": None,
            "capacity_min_kwp": 0,
            "capacity_max_kwp": 200,
            "capex_per_kwp": 15000000,
            "opex_annual_per_kwp": 200000,
            "lifetime_years": 25,
        },
        "generators": {
            "mode": "new",
            "unit_count": 1,
            "identical_units_assumption": True,
            "rated_power_each_kw": 100,
            "min_loading_fraction": 0.3,
            "max_loading_fraction": 1,
            "fuel_price_per_liter": 10000,
            "fuel_model": "efficiency",
            "efficiency_fraction": 0.33,
            "capex_per_kw": 10000000,
            "opex_annual_per_unit": 5000000,
            "lifetime_years": 10,
            "unit_commitment_model": "aggregate",
        },
        "battery": {
            "enabled": True,
            "capacity_min_kwh": 0,
            "capacity_max_kwh": 200,
            "power_max_kw": 50,
            "charge_efficiency": 0.97,
            "discharge_efficiency": 0.97,
            "soc_min_fraction": 0.2,
            "soc_max_fraction": 1,
            "soc_initial_fraction": 0.5,
            "capex_per_kwh": 2500000,
            "power_capex_per_kw": 500000,
            "lifetime_years": 13,
        },
        "economics": {
            "discount_rate": 0.08,
            "fuel_price_escalation_annual": 0,
            "additional_project_cost": 0,
        },
        "reliability": {
            "target_supply_fraction": 0.995,
            "shortage_policy": "forbid",
            "max_unmet_energy_fraction": 0,
            "reserve_margin_fraction": 0.1,
        },
        "optimization": {
            "objective": "annualized_cost",
            "scenarios": ["diesel_only", "pv_diesel", "pv_diesel_battery"],
            "solver_configuration": "backend_default",
        },
    }


def test_daily_energy_summary():
    request = OptimizationRequest.model_validate(sample_payload())
    summary = validate_request_summary(request)
    assert summary["valid"] is True
    assert summary["estimated_daily_energy_kwh"] == 9.0
    assert summary["estimated_annual_energy_kwh"] == 3285.0


def test_battery_initial_soc_must_be_within_bounds():
    payload = sample_payload()
    payload["battery"]["soc_initial_fraction"] = 0.1
    try:
        OptimizationRequest.model_validate(payload)
    except Exception as exc:
        assert "soc_initial_fraction" in str(exc)
    else:
        raise AssertionError("Expected invalid SOC input to be rejected")


def test_accepts_current_input_cards_contract_shape():
    payload = sample_payload()
    payload["schema_version"] = "desanyala.input.v1"
    payload["optimization"]["scenarios"] = [
        {"id": "diesel_only", "pv": False, "battery": False},
        {"id": "pv_diesel", "pv": True, "battery": False},
        {"id": "pv_diesel_battery", "pv": True, "battery": True},
    ]
    payload["generators"]["unit_commitment_model"] = "requires_validation"
    req = OptimizationRequest.model_validate(payload)
    assert req.optimization.scenarios == ["diesel_only", "pv_diesel", "pv_diesel_battery"]
    assert req.generators.unit_commitment_model == "requires_validation"
