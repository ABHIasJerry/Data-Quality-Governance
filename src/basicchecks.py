# pip install snowflake-connector-python pandas

import snowflake.connector
import pandas as pd
import logging
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SnowflakeTableManager:
    def __init__(self):
        # Retrieve credentials from environment variables
        self.conn = snowflake.connector.connect(
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
            database=os.getenv("SNOWFLAKE_DATABASE"),
            schema=os.getenv("SNOWFLAKE_SCHEMA")
        )

    def _execute_query(self, query):
        return pd.read_sql(query, self.conn)

    def table_exists(self, table_name, schema, database):
        query = f"""
        SELECT COUNT(*) FROM {database}.INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_SCHEMA = '{schema.upper()}' AND TABLE_NAME = '{table_name.upper()}'
        """
        return self._execute_query(query).iloc[0, 0] > 0

    def get_column_info(self, table_name, schema, database):
        query = f"""
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE 
        FROM {database}.INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME = '{table_name.upper()}' AND TABLE_SCHEMA = '{schema.upper()}'
        """
        return self._execute_query(query)

    def check_column_mismatches(self, table_name, schema, database, expected_columns):
        actual_columns = self.get_column_info(table_name, schema, database)['COLUMN_NAME'].tolist()
        actual_set = set(actual_columns)
        expected_set = set(expected_columns)
        
        return {
            "missing": list(expected_set - actual_set),
            "extra": list(actual_set - expected_set)
        }

    def get_last_load_date(self, table_name):
        # Assumes a metadata column like 'LOADED_AT' exists
        query = f"SELECT MAX(LOADED_AT) FROM {table_name}"
        return self._execute_query(query).iloc[0, 0]

    def get_null_report(self, table_name, columns):
        """Returns row numbers (index) where nulls exist."""
        cols_str = ", ".join(columns)
        query = f"SELECT * FROM {table_name} WHERE " + " OR ".join([f"{c} IS NULL" for c in columns])
        return self._execute_query(query)

    def _execute_query(self, query):
        try:
            return pd.read_sql(query, self.conn)
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

    def table_exists(self, table_name, schema, database):
        query = f"""
        SELECT COUNT(*) FROM {database}.INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_SCHEMA = '{schema.upper()}' AND TABLE_NAME = '{table_name.upper()}'
        """
        return self._execute_query(query).iloc[0, 0] > 0

    def close(self):
        self.conn.close()

manager = SnowflakeTableManager(config)

if manager.table_exists("MY_TABLE", "PUBLIC", "MY_DB"):
    cols = manager.get_column_info("MY_TABLE", "PUBLIC", "MY_DB")
    print(cols)

manager.close()
