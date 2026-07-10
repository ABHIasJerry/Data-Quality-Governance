-- Create Data Governance Schema and Tables
-- Run this script to initialize the governance tracking infrastructure

-- Create the governance schema
CREATE SCHEMA IF NOT EXISTS DATA_GOVERNANCE
  COMMENT = 'Data governance and quality tracking schema';

-- Table Registry: Catalog of all managed tables
CREATE TABLE IF NOT EXISTS DATA_GOVERNANCE.TABLE_REGISTRY (
    table_id STRING,
    database_name STRING,
    schema_name STRING,
    table_name STRING,
    governance_level STRING COMMENT 'PUBLIC, INTERNAL, CONFIDENTIAL, or RESTRICTED',
    owner_team STRING,
    description STRING,
    critical_table BOOLEAN DEFAULT FALSE,
    pii_present BOOLEAN DEFAULT FALSE,
    row_count_approx INTEGER,
    size_mb_approx FLOAT,
    last_accessed TIMESTAMP_TZ,
    last_modified TIMESTAMP_TZ,
    created_at TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (table_id)
)
COMMENT = 'Master registry of all data tables under governance';

-- Quality Metrics: Track data quality check results
CREATE TABLE IF NOT EXISTS DATA_GOVERNANCE.QUALITY_METRICS (
    metric_id STRING,
    table_id STRING,
    table_name STRING,
    check_type STRING COMMENT 'DUPLICATE_RECORDS, NULL_VALUES, DATA_TYPE_CONSISTENCY, etc.',
    passed BOOLEAN,
    severity STRING COMMENT 'INFO, WARNING, ERROR, CRITICAL',
    details STRING,
    check_timestamp TIMESTAMP_TZ,
    created_at TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (metric_id),
    FOREIGN KEY (table_id) REFERENCES TABLE_REGISTRY(table_id)
)
COMMENT = 'Historical data quality check results';

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_quality_metrics_table 
    ON DATA_GOVERNANCE.QUALITY_METRICS(table_id, check_timestamp DESC);

-- Data Lineage: Track data flow and transformations
CREATE TABLE IF NOT EXISTS DATA_GOVERNANCE.DATA_LINEAGE (
    lineage_id STRING,
    source_database STRING,
    source_schema STRING,
    source_table STRING,
    target_database STRING,
    target_schema STRING,
    target_table STRING,
    transformation_type STRING COMMENT 'ETL, ELT, COPY, etc.',
    transformation_logic STRING,
    job_name STRING,
    last_run TIMESTAMP_TZ,
    run_duration_seconds INTEGER,
    run_status STRING COMMENT 'SUCCESS, FAILED, RUNNING',
    rows_processed INTEGER,
    error_message STRING,
    created_at TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (lineage_id)
)
COMMENT = 'Data lineage and transformation tracking';

-- Access Logs: Track table access for audit compliance
CREATE TABLE IF NOT EXISTS DATA_GOVERNANCE.ACCESS_LOGS (
    access_id STRING,
    table_name STRING,
    user_name STRING,
    user_role STRING,
    access_type STRING COMMENT 'SELECT, INSERT, UPDATE, DELETE',
    query_hash STRING,
    rows_accessed INTEGER,
    success BOOLEAN,
    access_timestamp TIMESTAMP_TZ,
    created_at TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (access_id)
)
COMMENT = 'Audit log for table access patterns';

-- Compliance Issues: Track governance violations and remediation
CREATE TABLE IF NOT EXISTS DATA_GOVERNANCE.COMPLIANCE_ISSUES (
    issue_id STRING,
    table_id STRING,
    table_name STRING,
    issue_type STRING COMMENT 'DATA_QUALITY, MISSING_METADATA, ACCESS_CONTROL, etc.',
    severity STRING COMMENT 'INFO, WARNING, ERROR, CRITICAL',
    description STRING,
    remediation_action STRING,
    responsible_team STRING,
    status STRING COMMENT 'OPEN, IN_PROGRESS, RESOLVED, CLOSED',
    due_date DATE,
    created_at TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP(),
    resolved_at TIMESTAMP_TZ,
    resolution_notes STRING,
    PRIMARY KEY (issue_id),
    FOREIGN KEY (table_id) REFERENCES TABLE_REGISTRY(table_id)
)
COMMENT = 'Data governance compliance issue tracking';

-- Data Dictionary: Column-level metadata
CREATE TABLE IF NOT EXISTS DATA_GOVERNANCE.DATA_DICTIONARY (
    column_id STRING,
    table_id STRING,
    table_name STRING,
    column_name STRING,
    column_position INTEGER,
    data_type STRING,
    is_nullable BOOLEAN,
    is_key BOOLEAN COMMENT 'Primary or foreign key',
    is_encrypted BOOLEAN DEFAULT FALSE,
    contains_pii BOOLEAN DEFAULT FALSE,
    business_description STRING,
    technical_description STRING,
    valid_values_description STRING,
    created_at TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (column_id),
    FOREIGN KEY (table_id) REFERENCES TABLE_REGISTRY(table_id)
)
COMMENT = 'Detailed column-level metadata and lineage';

-- Create index for dictionary searches
CREATE INDEX IF NOT EXISTS idx_data_dictionary_table 
    ON DATA_GOVERNANCE.DATA_DICTIONARY(table_id);

-- Governance Rules: Define policies and constraints
CREATE TABLE IF NOT EXISTS DATA_GOVERNANCE.GOVERNANCE_RULES (
    rule_id STRING,
    rule_name STRING,
    rule_type STRING COMMENT 'ACCESS_CONTROL, DATA_QUALITY, RETENTION, ENCRYPTION',
    description STRING,
    applies_to_level STRING COMMENT 'PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED',
    rule_definition STRING COMMENT 'JSON or expression defining the rule',
    enforcement_required BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (rule_id)
)
COMMENT = 'Data governance policies and rules';

-- Data Quality Standards: Define quality thresholds
CREATE TABLE IF NOT EXISTS DATA_GOVERNANCE.QUALITY_STANDARDS (
    standard_id STRING,
    table_id STRING,
    check_type STRING,
    metric_name STRING,
    acceptable_threshold FLOAT,
    warning_threshold FLOAT,
    critical_threshold FLOAT,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (standard_id),
    FOREIGN KEY (table_id) REFERENCES TABLE_REGISTRY(table_id)
)
COMMENT = 'Quality standards and thresholds by table';

-- Grant appropriate permissions
GRANT USAGE ON SCHEMA DATA_GOVERNANCE TO ROLE SYSADMIN;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA DATA_GOVERNANCE TO ROLE SYSADMIN;
