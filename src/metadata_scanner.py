"""
Table Metadata Scanner
Profiles tables to collect comprehensive metadata information
"""

from typing import Dict, List, Any
import logging
from datetime import datetime
from snowflake_connector import SnowflakeConnector

logger = logging.getLogger(__name__)


class MetadataScanner:
    """Scans and catalogs table metadata"""
    
    def __init__(self, connector: SnowflakeConnector):
        self.connector = connector
    
    def scan_table_metadata(self, database: str, schema: str, 
                          table_name: str) -> Dict[str, Any]:
        """
        Scan a single table for comprehensive metadata
        
        Args:
            database: Database name
            schema: Schema name
            table_name: Table name
            
        Returns:
            Dictionary with table metadata
        """
        metadata = {
            'database': database,
            'schema': schema,
            'table_name': table_name,
            'scan_timestamp': datetime.utcnow().isoformat(),
        }
        
        # Get column information
        metadata['columns'] = self._get_column_info(database, schema, table_name)
        
        # Get table statistics
        metadata['row_count'] = self._get_row_count(database, schema, table_name)
        metadata['table_size_mb'] = self._get_table_size(database, schema, table_name)
        
        # Get table properties
        metadata['creation_time'] = self._get_creation_time(database, schema, table_name)
        metadata['last_altered'] = self._get_last_altered_time(database, schema, table_name)
        
        # Get primary keys and constraints
        metadata['constraints'] = self._get_constraints(database, schema, table_name)
        
        # Assess data completeness
        metadata['data_completeness'] = self._assess_completeness(
            database, schema, table_name, metadata['columns']
        )
        
        return metadata
    
    def _get_column_info(self, database: str, schema: str, table_name: str) -> List[Dict]:
        """Extract column information"""
        query = f"""
        SELECT 
            COLUMN_NAME,
            ORDINAL_POSITION,
            DATA_TYPE,
            IS_NULLABLE,
            COLUMN_DEFAULT
        FROM {database}.INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = '{schema}' 
          AND TABLE_NAME = '{table_name}'
        ORDER BY ORDINAL_POSITION
        """
        
        try:
            results = self.connector.execute_query(query)
            columns = []
            for row in results:
                columns.append({
                    'name': row['COLUMN_NAME'],
                    'position': row['ORDINAL_POSITION'],
                    'data_type': row['DATA_TYPE'],
                    'nullable': row['IS_NULLABLE'] == 'YES',
                    'default': row['COLUMN_DEFAULT']
                })
            return columns
        except Exception as e:
            logger.error(f"Error getting column info for {table_name}: {str(e)}")
            return []
    
    def _get_row_count(self, database: str, schema: str, table_name: str) -> int:
        """Get approximate row count"""
        query = f"SELECT COUNT(*) as row_count FROM {database}.{schema}.{table_name}"
        try:
            results = self.connector.execute_query(query)
            return results[0]['ROW_COUNT'] if results else 0
        except Exception as e:
            logger.warning(f"Could not count rows for {table_name}: {str(e)}")
            return 0
    
    def _get_table_size(self, database: str, schema: str, table_name: str) -> float:
        """Get table size in MB"""
        query = f"""
        SELECT ROUND(SUM(BYTES) / 1024 / 1024, 2) as size_mb
        FROM {database}.INFORMATION_SCHEMA.TABLE_STORAGE_METRICS
        WHERE SCHEMA_NAME = '{schema}' AND TABLE_NAME = '{table_name}'
        """
        try:
            results = self.connector.execute_query(query)
            return float(results[0]['SIZE_MB']) if results and results[0]['SIZE_MB'] else 0.0
        except Exception as e:
            logger.warning(f"Could not get size for {table_name}: {str(e)}")
            return 0.0
    
    def _get_creation_time(self, database: str, schema: str, table_name: str) -> str:
        """Get table creation time"""
        query = f"""
        SELECT CREATED as creation_time
        FROM {database}.INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = '{schema}' AND TABLE_NAME = '{table_name}'
        """
        try:
            results = self.connector.execute_query(query)
            return results[0]['CREATION_TIME'] if results else None
        except Exception as e:
            logger.warning(f"Could not get creation time for {table_name}: {str(e)}")
            return None
    
    def _get_last_altered_time(self, database: str, schema: str, table_name: str) -> str:
        """Get table last altered time"""
        query = f"""
        SELECT LAST_ALTERED as last_altered
        FROM {database}.INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = '{schema}' AND TABLE_NAME = '{table_name}'
        """
        try:
            results = self.connector.execute_query(query)
            return results[0]['LAST_ALTERED'] if results else None
        except Exception as e:
            logger.warning(f"Could not get last altered time for {table_name}: {str(e)}")
            return None
    
    def _get_constraints(self, database: str, schema: str, table_name: str) -> Dict[str, List]:
        """Get table constraints"""
        try:
            query = f"""
            SELECT 
                CONSTRAINT_TYPE,
                CONSTRAINT_NAME
            FROM {database}.INFORMATION_SCHEMA.TABLE_CONSTRAINTS
            WHERE TABLE_SCHEMA = '{schema}' AND TABLE_NAME = '{table_name}'
            """
            results = self.connector.execute_query(query)
            
            constraints = {'primary_keys': [], 'unique': [], 'foreign_keys': []}
            for row in results:
                if row['CONSTRAINT_TYPE'] == 'PRIMARY KEY':
                    constraints['primary_keys'].append(row['CONSTRAINT_NAME'])
                elif row['CONSTRAINT_TYPE'] == 'UNIQUE':
                    constraints['unique'].append(row['CONSTRAINT_NAME'])
                elif row['CONSTRAINT_TYPE'] == 'FOREIGN KEY':
                    constraints['foreign_keys'].append(row['CONSTRAINT_NAME'])
            return constraints
        except Exception as e:
            logger.warning(f"Could not get constraints for {table_name}: {str(e)}")
            return {}
    
    def _assess_completeness(self, database: str, schema: str, 
                            table_name: str, columns: List[Dict]) -> Dict:
        """Assess data completeness for each column"""
        completeness = {}
        
        for col in columns:
            col_name = col['name']
            query = f"""
            SELECT 
                COUNT(*) as total_rows,
                COUNT({col_name}) as non_null_count
            FROM {database}.{schema}.{table_name}
            """
            try:
                results = self.connector.execute_query(query)
                if results:
                    total = results[0]['TOTAL_ROWS']
                    non_null = results[0]['NON_NULL_COUNT']
                    pct = (non_null / total * 100) if total > 0 else 0
                    completeness[col_name] = {
                        'completeness_pct': round(pct, 2),
                        'null_count': total - non_null
                    }
            except Exception as e:
                logger.warning(f"Could not assess completeness for {col_name}: {str(e)}")
        
        return completeness
    
    def scan_all_tables(self, database: str, schema: str) -> List[Dict[str, Any]]:
        """Scan all tables in a schema"""
        tables = self.connector.fetch_table_list(database, schema)
        metadata_list = []
        
        logger.info(f"Starting scan of {len(tables)} tables in {database}.{schema}")
        
        for i, table in enumerate(tables, 1):
            logger.info(f"Scanning table {i}/{len(tables)}: {table}")
            try:
                metadata = self.scan_table_metadata(database, schema, table)
                metadata_list.append(metadata)
            except Exception as e:
                logger.error(f"Failed to scan table {table}: {str(e)}")
                continue
        
        return metadata_list
