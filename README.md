# Data Governance & Quality Framework for Snowflake

A comprehensive Python and SQL framework for implementing enterprise-grade data governance and data quality management across 100+ Snowflake tables.

## Overview

This framework provides:
- **Metadata Cataloging**: Automated scanning and registration of table metadata
- **Data Quality Checks**: Comprehensive quality assessments (duplicates, nulls, outliers, freshness, etc.)
- **Governance Policies**: Table classification, ownership tracking, and compliance monitoring
- **Data Lineage**: Track ETL transformations and data flow
- **Audit Logging**: Access logs and compliance issue tracking
- **Reporting**: JSON, HTML, and SQL-based reports and dashboards

## Architecture

```
snowflake_governance/
├── src/
│   ├── snowflake_connector.py      # Connection management
│   ├── metadata_scanner.py          # Table profiling and metadata
│   ├── data_quality_checker.py      # Quality check implementations
│   ├── governance_manager.py        # Governance policy management
│   └── governance_orchestrator.py   # Main orchestrator
├── sql/
│   ├── 01_create_governance_schema.sql  # Database schema setup
│   ├── 02_quality_checks.sql            # SQL procedures for checks
│   └── 03_governance_reports.sql        # Reporting queries
├── config/
│   ├── snowflake_config.template.json   # Connection config template
│   └── governance_config.yaml           # Table-specific configurations
├── tests/
│   └── (test files)
├── output/
│   └── (generated reports)
└── main_example.py                  # Main usage script
```

## Setup & Installation

### Prerequisites
- Python 3.8+
- Snowflake account with appropriate permissions
- Required packages:

```bash
pip install snowflake-connector-python pyyaml
```

### Step 1: Configure Snowflake Connection

1. Copy the template configuration:
```bash
cp config/snowflake_config.template.json config/snowflake_config.json
```

2. Update `config/snowflake_config.json` with your credentials:
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

### Step 2: Initialize Governance Schema

Run the SQL setup script in Snowflake:
```sql
-- Execute: sql/01_create_governance_schema.sql
```

This creates:
- `DATA_GOVERNANCE.TABLE_REGISTRY` - Master table catalog
- `DATA_GOVERNANCE.QUALITY_METRICS` - Quality check results
- `DATA_GOVERNANCE.DATA_LINEAGE` - Transformation tracking
- `DATA_GOVERNANCE.COMPLIANCE_ISSUES` - Issue tracking
- `DATA_GOVERNANCE.DATA_DICTIONARY` - Column metadata
- And supporting tables...

### Step 3: Configure Table-Specific Settings

Edit `config/governance_config.yaml` to define:
- Governance classification (PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED)
- Quality check rules (columns to validate, thresholds, etc.)
- Data type expectations
- Foreign key relationships
- Pattern validation rules

Example:
```yaml
tables:
  CUSTOMERS:
    governance:
      governance_level: CONFIDENTIAL
      owner_team: SALES_OPS
      critical_table: true
      pii_present: true
    quality_checks:
      check_nulls: true
      non_nullable_columns: [CUSTOMER_ID, EMAIL]
      numeric_columns: [ANNUAL_REVENUE]
      max_data_age_days: 1
```

### Step 4: Run the Framework

```bash
python main_example.py
```

## Core Features

### 1. Metadata Scanning
Automatically profiles tables to capture:
- Column information (name, data type, nullable)
- Row counts and table size
- Creation and modification timestamps
- Constraints and primary keys
- Data completeness by column

```python
metadata = orchestrator.scan_table_metadata(database, schema, table_name)
```

### 2. Data Quality Checks

#### Duplicate Records
Identifies exact row duplicates using hash partitioning

#### Null Value Analysis
Monitors unexpected nulls in critical columns

#### Data Type Validation
Ensures columns match expected data types

#### Referential Integrity
Validates foreign key relationships

#### Numeric Outlier Detection
Identifies statistical anomalies using z-score method

#### Data Freshness
Checks if data is within acceptable age threshold

#### Pattern Validation
Validates data against regex patterns (emails, phone numbers, etc.)

```python
results = orchestrator.run_quality_checks(database, schema, table_name, config)
for check in results:
    print(f"{check['check_type']}: {check['severity']}")
```

### 3. Governance Management

#### Table Registration
Register tables with governance metadata:
```python
orchestrator.governance_manager.register_table(
    database, schema, table_name,
    {
        'governance_level': 'CONFIDENTIAL',
        'owner_team': 'FINANCE',
        'pii_present': True
    }
)
```

#### Compliance Issue Tracking
Create and track governance violations:
```python
orchestrator.governance_manager.create_compliance_issue(
    database, table_id,
    {
        'issue_type': 'DATA_QUALITY',
        'severity': 'ERROR',
        'description': '500 null values in required field',
        'remediation_action': 'Data cleansing required',
        'due_date': '2024-12-31'
    }
)
```

### 4. Data Lineage Tracking
Record source-to-target transformations:
```python
orchestrator.record_data_lineage(
    database,
    source_table='ORDERS',
    target_table='FACT_SALES',
    transformation_logic='Aggregated order data with dimensions',
    run_status='SUCCESS'
)
```

### 5. Reporting

The framework generates three types of reports:

#### JSON Report
Machine-readable detailed results:
```bash
output/governance_report.json
```

#### HTML Report
Interactive dashboard with metrics:
```bash
output/governance_report.html
```

#### SQL Reports
Pre-built queries for Snowflake:
```sql
-- Query 1: Governance Summary
-- Query 2: Quality Status by Table
-- Query 3: Compliance Issues
-- ... and 12 more
```

## Quality Check Configuration

### Example: CUSTOMERS Table
```yaml
CUSTOMERS:
  quality_checks:
    # Check for duplicate full rows
    check_duplicates: true
    
    # Monitor null values
    check_nulls: true
    non_nullable_columns:
      - CUSTOMER_ID
      - CUSTOMER_NAME
      - EMAIL
    
    # Validate data types
    check_data_types: true
    data_type_rules:
      CUSTOMER_ID: "NUMBER"
      EMAIL: "VARCHAR"
      CREATED_AT: "TIMESTAMP_TZ"
    
    # Check numeric distributions
    check_outliers: true
    numeric_columns:
      - ANNUAL_REVENUE
      - EMPLOYEE_COUNT
    outlier_std_devs: 3  # Alert if >3 std deviations
    
    # Monitor data age
    check_freshness: true
    timestamp_column: "CREATED_AT"
    max_data_age_days: 1
    
    # Validate email format
    check_patterns: true
    pattern_validation:
      EMAIL: "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
    
    # Check foreign keys
    check_referential_integrity: true
    foreign_keys:
      ACCOUNT_ID: ["ACCOUNTS", "ACCOUNT_ID"]
```

## SQL Procedures

The framework provides 9 reusable SQL procedures:

1. **CHECK_DUPLICATES** - Find duplicate records
2. **CHECK_NULL_VALUES** - Analyze null percentages
3. **VALIDATE_DATA_TYPES** - Verify column types
4. **CHECK_NUMERIC_OUTLIERS** - Statistical anomaly detection
5. **CHECK_REFERENTIAL_INTEGRITY** - Foreign key validation
6. **CHECK_DATA_FRESHNESS** - Monitor data age
7. **VALIDATE_PATTERN** - Regex pattern matching
8. **PROFILE_TABLE** - Comprehensive table statistics
9. **ANALYZE_COLUMN_STATISTICS** - Column-level cardinality and stats

Usage:
```sql
CALL CHECK_DUPLICATES('ANALYTICS', 'PUBLIC', 'CUSTOMERS');
CALL CHECK_NULL_VALUES('ANALYTICS', 'PUBLIC', 'CUSTOMERS', 'EMAIL');
CALL CHECK_NUMERIC_OUTLIERS('ANALYTICS', 'PUBLIC', 'SALES', 'AMOUNT', 3.0);
```

## Governance Reports

15 pre-built SQL queries provide insights:

1. Data Governance Summary
2. Governance Level Distribution
3. Data Quality Status by Table
4. Quality Issues Severity Report
5. Data Lineage Overview
6. PII and Confidential Data Inventory
7. Compliance Issue Status
8. Critical Tables Health
9. Access Patterns
10. Governance Compliance Score by Team
11. Data Dictionary Gaps
12. Quality Trends (30-day)
13. Lineage Dependencies
14. Encryption & Security Status
15. Governance Readiness Assessment

## Advanced Usage

### Process All Tables in Bulk
```python
orchestrator.connect()
orchestrator.initialize_governance_framework(database)

report = orchestrator.process_all_tables(
    database='ANALYTICS',
    schema='PUBLIC',
    config_file='config/governance_config.yaml'
)

orchestrator.export_report_to_json('output/governance_report.json')
orchestrator.export_report_to_html('output/governance_report.html')
orchestrator.disconnect()
```

### Custom Quality Checks
Extend `DataQualityChecker` to add custom checks:
```python
from data_quality_checker import DataQualityChecker

class CustomChecker(DataQualityChecker):
    def _check_business_rules(self, database, schema, table_name, config):
        # Implement custom business logic
        pass
```

### Integration with CI/CD
Use the framework in automated pipelines:
```bash
# Run governance checks before deployment
python main_example.py
if [ $? -ne 0 ]; then
    echo "Governance checks failed"
    exit 1
fi
```

## Monitoring & Dashboards

### Snowflake Native Dashboard
Create a dashboard using the governance schema tables:
```sql
SELECT table_name, COUNT(*) as quality_issues
FROM DATA_GOVERNANCE.QUALITY_METRICS
WHERE passed = FALSE
GROUP BY table_name
ORDER BY quality_issues DESC;
```

### External Visualization
Export data to:
- Tableau
- Power BI
- Grafana
- Looker

## Best Practices

1. **Regular Scanning**: Schedule weekly metadata scans
2. **Progressive Enhancement**: Start with critical tables, expand gradually
3. **Documentation**: Keep data dictionary up-to-date
4. **Issue Resolution**: Set clear SLAs for compliance issues
5. **Access Control**: Restrict governance schema access to authorized users
6. **Retention**: Archive old quality metrics (quarterly)
7. **Automation**: Use Snowflake Tasks to run quality checks automatically

## Troubleshooting

### Connection Errors
```python
# Verify credentials in snowflake_config.json
# Check firewall and network access
# Ensure warehouse is active
```

### Permission Errors
```sql
-- Grant necessary permissions
GRANT USAGE ON SCHEMA DATA_GOVERNANCE TO ROLE SYSADMIN;
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA DATA_GOVERNANCE TO ROLE SYSADMIN;
```

### Performance Issues
- Create indexes on frequently queried columns
- Use table clustering for large tables
- Schedule quality checks during off-peak hours
- Archive old quality metrics

## Configuration Reference

### Governance Levels
- **PUBLIC**: No restrictions, general use data
- **INTERNAL**: Internal organizational data
- **CONFIDENTIAL**: Sensitive business data
- **RESTRICTED**: PII, financial, or highly confidential

### Severity Levels
- **INFO**: Informational, no action needed
- **WARNING**: Minor issue, should be addressed
- **ERROR**: Significant issue, must be resolved
- **CRITICAL**: Blocking issue, immediate action required

## Support & Contribution

For issues, questions, or contributions:
1. Check existing issues
2. Review documentation
3. Test in non-production first
4. Submit detailed issue reports

## License

This framework is provided as-is for data governance implementation.

## Additional Resources

- [Snowflake Documentation](https://docs.snowflake.com)
- [Data Governance Best Practices](https://www.gartner.com/doc/3883263)
- [Data Quality Metrics](https://www.iseatz.com/blog/data-quality-metrics)
