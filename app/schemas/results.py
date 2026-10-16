from typing import Literal
from pydantic import BaseModel, Field


RunStatus = Literal["queued", "running", "optimal", "feasible", "infeasible", "error", "not_implemented"]


class ValidationReport(BaseModel):
    energy_balance_passed: bool | None = None
    reliability_passed: bool | None = None
    capacity_constraints_passed: bool | None = None
    solver_message: str | None = None
    warnings: list[str] = Field(default_factory=list)


class ScenarioMetrics(BaseModel):
    lcoe: float | None = None
    annualized_cost: float | None = None
    npv: float | None = None
    annual_demand_kwh: float | None = None
    annual_supplied_kwh: float | None = None
    annual_unmet_energy_kwh: float | None = None
    supply_reliability_fraction: float | None = None
    renewable_share_fraction: float | None = None
    annual_fuel_liters: float | None = None
    annual_co2_kg: float | None = None
    peak_demand_kw: float | None = None
    annual_pv_generation_kwh: float | None = None
    annual_genset_generation_kwh: float | None = None
    annual_excess_energy_kwh: float | None = None


class Capacities(BaseModel):
    pv_kwp: float | None = None
    genset_kw: float | None = None
    battery_kwh: float | None = None
    battery_power_kw: float | None = None
    genset_capacity_basis: Literal["aggregate", "per_unit", "unknown"] = "unknown"


class DispatchPoint(BaseModel):
    timestamp: str
    demand_kw: float
    pv_kw: float = 0
    generator_power_kw: float = 0
    battery_charge_kw: float = 0
    battery_discharge_kw: float = 0
    battery_soc_kwh: float | None = None
    battery_soc_fraction: float | None = None
    excess_power_kw: float = 0
    unmet_demand_kw: float = 0


class ScenarioResult(BaseModel):
    scenario_id: str
    scenario_name: str
    status: RunStatus
    metrics: ScenarioMetrics = Field(default_factory=ScenarioMetrics)
    capacities: Capacities = Field(default_factory=Capacities)
    validation: ValidationReport = Field(default_factory=ValidationReport)
    dispatch: list[DispatchPoint] = Field(default_factory=list)


class OptimizationResponse(BaseModel):
    schema_version: str = "1.0.0"
    project_id: str
    status: RunStatus
    generated_at: str
    period_days: int
    time_step_hours: float
    units: dict[str, str]
    selected_scenario_id: str | None = None
    scenario_results: list[ScenarioResult] = Field(default_factory=list)
    validation: ValidationReport = Field(default_factory=ValidationReport)
    warnings: list[str] = Field(default_factory=list)
