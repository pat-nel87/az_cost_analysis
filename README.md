# Azure Cost Analyzer

A CLI tool that sweeps across Azure subscriptions, queries the Cost Management API for metered resource usage, and generates a self-contained interactive HTML report with cost breakdowns and charts. Optionally exportable to PDF.

## Features

- **Multi-subscription sweep** — automatically discovers and queries all accessible subscriptions, or target specific ones
- **Three cost dimensions** — cost by resource group, cost by meter category (resource type), and daily cost trends
- **Interactive HTML report** — 4 Plotly charts (bar, treemap, stacked area, sunburst) + searchable/sortable data table
- **PDF export** — optional Playwright-based rendering to PDF
- **Filtering** — exclude resource groups, set minimum cost thresholds
- **Resilient** — exponential backoff on rate limits, graceful skip on inaccessible subscriptions, auto-throttle for large subscription counts

## Prerequisites

- **Python 3.11+**
- **Azure authentication** — one of:
  - Azure CLI: `az login`
  - Service principal: set `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID`
  - Managed identity (when running in Azure)
- **Azure RBAC** — the authenticated identity needs at least **Cost Management Reader** (or **Reader**) role on target subscriptions

## Installation

```bash
# Clone the repository
git clone https://github.com/pat-nel87/az_cost_analysis.git
cd az_cost_analysis

# Create a virtual environment (Python 3.11+)
python3 -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install
pip install -e .

# With PDF export support
pip install -e ".[pdf]"
playwright install chromium

# With dev dependencies (testing, linting)
pip install -e ".[dev]"
```

## Usage

```bash
# Sweep all accessible subscriptions, last 30 days
azure-cost-analyzer

# Target specific subscriptions, 90-day lookback
azure-cost-analyzer --subscription "sub-id-1,sub-id-2" --days 90

# Exclude sandbox/test resource groups, set cost floor
azure-cost-analyzer --exclude-rg "sandbox-rg,test-rg" --min-cost 1.00

# Generate HTML + PDF
azure-cost-analyzer --pdf --output ./reports/march-costs.html

# Verify authentication without running queries
azure-cost-analyzer --dry-run

# Debug logging
azure-cost-analyzer --verbose
```

### CLI Reference

| Option | Default | Description |
|--------|---------|-------------|
| `--days INT` | `30` | Number of days to look back |
| `--subscription TEXT` | all | Comma-separated subscription ID(s) |
| `--output PATH` | `./cost-report.html` | Output HTML file path |
| `--pdf` | off | Also export as PDF alongside HTML |
| `--exclude-rg TEXT` | none | Comma-separated resource group names to exclude |
| `--min-cost FLOAT` | `0.01` | Minimum cost threshold to include a row |
| `--dry-run` | off | Authenticate and list subscriptions only |
| `--verbose` | off | Enable debug logging |

## Report Layout

The generated HTML report includes:

1. **Summary cards** — total spend, subscription count, resource group count, daily average
2. **Daily cost trend** — stacked area chart showing spend over time by resource group (top 10)
3. **Spend by resource group** — horizontal bar chart of top 20 resource groups
4. **Spend by meter category** — treemap showing resource group to meter category hierarchy
5. **Cost hierarchy sunburst** — subscription to resource group to meter category drilldown
6. **Data table** — full breakdown with client-side search and column sorting

The report is fully self-contained — charts are interactive (hover, zoom, pan) and work offline.

## Project Structure

```
├── pyproject.toml
├── src/azure_cost_analyzer/
│   ├── __init__.py
│   ├── cli.py              # argparse entry point
│   ├── auth.py             # DefaultAzureCredential wrapper
│   ├── subscriptions.py    # Subscription enumeration
│   ├── cost_query.py       # Cost Management API queries (3 query types)
│   ├── data_processing.py  # Pandas aggregation, filtering, summaries
│   ├── report.py           # Plotly chart generation + HTML assembly
│   └── pdf_export.py       # Playwright HTML-to-PDF renderer
├── templates/
│   └── report.html.j2      # Jinja2 HTML report template
└── tests/
    ├── conftest.py          # Shared fixtures
    ├── test_cost_query.py   # Query function tests (mocked SDK)
    └── test_data_processing.py  # Data transform tests
```

## How It Works

1. **Authenticate** — uses `DefaultAzureCredential` which tries Azure CLI, environment variables, managed identity, and other methods in order
2. **Enumerate subscriptions** — discovers all accessible subscriptions via Azure Resource Manager (or filters to specified IDs)
3. **Query costs** — runs 3 queries per subscription against the Cost Management API:
   - Cost by resource group (for bar chart)
   - Cost by resource group + meter category (for treemap, sunburst, and table)
   - Daily cost by resource group (for trend chart)
4. **Aggregate & filter** — combines results across subscriptions, applies exclusions and minimum cost thresholds
5. **Generate report** — builds Plotly charts, renders the Jinja2 template into a standalone HTML file
6. **Export PDF** (optional) — loads the HTML in headless Chromium via Playwright and renders to PDF

### Rate Limiting

The Cost Management API allows 30 requests/minute/subscription. The tool makes 3 queries per subscription, so:
- For **10 or fewer** subscriptions: queries run without throttling
- For **more than 10**: a 2-second delay is inserted between subscriptions
- **429 responses**: automatic exponential backoff (1s, 2s, 4s) with up to 3 retries

### Error Handling

| Scenario | Behavior |
|----------|----------|
| Authentication failure | Clear error message with fix instructions, exit |
| 403 Forbidden | Warning logged, subscription skipped, sweep continues |
| 404 Not Found | Warning logged, subscription skipped (Cost Management may not be available) |
| 429 Rate Limited | Exponential backoff with 3 retries |
| No data returned | Report generated with "no data" notice instead of crashing |
| Playwright not installed | Warning with install instructions, PDF skipped |

## Development

```bash
# Run tests
python -m pytest tests/ -v

# Lint
ruff check src/ tests/

# Format
ruff format src/ tests/
```

## License

MIT License — see [LICENSE](LICENSE) for details.
