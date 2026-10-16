"""Create a clearly-labelled synthetic hourly PV yield profile.

The output is kW produced per kWp installed. It is a simplified deterministic
profile and must not be presented as measured/site-validated irradiance data.
"""
from math import sin, pi
from app.schemas.input import PVInput


def build_daily_pv_yield_profile(pv: PVInput) -> list[float]:
    """Return 24 hourly kW/kWp values whose daily sum matches PSH * performance.

    The noon-centred sine shape is intentionally simple. A production deployment
    should replace it with hourly resource data from a documented source.
    """
    if not pv.enabled:
        return [0.0] * 24
    target_daily_yield = pv.peak_sun_hours_estimate * pv.system_performance_factor
    profile = [0.0] * 24
    daylight_hours = range(6, 18)  # approximate 06:00–18:00 daylight window
    shape = {h: max(0.0, sin(pi * ((h + 0.5) - 6.0) / 12.0)) for h in daylight_hours}
    shape_sum = sum(shape.values())
    if target_daily_yield <= 0 or shape_sum <= 0:
        return profile
    scale = target_daily_yield / shape_sum
    for hour, value in shape.items():
        profile[hour] = value * scale
    return profile


def build_hourly_pv_profile(pv: PVInput, period_days: int) -> list[float]:
    """Repeat a typical PV day; output is kW/kWp for each hourly timestep."""
    if period_days < 1:
        raise ValueError("period_days must be >= 1")
    return build_daily_pv_yield_profile(pv) * period_days
