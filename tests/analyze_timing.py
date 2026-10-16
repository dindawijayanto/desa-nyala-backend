
import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path

folder = Path(r".\runs\native_bounds_hlmtr6g8\outputs\electricity_mg")

files = [
    p for p in folder.glob("*.csv")
    if "pv-diesel-mg_" in p.name
    and "pv-diesel-storage" not in p.name
]

if not files:
    raise FileNotFoundError("CSV dispatch skenario PV + genset tidak ditemukan.")

path = files[0]
hourly = defaultdict(lambda: {
    "demand_sum": 0.0,
    "demand_active": 0,
    "pv_sum": 0.0,
    "pv_with_demand": 0.0,
    "overlap_hours": 0,
    "genset_sum": 0.0,
})

with path.open("r", encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
        timestamp = datetime.strptime(
            row["timestep"], "%Y-%m-%d %H:%M:%S"
        )
        hour = timestamp.hour

        demand = float(row.get("Demand") or 0)
        pv = float(row.get("PV generation") or 0)
        genset = float(row.get("Genset generation") or 0)

        data = hourly[hour]
        data["demand_sum"] += demand
        data["pv_sum"] += pv
        data["genset_sum"] += genset

        if demand > 1e-9:
            data["demand_active"] += 1

        if demand > 1e-9 and pv > 1e-9:
            data["pv_with_demand"] += pv
            data["overlap_hours"] += 1

print("File:", path.name)
print("Ringkasan menurut jam dalam sehari selama satu tahun")
print(
    "Jam | Beban aktif | Total beban | Total PV | "
    "PV saat beban aktif | Jam overlap | Total genset"
)

for hour in range(24):
    d = hourly[hour]
    print(
        f"{hour:02d}:00 | "
        f"{d['demand_active']:4d} | "
        f"{d['demand_sum']:10.3f} | "
        f"{d['pv_sum']:8.3f} | "
        f"{d['pv_with_demand']:18.4f} | "
        f"{d['overlap_hours']:11d} | "
        f"{d['genset_sum']:12.3f}"
    )
