"""Data aggregation and transformation for cost data."""

import pandas as pd


def aggregate_across_subscriptions(dataframes: list[pd.DataFrame]) -> pd.DataFrame:
    """Concatenate cost DataFrames from multiple subscriptions."""
    if not dataframes:
        return pd.DataFrame()
    return pd.concat(dataframes, ignore_index=True)


def filter_by_threshold(df: pd.DataFrame, min_cost: float) -> pd.DataFrame:
    """Drop rows where cost is below the minimum threshold."""
    if df.empty or "Cost" not in df.columns:
        return df
    return df[df["Cost"] >= min_cost].reset_index(drop=True)


def exclude_resource_groups(df: pd.DataFrame, exclude_list: list[str]) -> pd.DataFrame:
    """Remove rows matching excluded resource group names (case-insensitive)."""
    if df.empty or "ResourceGroup" not in df.columns or not exclude_list:
        return df
    exclude_lower = {name.lower() for name in exclude_list}
    return df[~df["ResourceGroup"].str.lower().isin(exclude_lower)].reset_index(drop=True)


def compute_summaries(df: pd.DataFrame) -> dict:
    """Compute summary statistics from resource-group-level cost data.

    Args:
        df: DataFrame with at least Cost and ResourceGroup columns.

    Returns:
        Dict with total_spend, daily_average, top_resource_groups,
        top_meter_categories, num_subscriptions, num_resource_groups.
    """
    if df.empty:
        return {
            "total_spend": 0.0,
            "daily_average": 0.0,
            "top_resource_groups": [],
            "top_meter_categories": [],
            "num_subscriptions": 0,
            "num_resource_groups": 0,
            "currency": "USD",
        }

    total_spend = df["Cost"].sum()

    num_subscriptions = df["SubscriptionId"].nunique() if "SubscriptionId" in df.columns else 1
    num_resource_groups = df["ResourceGroup"].nunique() if "ResourceGroup" in df.columns else 0

    # Top 5 resource groups by cost
    top_rgs = []
    if "ResourceGroup" in df.columns:
        rg_costs = df.groupby("ResourceGroup")["Cost"].sum().nlargest(5)
        top_rgs = [{"name": name, "cost": cost} for name, cost in rg_costs.items()]

    # Top 5 meter categories by cost
    top_meters = []
    if "MeterCategory" in df.columns:
        meter_costs = df.groupby("MeterCategory")["Cost"].sum().nlargest(5)
        top_meters = [{"name": name, "cost": cost} for name, cost in meter_costs.items()]

    # Currency from the data (Cost Management returns a Currency column)
    currency = "USD"
    if "Currency" in df.columns and not df["Currency"].empty:
        currency = df["Currency"].iloc[0]

    # Compute daily average from the date range span
    daily_average = 0.0
    if "UsageDate" in df.columns and len(df) > 0:
        dates = pd.to_datetime(df["UsageDate"].astype(str))
        date_span = (dates.max() - dates.min()).days + 1
        daily_average = total_spend / max(date_span, 1)
    elif total_spend > 0:
        daily_average = total_spend / 30  # fallback estimate

    return {
        "total_spend": round(total_spend, 2),
        "daily_average": round(daily_average, 2),
        "top_resource_groups": top_rgs,
        "top_meter_categories": top_meters,
        "num_subscriptions": num_subscriptions,
        "num_resource_groups": num_resource_groups,
        "currency": currency,
    }
