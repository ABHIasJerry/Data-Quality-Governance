"""
Data Governance Manager
Manages governance policies and compliance tracking
"""

from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
from enum import Enum
import json
from snowflake_connector import SnowflakeConnector

logger = logging.getLogger(__name__)


class GovernanceLevel(Enum):
    """Data governance classification levels"""
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


class GovernanceManager:
    """Manages data governance policies and enforcement"""
    
    def __init__(self, connector: SnowflakeConnector):
        self.connector = connector
    
    def create_governance_schema(self, database: str):
        """Create schema for governance tracking tables"""
        sql_statements = [
            f"""
            CREATE SCHEMA IF NOT EXISTS {database}.DATA_GOVERNANCE;
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {database}.DATA_GOVERNANCE.TABLE_REGISTRY (
                table_id STRING,
                database_name STRING,
                schema_name STRING,
                table_name STRING,
                governance_level STRING,
                owner_team STRING,
                description STRING,
                critical_table BOOLEAN,
                pii_present BOOLEAN,
                last_accessed TIMESTAMP_TZ,
                last_modified TIMESTAMP_TZ,
                created_at TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP(),
                PRIMARY KEY (table_id)
            );
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {database}.DATA_GOVERNANCE.QUALITY_METRICS (
                metric_id STRING,
                table_id STRING,
                check_type STRING,
                passed BOOLEAN,
                severity STRING,
                details STRING,
                check_timestamp TIMESTAMP_TZ,
                created_at TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP(),
                PRIMARY KEY (metric_id)
            );
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {database}.DATA_GOVERNANCE.DATA_LINEAGE (
                lineage_id STRING,
                source_table STRING,
                target_table STRING,
                transformation_logic STRING,
                last_run TIMESTAMP_TZ,
                run_status STRING,
                error_message STRING,
                created_at TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP(),
                PRIMARY KEY (lineage_id)
            );
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {database}.DATA_GOVERNANCE.ACCESS_LOGS (
                access_id STRING,
                table_name STRING,
                user_name STRING,
                access_type STRING,
                access_timestamp TIMESTAMP_TZ,
                rows_accessed INTEGER,
                created_at TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP(),
                PRIMARY KEY (access_id)
            );
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {database}.DATA_GOVERNANCE.COMPLIANCE_ISSUES (
                issue_id STRING,
                table_id STRING,
                issue_type STRING,
                severity STRING,
                description STRING,
                remediation_action STRING,
                status STRING,
                due_date DATE,
                created_at TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP(),
                resolved_at TIMESTAMP_TZ,
                PRIMARY KEY (issue_id)
            );
            """
        ]
        
        for statement in sql_statements:
            try:
                self.connector.execute_update(statement)
                logger.info("Created governance schema object")
            except Exception as e:
                logger.warning(f"Schema object creation statement skipped: {str(e)}")
    
    def register_table(self, database: str, schema: str, table_name: str, 
                      governance_config: Dict[str, Any]) -> str:
        """
        Register a table with governance metadata
        
        Args:
            database: Database name
            schema: Schema name
            table_name: Table name
            governance_config: Configuration dictionary with keys:
                - governance_level: PUBLIC, INTERNAL, CONFIDENTIAL, or RESTRICTED
                - owner_team: Team responsible for the table
                - description: Table description
                - critical_table: Boolean indicating criticality
                - pii_present: Boolean indicating if PII is present
                
        Returns:
            Table ID
        """
        table_id = f"{database}_{schema}_{table_name}".upper()
        
        insert_query = f"""
        INSERT INTO {database}.DATA_GOVERNANCE.TABLE_REGISTRY (
            table_id, database_name, schema_name, table_name,
            governance_level, owner_team, description, 
            critical_table, pii_present
        ) VALUES (
            '{table_id}',
            '{database}',
            '{schema}',
            '{table_name}',
            '{governance_config.get("governance_level", "INTERNAL")}',
            '{governance_config.get("owner_team", "UNKNOWN")}',
            '{governance_config.get("description", "")}',
            {str(governance_config.get("critical_table", False)).upper()},
            {str(governance_config.get("pii_present", False)).upper()}
        )
        """
        
        try:
            self.connector.execute_update(insert_query)
            logger.info(f"Registered table: {table_id}")
            return table_id
        except Exception as e:
            logger.error(f"Failed to register table {table_id}: {str(e)}")
            raise
    
    def log_quality_check(self, database: str, table_id: str, 
                         check_result: Dict[str, Any]) -> str:
        """
        Log a quality check result
        
        Args:
            database: Database name
            table_id: Table ID
            check_result: Quality check result dictionary
            
        Returns:
            Metric ID
        """
        metric_id = f"QM_{table_id}_{datetime.utcnow().timestamp()}".replace('.', '_')
        
        insert_query = f"""
        INSERT INTO {database}.DATA_GOVERNANCE.QUALITY_METRICS (
            metric_id, table_id, check_type, passed, severity, details, check_timestamp
        ) VALUES (
            '{metric_id}',
            '{table_id}',
            '{check_result.get("check_type", "UNKNOWN")}',
            {str(check_result.get("passed", False)).upper()},
            '{check_result.get("severity", "INFO")}',
            '{check_result.get("details", "").replace("'", "''")}',
            CURRENT_TIMESTAMP()
        )
        """
        
        try:
            self.connector.execute_update(insert_query)
            return metric_id
        except Exception as e:
            logger.error(f"Failed to log quality check: {str(e)}")
            raise
    
    def record_lineage(self, database: str, source_table: str, target_table: str,
                      transformation_logic: str, run_status: str = "SUCCESS",
                      error_message: Optional[str] = None) -> str:
        """
        Record data lineage information
        
        Args:
            database: Database name
            source_table: Source table name
            target_table: Target table name
            transformation_logic: Description of transformation
            run_status: SUCCESS or FAILED
            error_message: Optional error message if failed
            
        Returns:
            Lineage ID
        """
        lineage_id = f"LG_{source_table}_{target_table}_{datetime.utcnow().timestamp()}".replace('.', '_')
        
        insert_query = f"""
        INSERT INTO {database}.DATA_GOVERNANCE.DATA_LINEAGE (
            lineage_id, source_table, target_table, transformation_logic,
            last_run, run_status, error_message
        ) VALUES (
            '{lineage_id}',
            '{source_table}',
            '{target_table}',
            '{transformation_logic.replace("'", "''")}',
            CURRENT_TIMESTAMP(),
            '{run_status}',
            '{error_message.replace("'", "''") if error_message else ""}'
        )
        """
        
        try:
            self.connector.execute_update(insert_query)
            logger.info(f"Recorded lineage: {lineage_id}")
            return lineage_id
        except Exception as e:
            logger.error(f"Failed to record lineage: {str(e)}")
            raise
    
    def create_compliance_issue(self, database: str, table_id: str,
                               issue_config: Dict[str, Any]) -> str:
        """
        Create a compliance issue ticket
        
        Args:
            database: Database name
            table_id: Table ID
            issue_config: Dictionary with keys:
                - issue_type: Type of compliance issue
                - severity: INFO, WARNING, ERROR, CRITICAL
                - description: Detailed description
                - remediation_action: Recommended action
                - due_date: Due date for remediation
                
        Returns:
            Issue ID
        """
        issue_id = f"CI_{table_id}_{datetime.utcnow().timestamp()}".replace('.', '_')
        
        insert_query = f"""
        INSERT INTO {database}.DATA_GOVERNANCE.COMPLIANCE_ISSUES (
            issue_id, table_id, issue_type, severity, description,
            remediation_action, status, due_date
        ) VALUES (
            '{issue_id}',
            '{table_id}',
            '{issue_config.get("issue_type", "UNKNOWN")}',
            '{issue_config.get("severity", "WARNING")}',
            '{issue_config.get("description", "").replace("'", "''")}',
            '{issue_config.get("remediation_action", "").replace("'", "''")}',
            'OPEN',
            TO_DATE('{issue_config.get("due_date", "")}', 'YYYY-MM-DD')
        )
        """
        
        try:
            self.connector.execute_update(insert_query)
            logger.info(f"Created compliance issue: {issue_id}")
            return issue_id
        except Exception as e:
            logger.error(f"Failed to create compliance issue: {str(e)}")
            raise
    
    def get_governance_report(self, database: str, 
                             limit_days: int = 30) -> Dict[str, Any]:
        """
        Generate governance compliance report
        
        Args:
            database: Database name
            limit_days: Days to include in report
            
        Returns:
            Governance report dictionary
        """
        report = {
            'generated_at': datetime.utcnow().isoformat(),
            'total_tables': 0,
            'governance_summary': {},
            'quality_issues': {},
            'compliance_open_issues': 0
        }
        
        try:
            # Get table count
            table_count_query = f"""
            SELECT COUNT(*) as total
            FROM {database}.DATA_GOVERNANCE.TABLE_REGISTRY
            """
            results = self.connector.execute_query(table_count_query)
            report['total_tables'] = results[0]['TOTAL'] if results else 0
            
            # Get governance level distribution
            governance_query = f"""
            SELECT governance_level, COUNT(*) as count
            FROM {database}.DATA_GOVERNANCE.TABLE_REGISTRY
            GROUP BY governance_level
            """
            results = self.connector.execute_query(governance_query)
            report['governance_summary'] = {row['GOVERNANCE_LEVEL']: row['COUNT'] for row in results}
            
            # Get quality issues
            quality_query = f"""
            SELECT severity, COUNT(*) as count
            FROM {database}.DATA_GOVERNANCE.QUALITY_METRICS
            WHERE passed = FALSE
              AND check_timestamp > CURRENT_TIMESTAMP() - INTERVAL '{limit_days} days'
            GROUP BY severity
            """
            results = self.connector.execute_query(quality_query)
            report['quality_issues'] = {row['SEVERITY']: row['COUNT'] for row in results}
            
            # Get open compliance issues
            compliance_query = f"""
            SELECT COUNT(*) as total
            FROM {database}.DATA_GOVERNANCE.COMPLIANCE_ISSUES
            WHERE status = 'OPEN'
            """
            results = self.connector.execute_query(compliance_query)
            report['compliance_open_issues'] = results[0]['TOTAL'] if results else 0
            
        except Exception as e:
            logger.error(f"Failed to generate governance report: {str(e)}")
        
        return report
