"""
Main Example: Data Governance Framework Usage
Demonstrates how to use the complete governance framework
"""

import json
import sys
from pathlib import Path
import logging

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from governance_orchestrator import GovernanceOrchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config(config_file: str) -> dict:
    """Load configuration from JSON file"""
    with open(config_file, 'r') as f:
        return json.load(f)


def main():
    """Main execution function"""
    
    # Load Snowflake connection configuration
    # NOTE: Update config/snowflake_config.json with your credentials
    try:
        connection_config = load_config('config/snowflake_config.json')
    except FileNotFoundError:
        logger.error("Please create config/snowflake_config.json with Snowflake credentials")
        logger.info("Template available at config/snowflake_config.template.json")
        sys.exit(1)
    
    # Initialize orchestrator
    orchestrator = GovernanceOrchestrator(connection_config)
    
    try:
        # Connect to Snowflake
        logger.info("Connecting to Snowflake...")
        orchestrator.connect()
        
        # Initialize governance framework
        database = connection_config.get('database', 'ANALYTICS')
        schema = connection_config.get('schema', 'PUBLIC')
        
        logger.info("Initializing governance framework...")
        orchestrator.initialize_governance_framework(database)
        
        # Option 1: Process all tables with configuration
        logger.info("Starting comprehensive table processing...")
        report = orchestrator.process_all_tables(
            database=database,
            schema=schema,
            config_file='config/governance_config.yaml'
        )
        
        # Generate and export reports
        logger.info("Generating reports...")
        
        # Export to JSON
        orchestrator.export_report_to_json('output/governance_report.json')
        
        # Export to HTML
        orchestrator.export_report_to_html('output/governance_report.html')
        
        # Print summary
        logger.info("=" * 80)
        logger.info("EXECUTION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Tables Scanned: {report['tables_scanned']}")
        logger.info(f"Quality Checks Run: {report['quality_checks_run']}")
        logger.info(f"Quality Issues Found: {report['quality_issues_found']}")
        logger.info(f"Governance Issues Found: {report['governance_issues_found']}")
        logger.info("=" * 80)
        
        # Option 2: Process individual tables (example)
        logger.info("\nProcessing specific tables with detailed analysis...")
        
        sample_table = "CUSTOMERS"
        metadata = orchestrator.scan_table_metadata(database, schema, sample_table)
        logger.info(f"\nMetadata for {sample_table}:")
        logger.info(f"  Columns: {len(metadata.get('columns', []))}")
        logger.info(f"  Row Count: {metadata.get('row_count', 0)}")
        logger.info(f"  Size (MB): {metadata.get('table_size_mb', 0)}")
        
        # Option 3: Record data lineage (example)
        logger.info("\nRecording sample data lineage...")
        orchestrator.record_data_lineage(
            database=database,
            source_table=f"{database}.{schema}.ORDERS",
            target_table=f"{database}.{schema}.FACT_SALES",
            transformation_logic="Aggregated order data with customer and product dimensions",
            run_status="SUCCESS"
        )
        
        # Generate governance report
        governance_report = orchestrator.generate_governance_report(database)
        logger.info("\nGovernance Report Summary:")
        logger.info(json.dumps(governance_report, indent=2, default=str))
        
        logger.info("\nGovernance framework execution completed successfully!")
        logger.info("Check output/ directory for detailed reports")
        
    except Exception as e:
        logger.error(f"Error during execution: {str(e)}", exc_info=True)
        sys.exit(1)
    
    finally:
        # Disconnect from Snowflake
        logger.info("Disconnecting from Snowflake...")
        orchestrator.disconnect()


if __name__ == "__main__":
    main()
