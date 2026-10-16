from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status

from app.core.config import settings
from app.schemas.input import OptimizationRequest
from app.schemas.results import OptimizationResponse, ValidationReport
from app.services.offgridders_adapter import (
    OffgriddersAdapter,
    OffgriddersAdapterError,
    OffgriddersAdapterNotConfigured,
)
from app.services.demand_profile import estimate_daily_energy_kwh, build_hourly_demand_profile
from app.services.pv_profile import build_hourly_pv_profile

router = APIRouter(prefix="/optimizations", tags=["optimizations"])


@router.post("", response_model=OptimizationResponse, status_code=status.HTTP_200_OK)
def create_optimization(request: OptimizationRequest) -> OptimizationResponse:
    """Run selected scenarios via an isolated, embedded Offgridders copy."""
    run_id = uuid4().hex
    run_dir = settings.runs_dir / run_id
    adapter = OffgriddersAdapter(
        settings.offgridders_root,
        python_executable=settings.offgridders_python,
        timeout_seconds=settings.offgridders_timeout_seconds,
    )
    try:
        results = adapter.run(request, run_dir)
    except OffgriddersAdapterNotConfigured as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_configured",
                "message": str(exc),
                "next_step": "Run scripts/import_offgridders.ps1 and verify the Offgridders environment.",
            },
        ) from exc
    except OffgriddersAdapterError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "status": "engine_error",
                "message": str(exc),
                "run_dir": str(run_dir),
            },
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"status": "invalid_input", "message": str(exc)}) from exc

    scenario_results = results["scenarios"]
    warnings = results["warnings"]
    if len(scenario_results) != len(request.optimization.scenarios):
        warnings.append("Jumlah skenario hasil tidak sama dengan skenario yang diminta.")
    demand_profile = build_hourly_demand_profile(request.demand, request.project.simulation_days)
    pv_profile = build_hourly_pv_profile(request.pv, request.project.simulation_days)
    total_daily_kwh = estimate_daily_energy_kwh(request.demand)
    # Any scenario-level energy balance failure is surfaced rather than hidden.
    balance_values = [r.validation.energy_balance_passed for r in scenario_results if r.validation.energy_balance_passed is not None]
    overall_balance = all(balance_values) if balance_values else None
    shortages = [r.validation.reliability_passed for r in scenario_results if r.validation.reliability_passed is not None]
    overall_reliability = all(shortages) if shortages else None
    overall_capacity = None
    if scenario_results and all(
        result.status != "error"
        and result.validation.capacity_constraints_passed is not None
        for result in scenario_results
    ):
        overall_capacity = all(
            result.validation.capacity_constraints_passed is True
            for result in scenario_results
        )
    return OptimizationResponse(
        schema_version="1.0.0",
        project_id=run_id,
        status=results["status"],
        generated_at=results["generated_at"],
        period_days=request.project.simulation_days,
        time_step_hours=float(request.project.time_step_hours),
        units={
            "currency": request.project.currency,
            "lcoe": f"{request.project.currency}/kWh",
            "energy": "kWh",
            "power": "kW",
            "pv_capacity": "kWp",
            "battery_capacity": "kWh",
            "fuel": "L/year",
            "emissions": "kgCO2eq/year",
        },
        selected_scenario_id=(
            request.optimization.scenarios[0]
            if request.optimization.scenarios
            else None
        ),
        scenario_results=scenario_results,
        validation=ValidationReport(
            energy_balance_passed=overall_balance,
            reliability_passed=overall_reliability,
            capacity_constraints_passed=overall_capacity,
            solver_message=(
                f"Engine selesai; profil demand berisi {len(demand_profile)} interval dan "
                f"profil PV berisi {len(pv_profile)} interval. Data run: {results['output_dir']}"
            ),
            warnings=warnings,
        ),
        warnings=warnings,
    )
