"""Plotly chart generation and HTML report assembly."""

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.io as pio
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "templates"


def _chart_spend_by_rg(df: pd.DataFrame) -> str | None:
    """Horizontal bar chart of top resource groups by cost."""
    if df.empty or "ResourceGroup" not in df.columns:
        return None
    rg_costs = df.groupby("ResourceGroup")["Cost"].sum().nlargest(20).sort_values()
    chart_df = rg_costs.reset_index()
    fig = px.bar(
        chart_df,
        x="Cost",
        y="ResourceGroup",
        orientation="h",
        title="Spend by Resource Group (Top 20)",
        labels={"Cost": "Cost (USD)", "ResourceGroup": "Resource Group"},
    )
    fig.update_layout(height=max(400, len(chart_df) * 28), margin=dict(l=200))
    return pio.to_html(fig, full_html=False, include_plotlyjs=False)


def _chart_meter_treemap(df: pd.DataFrame) -> str | None:
    """Treemap: resource group -> meter category."""
    if df.empty or "MeterCategory" not in df.columns:
        return None
    grouped = df.groupby(["ResourceGroup", "MeterCategory"])["Cost"].sum().reset_index()
    grouped = grouped[grouped["Cost"] > 0]
    if grouped.empty:
        return None
    fig = px.treemap(
        grouped,
        path=["ResourceGroup", "MeterCategory"],
        values="Cost",
        title="Spend by Meter Category",
    )
    fig.update_layout(height=600)
    return pio.to_html(fig, full_html=False, include_plotlyjs=False)


def _chart_daily_trend(df: pd.DataFrame) -> str | None:
    """Stacked area chart of daily costs by resource group."""
    if df.empty or "UsageDate" not in df.columns:
        return None
    df = df.copy()
    df["UsageDate"] = pd.to_datetime(df["UsageDate"].astype(str))
    # Keep top 10 RGs by total cost, group rest as "Other"
    rg_totals = df.groupby("ResourceGroup")["Cost"].sum().nlargest(10)
    top_rgs = set(rg_totals.index)
    df["ResourceGroup"] = df["ResourceGroup"].where(df["ResourceGroup"].isin(top_rgs), "Other")
    daily = df.groupby(["UsageDate", "ResourceGroup"])["Cost"].sum().reset_index()
    fig = px.area(
        daily,
        x="UsageDate",
        y="Cost",
        color="ResourceGroup",
        title="Daily Cost Trend",
        labels={"Cost": "Cost (USD)", "UsageDate": "Date"},
    )
    fig.update_layout(height=500)
    return pio.to_html(fig, full_html=False, include_plotlyjs=False)


def _chart_sunburst(df: pd.DataFrame) -> str | None:
    """Sunburst: subscription -> resource group -> meter category."""
    if df.empty or "MeterCategory" not in df.columns:
        return None
    cols = []
    if "SubscriptionName" in df.columns:
        cols.append("SubscriptionName")
    cols.extend(["ResourceGroup", "MeterCategory"])
    grouped = df.groupby(cols)["Cost"].sum().reset_index()
    grouped = grouped[grouped["Cost"] > 0]
    if grouped.empty:
        return None
    fig = px.sunburst(
        grouped,
        path=cols,
        values="Cost",
        title="Cost Hierarchy",
    )
    fig.update_layout(height=600)
    return pio.to_html(fig, full_html=False, include_plotlyjs=False)


def _build_data_table(df: pd.DataFrame) -> list[dict]:
    """Build row data for the sortable HTML table."""
    if df.empty:
        return []
    table_cols = ["SubscriptionName", "ResourceGroup", "MeterCategory", "Cost", "Currency"]
    available = [c for c in table_cols if c in df.columns]
    table_df = df[available].copy()
    if "Cost" in table_df.columns:
        table_df = table_df.sort_values("Cost", ascending=False)
        table_df["Cost"] = table_df["Cost"].round(2)
    return table_df.to_dict("records")


def generate_report(
    rg_data: pd.DataFrame,
    meter_data: pd.DataFrame,
    trend_data: pd.DataFrame,
    summaries: dict,
    start_date: datetime,
    end_date: datetime,
    output_path: str,
) -> str:
    """Generate the full interactive HTML report.

    Returns the output file path.
    """
    charts = {
        "rg_bar": _chart_spend_by_rg(rg_data),
        "meter_treemap": _chart_meter_treemap(meter_data),
        "daily_trend": _chart_daily_trend(trend_data),
        "sunburst": _chart_sunburst(meter_data),
    }

    table_rows = _build_data_table(meter_data)

    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=True)
    template = env.get_template("report.html.j2")

    html = template.render(
        date_range=f"{start_date:%Y-%m-%d} to {end_date:%Y-%m-%d}",
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        summaries=summaries,
        charts=charts,
        table_rows=table_rows,
    )

    Path(output_path).write_text(html, encoding="utf-8")
    logger.info("Report written to %s", output_path)
    return output_path
