# Implementation checklist

- [ ] Compare the current HTML `buildConfig()` keys with `app/schemas/input.py`; reconcile any mismatches before integration.
- [ ] Implement profile preview endpoint that returns 24-hour and annual demand curves, with explicit assumptions.
- [ ] Decide/document the demand coincidence model and seasonal/weekday pattern.
- [ ] Choose a documented source/model for hourly PV yield; validate units and timezone.
- [ ] Pin Offgridders upstream commit and record license requirements.
- [ ] Implement per-run workbook and time-series creation.
- [ ] Implement run subprocess, timeouts, cancellation/error handling, and per-run logs.
- [ ] Parse summary and electricity/storage CSVs from that run only.
- [ ] Validate energy balance, SOC, bounds, annual energy, fuel, cost basis, and solver warnings.
- [ ] Implement multi-generator scheduling only if required after verifying the existing model's capabilities.
- [ ] Connect the frontend `fetch()` call and handle errors/loading/status.
