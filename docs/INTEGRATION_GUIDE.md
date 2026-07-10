# Integration Guide: Data Governance Framework

This guide covers integration of the governance framework with Snowflake native tools, external systems, and CI/CD pipelines.

## Snowflake Native Integration

### 1. Automated Scheduling with Snowflake Tasks

Create tasks to run quality checks automatically:

```sql
-- Create task for daily quality checks
CREATE OR REPLACE TASK daily_quality_checks
  WAREHOUSE = COMPUTE_WH
  SCHEDULE = '1 HOUR'
  COMMENT = 'Run daily data quality checks'
AS
-- Check CUSTOMERS table for duplicates
CALL CHECK_DUPLICATES('ANALYTICS', 'PUBLIC', 'CUSTOMERS');

-- Check ORDER table for freshness
CALL CHECK_DATA_FRESHNESS('ANALYTICS', 'PUBLIC', 'ORDERS', 'ORDER_DATE', 24);

-- Check critical numeric columns for outliers
CALL CHECK_NUMERIC_OUTLIERS('ANALYTICS', 'PUBLIC', 'FACT_SALES', 'AMOUNT', 3.0);

-- Insert results into tracking table
INSERT INTO DATA_GOVERNANCE.QUALITY_METRICS (metric_id, table_id, check_type, passed, severity, details, check_timestamp)
SELECT 
    UUID_STRING() as metric_id,
    'ANALYTICS_PUBLIC_' || TABLE_NAME as table_id,
    'SCHEDULED_CHECK' as check_type,
    TRUE as passed,
    'INFO' as severity,
    'Scheduled quality check completed' as details,
    CURRENT_TIMESTAMP() as check_timestamp
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = 'PUBLIC' AND TABLE_CATALOG = 'ANALYTICS';

-- Enable the task
EXECUTE TASK daily_quality_checks;
```

### 2. Snowflake Alerts for Failed Checks

Set up alerts to notify teams when quality issues are detected:

```sql
-- Create alert for critical quality issues
CREATE OR REPLACE ALERT quality_alert_critical
  WAREHOUSE = COMPUTE_WH
  CONDITION = 
    EXISTS (
      SELECT 1 FROM DATA_GOVERNANCE.QUALITY_METRICS 
      WHERE severity = 'CRITICAL' 
      AND check_timestamp > CURRENT_TIMESTAMP() - INTERVAL '1 hour'
    )
  ACTION = 
    SEND EMAIL TO 'data-quality-team@company.com' 
    SUBJECT = 'CRITICAL: Data Quality Issue Detected'
    BODY = (
      SELECT 'Table: ' || table_name || 
             ' Check: ' || check_type || 
             ' Details: ' || details
      FROM DATA_GOVERNANCE.QUALITY_METRICS 
      WHERE severity = 'CRITICAL'
      AND check_timestamp > CURRENT_TIMESTAMP() - INTERVAL '1 hour'
      ORDER BY check_timestamp DESC
      LIMIT 1
    );

-- Create alert for stale tables
CREATE OR REPLACE ALERT stale_table_alert
  WAREHOUSE = COMPUTE_WH
  CONDITION = 
    EXISTS (
      SELECT 1 FROM DATA_GOVERNANCE.TABLE_REGISTRY 
      WHERE critical_table = TRUE 
      AND last_modified < CURRENT_TIMESTAMP() - INTERVAL '7 days'
    )
  ACTION = 
    SEND EMAIL TO 'data-owners@company.com' 
    SUBJECT = 'WARNING: Critical Table Not Updated'
    BODY = 
      'Critical table has not been updated in 7+ days. Please investigate.';

-- Enable alerts
ALTER ALERT quality_alert_critical SET STATE = STARTED;
ALTER ALERT stale_table_alert SET STATE = STARTED;
```

### 3. Dynamic Table Integration

Create dynamic tables that automatically refresh governance metrics:

```sql
-- Dynamic table for governance dashboard
CREATE OR REPLACE DYNAMIC TABLE governance_dashboard
  TARGET LAG = '1 hour'
  WAREHOUSE = COMPUTE_WH
AS
SELECT 
    t.table_name,
    t.governance_level,
    t.owner_team,
    COUNT(CASE WHEN qm.passed = FALSE THEN 1 END) as quality_issues,
    MAX(qm.check_timestamp) as last_quality_check,
    COUNT(DISTINCT ci.issue_id) FILTER (WHERE ci.status = 'OPEN') as open_compliance_issues,
    ROUND(SUM(CASE WHEN qm.passed = TRUE THEN 1 ELSE 0 END) * 100.0 / 
          NULLIF(COUNT(*), 0), 2) as quality_score_pct
FROM DATA_GOVERNANCE.TABLE_REGISTRY t
LEFT JOIN DATA_GOVERNANCE.QUALITY_METRICS qm ON t.table_id = qm.table_id
LEFT JOIN DATA_GOVERNANCE.COMPLIANCE_ISSUES ci ON t.table_id = ci.table_id
GROUP BY t.table_name, t.governance_level, t.owner_team;
```

### 4. Snowflake Marketplace Integration

Share governance metadata:

```sql
-- Share governance data with other accounts
CREATE SHARE governance_data_share;

GRANT USAGE ON DATABASE ANALYTICS TO SHARE governance_data_share;
GRANT USAGE ON SCHEMA DATA_GOVERNANCE TO SHARE governance_data_share;
GRANT SELECT ON ALL TABLES IN SCHEMA DATA_GOVERNANCE TO SHARE governance_data_share;

-- Create consumer share
ALTER SHARE governance_data_share ADD ACCOUNTS = 'xy12345.us-east-1';
```

## CI/CD Pipeline Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/data-quality-check.yml
name: Data Quality Checks

on:
  schedule:
    - cron: '0 2 * * *'  # Run daily at 2 AM
  push:
    branches: [main]
    paths:
      - 'config/**'
      - 'sql/**'

jobs:
  quality-check:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Configure Snowflake credentials
        env:
          SF_USER: ${{ secrets.SNOWFLAKE_USER }}
          SF_PASSWORD: ${{ secrets.SNOWFLAKE_PASSWORD }}
          SF_ACCOUNT: ${{ secrets.SNOWFLAKE_ACCOUNT }}
        run: |
          cat > config/snowflake_config.json <<EOF
          {
            "user": "$SF_USER",
            "password": "$SF_PASSWORD",
            "account": "$SF_ACCOUNT",
            "warehouse": "COMPUTE_WH",
            "database": "ANALYTICS",
            "schema": "PUBLIC"
          }
          EOF
      
      - name: Run governance framework
        run: |
          python main_example.py
      
      - name: Upload reports
        uses: actions/upload-artifact@v3
        with:
          name: governance-reports
          path: output/
      
      - name: Comment PR with results
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const report = JSON.parse(fs.readFileSync('output/governance_report.json', 'utf8'));
            const comment = `## Data Governance Report
            - Tables Scanned: ${report.tables_scanned}
            - Quality Checks: ${report.quality_checks_run}
            - Issues Found: ${report.quality_issues_found}`;
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: comment
            });
      
      - name: Fail on critical issues
        run: |
          CRITICAL=$(jq '.governance_issues_found' output/governance_report.json)
          if [ "$CRITICAL" -gt 0 ]; then
            echo "Critical governance issues found"
            exit 1
          fi
```

### GitLab CI/CD Pipeline

```yaml
# .gitlab-ci.yml
stages:
  - quality-check
  - report
  - notify

variables:
  PYTHON_VERSION: "3.10"

quality-check:
  stage: quality-check
  image: python:${PYTHON_VERSION}
  script:
    - pip install -r requirements.txt
    - |
      cat > config/snowflake_config.json <<EOF
      {
        "user": "$SNOWFLAKE_USER",
        "password": "$SNOWFLAKE_PASSWORD",
        "account": "$SNOWFLAKE_ACCOUNT",
        "warehouse": "COMPUTE_WH",
        "database": "ANALYTICS",
        "schema": "PUBLIC"
      }
      EOF
    - python main_example.py
  artifacts:
    paths:
      - output/
    reports:
      dotenv: governance_metrics.env
  only:
    - main
    - merge_requests

generate-report:
  stage: report
  image: python:${PYTHON_VERSION}
  script:
    - pip install jinja2
    - python -c "
        import json
        from jinja2 import Template
        
        with open('output/governance_report.json') as f:
            report = json.load(f)
        
        template = Template(open('templates/report.html').read())
        html = template.render(report=report)
        
        with open('output/report.html', 'w') as f:
            f.write(html)
      "
  artifacts:
    paths:
      - output/report.html
  needs: ["quality-check"]

notify-slack:
  stage: notify
  script:
    - |
      SUMMARY=$(jq -r '"\(.tables_scanned) tables scanned, \(.quality_issues_found) issues found"' output/governance_report.json)
      curl -X POST $SLACK_WEBHOOK_URL \
        -H 'Content-Type: application/json' \
        -d "{\"text\": \"Data Governance Check: $SUMMARY\"}"
  needs: ["quality-check"]
```

## Apache Airflow Integration

```python
# dags/data_governance_dag.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.snowflake.operators.snowflake import SnowflakeSqlApiOperator
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, '/opt/airflow/data_governance/src')
from governance_orchestrator import GovernanceOrchestrator

default_args = {
    'owner': 'data-team',
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'email': ['data-quality@company.com'],
    'email_on_failure': True,
}

def run_governance_checks(**context):
    """Run governance checks"""
    config = {
        'user': context['var']['value']['sf_user'],
        'password': context['var']['value']['sf_password'],
        'account': context['var']['value']['sf_account'],
        'warehouse': 'COMPUTE_WH',
        'database': 'ANALYTICS',
        'schema': 'PUBLIC'
    }
    
    orchestrator = GovernanceOrchestrator(config)
    orchestrator.connect()
    
    try:
        report = orchestrator.process_all_tables(
            database='ANALYTICS',
            schema='PUBLIC',
            config_file='/opt/airflow/data_governance/config/governance_config.yaml'
        )
        
        orchestrator.export_report_to_json(
            f'/opt/airflow/data_governance/output/report_{datetime.now().isoformat()}.json'
        )
        
        # Push metrics to XCom for downstream tasks
        context['task_instance'].xcom_push(
            key='quality_issues',
            value=report['quality_issues_found']
        )
        
    finally:
        orchestrator.disconnect()

dag = DAG(
    'data_governance_check',
    default_args=default_args,
    description='Daily data governance and quality checks',
    schedule_interval='0 2 * * *',  # 2 AM daily
    start_date=datetime(2024, 1, 1),
    catchup=False,
)

# Initialize governance schema
init_schema = SnowflakeSqlApiOperator(
    task_id='init_governance_schema',
    sql='/opt/airflow/data_governance/sql/01_create_governance_schema.sql',
    snowflake_conn_id='snowflake_default',
    dag=dag,
)

# Run governance checks
run_checks = PythonOperator(
    task_id='run_governance_checks',
    python_callable=run_governance_checks,
    provide_context=True,
    dag=dag,
)

# Generate reports
generate_reports = SnowflakeSqlApiOperator(
    task_id='generate_governance_reports',
    sql='/opt/airflow/data_governance/sql/03_governance_reports.sql',
    snowflake_conn_id='snowflake_default',
    dag=dag,
)

init_schema >> run_checks >> generate_reports
```

## Kubernetes Integration

Deploy as Kubernetes CronJob:

```yaml
# kubernetes/governance-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: data-governance-check
  namespace: data-platform
spec:
  schedule: "0 2 * * *"  # 2 AM daily
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: governance-check
            image: data-governance:latest
            imagePullPolicy: Always
            env:
            - name: SNOWFLAKE_USER
              valueFrom:
                secretKeyRef:
                  name: snowflake-creds
                  key: user
            - name: SNOWFLAKE_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: snowflake-creds
                  key: password
            - name: SNOWFLAKE_ACCOUNT
              valueFrom:
                secretKeyRef:
                  name: snowflake-creds
                  key: account
            volumeMounts:
            - name: config
              mountPath: /app/config
            - name: output
              mountPath: /app/output
            command: ["python", "main_example.py"]
          volumes:
          - name: config
            configMap:
              name: governance-config
          - name: output
            emptyDir: {}
          restartPolicy: OnFailure
```

## Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/
COPY sql/ ./sql/
COPY config/ ./config/
COPY main_example.py .

ENV PYTHONUNBUFFERED=1

CMD ["python", "main_example.py"]
```

Build and run:
```bash
docker build -t data-governance:latest .
docker run \
  -e SNOWFLAKE_USER=user \
  -e SNOWFLAKE_PASSWORD=pass \
  -e SNOWFLAKE_ACCOUNT=account \
  -v $(pwd)/output:/app/output \
  data-governance:latest
```

## Monitoring & Alerting

### Datadog Integration

```python
# src/datadog_integration.py
from datadog import initialize, api
import json

def send_metrics_to_datadog(report):
    """Send governance metrics to Datadog"""
    options = {
        'api_key': os.getenv('DD_API_KEY'),
        'app_key': os.getenv('DD_APP_KEY')
    }
    
    initialize(**options)
    
    timestamp = int(datetime.now().timestamp())
    
    api.Metric.send(
        metric='data_governance.tables_scanned',
        points=report['tables_scanned'],
        timestamp=timestamp,
        tags=['env:production']
    )
    
    api.Metric.send(
        metric='data_governance.quality_issues',
        points=report['quality_issues_found'],
        timestamp=timestamp,
        tags=['env:production']
    )
```

### Prometheus Metrics

```python
# src/prometheus_metrics.py
from prometheus_client import Counter, Gauge, start_http_server

tables_scanned = Gauge('governance_tables_scanned_total', 'Total tables scanned')
quality_issues = Counter('governance_quality_issues_total', 'Total quality issues found')
compliance_issues = Gauge('governance_compliance_issues_open', 'Open compliance issues')

def export_metrics(report):
    tables_scanned.set(report['tables_scanned'])
    quality_issues.inc(report['quality_issues_found'])
    compliance_issues.set(report['governance_issues_found'])
```

## Best Practices for Integration

1. **Secrets Management**: Use proper secret management tools (Vault, AWS Secrets Manager)
2. **Logging**: Send logs to centralized logging (ELK, Splunk, Cloud Logging)
3. **Error Handling**: Implement retry logic and comprehensive error handling
4. **Testing**: Test integrations in non-production environments first
5. **Monitoring**: Track framework performance and alert on failures
6. **Documentation**: Keep integration docs updated
7. **Access Control**: Restrict access to governance data appropriately
