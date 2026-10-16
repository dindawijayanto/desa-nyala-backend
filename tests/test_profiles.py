from app.schemas.input import DemandInput, DemandLoad, PVInput
from app.services.demand_profile import estimate_daily_energy_kwh, build_hourly_demand_profile
from app.services.pv_profile import build_hourly_pv_profile


def test_demand_profile_preserves_declared_daily_energy():
    demand = DemandInput(loads=[
        DemandLoad(category="rumah", device="lampu", quantity=10, power_w=10, hours_per_day=6, usage_period="evening")
    ])
    profile = build_hourly_demand_profile(demand, 7)
    assert len(profile) == 168
    assert abs(sum(profile[:24]) - estimate_daily_energy_kwh(demand)) < 1e-8
    assert abs(sum(profile) - estimate_daily_energy_kwh(demand) * 7) < 1e-7


def test_pv_profile_has_expected_length_and_daily_energy():
    pv = PVInput(enabled=True, peak_sun_hours_estimate=4.5, system_performance_factor=0.8)
    profile = build_hourly_pv_profile(pv, 365)
    assert len(profile) == 8760
    assert abs(sum(profile[:24]) - 3.6) < 1e-8
    assert all(v >= 0 for v in profile)


def test_disabled_pv_is_zero():
    profile = build_hourly_pv_profile(PVInput(enabled=False), 7)
    assert len(profile) == 168
    assert sum(profile) == 0
