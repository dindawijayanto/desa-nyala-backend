# Contract notes for frontend integration

Use `docs/frontend_input_variables.txt` and `docs/frontend_output_variables.txt` as the current field-name references. The Pydantic request model in `app/schemas/input.py` is the authoritative runtime validation contract for the backend version in this package.

Important mismatches/limits surfaced explicitly by this integration:

- `reliability.reserve_margin_fraction` must currently be `0`; no reserve-margin constraint has been added to the native model.
- `generators.fuel_model="curve"` is rejected; only a constant efficiency approximation is currently mapped.
- `optimization.objective` must be `annualized_cost`; fuel-minimization as a separate objective is not implemented.
- `generators.unit_commitment_model="multi_unit"` with more than one unit is rejected; a multi-generator on/off schedule cannot yet be claimed.
- `generators.mode="new"` lets Offgridders optimize capacity, but the UI's `rated_power_each_kw` is not a hard upper capacity limit.
- `pv.capacity_min_kwp > 0` or `battery.capacity_min_kwh > 0` in optimize mode is rejected because such lower bounds are not present in the supplied native workbook model.
- PV maximum, battery maximum, and battery maximum power are post-checked. The native optimizer may return a solution outside these UI limits; such a solution is flagged and must not be presented as meeting all requested constraints.
- `DemandLoad.critical` is not separately prioritized in the native single Demand time series. This remains future work.

Avoid renaming JSON fields after frontend wiring without versioning the contract.
