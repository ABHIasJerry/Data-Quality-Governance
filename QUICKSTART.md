# Quick Start Guide: 5 Minutes to Data Governance

Get your data governance framework up and running in 5 minutes!

## Step 1: Install Dependencies (1 minute)

```bash
pip install -r requirements.txt
```

## Step 2: Configure Snowflake Connection (1 minute)

```bash
# Copy template
cp config/snowflake_config.template.json config/snowflake_config.json

# Edit with your credentials
nano config/snowflake_config.json
```

Replace with your Snowflake details:
```json
{
  "user": "your_username",
  "password": "your_password",
  "account": "xy12345.us-east-1",
  "warehouse": "COMPUTE_WH",
  "database": "ANALYTICS",
  "schema": "PUBLIC"
}
```

## Step 3: Initialize Governance Schema (1 minute)

Run this SQL in Snowflake:
```sql
-- Copy and paste from: sql/01_create_governance_schema.sql
```

Or use Python:
```python
from src.governance_orchestrator import GovernanceOrchestrator
import json

config = json.load(open('config/snowflake_config.json'))
orch = GovernanceOrchestrator(config)
orch.connect()
orch.initialize_governance_framework('ANALYTICS')
orch.disconnect()
```

## Step 4: Configure Tables (1 minute)

Edit `config/governance_config.yaml` to match your tables:

```yaml
tables:
  CUSTOMERS:
    governance:
      governance_level: CONFIDENTIAL
      owner_team: SALES
      critical_table: true
      pii_present: true
    quality_checks:
      check_duplicates: true
      check_nulls: true
      non_nullable_columns: [CUSTOMER_ID, EMAIL]
      max_data_age_days: 1
```

## Step 5: Run Governance Checks (1 minute)

```bash
python main_example.py
```

## What You Get

✅ **Metadata Report** - Column info, row counts, table sizes
✅ **Quality Metrics** - Duplicates, nulls, outliers detected
✅ **Compliance Issues** - Problems logged and tracked
✅ **Governance Dashboard** - JSON and HTML reports in `output/`

## Key Files Generated

```
output/
├── governance_report.json    # Machine-readable results
└── governance_report.html    # Visual dashboard
```

## Common Quick Configurations

### Minimal Setup (Just Duplicates & Nulls)
```yaml
ORDERS:
  quality_checks:
    check_duplicates: true
    check_nulls: true
    non_nullable_columns: [ORDER_ID, CUSTOMER_ID]
```

### Financial Data Setup
```yaml
FACT_SALES:
  governance:
    governance_level: CONFIDENTIAL
    critical_table: true
  quality_checks:
    check_duplicates: true
    check_nulls: true
    check_outliers: true
    numeric_columns: [AMOUNT, QUANTITY]
    outlier_std_devs: 3
    max_data_age_days: 1
```

### PII Data Setup
```yaml
CUSTOMERS:
  governance:
    governance_level: RESTRICTED
    pii_present: true
  quality_checks:
    check_nulls: true
    non_nullable_columns: [EMAIL, PHONE]
    pattern_validation:
      EMAIL: "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
```

## Viewing Results

### Option 1: HTML Dashboard
Open `output/governance_report.html` in browser

### Option 2: JSON Results
```bash
cat output/governance_report.json | jq
```

### Option 3: Snowflake SQL
```sql
SELECT * FROM DATA_GOVERNANCE.QUALITY_METRICS LIMIT 10;
SELECT * FROM DATA_GOVERNANCE.COMPLIANCE_ISSUES WHERE STATUS = 'OPEN';
```

## Next Steps

### Schedule Daily Runs
```bash
# Linux/Mac - Add to crontab
0 2 * * * cd /path/to/snowflake_governance && python main_example.py
```

### Monitor Specific Table
```python
orch.connect()
metadata = orch.scan_table_metadata('ANALYTICS', 'PUBLIC', 'CUSTOMERS')
checks = orch.run_quality_checks(
    'ANALYTICS', 'PUBLIC', 'CUSTOMERS',
    {'check_duplicates': True, 'check_nulls': True}
)
orch.disconnect()
```

### Track Data Lineage
```python
orch.record_data_lineage(
    'ANALYTICS',
    'ORDERS',
    'FACT_SALES',
    'Aggregated order data with dimensions',
    'SUCCESS'
)
```

### Generate Report
```python
report = orch.generate_governance_report('ANALYTICS', limit_days=30)
print(f"Compliance Score: {report['execution_summary']}")
```

## Troubleshooting

### Connection Error
```
Check:
- Credentials in snowflake_config.json
- Warehouse is running
- Network access to Snowflake
```

### No Tables Found
```
Make sure:
- Database and schema exist
- User has SELECT permission
- Table list is not empty
```

### Quality Check Errors
```
Solutions:
- Add --debug flag: python main_example.py --debug
- Check column names match UPPER_CASE
- Verify non-nullable_columns exist
```

## Useful SQL Queries

```sql
-- See all quality issues
SELECT table_name, check_type, severity, details 
FROM DATA_GOVERNANCE.QUALITY_METRICS 
WHERE passed = FALSE
ORDER BY check_timestamp DESC;

-- See open compliance issues
SELECT table_name, issue_type, severity, description
FROM DATA_GOVERNANCE.COMPLIANCE_ISSUES 
WHERE status = 'OPEN'
ORDER BY created_at DESC;

-- Monitor data freshness
SELECT 
    table_name,
    last_modified,
    DATEDIFF(day, last_modified, CURRENT_TIMESTAMP()) as days_old
FROM DATA_GOVERNANCE.TABLE_REGISTRY
WHERE critical_table = TRUE
ORDER BY last_modified ASC;
```

## Getting Help

1. **Check README.md** for detailed documentation
2. **Review sql/03_governance_reports.sql** for pre-built queries
3. **Look at docs/INTEGRATION_GUIDE.md** for advanced setup
4. **Run tests**: `python -m pytest tests/`

## Next: Production Deployment

Once you're comfortable with the basics:

1. ✅ Complete Step-by-Step Guide (see README.md)
2. ✅ Set up CI/CD integration (see INTEGRATION_GUIDE.md)
3. ✅ Schedule with Snowflake Tasks or Apache Airflow
4. ✅ Create custom quality checks
5. ✅ Integrate with your data platform

---

**You're now ready to govern your data!** 🎉

Questions? Check the main README.md or run `python -m pydoc src.governance_orchestrator`
