"""Tests for data_processing module."""

import pandas as pd
import pytest

from azure_cost_analyzer.data_processing import (
    aggregate_across_subscriptions,
    compute_summaries,
    exclude_resource_groups,
    filter_by_threshold,
)


class TestAggregateAcrossSubscriptions:
    def test_empty_list(self):
        result = aggregate_across_subscriptions([])
        assert result.empty

    def test_single_dataframe(self, sample_rg_data):
        result = aggregate_across_subscriptions([sample_rg_data])
        assert len(result) == len(sample_rg_data)

    def test_multiple_dataframes(self, sample_rg_data):
        df2 = sample_rg_data.copy()
        df2["SubscriptionId"] = "sub-2"
        result = aggregate_across_subscriptions([sample_rg_data, df2])
        assert len(result) == len(sample_rg_data) * 2


class TestFilterByThreshold:
    def test_filters_below_threshold(self, sample_rg_data):
        result = filter_by_threshold(sample_rg_data, 100.0)
        assert len(result) == 3
        assert all(result["Cost"] >= 100.0)

    def test_zero_threshold_keeps_all(self, sample_rg_data):
        result = filter_by_threshold(sample_rg_data, 0.0)
        assert len(result) == len(sample_rg_data)

    def test_empty_dataframe(self):
        result = filter_by_threshold(pd.DataFrame(), 10.0)
        assert result.empty


class TestExcludeResourceGroups:
    def test_excludes_named_groups(self, sample_rg_data):
        result = exclude_resource_groups(sample_rg_data, ["sandbox-rg", "test-rg"])
        assert len(result) == 3
        assert "sandbox-rg" not in result["ResourceGroup"].values
        assert "test-rg" not in result["ResourceGroup"].values

    def test_case_insensitive(self, sample_rg_data):
        result = exclude_resource_groups(sample_rg_data, ["SANDBOX-RG"])
        assert "sandbox-rg" not in result["ResourceGroup"].values

    def test_empty_exclude_list(self, sample_rg_data):
        result = exclude_resource_groups(sample_rg_data, [])
        assert len(result) == len(sample_rg_data)

    def test_empty_dataframe(self):
        result = exclude_resource_groups(pd.DataFrame(), ["foo"])
        assert result.empty


class TestComputeSummaries:
    def test_basic_summaries(self, sample_rg_data):
        result = compute_summaries(sample_rg_data)
        assert result["total_spend"] == 2705.0
        assert result["num_subscriptions"] == 1
        assert result["num_resource_groups"] == 5
        assert result["currency"] == "USD"

    def test_top_resource_groups(self, sample_rg_data):
        result = compute_summaries(sample_rg_data)
        top_rgs = result["top_resource_groups"]
        assert len(top_rgs) == 5
        assert top_rgs[0]["name"] == "prod-rg"
        assert top_rgs[0]["cost"] == 1500.0

    def test_top_meter_categories(self, sample_meter_data):
        result = compute_summaries(sample_meter_data)
        assert len(result["top_meter_categories"]) > 0
        # Virtual Machines should be top
        assert result["top_meter_categories"][0]["name"] == "Virtual Machines"

    def test_empty_dataframe(self):
        result = compute_summaries(pd.DataFrame())
        assert result["total_spend"] == 0.0
        assert result["num_subscriptions"] == 0

    def test_daily_average_with_dates(self, sample_trend_data):
        result = compute_summaries(sample_trend_data)
        # 5 days of data, total 550, avg should be 110
        assert result["daily_average"] == 110.0
