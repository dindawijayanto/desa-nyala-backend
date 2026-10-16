
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from test_api import sample_payload
from app.schemas.input import OptimizationRequest
from app.services.offgridders_adapter import OffgriddersAdapter

payload = sample_payload()

# Test batas kapasitas PV.
payload["pv"]["enabled"] = True
payload["pv"]["capacity_mode"] = "optimize"
payload["pv"]["capacity_min_kwp"] = 0.1
payload["pv"]["capacity_max_kwp"] = 0.2

# Test batas kapasitas dan daya baterai.
payload["battery"]["enabled"] = True
payload["battery"]["capacity_min_kwh"] = 0.1
payload["battery"]["capacity_max_kwh"] = 0.2
payload["battery"]["power_max_kw"] = 0.1

request = OptimizationRequest.model_validate(payload)

runs = ROOT / "runs"
runs.mkdir(parents=True, exist_ok=True)
run_dir = Path(
    tempfile.mkdtemp(prefix="native_bounds_", dir=runs)
)

adapter = OffgriddersAdapter(
    offgridders_root=ROOT / "engine" / "offgridders",
    python_executable=(
        r"C:\Users\ASUS\miniconda3\envs\offgridders_env\python.exe"
    ),
)

print("Run directory:", run_dir)
print(
    "PV bounds:",
    request.pv.capacity_min_kwp,
    "-",
    request.pv.capacity_max_kwp,
    "kWp",
)
print(
    "Battery bounds:",
    request.battery.capacity_min_kwh,
    "-",
    request.battery.capacity_max_kwh,
    "kWh",
)
print("Battery power maximum:", request.battery.power_max_kw, "kW")
print("Starting native optimization...")

try:
    result = adapter.run(request, run_dir)

    def inspect_result(obj):
        if hasattr(obj, "model_dump"):
            obj = obj.model_dump()

        if isinstance(obj, dict):
            if "scenario_id" in obj:
                print("\nScenario:", obj.get("scenario_id"))
                print("Status:", obj.get("status"))
                print("Capacities:", obj.get("capacities"))
                print("Validation:", obj.get("validation"))

            for value in obj.values():
                inspect_result(value)

        elif isinstance(obj, (list, tuple)):
            for value in obj:
                inspect_result(value)

    inspect_result(result)
    print("\nINTEGRATION RUN COMPLETED")
    print("Inspect output and logs in:", run_dir)

except Exception as exc:
    print("\nINTEGRATION RUN FAILED:", type(exc).__name__, str(exc))
    print("Inspect output and logs in:", run_dir)
    raise
