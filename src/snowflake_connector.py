"""
Snowflake Connection Manager
Handles all connections and database operations
"""

import snowflake.connector
from snowflake.connector.errors import Error as SnowflakeError
from typing import Dict, List, Any, Optional
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class SnowflakeConnector:
    """Manages Snowflake database connections"""
    
    def __init__(self, config: Dict[str, str]):
        """
        Initialize Snowflake connector
        
        Args:
            config: Dictionary with keys: user, password, account, warehouse, database, schema
        """
        self.config = config
        self.connection = None
        
    def connect(self):
        """Establish connection to Snowflake"""
        try:
            self.connection = snowflake.connector.connect(
                user=self.config['user'],
                password=self.config['password'],
                account=self.config['account'],
                warehouse=self.config.get('warehouse', 'COMPUTE_WH'),
                database=self.config.get('database', 'ANALYTICS'),
                schema=self.config.get('schema', 'PUBLIC')
            )
            logger.info("Connected to Snowflake successfully")
        except SnowflakeError as e:
            logger.error(f"Failed to connect to Snowflake: {str(e)}")
            raise
    
    def disconnect(self):
        """Close Snowflake connection"""
        if self.connection:
            self.connection.close()
            logger.info("Disconnected from Snowflake")
    
    @contextmanager
    def get_cursor(self):
        """Context manager for cursor operations"""
        cursor = self.connection.cursor()
        try:
            yield cursor
        finally:
            cursor.close()
    
    def execute_query(self, query: str, params: Optional[List] = None) -> List[Dict]:
        """
        Execute a query and return results as list of dicts
        
        Args:
            query: SQL query to execute
            params: Optional list of parameters for parameterized queries
            
        Returns:
            List of dictionaries with query results
        """
        try:
            with self.get_cursor() as cursor:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]
                return results
        except SnowflakeError as e:
            logger.error(f"Query execution failed: {str(e)}")
            raise
    
    def execute_update(self, query: str, params: Optional[List] = None) -> int:
        """
        Execute an update query
        
        Args:
            query: SQL query to execute
            params: Optional list of parameters for parameterized queries
            
        Returns:
            Number of rows affected
        """
        try:
            with self.get_cursor() as cursor:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                return cursor.rowcount
        except SnowflakeError as e:
            logger.error(f"Update execution failed: {str(e)}")
            raise
    
    def fetch_table_list(self, database: str, schema: str) -> List[str]:
        """Get list of all tables in schema"""
        query = """
        SELECT TABLE_NAME 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_CATALOG = %s AND TABLE_SCHEMA = %s
        ORDER BY TABLE_NAME
        """
        results = self.execute_query(query, [database, schema])
        return [row['TABLE_NAME'] for row in results]
