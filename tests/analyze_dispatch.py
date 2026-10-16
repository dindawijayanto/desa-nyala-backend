
import csv
from pathlib import Path

root = Path(r".\runs\native_bounds_hlmtr6g8\outputs")
dispatch_dir = root / "electricity_mg"

columns = [
    "Demand",
    "PV generation",
    "Excess generation",
    "Genset generation",
    "Storage charge",
    "Storage discharge",
]


def number(row, column):
    """Ambil angka dari CSV; kolom yang tidak tersedia dianggap kosong."""
    try:
        return float(row.get(column, "") or 0)
    except (ValueError, TypeError):
        return 0.0


for path in sorted(dispatch_dir.glob("*.csv")):
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    print(f"\n{'=' * 70}")
    print(path.name)
    print(f"Jumlah timestep: {len(rows)}")

    for col in columns:
        if not rows or col not in rows[0]:
            continue

        values = [number(row, col) for row in rows]
        print(
            f"{col}: total={sum(values):.4f}, "
            f"maksimum={max(values):.4f}, "
            f"timestep aktif={sum(abs(v) > 1e-9 for v in values)}"
        )

    if not rows or "PV generation" not in rows[0]:
        continue

    pv = [max(0.0, number(r, "PV generation")) for r in rows]
    demand = [number(r, "Demand") for r in rows]
    genset = [number(r, "Genset generation") for r in rows]
    excess = [
        max(0.0, number(r, "Excess generation")) for r in rows
    ]

    demand_positive = [d > 1e-9 for d in demand]

    print(
        "Jam PV dan beban sama-sama positif:",
        sum(p > 1e-9 and d for p, d in zip(pv, demand_positive)),
    )
    print(
        "Produksi PV saat beban positif:",
        f"{sum(p for p, d in zip(pv, demand_positive) if d):.4f}",
    )
    print(
        "Jam PV dan genset sama-sama berproduksi:",
        sum(p > 1e-9 and g > 1e-9 for p, g in zip(pv, genset)),
    )
    print(
        "Rasio energi berlebih terhadap produksi PV:",
        f"{sum(excess) / sum(pv):.2%}" if sum(pv) > 0
        else "Tidak ada produksi PV",
    )

    active = [
        r for r, p in zip(rows, pv) if p > 1e-9
    ]

    print("\nContoh 10 timestep saat PV berproduksi:")
    for row in active[:10]:
        print({
            key: row.get(key)
            for key in [
                "timestep",
                "Demand",
                "PV generation",
                "Excess generation",
                "Genset generation",
            ]
            if key in row
        })
