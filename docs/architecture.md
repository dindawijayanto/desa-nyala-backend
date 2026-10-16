# Backend folder guide

- `app/main.py`: constructs the FastAPI application and registers routes.
- `app/core/config.py`: reads environment configuration, including Offgridders root path.
- `app/api/routes/health.py`: health check.
- `app/api/routes/inputs.py`: validates the request contract and provides a daily energy summary.
- `app/api/routes/optimizations.py`: reserved optimization endpoint. It currently returns `501 Not Implemented` rather than pretending it ran a solver.
- `app/schemas/input.py`: Pydantic request models and validation.
- `app/schemas/results.py`: response/metrics/dispatch data models.
- `app/services/demand_profile.py`: daily energy sum now; hourly profile TODO.
- `app/services/pv_profile.py`: PV hourly profile TODO.
- `app/services/offgridders_adapter.py`: future workbook/time-series creation and subprocess bridge.
- `app/services/result_mapper.py`: future native output CSV mapping.
- `app/services/validation.py`: request sanity summary.
- `tests/`: basic request and API tests.
- `data/demo/`: clearly labeled synthetic/demo inputs, never mixed with real village measurements.
- `runs/`: per-run outputs; excluded from Git.
