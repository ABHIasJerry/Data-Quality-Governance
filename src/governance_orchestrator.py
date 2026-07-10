"""
Data Governance Orchestrator
Main orchestrator that coordinates all governance activities
"""

import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import yaml
from snowflake_connector import SnowflakeConnector
from metadata_scanner import MetadataScanner
from data_quality_checker import DataQualityChecker
from governance_manager import GovernanceManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GovernanceOrchestrator:
    """
    Main orchestrator for data governance framework
    Coordinates metadata scanning, quality checks, and governance enforcement
    """
    
    def __init__(self, connection_config: Dict[str, str], 
                 governance_config: Optional[Dict[str, Any]] = None):
        """
        Initialize the orchestrator
        
        Args:
            connection_config: Snowflake connection configuration
            governance_config: Governance configuration dictionary
        """
        self.connector = SnowflakeConnector(connection_config)
        self.metadata_scanner = None
        self.quality_checker = None
        self.governance_manager = None
        self.governance_config = governance_config or {}
        self.execution_report = {
            'start_time': None,
            'end_time': None,
            'tables_scanned': 0,
            'quality_checks_run': 0,
            'quality_issues_found': 0,
            'governance_issues_found': 0,
            'detailed_results': []
        }
    
    def connect(self):
        """Establish Snowflake connection"""
        self.connector.connect()
        self.metadata_scanner = MetadataScanner(self.connector)
        self.quality_checker = DataQualityChecker(self.connector)
        self.governance_manager = GovernanceManager(self.connector)
    
    def disconnect(self):
        """Close Snowflake connection"""
        self.connector.disconnect()
    
    def initialize_governance_framework(self, database: str):
        """Initialize governance tracking tables"""
        logger.info("Initializing governance framework...")
        self.governance_manager.create_governance_schema(database)
        logger.info("Governance framework initialized successfully")
    
    def scan_and_register_tables(self, database: str, schema: str, 
                                governance_mappings: Optional[Dict[str, Dict]] = None) -> List[str]:
        """
        Scan tables and register them in governance system
        
        Args:
            database: Database name
            schema: Schema name
            governance_mappings: Mapping of table_name -> governance config
            
        Returns:
            List of registered table IDs
        """
        logger.info(f"Scanning tables in {database}.{schema}...")
        
        tables = self.connector.fetch_table_list(database, schema)
        registered_tables = []
        
        for table_name in tables:
            try:
                # Get governance config for this table
                table_config = governance_mappings.get(table_name, {}) if governance_mappings else {}
                
                # Register table
                table_id = self.governance_manager.register_table(
                    database, schema, table_name, table_config
                )
                registered_tables.append(table_id)
            except Exception as e:
                logger.error(f"Failed to register table {table_name}: {str(e)}")
        
        logger.info(f"Registered {len(registered_tables)} tables")
        return registered_tables
    
    def scan_table_metadata(self, database: str, schema: str, 
                           table_name: str) -> Dict[str, Any]:
        """Scan and return metadata for a specific table"""
        logger.info(f"Scanning metadata for {database}.{schema}.{table_name}")
        metadata = self.metadata_scanner.scan_table_metadata(database, schema, table_name)
        self.execution_report['tables_scanned'] += 1
        return metadata
    
    def run_quality_checks(self, database: str, schema: str, table_name: str,
                          quality_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Run quality checks on a table
        
        Args:
            database: Database name
            schema: Schema name
            table_name: Table name
            quality_config: Quality check configuration
            
        Returns:
            List of quality check results
        """
        logger.info(f"Running quality checks for {database}.{schema}.{table_name}")
        
        results = self.quality_checker.run_quality_checks(
            database, schema, table_name, quality_config
        )
        
        # Log results and track issues
        table_id = f"{database}_{schema}_{table_name}".upper()
        for result in results:
            self.governance_manager.log_quality_check(database, table_id, result)
            self.execution_report['quality_checks_run'] += 1
            
            if not result['passed']:
                self.execution_report['quality_issues_found'] += 1
        
        return results
    
    def record_data_lineage(self, database: str, source_table: str, 
                           target_table: str, transformation_logic: str,
                           run_status: str = "SUCCESS", 
                           error_message: Optional[str] = None):
        """Record data lineage for ETL/transformation processes"""
        logger.info(f"Recording lineage: {source_table} -> {target_table}")
        
        self.governance_manager.record_lineage(
            database, source_table, target_table,
            transformation_logic, run_status, error_message
        )
    
    def process_all_tables(self, database: str, schema: str,
                          config_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Process all tables: scan metadata and run quality checks
        
        Args:
            database: Database name
            schema: Schema name
            config_file: Path to YAML configuration file with table-specific configs
            
        Returns:
            Execution report
        """
        self.execution_report['start_time'] = datetime.utcnow().isoformat()
        
        # Load configuration if provided
        table_configs = {}
        if config_file:
            try:
                with open(config_file, 'r') as f:
                    table_configs = yaml.safe_load(f) or {}
                logger.info(f"Loaded configuration from {config_file}")
            except Exception as e:
                logger.warning(f"Could not load config file: {str(e)}")
        
        # Get all tables
        tables = self.connector.fetch_table_list(database, schema)
        logger.info(f"Processing {len(tables)} tables...")
        
        for i, table_name in enumerate(tables, 1):
            logger.info(f"[{i}/{len(tables)}] Processing {table_name}")
            
            try:
                # Get table-specific config
                table_config = table_configs.get(table_name, {})
                governance_config = table_config.get('governance', {})
                quality_config = table_config.get('quality_checks', {})
                
                # Register table
                self.governance_manager.register_table(
                    database, schema, table_name, governance_config
                )
                
                # Scan metadata
                metadata = self.scan_table_metadata(database, schema, table_name)
                
                # Run quality checks
                check_results = self.run_quality_checks(
                    database, schema, table_name, quality_config
                )
                
                # Store results
                result_entry = {
                    'table_name': table_name,
                    'metadata': metadata,
                    'quality_checks': check_results,
                    'processed_at': datetime.utcnow().isoformat()
                }
                self.execution_report['detailed_results'].append(result_entry)
                
                # Create compliance issues for failed checks
                for check in check_results:
                    if not check['passed'] and check['severity'] in ['ERROR', 'CRITICAL']:
                        table_id = f"{database}_{schema}_{table_name}".upper()
                        self.governance_manager.create_compliance_issue(
                            database, table_id,
                            {
                                'issue_type': check['check_type'],
                                'severity': check['severity'],
                                'description': check['details'],
                                'remediation_action': 'Review and remediate data quality issue',
                                'due_date': '2024-12-31'
                            }
                        )
                        self.execution_report['governance_issues_found'] += 1
                
            except Exception as e:
                logger.error(f"Error processing table {table_name}: {str(e)}")
                self.execution_report['detailed_results'].append({
                    'table_name': table_name,
                    'error': str(e),
                    'processed_at': datetime.utcnow().isoformat()
                })
        
        self.execution_report['end_time'] = datetime.utcnow().isoformat()
        return self.execution_report
    
    def generate_governance_report(self, database: str, limit_days: int = 30) -> Dict[str, Any]:
        """Generate comprehensive governance report"""
        logger.info("Generating governance report...")
        report = self.governance_manager.get_governance_report(database, limit_days)
        report['execution_summary'] = {
            'tables_scanned': self.execution_report['tables_scanned'],
            'quality_checks_run': self.execution_report['quality_checks_run'],
            'quality_issues_found': self.execution_report['quality_issues_found'],
            'governance_issues_found': self.execution_report['governance_issues_found']
        }
        return report
    
    def export_report_to_json(self, filepath: str):
        """Export execution report to JSON file"""
        try:
            with open(filepath, 'w') as f:
                json.dump(self.execution_report, f, indent=2, default=str)
            logger.info(f"Report exported to {filepath}")
        except Exception as e:
            logger.error(f"Failed to export report: {str(e)}")
    
    def export_report_to_html(self, filepath: str):
        """Export execution report to HTML for visualization"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Data Governance Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .summary {{ background-color: #f0f0f0; padding: 15px; border-radius: 5px; }}
                .metric {{ display: inline-block; margin: 10px 20px; }}
                .metric-value {{ font-size: 24px; font-weight: bold; color: #0066cc; }}
                .metric-label {{ color: #666; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                th {{ background-color: #0066cc; color: white; }}
                .error {{ color: #cc0000; }}
                .warning {{ color: #ff9900; }}
                .success {{ color: #00cc00; }}
            </style>
        </head>
        <body>
            <h1>Data Governance Report</h1>
            <div class="summary">
                <h2>Execution Summary</h2>
                <div class="metric">
                    <div class="metric-value">{self.execution_report['tables_scanned']}</div>
                    <div class="metric-label">Tables Scanned</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{self.execution_report['quality_checks_run']}</div>
                    <div class="metric-label">Quality Checks Run</div>
                </div>
                <div class="metric">
                    <div class="metric-value error">{self.execution_report['quality_issues_found']}</div>
                    <div class="metric-label">Quality Issues Found</div>
                </div>
                <div class="metric">
                    <div class="metric-value error">{self.execution_report['governance_issues_found']}</div>
                    <div class="metric-label">Governance Issues</div>
                </div>
            </div>
            
            <h2>Details</h2>
            <table>
                <tr>
                    <th>Table Name</th>
                    <th>Status</th>
                    <th>Processed At</th>
                </tr>
        """
        
        for result in self.execution_report['detailed_results']:
            status = 'Error' if 'error' in result else 'Success'
            status_class = 'error' if status == 'Error' else 'success'
            html_content += f"""
                <tr>
                    <td>{result['table_name']}</td>
                    <td class="{status_class}">{status}</td>
                    <td>{result.get('processed_at', '')}</td>
                </tr>
            """
        
        html_content += """
            </table>
        </body>
        </html>
        """
        
        try:
            with open(filepath, 'w') as f:
                f.write(html_content)
            logger.info(f"HTML report exported to {filepath}")
        except Exception as e:
            logger.error(f"Failed to export HTML report: {str(e)}")
