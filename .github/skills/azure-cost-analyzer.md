---
name: azure-cost-analyzer
description: Skills for building, testing, debugging, and extending the Azure Cost Analyzer CLI tool.
---

# Azure Cost Analyzer Skills

## Skill: Run the Tool

### Prerequisites Check
```bash
# Verify Python 3.11+
python3 --version

# Verify Azure auth
az account show

# Verify installation
azure-cost-analyzer --help
```

### Quick Start
```bash
# Activate the project venv
source .venv/bin/activate

# Dry run — verify auth and list subscriptions without cost queries
azure-cost-analyzer --dry-run

# Full run — default 30 days, all subscriptions
azure-cost-analyzer

# Targeted run
azure-cost-analyzer --subscription "SUBSCRIPTION_ID" --days 7 --output quick-report.html
```

### Common Scenarios
```bash
# Monthly cost review across all subscriptions
azure-cost-analyzer --days 30 --output monthly-$(date +%Y-%m).html

# Quarterly report for finance, excluding dev/test
azure-cost-analyzer --days 90 --exclude-rg "dev-rg,test-rg,sandbox-rg" --min-cost 10.00 --pdf

# Quick check on a single subscription
azure-cost-analyzer --subscription "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" --days 7

# Debug a failing run
azure-cost-analyzer --verbose 2>&1 | tee debug.log
```

---

## Skill: Run Tests

```bash
# Activate venv
source .venv/bin/activate

# Run all tests
python -m pytest tests/ -v

# Run specific test module
python -m pytest tests/test_data_processing.py -v
python -m pytest tests/test_cost_query.py -v

# Run a single test
python -m pytest tests/test_data_processing.py::TestComputeSummaries::test_basic_summaries -v

# Run with coverage (if pytest-cov is installed)
python -m pytest tests/ --cov=azure_cost_analyzer --cov-report=term-missing
```

---

## Skill: Lint and Format

```bash
# Check for issues
ruff check src/ tests/

# Auto-fix
ruff check src/ tests/ --fix

# Format
ruff format src/ tests/

# Check formatting without changing files
ruff format src/ tests/ --check
```

---

## Skill: Add a New Cost Query

When adding a new query dimension (e.g., cost by tag, cost by location):

1. **Define the query function** in `src/azure_cost_analyzer/cost_query.py`:
   ```python
   def query_cost_by_<dimension>(client, subscription_id, start_date, end_date) -> pd.DataFrame:
       scope = f"/subscriptions/{subscription_id}"
       query = QueryDefinition(
           type="Usage",
           timeframe="Custom",
           time_period=QueryTimePeriod(from_property=start_date, to=end_date),
           dataset=QueryDataset(
               granularity="None",
               aggregation={"totalCost": QueryAggregation(name="Cost", function="Sum")},
               grouping=[QueryGrouping(type="Dimension", name="<AzureDimensionName>")],
           ),
       )
       df = _execute_query(client, scope, query)
       if not df.empty:
           df["SubscriptionId"] = subscription_id
       return df
   ```

2. **Add to `fetch_all_cost_data()`** in the same file — add a key to the results dict and call the new function in the subscription loop.

3. **Wire through `cli.py`** — aggregate, filter, and pass to `generate_report()`.

4. **Add a chart** in `src/azure_cost_analyzer/report.py` — create a `_chart_<name>()` function returning a Plotly HTML fragment.

5. **Update the Jinja2 template** in `templates/report.html.j2` — add a new chart section.

6. **Add tests** in `tests/test_cost_query.py` — mock the SDK response and verify DataFrame output.

### Available Azure Cost Management Dimensions
Common grouping dimensions you can use:
- `ResourceGroup` — resource group name
- `MeterCategory` — service type (Virtual Machines, Storage, etc.)
- `MeterSubCategory` — service sub-type
- `ResourceType` — ARM resource type
- `ResourceLocation` — Azure region
- `ServiceName` — service name
- `TagKey:TagName` — cost by tag (requires tag-based grouping)

**Important**: Maximum 2 grouping dimensions per query.

---

## Skill: Add a New Chart

1. **Create the chart function** in `src/azure_cost_analyzer/report.py`:
   ```python
   def _chart_<name>(df: pd.DataFrame) -> str | None:
       if df.empty or "<required_column>" not in df.columns:
           return None
       fig = px.<chart_type>(...)
       fig.update_layout(height=500)
       return pio.to_html(fig, full_html=False, include_plotlyjs=False)
   ```

2. **Add to `generate_report()`** — include in the `charts` dict.

3. **Add to the template** — wrap in a conditional block:
   ```jinja2
   {% if charts.new_chart %}
   <div class="chart-section">
       {{ charts.new_chart | safe }}
   </div>
   {% endif %}
   ```

---

## Skill: Debug Azure API Issues

### Authentication Problems
```bash
# Check current Azure CLI auth
az account show
az account list --output table

# Re-authenticate
az login

# For service principal auth, verify env vars
echo $AZURE_CLIENT_ID
echo $AZURE_TENANT_ID
# (don't echo AZURE_CLIENT_SECRET)
```

### Cost Management API Issues
```bash
# Verify Cost Management access on a subscription
az rest --method post \
  --url "https://management.azure.com/subscriptions/SUBSCRIPTION_ID/providers/Microsoft.CostManagement/query?api-version=2023-11-01" \
  --body '{"type":"Usage","timeframe":"MonthToDate","dataset":{"granularity":"None","aggregation":{"totalCost":{"name":"Cost","function":"Sum"}}}}'

# Check role assignments
az role assignment list --subscription SUBSCRIPTION_ID --output table
```

### Common Error Codes
| Code | Meaning | Fix |
|------|---------|-----|
| 401 | Token expired or invalid | Run `az login` |
| 403 | No Cost Management access | Add Reader or Cost Management Reader role |
| 404 | Cost Management not registered | Run `az provider register -n Microsoft.CostManagement` |
| 429 | Rate limited | Tool handles this automatically with backoff |
| BillingAccount error | MSDN/Visual Studio subscription | These don't support cost queries — tool will skip |

---

## Skill: Modify the HTML Report Template

The template is at `templates/report.html.j2`. Key conventions:

- **Charts** are Plotly HTML fragments injected with `{{ charts.<name> | safe }}`
- **Summary data** comes from the `summaries` dict (see `compute_summaries()` in `data_processing.py`)
- **Table data** is a list of dicts in `table_rows`
- **CSS variables** are in `:root` — modify these for theming
- **Print styles** are in `@media print` — ensure new sections have `break-inside: avoid`
- **Client-side JS** handles table search (`filterTable()`) and column sorting (`sortTable()`)

### Template Variables

| Variable | Type | Source |
|----------|------|--------|
| `date_range` | string | `"2024-01-01 to 2024-01-31"` |
| `generated_at` | string | Timestamp |
| `summaries.total_spend` | float | Total cost across all data |
| `summaries.daily_average` | float | Average daily spend |
| `summaries.num_subscriptions` | int | Count of queried subscriptions |
| `summaries.num_resource_groups` | int | Count of unique resource groups |
| `summaries.currency` | string | Currency code (e.g., `"USD"`) |
| `charts.rg_bar` | string\|None | Bar chart HTML |
| `charts.meter_treemap` | string\|None | Treemap HTML |
| `charts.daily_trend` | string\|None | Stacked area chart HTML |
| `charts.sunburst` | string\|None | Sunburst chart HTML |
| `table_rows` | list[dict] | Row data for the details table |
