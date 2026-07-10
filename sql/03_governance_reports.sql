-- Governance Reporting Queries
-- Use these queries for dashboards and compliance reports

-- 1. Data Governance Summary Dashboard
SELECT 
    'Total Tables Under Governance' as metric,
    COUNT(*) as value
FROM DATA_GOVERNANCE.TABLE_REGISTRY
UNION ALL
SELECT 
    'Tables Classified as Critical' as metric,
    COUNT(*) as value
FROM DATA_GOVERNANCE.TABLE_REGISTRY
WHERE critical_table = TRUE
UNION ALL
SELECT 
    'Tables with PII' as metric,
    COUNT(*) as value
FROM DATA_GOVERNANCE.TABLE_REGISTRY
WHERE pii_present = TRUE
UNION ALL
SELECT 
    'Data Quality Issues (Last 7 Days)' as metric,
    COUNT(*) as value
FROM DATA_GOVERNANCE.QUALITY_METRICS
WHERE passed = FALSE
  AND check_timestamp > CURRENT_TIMESTAMP() - INTERVAL '7 days'
UNION ALL
SELECT 
    'Open Compliance Issues' as metric,
    COUNT(*) as value
FROM DATA_GOVERNANCE.COMPLIANCE_ISSUES
WHERE status = 'OPEN';

-- 2. Governance Level Distribution
SELECT 
    governance_level,
    COUNT(*) as table_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM DATA_GOVERNANCE.TABLE_REGISTRY), 2) as percentage
FROM DATA_GOVERNANCE.TABLE_REGISTRY
GROUP BY governance_level
ORDER BY table_count DESC;

-- 3. Data Quality Status by Table
SELECT 
    tr.table_name,
    tr.owner_team,
    tr.critical_table,
    COUNT(qm.metric_id) as total_checks,
    COUNT(qm.metric_id) FILTER (WHERE qm.passed = TRUE) as passed_checks,
    COUNT(qm.metric_id) FILTER (WHERE qm.passed = FALSE) as failed_checks,
    ROUND(
        COUNT(qm.metric_id) FILTER (WHERE qm.passed = TRUE) * 100.0 / NULLIF(COUNT(qm.metric_id), 0), 
        2
    ) as quality_score_pct,
    MAX(qm.check_timestamp) as last_check_time
FROM DATA_GOVERNANCE.TABLE_REGISTRY tr
LEFT JOIN DATA_GOVERNANCE.QUALITY_METRICS qm 
    ON tr.table_id = qm.table_id
GROUP BY tr.table_name, tr.owner_team, tr.critical_table
ORDER BY quality_score_pct ASC;

-- 4. Quality Issues Severity Report
SELECT 
    check_type,
    severity,
    COUNT(*) as issue_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM DATA_GOVERNANCE.QUALITY_METRICS WHERE passed = FALSE), 2) as percentage_of_issues
FROM DATA_GOVERNANCE.QUALITY_METRICS
WHERE passed = FALSE
  AND check_timestamp > CURRENT_TIMESTAMP() - INTERVAL '30 days'
GROUP BY check_type, severity
ORDER BY issue_count DESC;

-- 5. Data Lineage Overview
SELECT 
    source_table,
    target_table,
    transformation_type,
    COUNT(*) as lineage_count,
    MAX(last_run) as last_execution,
    COUNT(*) FILTER (WHERE run_status = 'SUCCESS') as successful_runs,
    COUNT(*) FILTER (WHERE run_status = 'FAILED') as failed_runs
FROM DATA_GOVERNANCE.DATA_LINEAGE
GROUP BY source_table, target_table, transformation_type
ORDER BY last_execution DESC NULLS LAST;

-- 6. PII and Confidential Data Inventory
SELECT 
    table_name,
    database_name,
    schema_name,
    owner_team,
    row_count_approx,
    COUNT(DISTINCT dd.column_name) as pii_columns,
    STRING_AGG(dd.column_name, ', ') as column_names
FROM DATA_GOVERNANCE.TABLE_REGISTRY tr
LEFT JOIN DATA_GOVERNANCE.DATA_DICTIONARY dd 
    ON tr.table_id = dd.table_id AND dd.contains_pii = TRUE
WHERE tr.pii_present = TRUE OR tr.governance_level IN ('CONFIDENTIAL', 'RESTRICTED')
GROUP BY tr.table_name, tr.database_name, tr.schema_name, tr.owner_team, tr.row_count_approx
ORDER BY tr.table_name;

-- 7. Compliance Issue Resolution Status
SELECT 
    status,
    severity,
    COUNT(*) as issue_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM DATA_GOVERNANCE.COMPLIANCE_ISSUES), 2) as percentage
FROM DATA_GOVERNANCE.COMPLIANCE_ISSUES
GROUP BY status, severity
ORDER BY issue_count DESC;

-- 8. Critical Tables Health Status
SELECT 
    tr.table_name,
    tr.owner_team,
    COALESCE(qm_last.passed, TRUE) as last_quality_check_passed,
    qm_last.severity as last_check_severity,
    qm_last.check_timestamp as last_check_time,
    tr.last_modified,
    DATEDIFF(day, tr.last_modified, CURRENT_TIMESTAMP()) as days_since_update,
    CASE 
        WHEN tr.last_modified < CURRENT_TIMESTAMP() - INTERVAL '7 days' THEN 'STALE'
        WHEN qm_last.passed = FALSE AND qm_last.severity IN ('ERROR', 'CRITICAL') THEN 'FAILING'
        ELSE 'HEALTHY'
    END as health_status
FROM DATA_GOVERNANCE.TABLE_REGISTRY tr
LEFT JOIN (
    SELECT 
        table_id,
        passed,
        severity,
        check_timestamp,
        ROW_NUMBER() OVER (PARTITION BY table_id ORDER BY check_timestamp DESC) as rn
    FROM DATA_GOVERNANCE.QUALITY_METRICS
) qm_last ON tr.table_id = qm_last.table_id AND qm_last.rn = 1
WHERE tr.critical_table = TRUE
ORDER BY health_status DESC, last_check_time DESC NULLS LAST;

-- 9. Access Patterns by Table
SELECT 
    table_name,
    COUNT(*) as access_count,
    COUNT(DISTINCT user_name) as unique_users,
    COUNT(DISTINCT access_type) as access_types,
    SUM(rows_accessed) as total_rows_accessed,
    MAX(access_timestamp) as last_access_time,
    ROUND(SUM(rows_accessed) / NULLIF(COUNT(*), 0), 0) as avg_rows_per_access
FROM DATA_GOVERNANCE.ACCESS_LOGS
WHERE access_timestamp > CURRENT_TIMESTAMP() - INTERVAL '30 days'
GROUP BY table_name
ORDER BY access_count DESC;

-- 10. Governance Compliance Score by Team
SELECT 
    owner_team,
    COUNT(*) as table_count,
    COUNT(*) FILTER (WHERE critical_table = TRUE) as critical_tables,
    COUNT(*) FILTER (WHERE pii_present = TRUE) as tables_with_pii,
    ROUND(
        COUNT(*) FILTER (WHERE governance_level != 'PUBLIC') * 100.0 / COUNT(*),
        2
    ) as classified_pct,
    ROUND(
        COUNT(*) FILTER (WHERE governance_level IN ('CONFIDENTIAL', 'RESTRICTED')) * 100.0 / COUNT(*),
        2
    ) as highly_protected_pct
FROM DATA_GOVERNANCE.TABLE_REGISTRY
GROUP BY owner_team
ORDER BY table_count DESC;

-- 11. Data Dictionary Gaps
SELECT 
    tr.table_name,
    tr.owner_team,
    COUNT(DISTINCT ic.COLUMN_NAME) as total_columns,
    COUNT(DISTINCT dd.column_name) as documented_columns,
    COUNT(DISTINCT ic.COLUMN_NAME) - COUNT(DISTINCT dd.column_name) as missing_documentation
FROM DATA_GOVERNANCE.TABLE_REGISTRY tr
LEFT JOIN INFORMATION_SCHEMA.COLUMNS ic 
    ON ic.TABLE_SCHEMA = tr.schema_name 
    AND ic.TABLE_NAME = tr.table_name
LEFT JOIN DATA_GOVERNANCE.DATA_DICTIONARY dd 
    ON tr.table_id = dd.table_id 
    AND ic.COLUMN_NAME = dd.column_name
GROUP BY tr.table_name, tr.owner_team
HAVING COUNT(DISTINCT ic.COLUMN_NAME) > COUNT(DISTINCT dd.column_name)
ORDER BY missing_documentation DESC;

-- 12. Data Quality Trend (Last 30 Days)
SELECT 
    DATE_TRUNC('day', check_timestamp) as check_date,
    COUNT(*) as total_checks,
    COUNT(*) FILTER (WHERE passed = TRUE) as passed_checks,
    COUNT(*) FILTER (WHERE passed = FALSE) as failed_checks,
    ROUND(
        COUNT(*) FILTER (WHERE passed = TRUE) * 100.0 / COUNT(*),
        2
    ) as quality_pct
FROM DATA_GOVERNANCE.QUALITY_METRICS
WHERE check_timestamp > CURRENT_TIMESTAMP() - INTERVAL '30 days'
GROUP BY DATE_TRUNC('day', check_timestamp)
ORDER BY check_date DESC;

-- 13. Lineage Dependencies Analysis
WITH lineage_tree AS (
    SELECT 
        source_table,
        target_table,
        1 as depth
    FROM DATA_GOVERNANCE.DATA_LINEAGE
    WHERE source_table IS NOT NULL
    
    UNION ALL
    
    SELECT 
        lt.source_table,
        dl.target_table,
        lt.depth + 1
    FROM lineage_tree lt
    JOIN DATA_GOVERNANCE.DATA_LINEAGE dl 
        ON lt.target_table = dl.source_table
    WHERE lt.depth < 5
)
SELECT 
    source_table,
    COUNT(DISTINCT target_table) as downstream_tables,
    MAX(depth) as max_depth
FROM lineage_tree
GROUP BY source_table
ORDER BY downstream_tables DESC;

-- 14. Encryption and Security Status
SELECT 
    tr.table_name,
    tr.governance_level,
    COUNT(*) as total_columns,
    COUNT(*) FILTER (WHERE dd.is_encrypted = TRUE) as encrypted_columns,
    COUNT(*) FILTER (WHERE dd.contains_pii = TRUE) as pii_columns,
    COUNT(*) FILTER (WHERE dd.is_key = TRUE) as key_columns,
    ROUND(
        COUNT(*) FILTER (WHERE dd.is_encrypted = TRUE) * 100.0 / COUNT(*),
        2
    ) as encryption_coverage_pct
FROM DATA_GOVERNANCE.TABLE_REGISTRY tr
LEFT JOIN DATA_GOVERNANCE.DATA_DICTIONARY dd 
    ON tr.table_id = dd.table_id
GROUP BY tr.table_name, tr.governance_level
ORDER BY encryption_coverage_pct ASC;

-- 15. Governance Readiness Assessment
SELECT 
    CASE 
        WHEN a.tables_registered = 0 THEN 'RED'
        WHEN b.tables_with_quality_issues > (a.tables_registered * 0.2) THEN 'YELLOW'
        WHEN c.open_issues > (a.tables_registered * 0.1) THEN 'YELLOW'
        ELSE 'GREEN'
    END as readiness_status,
    a.tables_registered,
    COUNT(*) FILTER (WHERE c.status = 'OPEN') as open_compliance_issues,
    b.tables_with_quality_issues,
    ROUND(
        (a.tables_registered - COUNT(*) FILTER (WHERE c.status = 'OPEN')) * 100.0 / a.tables_registered,
        2
    ) as compliance_score_pct
FROM (SELECT COUNT(*) as tables_registered FROM DATA_GOVERNANCE.TABLE_REGISTRY) a
CROSS JOIN (
    SELECT COUNT(DISTINCT table_id) as tables_with_quality_issues
    FROM DATA_GOVERNANCE.QUALITY_METRICS
    WHERE passed = FALSE
) b
LEFT JOIN DATA_GOVERNANCE.COMPLIANCE_ISSUES c ON TRUE
GROUP BY a.tables_registered, b.tables_with_quality_issues;
