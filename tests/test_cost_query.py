"""Tests for cost_query module — mocked Azure SDK responses."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from azure_cost_analyzer.cost_query import (
    _execute_query,
    query_cost_by_resource_group,
    query_cost_by_meter,
    query_daily_cost_trend,
)


def _make_query_result(columns, rows, next_link=None):
    """Build a mock query result matching the Azure SDK shape."""
    result = MagicMock()
    col_objects = []
    for name in columns:
        col = MagicMock()
        col.name = name
        col_objects.append(col)
    result.columns = col_objects
    result.rows = rows
    result.next_link = next_link
    return result


@pytest.fixture
def mock_client():
    client = MagicMock()
    return client


class TestExecuteQuery:
    def test_basic_query(self, mock_client):
        mock_client.query.usage.return_value = _make_query_result(
            columns=["Cost", "ResourceGroup", "Currency"],
            rows=[[100.0, "rg-1", "USD"], [200.0, "rg-2", "USD"]],
        )
        df = _execute_query(mock_client, "/subscriptions/sub-1", MagicMock())
        assert len(df) == 2
        assert list(df.columns) == ["Cost", "ResourceGroup", "Currency"]

    def test_empty_result(self, mock_client):
        mock_client.query.usage.return_value = _make_query_result(
            columns=["Cost", "ResourceGroup"],
            rows=[],
        )
        df = _execute_query(mock_client, "/subscriptions/sub-1", MagicMock())
        assert df.empty

    def test_403_returns_empty(self, mock_client):
        from azure.core.exceptions import HttpResponseError
        error = HttpResponseError(message="Forbidden")
        error.status_code = 403
        mock_client.query.usage.side_effect = error
        df = _execute_query(mock_client, "/subscriptions/sub-1", MagicMock())
        assert df.empty

    def test_404_returns_empty(self, mock_client):
        from azure.core.exceptions import HttpResponseError
        error = HttpResponseError(message="Not found")
        error.status_code = 404
        mock_client.query.usage.side_effect = error
        df = _execute_query(mock_client, "/subscriptions/sub-1", MagicMock())
        assert df.empty

    @patch("azure_cost_analyzer.cost_query.time.sleep")
    def test_429_retries(self, mock_sleep, mock_client):
        from azure.core.exceptions import HttpResponseError
        error = HttpResponseError(message="Too many requests")
        error.status_code = 429
        success = _make_query_result(
            columns=["Cost", "ResourceGroup"],
            rows=[[100.0, "rg-1"]],
        )
        mock_client.query.usage.side_effect = [error, error, success]
        df = _execute_query(mock_client, "/subscriptions/sub-1", MagicMock())
        assert len(df) == 1
        assert mock_sleep.call_count == 2


class TestQueryFunctions:
    def test_query_cost_by_rg_adds_subscription_id(self, mock_client):
        mock_client.query.usage.return_value = _make_query_result(
            columns=["Cost", "ResourceGroup", "Currency"],
            rows=[[100.0, "rg-1", "USD"]],
        )
        df = query_cost_by_resource_group(
            mock_client, "sub-1", datetime(2024, 1, 1), datetime(2024, 1, 31),
        )
        assert "SubscriptionId" in df.columns
        assert df["SubscriptionId"].iloc[0] == "sub-1"

    def test_query_cost_by_meter(self, mock_client):
        mock_client.query.usage.return_value = _make_query_result(
            columns=["Cost", "ResourceGroup", "MeterCategory", "Currency"],
            rows=[[100.0, "rg-1", "Virtual Machines", "USD"]],
        )
        df = query_cost_by_meter(
            mock_client, "sub-1", datetime(2024, 1, 1), datetime(2024, 1, 31),
        )
        assert "MeterCategory" in df.columns

    def test_query_daily_trend(self, mock_client):
        mock_client.query.usage.return_value = _make_query_result(
            columns=["Cost", "UsageDate", "ResourceGroup", "Currency"],
            rows=[[100.0, "20240101", "rg-1", "USD"]],
        )
        df = query_daily_cost_trend(
            mock_client, "sub-1", datetime(2024, 1, 1), datetime(2024, 1, 31),
        )
        assert "UsageDate" in df.columns
