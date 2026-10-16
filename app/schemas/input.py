from typing import Literal
from pydantic import BaseModel, Field, model_validator, field_validator


class ProjectInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    location: str = Field(min_length=1, max_length=240)
    households: int = Field(ge=0)
    electrification_status: Literal["unserved", "diesel_existing", "hybrid_existing"]
    simulation_days: Literal[7, 30, 365] = 365
    time_step_hours: Literal[1] = 1
    project_lifetime_years: int = Field(default=20, ge=1, le=60)
    currency: Literal["IDR", "USD"] = "IDR"


class DemandLoad(BaseModel):
    category: str = Field(min_length=1, max_length=80)
    device: str = Field(min_length=1, max_length=120)
    quantity: int = Field(ge=0)
    power_w: float = Field(ge=0)
    hours_per_day: float = Field(ge=0, le=24)
    usage_period: Literal["morning", "day", "evening", "night", "all_day"] = "all_day"
    critical: bool = False

    @model_validator(mode="after")
    def validate_usage_window(self):
        window_hours = {
            "morning": 6,
            "day": 9,
            "evening": 6,
            "night": 7,
            "all_day": 24,
        }[self.usage_period]
        if self.hours_per_day > window_hours + 1e-9:
            raise ValueError(
                f"hours_per_day tidak boleh melebihi {window_hours} jam untuk usage_period='{self.usage_period}'"
            )
        return self

    @property
    def estimated_kwh_day(self) -> float:
        return self.quantity * self.power_w * self.hours_per_day / 1000.0


class DemandInput(BaseModel):
    profile_source: Literal["equipment_estimate"] = "equipment_estimate"
    loads: list[DemandLoad] = Field(min_length=1)


class PVInput(BaseModel):
    enabled: bool = True
    resource_location: str | None = None
    peak_sun_hours_estimate: float = Field(default=4.5, ge=0, le=24)
    system_performance_factor: float = Field(default=0.8, gt=0, le=1)
    capacity_mode: Literal["optimize", "fixed"] = "optimize"
    fixed_capacity_kwp: float | None = Field(default=None, ge=0)
    capacity_min_kwp: float = Field(default=0, ge=0)
    capacity_max_kwp: float = Field(default=200, gt=0)
    capex_per_kwp: float = Field(default=0, ge=0)
    opex_annual_per_kwp: float = Field(default=0, ge=0)
    lifetime_years: int = Field(default=25, ge=1, le=60)

    @model_validator(mode="after")
    def validate_capacity(self):
        if self.capacity_max_kwp < self.capacity_min_kwp:
            raise ValueError("pv.capacity_max_kwp must be >= capacity_min_kwp")
        if self.capacity_mode == "fixed" and self.fixed_capacity_kwp is None:
            raise ValueError("fixed_capacity_kwp is required when capacity_mode='fixed'")
        if self.fixed_capacity_kwp is not None and not self.capacity_min_kwp <= self.fixed_capacity_kwp <= self.capacity_max_kwp:
            raise ValueError("fixed_capacity_kwp must be within the configured minimum/maximum bounds")
        return self


class GeneratorInput(BaseModel):
    mode: Literal["existing", "new"] = "new"
    unit_count: int = Field(default=1, ge=1, le=100)
    identical_units_assumption: bool = True
    rated_power_each_kw: float = Field(gt=0)
    min_loading_fraction: float = Field(default=0.3, ge=0, le=1)
    max_loading_fraction: float = Field(default=1.0, gt=0, le=1)
    fuel_price_per_liter: float = Field(gt=0)
    fuel_model: Literal["default", "efficiency", "curve"] = "efficiency"
    efficiency_fraction: float = Field(default=0.33, gt=0, le=1)
    capex_per_kw: float = Field(default=0, ge=0)
    opex_annual_per_unit: float = Field(default=0, ge=0)
    lifetime_years: int = Field(default=10, ge=1, le=60)
    unit_commitment_model: Literal["aggregate", "multi_unit", "requires_validation"] = "requires_validation"

    @model_validator(mode="after")
    def validate_load_limits(self):
        if self.min_loading_fraction > self.max_loading_fraction:
            raise ValueError("min_loading_fraction must be <= max_loading_fraction")
        if self.unit_count > 1 and self.unit_commitment_model == "multi_unit":
            # Schema accepts the requested mode but does not assert the optimizer supports it.
            pass
        return self


class BatteryInput(BaseModel):
    enabled: bool = True
    capacity_min_kwh: float = Field(default=0, ge=0)
    capacity_max_kwh: float = Field(default=200, ge=0)
    power_max_kw: float = Field(default=50, ge=0)
    charge_efficiency: float = Field(default=0.97, gt=0, le=1)
    discharge_efficiency: float = Field(default=0.97, gt=0, le=1)
    soc_min_fraction: float = Field(default=0.2, ge=0, le=1)
    soc_max_fraction: float = Field(default=1.0, ge=0, le=1)
    soc_initial_fraction: float = Field(default=0.5, ge=0, le=1)
    capex_per_kwh: float = Field(default=0, ge=0)
    opex_annual_per_kwh: float = Field(default=0, ge=0)
    power_capex_per_kw: float = Field(default=0, ge=0)
    power_opex_annual_per_kw: float = Field(default=0, ge=0)
    lifetime_years: int = Field(default=13, ge=1, le=60)

    @model_validator(mode="after")
    def validate_soc_and_capacity(self):
        if self.capacity_max_kwh < self.capacity_min_kwh:
            raise ValueError("battery.capacity_max_kwh must be >= capacity_min_kwh")
        if self.soc_min_fraction > self.soc_max_fraction:
            raise ValueError("battery.soc_min_fraction must be <= soc_max_fraction")
        if not self.soc_min_fraction <= self.soc_initial_fraction <= self.soc_max_fraction:
            raise ValueError("battery.soc_initial_fraction must be between soc_min_fraction and soc_max_fraction")
        return self


class EconomicsInput(BaseModel):
    discount_rate: float = Field(default=0.08, ge=0, le=1)
    fuel_price_escalation_annual: float = Field(default=0, ge=0, le=1)
    additional_project_cost: float = Field(default=0, ge=0)


class ReliabilityInput(BaseModel):
    target_supply_fraction: float = Field(default=0.995, gt=0, le=1)
    shortage_policy: Literal["forbid", "bounded"] = "forbid"
    max_unmet_energy_fraction: float = Field(default=0, ge=0, le=1)
    reserve_margin_fraction: float = Field(default=0.1, ge=0, le=2)

    @model_validator(mode="after")
    def validate_policy(self):
        if self.shortage_policy == "forbid" and self.max_unmet_energy_fraction != 0:
            raise ValueError("max_unmet_energy_fraction must be 0 when shortage_policy='forbid'")
        if self.shortage_policy == "bounded" and self.max_unmet_energy_fraction > (1 - self.target_supply_fraction + 1e-9):
            raise ValueError("max_unmet_energy_fraction conflicts with target_supply_fraction")
        return self


class OptimizationInput(BaseModel):
    objective: Literal["annualized_cost", "fuel_consumption"] = "annualized_cost"
    scenarios: list[Literal["diesel_only", "pv_diesel", "pv_diesel_battery"]] = Field(
        default_factory=lambda: ["diesel_only", "pv_diesel", "pv_diesel_battery"], min_length=1
    )
    solver_configuration: str = "backend_default"

    @field_validator("scenarios", mode="before")
    @classmethod
    def normalize_frontend_scenarios(cls, value):
        # The current input-cards HTML emits [{id, pv, battery}, ...], while the
        # internal API contract uses scenario IDs. Accept both versions.
        if isinstance(value, list):
            return [item.get("id") if isinstance(item, dict) else item for item in value]
        return value


class OptimizationRequest(BaseModel):
    schema_version: Literal["1.0.0", "desanyala.input.v1"] = "desanyala.input.v1"
    project: ProjectInput
    demand: DemandInput
    pv: PVInput
    generators: GeneratorInput
    battery: BatteryInput
    economics: EconomicsInput
    reliability: ReliabilityInput
    optimization: OptimizationInput

    @model_validator(mode="after")
    def validate_scenarios(self):
        if "pv_diesel" in self.optimization.scenarios and not self.pv.enabled:
            raise ValueError("Scenario pv_diesel selected but pv.enabled=false")
        if "pv_diesel_battery" in self.optimization.scenarios and (not self.pv.enabled or not self.battery.enabled):
            raise ValueError("Scenario pv_diesel_battery requires both pv.enabled and battery.enabled")
        if "diesel_only" in self.optimization.scenarios and self.generators.unit_count < 1:
            raise ValueError("diesel_only requires at least one generator")
        return self
