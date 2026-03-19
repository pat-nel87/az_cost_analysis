"""Shared test fixtures."""

import pandas as pd
import pytest


@pytest.fixture
def sample_rg_data():
    """Cost data grouped by resource group."""
    return pd.DataFrame({
        "Cost": [1500.0, 800.0, 350.0, 50.0, 5.0],
        "ResourceGroup": ["prod-rg", "staging-rg", "dev-rg", "sandbox-rg", "test-rg"],
        "Currency": ["USD"] * 5,
        "SubscriptionId": ["sub-1"] * 5,
        "SubscriptionName": ["Production"] * 5,
    })


@pytest.fixture
def sample_meter_data():
    """Cost data grouped by resource group and meter category."""
    return pd.DataFrame({
        "Cost": [800.0, 500.0, 200.0, 400.0, 300.0, 100.0, 200.0, 100.0, 50.0],
        "ResourceGroup": [
            "prod-rg", "prod-rg", "prod-rg",
            "staging-rg", "staging-rg",
            "dev-rg", "dev-rg",
            "sandbox-rg", "test-rg",
        ],
        "MeterCategory": [
            "Virtual Machines", "Storage", "Networking",
            "Virtual Machines", "Storage",
            "Virtual Machines", "SQL Database",
            "Virtual Machines", "Virtual Machines",
        ],
        "Currency": ["USD"] * 9,
        "SubscriptionId": ["sub-1"] * 9,
        "SubscriptionName": ["Production"] * 9,
    })


@pytest.fixture
def sample_trend_data():
    """Daily cost trend data."""
    dates = pd.date_range("2024-01-01", periods=5, freq="D")
    return pd.DataFrame({
        "Cost": [100.0, 120.0, 90.0, 110.0, 130.0],
        "UsageDate": [d.strftime("%Y%m%d") for d in dates],
        "ResourceGroup": ["prod-rg"] * 5,
        "Currency": ["USD"] * 5,
        "SubscriptionId": ["sub-1"] * 5,
        "SubscriptionName": ["Production"] * 5,
    })
