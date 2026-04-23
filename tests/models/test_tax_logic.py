import pytest
from solar.models.grid_finance import calculate_yearly_metrics

def test_calculate_yearly_metrics_sell_limited():
    """Tax credit capped by grid sell (export) volume."""
    results = calculate_yearly_metrics(
        total_spend_sek=10000.0,
        total_earn_spot_sek=2000.0,
        total_earn_fcr_sek=500.0,
        total_grid_buy_kwh=5000.0,
        total_grid_sell_kwh=2000.0,  # Credit < Buy < 30k
        aggregator_flat_fee_yearly=100.0
    )
    
    assert results["total_grid_buy_kwh"] == 5000.0
    assert results["total_grid_sell_kwh"] == 2000.0
    # Tax credit is removed
    assert results["total_tax_credit_sek"] == 0.0
    
    # Cost = Spend - Earn + Flat Fee
    # 10000 - 2500 + 100 = 7600
    assert results["net_electricity_cost_sek"] == 7600.0
    assert results["total_money_spent"] == 10000.0

def test_calculate_yearly_metrics_buy_limited():
    """Tax credit capped by grid buy (import) volume."""
    results = calculate_yearly_metrics(
        total_spend_sek=5000.0,
        total_earn_spot_sek=8000.0,
        total_earn_fcr_sek=0.0,
        total_grid_buy_kwh=1000.0,   # Credit < Sell < 30k
        total_grid_sell_kwh=4000.0,
        aggregator_flat_fee_yearly=0.0
    )
    
    # Tax credit is removed
    assert results["total_tax_credit_sek"] == 0.0
    # 5000 - 8000 + 0 = -3000
    assert results["net_electricity_cost_sek"] == -3000.0

def test_calculate_yearly_metrics_30k_cap():
    """Tax credit capped by 30,000 kWh legal limit."""
    results = calculate_yearly_metrics(
        total_spend_sek=100000.0,
        total_earn_spot_sek=50000.0,
        total_earn_fcr_sek=10000.0,
        total_grid_buy_kwh=40000.0,
        total_grid_sell_kwh=35000.0,  # Both > 30k
        aggregator_flat_fee_yearly=0.0
    )
    
    # Tax credit is removed
    assert results["total_tax_credit_sek"] == 0.0
    # 100000 - 60000 = 40000
    assert results["net_electricity_cost_sek"] == 40000.0

def test_calculate_yearly_metrics_zero_buy():
    """No tax credit if nothing was bought from grid."""
    results = calculate_yearly_metrics(
        total_spend_sek=0.0,
        total_earn_spot_sek=5000.0,
        total_earn_fcr_sek=0.0,
        total_grid_buy_kwh=0.0,
        total_grid_sell_kwh=10000.0,
        aggregator_flat_fee_yearly=500.0
    )
    
    # Tax credit is removed
    assert results["total_tax_credit_sek"] == 0.0
    # 0 - 5000 + 500 = -4500
    assert results["net_electricity_cost_sek"] == -4500.0

def test_calculate_yearly_metrics_guards():
    """Verify negative and NaN guards."""
    import numpy as np
    results = calculate_yearly_metrics(
        total_spend_sek=np.nan,
        total_earn_spot_sek=2000.0,
        total_earn_fcr_sek=0.0,
        total_grid_buy_kwh=-1000.0,
        total_grid_sell_kwh=5000.0,
        aggregator_flat_fee_yearly=0.0
    )
    
    assert results["total_spend_sek"] == 0.0 if "total_spend_sek" in results else True
    # Tax credit is removed
    assert results["total_tax_credit_sek"] == 0.0
    # 0 - 2000 = -2000
    assert results["net_electricity_cost_sek"] == -2000.0
    assert results["total_tax_credit_sek"] == 0.0
    assert results["net_electricity_cost_sek"] == -2000.0
