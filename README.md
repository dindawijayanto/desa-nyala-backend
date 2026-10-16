# DesaNyala Backend + Offgridders Engine Adapter

Backend for the DesaNyala PV + diesel + optional battery planning flow. This package contains the adapter, input validation, a simple documented demand/PV profile generator, result normalization, tests, an Offgridders import script, and the input workbook template supplied for this project.

**Important source note:** the user's actual Offgridders checkout was not included in the artifact environment. The folder `engine/offgridders/` is therefore a destination placeholder until you run `scripts/import_offgridders.ps1` against your existing local clone. No fake/offline stub is returned as an optimization result. Once imported, `POST /api/v1/optimizations` configures a run-specific workbook/timeseries and invokes the embedded engine as a subprocess.

## Workspace expected by the import script

```text
desa-nyala/
  backend/                 # this folder
    scripts/import_offgridders.ps1
    engine/offgridders/    # populated by import script
  offgridders/             # the existing clone from your previous work
```

## Import the existing engine (Windows PowerShell)

Open PowerShell in `backend/` and run:

```powershell
.\scripts\import_offgridders.ps1
.\scripts\verify_engine.ps1
```

If your clone is elsewhere:

```powershell
.\scripts\import_offgridders.ps1 -SourceRoot 'C:\Users\ASUS\.vscode\desa-nyala\offgridders'
```

The script excludes `.git`, Python virtual environments, generated simulation output folders, logs, and generated result CSVs. It copies the source tree plus LICENSE/notices and records source remote + commit. Check the upstream license in `engine/offgridders/` before distributing a modified bundle. Do not remove upstream attribution.

## Install and run API (Windows CMD)

Use a Python environment with backend dependencies installed:

```cmd
cd backend
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

Offgridders also needs its own upstream dependencies and solver (in your current setup, CBC). To use the already-working conda environment, set `OFFGRIDDERS_PYTHON` before launching the API, for example:

```cmd
set OFFGRIDDERS_PYTHON=C:\Users\ASUS\miniconda3\envs\offgridders_env\python.exe
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs`.

## API endpoints

- `GET /health`: API + embedded engine presence.
- `POST /api/v1/inputs/validate`: validates the cards contract and estimates daily energy.
- `POST /api/v1/optimizations`: generates hourly profiles, configures a run-specific Excel input and CSV time series, invokes Offgridders, parses the result summary/dispatch CSVs, and returns the frontend response schema.

Each run lives in `runs/<run_id>/`; it includes the generated config, hourly input series, output files, and stdout/stderr logs. The source template is not edited in place.

## Supported scope of the adapter

- Native cases: `diesel_mg`, `pv-diesel-mg`, `pv-diesel-storage-mg`.
- Wind case is disabled. The generated input CSV retains an all-zero `Wind` column only because the source workbook schema includes it.
- User's `pv_cost_investment` and `pv_lifetime` values are also written to sensitivity rows because the observed template's sensitivity values override constants.
- A nonzero annual diesel-price escalation is rejected for now because your observed engine log explicitly warns that this calculation is faulty.
- The current native model has not been validated for per-unit startup/on-off commitment. Requests that explicitly ask for multi-unit commitment are rejected instead of pretending it works.
- Optimized PV/battery minimum constraints are not native bounds in the supplied template. Requests with nonzero optimized minimum PV/battery sizes are rejected until those constraints are added to the model. Output bounds are also checked in future validation before those fields can be treated as guaranteed constraints.
- Demand profile: equipment wattage x quantity x daily run hours is spread over a declared period of use and repeated each day. This preserves daily energy but does not represent stochastic coincidence, weekdays/weekends, seasonal demand, or motor start surges.
- PV profile: a simplified daylight curve whose daily sum equals `peak_sun_hours_estimate * system_performance_factor`. This is an estimate, not site-validated weather/irradiance. For actual planning, use a documented hourly resource profile/provider and record its provenance.
- `target_supply_fraction` is not an independent native constraint. `shortage_policy=forbid` maps to zero allowed shortage; bounded maps to the allowed shortage fraction.
- Output capacity of multi-generator cases is marked unknown basis; verify native semantics before displaying per-unit capacity.

## Tests

Run in the backend environment:

```cmd
pytest -q
```

Tests cover schema validation and deterministic profile generation. The real solver integration test must be run on the user's Windows machine after importing Offgridders, because the upstream engine checkout and solver environment were not present in this package-generation runtime.
