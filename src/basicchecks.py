# pip install snowflake-connector-python pandas

import snowflake.connector
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SnowflakeTableManager:
    def __init__(self, connection_params):
        self.conn = snowflake.connector.connect(**connection_params)

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

# --- Example Usage ---
config = {
    "user": "YOUR_USER",
    "password": "YOUR_PASSWORD",
    "account": "YOUR_ACCOUNT",
    "warehouse": "YOUR_WH",
    "database": "YOUR_DB",
    "schema": "YOUR_SCHEMA"
}

manager = SnowflakeTableManager(config)

if manager.table_exists("MY_TABLE", "PUBLIC", "MY_DB"):
    cols = manager.get_column_info("MY_TABLE", "PUBLIC", "MY_DB")
    print(cols)

manager.close()
