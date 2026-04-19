import numpy as np
import pytest
from solar.models.grid_finance import calculate_financials

def test_calculate_financials_basic():
    # Setup
    size = 10
    grid_buy = np.ones(size) * 1.0  # 1 kWh buy
    grid_sell = np.zeros(size)
    p_fcr_kw = 0.0
    spot_prices = np.ones(size) * 1.0  # 1 SEK/kWh
    fcr_prices = np.zeros(size)
    
    # Financial params
    grid_transfer_fee_sek = 0.18
    energy_tax_sek = 0.264
    vat_rate = 0.25
    utility_sell_compensation = 0.05
    aggregator_fee_pct = 0.20
    
    # Execute
    results = calculate_financials(
        grid_buy=grid_buy,
        grid_sell=grid_sell,
        p_fcr_kw=p_fcr_kw,
        price_spot_hourly=spot_prices,
        price_fcr_hourly=fcr_prices,
        grid_transfer_fee_sek=grid_transfer_fee_sek,
        energy_tax_sek=energy_tax_sek,
        vat_rate=vat_rate,
        utility_sell_compensation=utility_sell_compensation,
        aggregator_fee_pct=aggregator_fee_pct
    )
    
    # Verify Spend
    # Spend = 1.0 * ((1.0 + 0.18 + 0.264) * 1.25)
    # 1.444 * 1.25 = 1.805
    expected_spend = (1.0 + 0.18 + 0.264) * 1.25
    np.testing.assert_allclose(results["hourly_spend"], expected_spend)
    np.testing.assert_allclose(results["hourly_earn_spot"], 0.0)
    np.testing.assert_allclose(results["hourly_revenue_fcr"], 0.0)

def test_calculate_financials_fcr():
    # Setup
    size = 10
    grid_buy = np.zeros(size)
    grid_sell = np.zeros(size)
    p_fcr_kw = 10.0 # 10 kW
    spot_prices = np.zeros(size)
    fcr_prices = np.ones(size) * 1000.0 # 1000 SEK/MW/h
    
    # Financial params
    grid_transfer_fee_sek = 0.18
    energy_tax_sek = 0.264
    vat_rate = 0.25
    utility_sell_compensation = 0.05
    aggregator_fee_pct = 0.20
    
    # Execute
    results = calculate_financials(
        grid_buy=grid_buy,
        grid_sell=grid_sell,
        p_fcr_kw=p_fcr_kw,
        price_spot_hourly=spot_prices,
        price_fcr_hourly=fcr_prices,
        grid_transfer_fee_sek=grid_transfer_fee_sek,
        energy_tax_sek=energy_tax_sek,
        vat_rate=vat_rate,
        utility_sell_compensation=utility_sell_compensation,
        aggregator_fee_pct=aggregator_fee_pct
    )
    
    # Verify FCR Revenue
    # Rev_FCR = (10 / 1000) * 1000 * (1 - 0.20)
    # 0.01 * 1000 * 0.8 = 8.0 SEK
    expected_fcr = 8.0
    np.testing.assert_allclose(results["hourly_revenue_fcr"], expected_fcr)

def test_calculate_financials_zero_fcr():
    # Verify that if p_fcr_kw is 0, revenue is 0 even if prices are high
    results = calculate_financials(
        grid_buy=np.ones(10),
        grid_sell=np.zeros(10),
        p_fcr_kw=0.0,
        price_spot_hourly=np.ones(10),
        price_fcr_hourly=np.ones(10) * 1000, # Very high price
        grid_transfer_fee_sek=0.18,
        energy_tax_sek=0.264,
        vat_rate=0.25,
        utility_sell_compensation=0.05,
        aggregator_fee_pct=0.20
    )
    assert np.all(results["hourly_revenue_fcr"] == 0.0)

def test_calculate_financials_aggregator_no_fee():
    results = calculate_financials(
        grid_buy=np.zeros(10),
        grid_sell=np.zeros(10),
        p_fcr_kw=1000.0, # 1 MW
        price_spot_hourly=np.zeros(10),
        price_fcr_hourly=np.ones(10) * 100.0,
        grid_transfer_fee_sek=0.18,
        energy_tax_sek=0.264,
        vat_rate=0.25,
        utility_sell_compensation=0.05,
        aggregator_fee_pct=0.0 # No fee
    )
    # 1MW * 100SEK/MW/h * (1-0) = 100.0
    np.testing.assert_allclose(results["hourly_revenue_fcr"], 100.0)

def test_calculate_financials_negative_prices():
    # Spot price is -2.0, fees are 0.5. Combined stack = -1.5. Should cap at 0.
    results = calculate_financials(
        grid_buy=np.ones(10),
        grid_sell=np.ones(10),
        p_fcr_kw=0.0,
        price_spot_hourly=np.ones(10) * -2.0,
        price_fcr_hourly=np.zeros(10),
        grid_transfer_fee_sek=0.2, # Stack = -2.0 + 0.2 + 0.3 = -1.5
        energy_tax_sek=0.3,
        vat_rate=0.25,
        utility_sell_compensation=0.05, # Sell stack = -2.0 + 0.05 = -1.95
        aggregator_fee_pct=0.20
    )
    # Spend and Earn should both be 0.0 because of capping
    assert np.all(results["hourly_spend"] == 0.0)
    assert np.all(results["hourly_earn_spot"] == 0.0)

def test_calculate_financials_mismatched_shapes():
    with pytest.raises(ValueError, match="same shape"):
        calculate_financials(
            grid_buy=np.ones(10), # Length 10
            grid_sell=np.ones(5),  # Length 5
            p_fcr_kw=0.0,
            price_spot_hourly=np.ones(10),
            price_fcr_hourly=np.ones(10),
            grid_transfer_fee_sek=0.2,
            energy_tax_sek=0.3,
            vat_rate=0.25,
            utility_sell_compensation=0.05,
            aggregator_fee_pct=0.20
        )

def test_calculate_financials_invalid_fee():
    with pytest.raises(ValueError, match="between 0 and 1"):
        calculate_financials(
            grid_buy=np.ones(10),
            grid_sell=np.ones(10),
            p_fcr_kw=10.0,
            price_spot_hourly=np.ones(10),
            price_fcr_hourly=np.ones(10),
            grid_transfer_fee_sek=0.2,
            energy_tax_sek=0.3,
            vat_rate=0.25,
            utility_sell_compensation=0.05,
            aggregator_fee_pct=1.5 # Invalid
        )
