# Offgridders adapter plan

## Scope

MVP scenarios:
1. Diesel-only
2. PV + diesel
3. PV + diesel + battery

Wind and main-grid import/export are outside the first DesaNyala UI scope.

## Adapter work to implement

1. Configure `OFFGRIDDERS_ROOT` to the user's validated local clone, pinned to a recorded commit.
2. Create a unique directory per run under `runs/<run_id>/`.
3. Copy a known template workbook into that run directory; do not edit the baseline workbook.
4. Generate a run-specific hourly time-series file in the exact delimiter, column names, units, and period convention expected by the clone.
5. Produce or modify a run-specific workbook with the correct `project_sites` and `case_definitions` and desired output folder.
6. Run Offgridders in a subprocess using an explicit executable path and a timeout. Capture stdout/stderr and exit code.
7. Read only files produced in that run directory. Check the native solver status and warnings.
8. Normalize summary fields and hourly dispatch into the schemas in `app/schemas/results.py`.
9. Validate 8,760 intervals for a non-leap 365-day hourly run, energy balance, SOC limits, capacity bounds, and shortages.
10. Return `optimal`/`feasible` only when evidence supports that status. Otherwise return `error` or `infeasible` with warnings.

## Open technical questions

- Exact per-unit generator behavior and unit commitment support in the selected Offgridders version.
- Correct meaning and units of `genset_cost_var`, `genset_efficiency`, and native generator capacity.
- Validated behavior of fuel price escalation; current logs warned about nonzero `fuel_price_change_annual`.
- Stability criterion warning reported during baseline runs; characterize before production use.
- How to supply fixed-vs-optimized component capacities in each `case_definitions` entry.
- Hourly demand generation model and documented hourly PV resource data.

## Attribution and license

Offgridders is an external project. If source is copied/modified, preserve required notices and follow its GPL-3.0 license. Record the exact upstream URL, commit hash, files changed, and tests run. This starter has not copied Offgridders source code.
