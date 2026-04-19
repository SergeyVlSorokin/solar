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
        tax_credit_rate=0.60,
        tax_credit_limit_kwh=30000.0,
        aggregator_flat_fee_yearly=100.0
    )
    
    # max_tax_kwh = min(5000, 2000, 30000) = 2000
    # credit = 2000 * 0.60 = 1200
    # net_cost = 10000 - (2000 + 500 + 1200) + 100 = 10000 - 3700 + 100 = 6400
    assert results["total_tax_credit_sek"] == 1200.0
    assert results["net_electricity_cost_sek"] == 6400.0
    assert results["total_money_spent"] == 10000.0

def test_calculate_yearly_metrics_buy_limited():
    """Tax credit capped by grid buy (import) volume."""
    results = calculate_yearly_metrics(
        total_spend_sek=5000.0,
        total_earn_spot_sek=8000.0,
        total_earn_fcr_sek=0.0,
        total_grid_buy_kwh=1000.0,   # Credit < Sell < 30k
        total_grid_sell_kwh=4000.0,
        tax_credit_rate=0.60,
        tax_credit_limit_kwh=30000.0,
        aggregator_flat_fee_yearly=0.0
    )
    
    # max_tax_kwh = min(1000, 4000, 30000) = 1000
    # credit = 1000 * 0.60 = 600
    # net_cost = 5000 - (8000 + 0 + 600) + 0 = 5000 - 8600 = -3600
    assert results["total_tax_credit_sek"] == 600.0
    assert results["net_electricity_cost_sek"] == -3600.0

def test_calculate_yearly_metrics_30k_cap():
    """Tax credit capped by 30,000 kWh legal limit."""
    results = calculate_yearly_metrics(
        total_spend_sek=100000.0,
        total_earn_spot_sek=50000.0,
        total_earn_fcr_sek=10000.0,
        total_grid_buy_kwh=40000.0,
        total_grid_sell_kwh=35000.0,  # Both > 30k
        tax_credit_rate=0.60,
        tax_credit_limit_kwh=30000.0,
        aggregator_flat_fee_yearly=0.0
    )
    
    # max_tax_kwh = min(40000, 35000, 30000) = 30000
    # credit = 30000 * 0.60 = 18000
    # net_cost = 100000 - (50000 + 10000 + 18000) = 100000 - 78000 = 22000
    assert results["total_tax_credit_sek"] == 18000.0
    assert results["net_electricity_cost_sek"] == 22000.0

def test_calculate_yearly_metrics_zero_buy():
    """No tax credit if nothing was bought from grid."""
    results = calculate_yearly_metrics(
        total_spend_sek=0.0,
        total_earn_spot_sek=5000.0,
        total_earn_fcr_sek=0.0,
        total_grid_buy_kwh=0.0,
        total_grid_sell_kwh=10000.0,
        tax_credit_rate=0.60,
        tax_credit_limit_kwh=30000.0,
        aggregator_flat_fee_yearly=500.0
    )
    
    assert results["total_tax_credit_sek"] == 0.0
    assert results["net_electricity_cost_sek"] == -5000.0 + 500.0  # -4500

def test_calculate_yearly_metrics_guards():
    """Verify negative and NaN guards."""
    import numpy as np
    results = calculate_yearly_metrics(
        total_spend_sek=np.nan,
        total_earn_spot_sek=2000.0,
        total_earn_fcr_sek=0.0,
        total_grid_buy_kwh=-1000.0,
        total_grid_sell_kwh=5000.0,
        tax_credit_rate=0.60,
        tax_credit_limit_kwh=30000.0,
        aggregator_flat_fee_yearly=0.0
    )
    
    # NaN spend -> 0
    # Negative buy -> 0
    # max_tax_kwh = min(5000, 0, 30000) = 0
    # net_cost = 0 - (2000 + 0 + 0) = -2000
    assert results["total_grid_buy_kwh"] == 0.0
    assert results["total_tax_credit_sek"] == 0.0
    assert results["net_electricity_cost_sek"] == -2000.0
