# DesaNyala ↔ Offgridders mapping

This adapter intentionally supports only three scenarios:

- `diesel_only` → upstream case `diesel_mg`
- `pv_diesel` → upstream case `pv-diesel-mg`
- `pv_diesel_battery` → upstream case `pv-diesel-storage-mg`

Wind scenarios are disabled. The generated timeseries still includes a zero-valued `Wind` column to stay compatible with the provided workbook schema; no wind capacity or wind generation is selected.

## Input mappings

| DesaNyala field | Offgridders field | Notes |
|---|---|---|
| `project.simulation_days` | settings `evaluated_days` | Builds a matching hourly index |
| `demand.loads[]` | generated `Demand` timeseries | Estimated profile; not measured demand |
| `pv.peak_sun_hours_estimate`, `pv.system_performance_factor` | generated `SolarGen` timeseries | Simplified synthetic bell profile, repeated daily; not suitable as site-validated resource data |
| `pv.capex_per_kwp` | `pv_cost_investment` and fixed sensitivity value | Upstream sensitivity entry is updated because it overrides constant values |
| `pv.lifetime_years` | `pv_lifetime` and sensitivity value | same reason |
| `generators.fuel_price_per_liter` | `fuel_price` | Use consistent currency per litre |
| `generators.efficiency_fraction` | `genset_efficiency` | Constant efficiency approximation only |
| `generators.capex_per_kw` | `genset_cost_investment` | Currency per kW |
| `generators.min_loading_fraction` | `genset_min_loading` | Native parameter |
| `generators.max_loading_fraction` | `genset_max_loading` | Native parameter |
| `battery.capex_per_kwh` | `storage_capacity_cost_investment` | Currency per kWh |
| `battery.opex_annual_per_kwh` | `storage_capacity_cost_opex` | Currency per kWh/year |
| `battery.power_capex_per_kw` | `storage_power_cost_investment` | Currency per kW |
| `battery.power_opex_annual_per_kw` | `storage_power_cost_opex` | Currency per kW/year |
| `battery.charge_efficiency` / `discharge_efficiency` | storage efficiency constants | Native parameters |
| `economics.discount_rate` | `wacc` | Must use fraction form |
| `economics.additional_project_cost` | `project_cost_investment` | Currency |
| `reliability.shortage_policy` | settings and case `allow_shortage` | shortage fraction is configured separately |

## Known limitations, deliberately surfaced

- `fuel_price_escalation_annual` must be zero for now, because the user's observed engine log explicitly warned that nonzero `fuel_price_change_annual` calculation is faulty.
- A fixed PV capacity can be mapped to the case. For optimized PV, the UI `capacity_min_kwp` and `capacity_max_kwp` are not native input bounds in the workbook template; a post-solution bound check is performed, not a guarantee that the solver obeyed those bounds internally.
- Offgridders has `number_of_equal_generators`, but this adapter does not claim per-unit commitment (on/off, min-up/down, startup cost). Multi-unit dispatch must be separately verified/extended.
- A uniform repeating daily demand profile and synthetic solar profile are estimation inputs. For research/real planning, validate the profile-generation method against measured or authoritative hourly data.
- The upstream solver status should be reviewed with logs. A CSV existing is not alone proof that all numerical criteria are fully satisfied.
