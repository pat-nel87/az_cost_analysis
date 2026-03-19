"""Cost Management API query functions."""

import logging
import time
from datetime import datetime

import pandas as pd
from azure.core.exceptions import HttpResponseError
from azure.identity import DefaultAzureCredential
from azure.mgmt.costmanagement import CostManagementClient
from azure.mgmt.costmanagement.models import (
    QueryAggregation,
    QueryDataset,
    QueryDefinition,
    QueryGrouping,
    QueryTimePeriod,
)

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BACKOFF_SECONDS = [1, 2, 4]


def _execute_query(
    client: CostManagementClient,
    scope: str,
    query: QueryDefinition,
) -> pd.DataFrame:
    """Execute a cost query with pagination and retry logic.

    Handles 429 (rate limit) with exponential backoff and
    skips subscriptions that return 403/404.
    """
    rows = []
    columns = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            result = client.query.usage(scope=scope, parameters=query)
            columns = [col.name for col in result.columns]
            rows.extend(result.rows)

            # Handle pagination
            while result.next_link:
                result = client.query.usage(scope=scope, parameters=query)
                rows.extend(result.rows)
                if not result.next_link:
                    break

            break
        except HttpResponseError as e:
            if e.status_code == 429:
                if attempt < MAX_RETRIES:
                    wait = BACKOFF_SECONDS[attempt]
                    logger.warning("Rate limited on %s, retrying in %ds...", scope, wait)
                    time.sleep(wait)
                    continue
                logger.error("Rate limit exceeded after %d retries for %s", MAX_RETRIES, scope)
                return pd.DataFrame()
            elif e.status_code == 403:
                logger.warning("Access denied for %s — skipping", scope)
                return pd.DataFrame()
            elif e.status_code == 404:
                logger.warning("Cost Management not available for %s — skipping", scope)
                return pd.DataFrame()
            else:
                logger.error("Query failed for %s: %s", scope, e.message)
                return pd.DataFrame()

    if not columns or not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows, columns=columns)


def _build_client(credential: DefaultAzureCredential) -> CostManagementClient:
    return CostManagementClient(credential)


def query_cost_by_resource_group(
    client: CostManagementClient,
    subscription_id: str,
    start_date: datetime,
    end_date: datetime,
) -> pd.DataFrame:
    """Query total cost grouped by resource group."""
    scope = f"/subscriptions/{subscription_id}"
    query = QueryDefinition(
        type="Usage",
        timeframe="Custom",
        time_period=QueryTimePeriod(from_property=start_date, to=end_date),
        dataset=QueryDataset(
            granularity="None",
            aggregation={
                "totalCost": QueryAggregation(name="Cost", function="Sum"),
            },
            grouping=[
                QueryGrouping(type="Dimension", name="ResourceGroup"),
            ],
        ),
    )
    df = _execute_query(client, scope, query)
    if not df.empty:
        df["SubscriptionId"] = subscription_id
    return df


def query_cost_by_meter(
    client: CostManagementClient,
    subscription_id: str,
    start_date: datetime,
    end_date: datetime,
) -> pd.DataFrame:
    """Query total cost grouped by resource group and meter category."""
    scope = f"/subscriptions/{subscription_id}"
    query = QueryDefinition(
        type="Usage",
        timeframe="Custom",
        time_period=QueryTimePeriod(from_property=start_date, to=end_date),
        dataset=QueryDataset(
            granularity="None",
            aggregation={
                "totalCost": QueryAggregation(name="Cost", function="Sum"),
            },
            grouping=[
                QueryGrouping(type="Dimension", name="ResourceGroup"),
                QueryGrouping(type="Dimension", name="MeterCategory"),
            ],
        ),
    )
    df = _execute_query(client, scope, query)
    if not df.empty:
        df["SubscriptionId"] = subscription_id
    return df


def query_daily_cost_trend(
    client: CostManagementClient,
    subscription_id: str,
    start_date: datetime,
    end_date: datetime,
) -> pd.DataFrame:
    """Query daily cost trend grouped by resource group."""
    scope = f"/subscriptions/{subscription_id}"
    query = QueryDefinition(
        type="Usage",
        timeframe="Custom",
        time_period=QueryTimePeriod(from_property=start_date, to=end_date),
        dataset=QueryDataset(
            granularity="Daily",
            aggregation={
                "totalCost": QueryAggregation(name="Cost", function="Sum"),
            },
            grouping=[
                QueryGrouping(type="Dimension", name="ResourceGroup"),
            ],
        ),
    )
    df = _execute_query(client, scope, query)
    if not df.empty:
        df["SubscriptionId"] = subscription_id
    return df


def fetch_all_cost_data(
    credential: DefaultAzureCredential,
    subscriptions: list[dict],
    start_date: datetime,
    end_date: datetime,
) -> dict[str, list[pd.DataFrame]]:
    """Fetch all cost data across subscriptions.

    Returns dict with keys: 'by_rg', 'by_meter', 'daily_trend',
    each containing a list of DataFrames (one per subscription).
    """
    client = _build_client(credential)
    should_throttle = len(subscriptions) > 10

    results: dict[str, list[pd.DataFrame]] = {
        "by_rg": [],
        "by_meter": [],
        "daily_trend": [],
    }

    for i, sub in enumerate(subscriptions):
        sub_id = sub["subscription_id"]
        sub_name = sub["display_name"]
        logger.info("Querying subscription %d/%d: %s (%s)",
                     i + 1, len(subscriptions), sub_name, sub_id)

        rg_df = query_cost_by_resource_group(client, sub_id, start_date, end_date)
        if not rg_df.empty:
            rg_df["SubscriptionName"] = sub_name
            results["by_rg"].append(rg_df)

        meter_df = query_cost_by_meter(client, sub_id, start_date, end_date)
        if not meter_df.empty:
            meter_df["SubscriptionName"] = sub_name
            results["by_meter"].append(meter_df)

        trend_df = query_daily_cost_trend(client, sub_id, start_date, end_date)
        if not trend_df.empty:
            trend_df["SubscriptionName"] = sub_name
            results["daily_trend"].append(trend_df)

        if should_throttle and i < len(subscriptions) - 1:
            time.sleep(2)

    return results
