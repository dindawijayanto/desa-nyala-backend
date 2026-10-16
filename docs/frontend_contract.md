# Frontend input contract (v1 proposal)

The intended request body is JSON with these top-level properties:

- `schema_version`
- `project`: `name`, `location`, `households`, `electrification_status`, `simulation_days`, `time_step_hours`, `project_lifetime_years`, `currency`
- `demand`: `profile_source`, `loads[]` (`category`, `device`, `quantity`, `power_w`, `hours_per_day`, `usage_period`, `critical`)
- `pv`: `enabled`, `resource_location`, `peak_sun_hours_estimate`, `system_performance_factor`, `capacity_mode`, `fixed_capacity_kwp`, `capacity_min_kwp`, `capacity_max_kwp`, `capex_per_kwp`, `opex_annual_per_kwp`, `lifetime_years`
- `generators`: `mode`, `unit_count`, `identical_units_assumption`, `rated_power_each_kw`, `min_loading_fraction`, `max_loading_fraction`, `fuel_price_per_liter`, `fuel_model`, `efficiency_fraction`, `capex_per_kw`, `opex_annual_per_unit`, `lifetime_years`, `unit_commitment_model`
- `battery`: `enabled`, `capacity_min_kwh`, `capacity_max_kwh`, `power_max_kw`, `charge_efficiency`, `discharge_efficiency`, `soc_min_fraction`, `soc_max_fraction`, `soc_initial_fraction`, `capex_per_kwh`, `power_capex_per_kw`, `lifetime_years`
- `economics`: `discount_rate`, `fuel_price_escalation_annual`, `additional_project_cost`
- `reliability`: `target_supply_fraction`, `shortage_policy`, `max_unmet_energy_fraction`, `reserve_margin_fraction`
- `optimization`: `objective`, `scenarios[]`, `solver_configuration`

Enums:
- `project.electrification_status`: `unserved | diesel_existing | hybrid_existing`
- `pv.capacity_mode`: `optimize | fixed`
- `generators.mode`: `existing | new`
- `generators.fuel_model`: `default | efficiency | curve`
- `reliability.shortage_policy`: `forbid | bounded`
- `optimization.objective`: `annualized_cost | fuel_consumption`
- `optimization.scenarios[]`: `diesel_only | pv_diesel | pv_diesel_battery`

Percent values should be sent as fractions in API JSON, e.g. 97% -> `0.97`. Currency fields must use the same currency and price basis across the request.

This is an API proposal. Ensure the current HTML `buildConfig()` serializes exactly these keys before wiring `fetch()`.
