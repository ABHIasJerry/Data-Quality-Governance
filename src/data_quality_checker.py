"""
Data Quality Checker
Performs comprehensive data quality assessments on tables
"""

from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
from enum import Enum
from snowflake_connector import SnowflakeConnector

logger = logging.getLogger(__name__)


class CheckSeverity(Enum):
    """Severity levels for quality checks"""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DataQualityChecker:
    """Performs data quality checks on tables"""
    
    def __init__(self, connector: SnowflakeConnector):
        self.connector = connector
        self.checks_performed = []
    
    def run_quality_checks(self, database: str, schema: str, 
                          table_name: str, config: Dict) -> List[Dict[str, Any]]:
        """
        Run all configured quality checks on a table
        
        Args:
            database: Database name
            schema: Schema name
            table_name: Table name
            config: Configuration for quality checks
            
        Returns:
            List of quality check results
        """
        results = []
        
        # Check for duplicate records
        if config.get('check_duplicates', True):
            results.append(self._check_duplicates(database, schema, table_name))
        
        # Check for null values in key columns
        if config.get('check_nulls', True):
            results.append(self._check_null_values(database, schema, table_name, config))
        
        # Check for data type consistency
        if config.get('check_data_types', True):
            results.append(self._check_data_type_consistency(database, schema, table_name, config))
        
        # Check for referential integrity
        if config.get('check_referential_integrity', True):
            results.extend(self._check_referential_integrity(database, schema, table_name, config))
        
        # Check for outliers/anomalies
        if config.get('check_outliers', True):
            results.extend(self._check_numeric_outliers(database, schema, table_name, config))
        
        # Check for freshness (last update time)
        if config.get('check_freshness', True):
            results.append(self._check_data_freshness(database, schema, table_name, config))
        
        # Check for patterns/regex validation
        if config.get('check_patterns', True):
            results.extend(self._check_patterns(database, schema, table_name, config))
        
        return results
    
    def _check_duplicates(self, database: str, schema: str, table_name: str) -> Dict:
        """Check for duplicate records"""
        query = f"""
        WITH row_numbers AS (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY * ORDER BY 1) as rn
            FROM {database}.{schema}.{table_name}
        )
        SELECT COUNT(*) as duplicate_count
        FROM row_numbers
        WHERE rn > 1
        """
        
        try:
            results = self.connector.execute_query(query)
            duplicate_count = results[0]['DUPLICATE_COUNT'] if results else 0
            
            passed = duplicate_count == 0
            severity = CheckSeverity.ERROR if duplicate_count > 0 else CheckSeverity.INFO
            
            return {
                'check_type': 'DUPLICATE_RECORDS',
                'table_name': table_name,
                'passed': passed,
                'severity': severity.value,
                'details': f"Found {duplicate_count} duplicate records",
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Duplicate check failed for {table_name}: {str(e)}")
            return self._create_check_failure('DUPLICATE_RECORDS', table_name, str(e))
    
    def _check_null_values(self, database: str, schema: str, 
                          table_name: str, config: Dict) -> Dict:
        """Check for unexpected null values"""
        nullable_config = config.get('nullable_columns', [])
        non_nullable = config.get('non_nullable_columns', [])
        
        issues = []
        
        # Check columns that shouldn't be null
        for col in non_nullable:
            query = f"""
            SELECT COUNT(*) as null_count
            FROM {database}.{schema}.{table_name}
            WHERE {col} IS NULL
            """
            try:
                results = self.connector.execute_query(query)
                null_count = results[0]['NULL_COUNT'] if results else 0
                if null_count > 0:
                    issues.append(f"Column '{col}' has {null_count} null values")
            except Exception as e:
                logger.warning(f"Could not check nulls for {col}: {str(e)}")
        
        passed = len(issues) == 0
        severity = CheckSeverity.ERROR if issues else CheckSeverity.INFO
        
        return {
            'check_type': 'NULL_VALUES',
            'table_name': table_name,
            'passed': passed,
            'severity': severity.value,
            'details': "; ".join(issues) if issues else "No unexpected null values found",
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def _check_data_type_consistency(self, database: str, schema: str, 
                                    table_name: str, config: Dict) -> Dict:
        """Check for data type consistency"""
        type_rules = config.get('data_type_rules', {})
        issues = []
        
        for col_name, expected_type in type_rules.items():
            query = f"""
            SELECT DATA_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = '{schema}' 
              AND TABLE_NAME = '{table_name}'
              AND COLUMN_NAME = '{col_name}'
            """
            try:
                results = self.connector.execute_query(query)
                if results:
                    actual_type = results[0]['DATA_TYPE']
                    if actual_type != expected_type:
                        issues.append(f"Column '{col_name}': expected {expected_type}, got {actual_type}")
            except Exception as e:
                logger.warning(f"Could not check type for {col_name}: {str(e)}")
        
        passed = len(issues) == 0
        severity = CheckSeverity.WARNING if issues else CheckSeverity.INFO
        
        return {
            'check_type': 'DATA_TYPE_CONSISTENCY',
            'table_name': table_name,
            'passed': passed,
            'severity': severity.value,
            'details': "; ".join(issues) if issues else "All data types are consistent",
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def _check_referential_integrity(self, database: str, schema: str, 
                                     table_name: str, config: Dict) -> List[Dict]:
        """Check for referential integrity violations"""
        results = []
        fk_rules = config.get('foreign_keys', {})
        
        for fk_col, (ref_table, ref_col) in fk_rules.items():
            query = f"""
            SELECT COUNT(*) as orphan_count
            FROM {database}.{schema}.{table_name} t1
            WHERE t1.{fk_col} IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM {database}.{schema}.{ref_table} t2
                  WHERE t2.{ref_col} = t1.{fk_col}
              )
            """
            try:
                check_results = self.connector.execute_query(query)
                orphan_count = check_results[0]['ORPHAN_COUNT'] if check_results else 0
                
                passed = orphan_count == 0
                severity = CheckSeverity.ERROR if orphan_count > 0 else CheckSeverity.INFO
                
                results.append({
                    'check_type': 'REFERENTIAL_INTEGRITY',
                    'table_name': table_name,
                    'column': fk_col,
                    'passed': passed,
                    'severity': severity.value,
                    'details': f"Found {orphan_count} orphaned records in {fk_col}",
                    'timestamp': datetime.utcnow().isoformat()
                })
            except Exception as e:
                logger.warning(f"Referential integrity check failed for {fk_col}: {str(e)}")
        
        return results
    
    def _check_numeric_outliers(self, database: str, schema: str, 
                               table_name: str, config: Dict) -> List[Dict]:
        """Check for numeric outliers using IQR method"""
        results = []
        numeric_cols = config.get('numeric_columns', [])
        outlier_threshold = config.get('outlier_std_devs', 3)
        
        for col in numeric_cols:
            query = f"""
            WITH stats AS (
                SELECT 
                    AVG({col}) as mean_val,
                    STDDEV({col}) as std_dev,
                    COUNT(*) as total_rows
                FROM {database}.{schema}.{table_name}
                WHERE {col} IS NOT NULL
            )
            SELECT 
                (SELECT COUNT(*) FROM {database}.{schema}.{table_name} 
                 WHERE {col} IS NOT NULL AND (
                    {col} > (SELECT mean_val + {outlier_threshold} * std_dev FROM stats) OR
                    {col} < (SELECT mean_val - {outlier_threshold} * std_dev FROM stats)
                 )) as outlier_count,
                (SELECT total_rows FROM stats) as total_rows
            """
            try:
                check_results = self.connector.execute_query(query)
                if check_results:
                    outlier_count = check_results[0]['OUTLIER_COUNT']
                    total = check_results[0]['TOTAL_ROWS']
                    outlier_pct = (outlier_count / total * 100) if total > 0 else 0
                    
                    passed = outlier_pct < 1.0  # Alert if >1% outliers
                    severity = CheckSeverity.WARNING if not passed else CheckSeverity.INFO
                    
                    results.append({
                        'check_type': 'NUMERIC_OUTLIERS',
                        'table_name': table_name,
                        'column': col,
                        'passed': passed,
                        'severity': severity.value,
                        'details': f"Found {outlier_count} outliers ({outlier_pct:.2f}%) in {col}",
                        'timestamp': datetime.utcnow().isoformat()
                    })
            except Exception as e:
                logger.warning(f"Outlier check failed for {col}: {str(e)}")
        
        return results
    
    def _check_data_freshness(self, database: str, schema: str, 
                             table_name: str, config: Dict) -> Dict:
        """Check if data is fresh (recently updated)"""
        timestamp_col = config.get('timestamp_column', 'CREATED_AT')
        max_age_days = config.get('max_data_age_days', 7)
        
        query = f"""
        SELECT 
            MAX({timestamp_col}) as last_update,
            CURRENT_TIMESTAMP() as current_time,
            DATEDIFF(day, MAX({timestamp_col}), CURRENT_TIMESTAMP()) as days_old
        FROM {database}.{schema}.{table_name}
        """
        
        try:
            results = self.connector.execute_query(query)
            if results:
                days_old = results[0]['DAYS_OLD']
                passed = days_old <= max_age_days
                severity = CheckSeverity.WARNING if not passed else CheckSeverity.INFO
                
                return {
                    'check_type': 'DATA_FRESHNESS',
                    'table_name': table_name,
                    'passed': passed,
                    'severity': severity.value,
                    'details': f"Data is {days_old} days old (max allowed: {max_age_days})",
                    'timestamp': datetime.utcnow().isoformat()
                }
        except Exception as e:
            logger.warning(f"Freshness check failed for {table_name}: {str(e)}")
        
        return self._create_check_failure('DATA_FRESHNESS', table_name, 
                                         f"Could not check freshness: {str(e)}")
    
    def _check_patterns(self, database: str, schema: str, 
                       table_name: str, config: Dict) -> List[Dict]:
        """Check data against regex patterns"""
        results = []
        pattern_rules = config.get('pattern_validation', {})
        
        for col_name, pattern in pattern_rules.items():
            query = f"""
            SELECT COUNT(*) as invalid_count
            FROM {database}.{schema}.{table_name}
            WHERE {col_name} IS NOT NULL
              AND NOT REGEXP_LIKE({col_name}, '{pattern}')
            """
            try:
                check_results = self.connector.execute_query(query)
                invalid_count = check_results[0]['INVALID_COUNT'] if check_results else 0
                
                passed = invalid_count == 0
                severity = CheckSeverity.ERROR if invalid_count > 0 else CheckSeverity.INFO
                
                results.append({
                    'check_type': 'PATTERN_VALIDATION',
                    'table_name': table_name,
                    'column': col_name,
                    'passed': passed,
                    'severity': severity.value,
                    'details': f"Found {invalid_count} values not matching pattern in {col_name}",
                    'timestamp': datetime.utcnow().isoformat()
                })
            except Exception as e:
                logger.warning(f"Pattern check failed for {col_name}: {str(e)}")
        
        return results
    
    @staticmethod
    def _create_check_failure(check_type: str, table_name: str, error_msg: str) -> Dict:
        """Create a failure result for a check"""
        return {
            'check_type': check_type,
            'table_name': table_name,
            'passed': False,
            'severity': CheckSeverity.ERROR.value,
            'details': f"Check execution failed: {error_msg}",
            'timestamp': datetime.utcnow().isoformat()
        }
