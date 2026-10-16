"""Generate an explicit, repeatable hourly demand estimate from appliance cards.

The profile is a planning approximation, not measured demand. It preserves the
energy implied by quantity * rated watts * hours/day while spreading average
load across a documented usage window.
"""
from app.schemas.input import DemandInput

USAGE_WINDOWS: dict[str, tuple[int, ...]] = {
    # Hour indices use a 24-hour local day. Night intentionally crosses midnight.
    "morning": (5, 6, 7, 8, 9, 10),
    "day": tuple(range(8, 17)),
    "evening": (17, 18, 19, 20, 21, 22),
    "night": (23, 0, 1, 2, 3, 4, 5),
    "all_day": tuple(range(24)),
}


def estimate_daily_energy_kwh(demand: DemandInput) -> float:
    """Compute energy from appliance nameplate power and daily use hours."""
    return sum(load.estimated_kwh_day for load in demand.loads)


def build_typical_day_demand_profile(demand: DemandInput) -> list[float]:
    """Return 24 average hourly kW values for a representative day.

    Every load's energy is distributed evenly over its selected usage window.
    Overlapping loads add together. This preserves the daily energy estimate but
    does not model stochastic coincidence, start-up surge, weekdays, or seasonality.
    """
    profile = [0.0] * 24
    for load in demand.loads:
        if load.quantity == 0 or load.power_w == 0 or load.hours_per_day == 0:
            continue
        window = USAGE_WINDOWS[load.usage_period]
        if load.hours_per_day > len(window) + 1e-9:
            raise ValueError(
                f"Peralatan '{load.device}': jam penggunaan ({load.hours_per_day}) "
                f"melebihi panjang periode '{load.usage_period}' ({len(window)} jam). "
                "Pilih periode yang lebih luas atau kurangi jam pemakaian."
            )
        rated_kw = load.quantity * load.power_w / 1000.0
        average_fraction = load.hours_per_day / len(window)
        for hour in window:
            profile[hour] += rated_kw * average_fraction
    return profile


def build_hourly_demand_profile(demand: DemandInput, period_days: int = 365) -> list[float]:
    """Repeat the declared typical day for the requested number of days."""
    if period_days < 1:
        raise ValueError("period_days must be >= 1")
    one_day = build_typical_day_demand_profile(demand)
    return one_day * period_days
