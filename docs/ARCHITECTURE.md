# Data Governance Framework Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                   Data Governance Framework                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐   │
│  │         Governance Orchestrator (Main Entry)           │   │
│  │  - Coordinates all governance activities              │   │
│  │  - Manages workflow execution                         │   │
│  │  - Generates reports                                  │   │
│  └────────────┬───────────────────────────────────────────┘   │
│               │                                                │
│     ┌─────────┴──────────┬──────────────┬──────────────┐      │
│     ▼                    ▼              ▼              ▼      │
│ ┌─────────┐  ┌──────────────────┐ ┌──────────────┐ ┌────────┐ │
│ │Metadata │  │Data Quality      │ │Governance    │ │Snowflake│
│ │Scanner  │  │Checker           │ │Manager       │ │Connector│
│ │         │  │                  │ │              │ │         │
│ │- Scans  │  │- Duplicates      │ │- Registration│ │- Connect│
│ │- Profiles│ │- Null values     │ │- Compliance  │ │- Execute│
│ │- Profiles│ │- Data types      │ │- Lineage     │ │- Query  │
│ │- Records │ │- Referential     │ │- Tracking    │ │         │
│ │metadata  │ │- Outliers        │ │              │ │         │
│ │          │ │- Freshness       │ │              │ │         │
│ │          │ │- Patterns        │ │              │ │         │
│ └─────────┘  └──────────────────┘ └──────────────┘ └────────┘
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
         │                                           │
         │ Reads                              Writes & Reads
         ▼                                           ▼
    ┌──────────────────────────────────────────────────────┐
    │            Snowflake ANALYTICS Database             │
    ├──────────────────────────────────────────────────────┤
    │                                                      │
    │  ┌──────────────────────────────────────────────┐  │
    │  │        DATA_GOVERNANCE Schema                │  │
    │  ├──────────────────────────────────────────────┤  │
    │  │                                              │  │
    │  │  • TABLE_REGISTRY          (Master Catalog) │  │
    │  │  • QUALITY_METRICS         (Check Results)  │  │
    │  │  • COMPLIANCE_ISSUES       (Issue Tracking) │  │
    │  │  • DATA_LINEAGE            (Transform Flow) │  │
    │  │  • DATA_DICTIONARY         (Column Metadata)│  │
    │  │  • ACCESS_LOGS             (Audit Trail)    │  │
    │  │  • GOVERNANCE_RULES        (Policies)       │  │
    │  │  • QUALITY_STANDARDS       (Thresholds)     │  │
    │  │                                              │  │
    │  └──────────────────────────────────────────────┘  │
    │                                                      │
    │  ┌──────────────────────────────────────────────┐  │
    │  │        PUBLIC Schema (Business Tables)       │  │
    │  ├──────────────────────────────────────────────┤  │
    │  │  • CUSTOMERS       (Scanned & Monitored)    │  │
    │  │  • ORDERS          (Scanned & Monitored)    │  │
    │  │  • PRODUCTS        (Scanned & Monitored)    │  │
    │  │  • ... (100+ tables)                        │  │
    │  └──────────────────────────────────────────────┘  │
    │                                                      │
    └──────────────────────────────────────────────────────┘
```

## Component Architecture

### 1. SnowflakeConnector
**Purpose**: Handle all database connectivity and operations

```
┌─────────────────────────────────┐
│   SnowflakeConnector            │
├─────────────────────────────────┤
│ Attributes:                     │
│ - config (connection params)    │
│ - connection (active conn)      │
├─────────────────────────────────┤
│ Methods:                        │
│ + connect()                     │
│ + disconnect()                  │
│ + get_cursor()                  │
│ + execute_query()               │
│ + execute_update()              │
│ + fetch_table_list()            │
└─────────────────────────────────┘
```

**Responsibility**: Connection management and SQL execution
**Used By**: All other components

### 2. MetadataScanner
**Purpose**: Profile and catalog table metadata

```
┌─────────────────────────────────┐
│   MetadataScanner               │
├─────────────────────────────────┤
│ Attributes:                     │
│ - connector (SnowflakeConn)     │
├─────────────────────────────────┤
│ Methods:                        │
│ + scan_table_metadata()         │
│ + scan_all_tables()             │
│ - _get_column_info()            │
│ - _get_row_count()              │
│ - _get_table_size()             │
│ - _assess_completeness()        │
└─────────────────────────────────┘
```

**Returns**:
```json
{
  "database": "ANALYTICS",
  "schema": "PUBLIC",
  "table_name": "CUSTOMERS",
  "columns": [...],
  "row_count": 1000000,
  "table_size_mb": 250.5,
  "creation_time": "2024-01-01",
  "data_completeness": {...}
}
```

### 3. DataQualityChecker
**Purpose**: Execute comprehensive quality checks

```
┌─────────────────────────────────┐
│   DataQualityChecker            │
├─────────────────────────────────┤
│ Attributes:                     │
│ - connector (SnowflakeConn)     │
│ - checks_performed (list)       │
├─────────────────────────────────┤
│ Check Methods:                  │
│ + run_quality_checks()          │
│ - _check_duplicates()           │
│ - _check_null_values()          │
│ - _check_data_types()           │
│ - _check_referential_integrity()│
│ - _check_numeric_outliers()     │
│ - _check_data_freshness()       │
│ - _check_patterns()             │
└─────────────────────────────────┘
```

**Check Types**:
1. **DUPLICATE_RECORDS** - Full row duplicates
2. **NULL_VALUES** - Unexpected nulls
3. **DATA_TYPE_CONSISTENCY** - Type mismatches
4. **REFERENTIAL_INTEGRITY** - Foreign key violations
5. **NUMERIC_OUTLIERS** - Statistical anomalies
6. **DATA_FRESHNESS** - Age threshold violations
7. **PATTERN_VALIDATION** - Regex non-matches

### 4. GovernanceManager
**Purpose**: Manage governance policies and tracking

```
┌─────────────────────────────────┐
│   GovernanceManager             │
├─────────────────────────────────┤
│ Methods:                        │
│ + create_governance_schema()    │
│ + register_table()              │
│ + log_quality_check()           │
│ + record_lineage()              │
│ + create_compliance_issue()     │
│ + get_governance_report()       │
└─────────────────────────────────┘
```

**Governance Levels**:
```
PUBLIC        ─► No restrictions
   ↓
INTERNAL      ─► Internal use only
   ↓
CONFIDENTIAL   ─► Sensitive business data
   ↓
RESTRICTED    ─► PII/Financial/Critical
```

### 5. GovernanceOrchestrator
**Purpose**: Coordinate all activities and workflows

```
┌──────────────────────────────────────────────┐
│     GovernanceOrchestrator                   │
├──────────────────────────────────────────────┤
│ Attributes:                                  │
│ - connector                                  │
│ - metadata_scanner                          │
│ - quality_checker                           │
│ - governance_manager                        │
│ - governance_config                         │
│ - execution_report                          │
├──────────────────────────────────────────────┤
│ Orchestration Methods:                      │
│ + connect()                                 │
│ + disconnect()                              │
│ + initialize_governance_framework()         │
│ + scan_and_register_tables()                │
│ + process_all_tables()                      │
│ + run_quality_checks()                      │
│ + record_data_lineage()                     │
│ + generate_governance_report()              │
│ + export_report_to_json()                   │
│ + export_report_to_html()                   │
└──────────────────────────────────────────────┘
```

## Data Flow Diagram

```
┌─────────────┐
│  Start Job  │
└──────┬──────┘
       │
       ▼
┌──────────────────────────┐
│ Load Configuration       │
│ - Snowflake Connection   │
│ - Governance Config      │
└──────┬───────────────────┘
       │
       ▼
┌──────────────────────────┐
│ Connect to Snowflake     │
│ - Establish Connection   │
│ - Initialize Components  │
└──────┬───────────────────┘
       │
       ▼
┌──────────────────────────────┐
│ Initialize Governance Schema │
│ - Create Tables              │
│ - Set Permissions            │
└──────┬───────────────────────┘
       │
       ▼
┌───────────────────────────────┐
│ For Each Table:               │
├───────────────────────────────┤
│                               │
│  1. Register Table            │
│     └─► Governance Config     │
│         └─► TABLE_REGISTRY    │
│                               │
│  2. Scan Metadata             │
│     └─► Column Info           │
│     └─► Row Count             │
│     └─► Size Metrics          │
│     └─► Data Completeness     │
│                               │
│  3. Run Quality Checks        │
│     └─► Duplicates            │
│     └─► Nulls                 │
│     └─► Types                 │
│     └─► Freshness             │
│     └─► Patterns              │
│         └─► QUALITY_METRICS   │
│                               │
│  4. Log Issues                │
│     └─► Create Compliance     │
│         Issues if Failed      │
│         └─► COMPLIANCE_ISSUES │
│                               │
└──────┬────────────────────────┘
       │
       ▼
┌──────────────────────────┐
│ Generate Reports         │
│ - Execution Summary      │
│ - Quality Status         │
│ - Compliance Issues      │
└──────┬───────────────────┘
       │
       ▼
┌──────────────────────────┐
│ Export Results           │
│ - JSON Report            │
│ - HTML Dashboard         │
│ - Database Tables        │
└──────┬───────────────────┘
       │
       ▼
┌──────────────────────────┐
│ Disconnect               │
│ - Close Connection       │
│ - Cleanup Resources      │
└──────┬───────────────────┘
       │
       ▼
┌─────────────┐
│  End Job    │
└─────────────┘
```

## Database Schema

### Core Tables

#### TABLE_REGISTRY
```sql
table_id          ──► STRING (PK) - Unique identifier
database_name    ──► STRING       - Source database
schema_name      ──► STRING       - Source schema
table_name       ──► STRING       - Table name
governance_level ──► STRING       - Classification
owner_team       ──► STRING       - Responsible team
critical_table   ──► BOOLEAN      - Criticality flag
pii_present      ──► BOOLEAN      - PII indicator
row_count_approx ──► INTEGER      - Approximate row count
last_modified    ──► TIMESTAMP    - Last change
```

#### QUALITY_METRICS
```sql
metric_id        ──► STRING (PK) - Unique identifier
table_id         ──► STRING (FK) - References TABLE_REGISTRY
check_type       ──► STRING       - Type of check
passed           ──► BOOLEAN      - Pass/fail status
severity         ──► STRING       - INFO/WARNING/ERROR/CRITICAL
details          ──► STRING       - Issue description
check_timestamp  ──► TIMESTAMP    - When check ran
```

#### COMPLIANCE_ISSUES
```sql
issue_id         ──► STRING (PK) - Unique identifier
table_id         ──► STRING (FK) - References TABLE_REGISTRY
issue_type       ──► STRING       - Type of issue
severity         ──► STRING       - Severity level
description      ──► STRING       - Issue details
status           ──► STRING       - OPEN/IN_PROGRESS/RESOLVED
due_date         ──► DATE         - Remediation due date
remediation_action ──► STRING     - Required action
```

#### DATA_LINEAGE
```sql
lineage_id       ──► STRING (PK) - Unique identifier
source_table     ──► STRING       - Source table name
target_table     ──► STRING       - Target table name
transformation_type ──► STRING    - ETL/ELT/COPY/etc
transformation_logic ──► STRING   - Transformation description
run_status       ──► STRING       - SUCCESS/FAILED
last_run         ──► TIMESTAMP    - Last execution time
```

## Quality Check Execution Flow

```
Quality Check Request
    │
    ├─► DUPLICATE_RECORDS
    │   └─► ROW_NUMBER() window function
    │       └─► Compare all column combinations
    │           └─► Count duplicates
    │
    ├─► NULL_VALUES
    │   └─► Count nulls by column
    │       └─► Compare against expected nullability
    │
    ├─► DATA_TYPE_CONSISTENCY
    │   └─► Query INFORMATION_SCHEMA
    │       └─► Compare actual vs expected types
    │
    ├─► REFERENTIAL_INTEGRITY
    │   └─► Check FK columns exist in ref table
    │       └─► Count orphaned records
    │
    ├─► NUMERIC_OUTLIERS
    │   └─► Calculate mean and std dev
    │       └─► Identify values beyond threshold
    │
    ├─► DATA_FRESHNESS
    │   └─► Query timestamp column
    │       └─► Compare against max age
    │
    └─► PATTERN_VALIDATION
        └─► REGEXP_LIKE matching
            └─► Count violations
                
Results:
├─► Passed (severity: INFO)
│   └─► Log successful check
│
└─► Failed (severity: WARNING/ERROR/CRITICAL)
    └─► Create compliance issue
    └─► Store in QUALITY_METRICS
    └─► Alert relevant team
```

## Configuration Hierarchy

```
snowflake_config.json (Connection)
    │
    └─► governance_config.yaml (Table Configs)
        │
        ├─► Global defaults
        │   └─► Apply to all tables
        │
        ├─► Per-table governance
        │   ├─► governance_level
        │   ├─► owner_team
        │   ├─► critical_table
        │   └─► pii_present
        │
        └─► Per-table quality checks
            ├─► check_duplicates
            ├─► check_nulls (+ nullable_columns)
            ├─► check_data_types (+ type_rules)
            ├─► check_outliers (+ numeric_columns)
            ├─► check_freshness (+ timestamp_column)
            ├─► check_patterns (+ regex rules)
            └─► check_referential_integrity (+ FK rules)
```

## Report Generation Pipeline

```
Execution Report
    │
    ├─► Summary Metrics
    │   ├─► tables_scanned
    │   ├─► quality_checks_run
    │   ├─► quality_issues_found
    │   ├─► governance_issues_found
    │   └─► execution_time
    │
    ├─► Detailed Results
    │   ├─► Per-table metadata
    │   ├─► Per-table quality checks
    │   ├─► Per-table issues
    │   └─► Per-table errors (if any)
    │
    └─► Export Formats
        ├─► JSON
        │   └─► Machine readable
        │       └─► Can be parsed by systems
        │
        ├─► HTML
        │   └─► Visual dashboard
        │       └─► Browser view
        │
        └─► Database Tables
            └─► Snowflake queries
                └─► Pre-built dashboards
```

## Scaling Architecture

### For 100+ Tables

```
Sequential Processing
    ├─► Process one table at a time
    ├─► Estimated time: 2-5 min per table
    ├─► Total: 3-8 hours for 100 tables
    └─► Use nightly scheduling

Parallel Processing (Advanced)
    ├─► Thread pool executor
    ├─► Process multiple tables simultaneously
    ├─► Max workers: 5-10 (depends on warehouse)
    ├─► Estimated time: 30 min for 100 tables
    └─► Recommended for production
```

### Database Optimization

```
Indexing Strategy
├─► Primary Indexes (PKs)
│   └─► All primary keys
│
├─► Foreign Keys
│   └─► table_id references
│
└─► Query Optimization
    ├─► Index on (table_id, check_timestamp)
    ├─► Index on (table_name)
    └─► Cluster tables by check_timestamp
```

## Monitoring & Observability

```
Framework Metrics
├─► Execution Metrics
│   ├─► Total tables scanned
│   ├─► Checks executed
│   ├─► Issues found
│   └─► Execution time
│
├─► Quality Metrics
│   ├─► Pass/fail rates
│   ├─► Issue severity distribution
│   ├─► Issue resolution time
│   └─► Quality trends
│
├─► Governance Metrics
│   ├─► Classification coverage
│   ├─► Documentation completeness
│   ├─► Compliance issue count
│   └─► PII data inventory
│
└─► System Metrics
    ├─► Database query performance
    ├─► API response times
    ├─► Memory usage
    └─► Error rates
```

## Security Architecture

```
Access Control
├─► Schema Level
│   ├─► DATA_GOVERNANCE schema
│   │   └─► Only SYSADMIN role
│   │
│   └─► PUBLIC schema
│       └─► Business users
│
├─► Table Level
│   ├─► Sensitive tables (PII)
│   │   └─► Restricted access
│   │
│   └─► Quality metrics
│       └─► Team read-only
│
└─► Row Level
    ├─► Access logs
    │   └─► Audit trail
    │
    └─► Compliance issues
        └─► Team visibility
```

---

This architecture provides:
✅ **Scalability** - Process 100+ tables efficiently
✅ **Modularity** - Each component has single responsibility
✅ **Extensibility** - Add custom checks easily
✅ **Observability** - Track all activities
✅ **Security** - Proper access controls
✅ **Reliability** - Error handling and recovery
