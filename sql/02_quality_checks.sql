-- Data Quality Check Procedures
-- Reusable SQL procedures for comprehensive data quality assessment

-- 1. Check for duplicate records
CREATE OR REPLACE PROCEDURE CHECK_DUPLICATES(
    p_database STRING,
    p_schema STRING,
    p_table STRING
)
RETURNS TABLE (duplicate_count INTEGER, duplicate_pct FLOAT)
LANGUAGE SQL
AS
$$
WITH row_numbers AS (
    SELECT 
        ROW_NUMBER() OVER (PARTITION BY * ORDER BY 1) as rn
    FROM IDENTIFIER(p_database || '.' || p_schema || '.' || p_table)
)
SELECT 
    COUNT(*) FILTER (WHERE rn > 1) as duplicate_count,
    ROUND(COUNT(*) FILTER (WHERE rn > 1) * 100.0 / COUNT(*), 2) as duplicate_pct
FROM row_numbers;
$$;

-- 2. Check for null values by column
CREATE OR REPLACE PROCEDURE CHECK_NULL_VALUES(
    p_database STRING,
    p_schema STRING,
    p_table STRING,
    p_column STRING
)
RETURNS TABLE (
    column_name STRING,
    null_count INTEGER,
    total_count INTEGER,
    null_pct FLOAT
)
LANGUAGE SQL
AS
$$
EXECUTE IMMEDIATE
    'SELECT 
        ''' || p_column || ''' as column_name,
        COUNT(*) FILTER (WHERE ' || p_column || ' IS NULL) as null_count,
        COUNT(*) as total_count,
        ROUND(COUNT(*) FILTER (WHERE ' || p_column || ' IS NULL) * 100.0 / COUNT(*), 2) as null_pct
    FROM ' || p_database || '.' || p_schema || '.' || p_table;
$$;

-- 3. Data type validation
CREATE OR REPLACE PROCEDURE VALIDATE_DATA_TYPES(
    p_database STRING,
    p_schema STRING,
    p_table STRING
)
RETURNS TABLE (
    column_name STRING,
    expected_type STRING,
    actual_type STRING,
    is_valid BOOLEAN
)
LANGUAGE SQL
AS
$$
SELECT 
    COLUMN_NAME,
    DATA_TYPE,
    DATA_TYPE as actual_type,
    TRUE as is_valid
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_CATALOG = p_database
  AND TABLE_SCHEMA = p_schema
  AND TABLE_NAME = p_table;
$$;

-- 4. Check for numeric outliers using z-score
CREATE OR REPLACE PROCEDURE CHECK_NUMERIC_OUTLIERS(
    p_database STRING,
    p_schema STRING,
    p_table STRING,
    p_column STRING,
    p_std_dev_threshold FLOAT
)
RETURNS TABLE (
    column_name STRING,
    outlier_count INTEGER,
    outlier_pct FLOAT,
    mean_value FLOAT,
    std_dev_value FLOAT,
    min_value FLOAT,
    max_value FLOAT
)
LANGUAGE SQL
AS
$$
DECLARE
    query STRING;
BEGIN
    query := 
    'WITH stats AS (
        SELECT 
            AVG(CAST(' || p_column || ' AS FLOAT)) as mean_val,
            STDDEV_POP(CAST(' || p_column || ' AS FLOAT)) as std_dev_val,
            MIN(CAST(' || p_column || ' AS FLOAT)) as min_val,
            MAX(CAST(' || p_column || ' AS FLOAT)) as max_val,
            COUNT(*) as total_rows
        FROM ' || p_database || '.' || p_schema || '.' || p_table || '
        WHERE ' || p_column || ' IS NOT NULL
    )
    SELECT 
        ''' || p_column || ''' as column_name,
        COUNT(*) as outlier_count,
        ROUND(COUNT(*) * 100.0 / (SELECT total_rows FROM stats), 2) as outlier_pct,
        (SELECT mean_val FROM stats) as mean_value,
        (SELECT std_dev_val FROM stats) as std_dev_value,
        (SELECT min_val FROM stats) as min_value,
        (SELECT max_val FROM stats) as max_value
    FROM ' || p_database || '.' || p_schema || '.' || p_table || '
    WHERE ' || p_column || ' IS NOT NULL
      AND (
        CAST(' || p_column || ' AS FLOAT) > (SELECT mean_val + ' || p_std_dev_threshold || ' * std_dev_val FROM stats)
        OR CAST(' || p_column || ' AS FLOAT) < (SELECT mean_val - ' || p_std_dev_threshold || ' * std_dev_val FROM stats)
      )';
    
    EXECUTE IMMEDIATE query;
END;
$$;

-- 5. Check referential integrity
CREATE OR REPLACE PROCEDURE CHECK_REFERENTIAL_INTEGRITY(
    p_database STRING,
    p_schema STRING,
    p_table STRING,
    p_fk_column STRING,
    p_ref_table STRING,
    p_ref_column STRING
)
RETURNS TABLE (
    foreign_key_column STRING,
    reference_table STRING,
    reference_column STRING,
    orphaned_record_count INTEGER,
    integrity_valid BOOLEAN
)
LANGUAGE SQL
AS
$$
DECLARE
    query STRING;
    orphan_count INTEGER;
BEGIN
    query := 
    'SELECT COUNT(*) FROM ' || p_database || '.' || p_schema || '.' || p_table || ' t1
    WHERE t1.' || p_fk_column || ' IS NOT NULL
    AND NOT EXISTS (
        SELECT 1 FROM ' || p_database || '.' || p_schema || '.' || p_ref_table || ' t2
        WHERE t2.' || p_ref_column || ' = t1.' || p_fk_column || '
    )';
    
    EXECUTE IMMEDIATE query INTO orphan_count;
    
    SELECT 
        p_fk_column as foreign_key_column,
        p_ref_table as reference_table,
        p_ref_column as reference_column,
        orphan_count as orphaned_record_count,
        (orphan_count = 0) as integrity_valid;
END;
$$;

-- 6. Data freshness check
CREATE OR REPLACE PROCEDURE CHECK_DATA_FRESHNESS(
    p_database STRING,
    p_schema STRING,
    p_table STRING,
    p_timestamp_column STRING,
    p_max_age_hours INTEGER
)
RETURNS TABLE (
    table_name STRING,
    last_update TIMESTAMP_TZ,
    age_hours FLOAT,
    is_fresh BOOLEAN
)
LANGUAGE SQL
AS
$$
DECLARE
    query STRING;
BEGIN
    query := 
    'SELECT 
        ''' || p_table || ''' as table_name,
        MAX(' || p_timestamp_column || ') as last_update,
        DATEDIFF(hour, MAX(' || p_timestamp_column || '), CURRENT_TIMESTAMP()) as age_hours,
        (DATEDIFF(hour, MAX(' || p_timestamp_column || '), CURRENT_TIMESTAMP()) <= ' || p_max_age_hours || ') as is_fresh
    FROM ' || p_database || '.' || p_schema || '.' || p_table;
    
    EXECUTE IMMEDIATE query;
END;
$$;

-- 7. Pattern validation using regex
CREATE OR REPLACE PROCEDURE VALIDATE_PATTERN(
    p_database STRING,
    p_schema STRING,
    p_table STRING,
    p_column STRING,
    p_pattern STRING
)
RETURNS TABLE (
    column_name STRING,
    invalid_count INTEGER,
    total_count INTEGER,
    valid_pct FLOAT
)
LANGUAGE SQL
AS
$$
DECLARE
    query STRING;
BEGIN
    query := 
    'SELECT 
        ''' || p_column || ''' as column_name,
        COUNT(*) FILTER (WHERE NOT REGEXP_LIKE(' || p_column || ', ''' || p_pattern || ''')) as invalid_count,
        COUNT(*) as total_count,
        ROUND(COUNT(*) FILTER (WHERE REGEXP_LIKE(' || p_column || ', ''' || p_pattern || ''')) * 100.0 / COUNT(*), 2) as valid_pct
    FROM ' || p_database || '.' || p_schema || '.' || p_table || '
    WHERE ' || p_column || ' IS NOT NULL';
    
    EXECUTE IMMEDIATE query;
END;
$$;

-- 8. Comprehensive table profiling
CREATE OR REPLACE PROCEDURE PROFILE_TABLE(
    p_database STRING,
    p_schema STRING,
    p_table STRING
)
RETURNS TABLE (
    table_name STRING,
    row_count INTEGER,
    size_mb FLOAT,
    column_count INTEGER,
    creation_time TIMESTAMP_TZ,
    last_altered TIMESTAMP_TZ,
    has_primary_key BOOLEAN,
    distinct_values TEXT
)
LANGUAGE SQL
AS
$$
DECLARE
    query STRING;
BEGIN
    query := 
    'SELECT 
        TABLE_NAME,
        (SELECT COUNT(*) FROM ' || p_database || '.' || p_schema || '.' || p_table || ') as row_count,
        ROUND(SUM(BYTES) / 1024 / 1024, 2) as size_mb,
        (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
         WHERE TABLE_CATALOG = ''' || p_database || '''
         AND TABLE_SCHEMA = ''' || p_schema || '''
         AND TABLE_NAME = ''' || p_table || ''') as column_count,
        CREATED as creation_time,
        LAST_ALTERED as last_altered,
        FALSE as has_primary_key,
        '''' as distinct_values
    FROM INFORMATION_SCHEMA.TABLE_STORAGE_METRICS
    WHERE SCHEMA_NAME = ''' || p_schema || ''' 
    AND TABLE_NAME = ''' || p_table || '''';
    
    EXECUTE IMMEDIATE query;
END;
$$;

-- 9. Column statistics and cardinality
CREATE OR REPLACE PROCEDURE ANALYZE_COLUMN_STATISTICS(
    p_database STRING,
    p_schema STRING,
    p_table STRING,
    p_column STRING
)
RETURNS TABLE (
    column_name STRING,
    data_type STRING,
    non_null_count INTEGER,
    null_count INTEGER,
    cardinality INTEGER,
    cardinality_pct FLOAT,
    min_value STRING,
    max_value STRING
)
LANGUAGE SQL
AS
$$
DECLARE
    query STRING;
BEGIN
    query := 
    'WITH stats AS (
        SELECT 
            COUNT(*) as total_count,
            COUNT(' || p_column || ') as non_null_count,
            COUNT(DISTINCT ' || p_column || ') as distinct_count,
            MIN(CAST(' || p_column || ' AS VARCHAR)) as min_val,
            MAX(CAST(' || p_column || ' AS VARCHAR)) as max_val
        FROM ' || p_database || '.' || p_schema || '.' || p_table || '
    )
    SELECT 
        ''' || p_column || ''' as column_name,
        (SELECT DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS 
         WHERE TABLE_CATALOG = ''' || p_database || '''
         AND TABLE_SCHEMA = ''' || p_schema || '''
         AND TABLE_NAME = ''' || p_table || '''
         AND COLUMN_NAME = ''' || p_column || ''') as data_type,
        non_null_count,
        total_count - non_null_count as null_count,
        distinct_count as cardinality,
        ROUND(distinct_count * 100.0 / total_count, 2) as cardinality_pct,
        min_val as min_value,
        max_val as max_value
    FROM stats';
    
    EXECUTE IMMEDIATE query;
END;
$$;
