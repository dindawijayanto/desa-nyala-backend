import csv
from pathlib import Path
from app.services.result_mapper import parse_offgridders_summary


def test_maps_summary_and_dispatch_to_contract(tmp_path):
    output = tmp_path / 'outputs'
    dispatch_dir = output / 'electricity_mg'
    dispatch_dir.mkdir(parents=True)
    summary = output / 'results.csv'
    with summary.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'case','lcoe','annuity','npv','total_demand_annual_kWh',
            'total_demand_supplied_annual_kWh','total_demand_shortage_annual_kWh','res_share',
            'consumption_fuel_annual_l','co2_emissions_kgCO2eq','demand_peak_kW',
            'total_pv_generation_kWh','total_genset_generation_kWh','total_excess_annual_kWh',
            'capacity_pv_kWp','capacity_genset_kW','capacity_storage_kWh','power_storage_kW','comments'
        ])
        writer.writeheader()
        writer.writerow({
            'case':'pv-diesel-storage-mg','lcoe':0.3,'annuity':1000,'npv':5000,
            'total_demand_annual_kWh':1000,'total_demand_supplied_annual_kWh':1000,
            'total_demand_shortage_annual_kWh':0,'res_share':0.4,'consumption_fuel_annual_l':120,
            'co2_emissions_kgCO2eq':321.6,'demand_peak_kW':4,'total_pv_generation_kWh':500,
            'total_genset_generation_kWh':500,'total_excess_annual_kWh':0,'capacity_pv_kWp':2,
            'capacity_genset_kW':4,'capacity_storage_kWh':3,'power_storage_kW':1.5,'comments':''
        })
    dispatch = dispatch_dir / 'pv-diesel-storage-mg_s_test_electricity_mg.csv'
    with dispatch.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['timestep','Demand','PV generation','Genset generation','Storage charge','Storage discharge','Storage SOC','Excess generation','Demand shortage AC','Demand shortage DC'])
        writer.writeheader()
        writer.writerow({'timestep':'2018-01-01 00:00:00','Demand':2,'PV generation':1,'Genset generation':1,'Storage charge':0,'Storage discharge':0,'Storage SOC':0.5,'Excess generation':0,'Demand shortage AC':0,'Demand shortage DC':0})
    results = parse_offgridders_summary(summary, output, currency='IDR', generator_unit_count=1, expected_scenarios=['pv_diesel_battery'])
    assert len(results) == 1
    assert results[0].scenario_id == 'pv_diesel_battery'
    assert results[0].metrics.lcoe == 0.3
    assert len(results[0].dispatch) == 1
    assert results[0].dispatch[0].battery_soc_kwh == 1.5
    assert results[0].validation.energy_balance_passed is True
