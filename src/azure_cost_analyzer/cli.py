"""CLI entry point for Azure Cost Analyzer."""

import argparse
import logging
import sys
from datetime import datetime, timedelta

from azure_cost_analyzer.auth import get_credential
from azure_cost_analyzer.cost_query import fetch_all_cost_data
from azure_cost_analyzer.data_processing import (
    aggregate_across_subscriptions,
    compute_summaries,
    exclude_resource_groups,
    filter_by_threshold,
)
from azure_cost_analyzer.pdf_export import export_pdf
from azure_cost_analyzer.report import generate_report
from azure_cost_analyzer.subscriptions import list_subscriptions


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="azure-cost-analyzer",
        description="Sweep Azure subscriptions and generate an interactive HTML cost report.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days to look back (default: 30)",
    )
    parser.add_argument(
        "--subscription",
        type=str,
        default=None,
        help="Comma-separated subscription ID(s). If omitted, sweeps all accessible.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="./cost-report.html",
        help="Output HTML file path (default: ./cost-report.html)",
    )
    parser.add_argument(
        "--pdf",
        action="store_true",
        help="Also export the report as PDF alongside the HTML",
    )
    parser.add_argument(
        "--exclude-rg",
        type=str,
        default=None,
        help="Comma-separated resource group names to exclude",
    )
    parser.add_argument(
        "--min-cost",
        type=float,
        default=0.01,
        help="Minimum cost threshold to include a resource (default: 0.01)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Authenticate and list subscriptions without running cost queries",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logger = logging.getLogger("azure_cost_analyzer")

    # Auth
    logger.info("Authenticating with Azure...")
    credential = get_credential()

    # Subscriptions
    filter_ids = None
    if args.subscription:
        filter_ids = [s.strip() for s in args.subscription.split(",")]

    subscriptions = list_subscriptions(credential, filter_ids)
    if not subscriptions:
        print("No accessible subscriptions found.", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(subscriptions)} subscription(s):")
    for sub in subscriptions:
        print(f"  - {sub['display_name']} ({sub['subscription_id']})")

    if args.dry_run:
        print("\n--dry-run: exiting after subscription enumeration.")
        return

    # Date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=args.days)
    logger.info("Querying costs from %s to %s (%d days)",
                start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), args.days)

    # Fetch cost data
    raw_data = fetch_all_cost_data(credential, subscriptions, start_date, end_date)

    # Aggregate
    rg_data = aggregate_across_subscriptions(raw_data["by_rg"])
    meter_data = aggregate_across_subscriptions(raw_data["by_meter"])
    trend_data = aggregate_across_subscriptions(raw_data["daily_trend"])

    # Filter
    exclude_list = []
    if args.exclude_rg:
        exclude_list = [rg.strip() for rg in args.exclude_rg.split(",")]

    rg_data = filter_by_threshold(exclude_resource_groups(rg_data, exclude_list), args.min_cost)
    meter_data = filter_by_threshold(exclude_resource_groups(meter_data, exclude_list), args.min_cost)
    trend_data = filter_by_threshold(exclude_resource_groups(trend_data, exclude_list), args.min_cost)

    # Summaries (use meter data for richest breakdown, fall back to rg data)
    summary_source = meter_data if not meter_data.empty else rg_data
    summaries = compute_summaries(summary_source)

    # Handle empty data
    if rg_data.empty and meter_data.empty:
        print("No cost data returned for the selected subscriptions and time range.")
        print("Generating report with empty data notice...")

    # Generate report
    output_path = generate_report(
        rg_data=rg_data,
        meter_data=meter_data,
        trend_data=trend_data,
        summaries=summaries,
        start_date=start_date,
        end_date=end_date,
        output_path=args.output,
    )
    print(f"\nHTML report generated: {output_path}")

    # PDF export
    if args.pdf:
        pdf_path = export_pdf(output_path)
        if pdf_path:
            print(f"PDF report generated: {pdf_path}")
        else:
            print("PDF export failed. See logs for details.", file=sys.stderr)


if __name__ == "__main__":
    main()
