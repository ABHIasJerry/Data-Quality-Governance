"""
snowflake_validator.py
======================

A single-file toolkit to:
  1. Connect to Snowflake using either PASSWORD or SSO (external browser / Okta)
     authentication, with all connection settings loaded from a .env file.
  2. Run a comprehensive set of SQL validation functions against Snowflake
     (syntax checks, row counts, null checks, duplicate checks, referential
     integrity, schema checks, data-type checks, value-range checks, etc.)

--------------------------------------------------------------------------
SETUP
--------------------------------------------------------------------------
1. Install dependencies:
       pip install snowflake-connector-python python-dotenv

2. Create a ".env" file in the same directory as this script:

       # Required
       SNOWFLAKE_ACCOUNT=your_account_identifier      # e.g. xy12345.ap-southeast-1
       SNOWFLAKE_USER=your_username

       # Auth mode: "password" | "externalbrowser" | "https://<okta_url>"
       SNOWFLAKE_AUTHENTICATOR=password

       # Required only when SNOWFLAKE_AUTHENTICATOR=password
       SNOWFLAKE_PASSWORD=your_password

       # Optional
       SNOWFLAKE_ROLE=your_role
       SNOWFLAKE_WAREHOUSE=your_warehouse
       SNOWFLAKE_DATABASE=your_database
       SNOWFLAKE_SCHEMA=your_schema
       SNOWFLAKE_LOGIN_TIMEOUT=60

   For SSO login (browser-based), set:
       SNOWFLAKE_AUTHENTICATOR=externalbrowser
   For Okta native SSO, set:
       SNOWFLAKE_AUTHENTICATOR=https://<your_okta_domain>.okta.com

3. Run:
       python snowflake_validator.py
--------------------------------------------------------------------------
"""

import os
import logging
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple, Union

from dotenv import load_dotenv
import snowflake.connector
from snowflake.connector import DictCursor
from snowflake.connector.errors import (
    DatabaseError,
    OperationalError,
    ProgrammingError,
)

# --------------------------------------------------------------------------
# Setup
# --------------------------------------------------------------------------
load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("snowflake_validator")


# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------
class SnowflakeConfig:
    """Loads and validates Snowflake connection settings from environment variables."""

    def __init__(self):
        self.account: Optional[str] = os.getenv("SNOWFLAKE_ACCOUNT")
        self.user: Optional[str] = os.getenv("SNOWFLAKE_USER")
        self.password: Optional[str] = os.getenv("SNOWFLAKE_PASSWORD")
        self.authenticator: str = os.getenv("SNOWFLAKE_AUTHENTICATOR", "password").strip()
        self.role: Optional[str] = os.getenv("SNOWFLAKE_ROLE")
        self.warehouse: Optional[str] = os.getenv("SNOWFLAKE_WAREHOUSE")
        self.database: Optional[str] = os.getenv("SNOWFLAKE_DATABASE")
        self.schema: Optional[str] = os.getenv("SNOWFLAKE_SCHEMA")
        self.login_timeout: int = int(os.getenv("SNOWFLAKE_LOGIN_TIMEOUT", "60"))
        self._validate()

    def _validate(self) -> None:
        missing = []
        if not self.account:
            missing.append("SNOWFLAKE_ACCOUNT")
        if not self.user:
            missing.append("SNOWFLAKE_USER")

        auth = self.authenticator.lower()
        is_password_auth = auth in ("password", "snowflake", "")
        if is_password_auth and not self.password:
            missing.append("SNOWFLAKE_PASSWORD (required when SNOWFLAKE_AUTHENTICATOR=password)")

        if missing:
            raise EnvironmentError(
                "Missing required environment variable(s): " + ", ".join(missing)
            )

    def is_sso(self) -> bool:
        auth = self.authenticator.lower()
        return auth == "externalbrowser" or auth.startswith("http")


# --------------------------------------------------------------------------
# Connection Manager
# --------------------------------------------------------------------------
class SnowflakeConnectionManager:
    """Handles connecting to / disconnecting from Snowflake with either
    password or SSO authentication, and hands out cursors."""

    def __init__(self, config: Optional[SnowflakeConfig] = None):
        self.config = config or SnowflakeConfig()
        self.conn: Optional[snowflake.connector.SnowflakeConnection] = None

    def _build_connection_params(self) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "account": self.config.account,
            "user": self.config.user,
            "login_timeout": self.config.login_timeout,
        }

        auth = self.config.authenticator.lower()
        if auth == "externalbrowser":
            params["authenticator"] = "externalbrowser"
            logger.info("Using SSO authentication (external browser)")
        elif auth.startswith("http"):
            params["authenticator"] = self.config.authenticator
            logger.info("Using SSO authentication (Okta/SAML native)")
        else:
            params["password"] = self.config.password
            logger.info("Using username/password authentication")

        if self.config.role:
            params["role"] = self.config.role
        if self.config.warehouse:
            params["warehouse"] = self.config.warehouse
        if self.config.database:
            params["database"] = self.config.database
        if self.config.schema:
            params["schema"] = self.config.schema

        return params

    def connect(self) -> snowflake.connector.SnowflakeConnection:
        if self.conn is not None and not self.conn.is_closed():
            return self.conn

        params = self._build_connection_params()
        try:
            self.conn = snowflake.connector.connect(**params)
            logger.info("Connected to Snowflake successfully.")
        except (DatabaseError, OperationalError) as exc:
            logger.error("Failed to connect to Snowflake: %s", exc)
            raise
        return self.conn

    def close(self) -> None:
        if self.conn is not None and not self.conn.is_closed():
            self.conn.close()
            logger.info("Snowflake connection closed.")

    @contextmanager
    def cursor(self, dict_cursor: bool = False):
        """Context manager yielding a cursor; auto-connects if needed."""
        if self.conn is None or self.conn.is_closed():
            self.connect()
        cur = self.conn.cursor(DictCursor) if dict_cursor else self.conn.cursor()
        try:
            yield cur
        finally:
            cur.close()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# --------------------------------------------------------------------------
# SQL Validator
# --------------------------------------------------------------------------
class SQLValidator:
    """A collection of SQL validation functions that run against Snowflake."""

    def __init__(self, connection_manager: SnowflakeConnectionManager):
        self.cm = connection_manager

    @staticmethod
    def _fq_name(name: str, schema: Optional[str] = None, database: Optional[str] = None) -> str:
        """Builds a fully-qualified object name from optional database/schema."""
        parts = [p for p in (database, schema, name) if p]
        return ".".join(parts)

    # ---------------------- Connectivity -----------------------------
    def test_connection(self) -> bool:
        """Simple connectivity + credential check."""
        try:
            with self.cm.cursor() as cur:
                cur.execute("SELECT CURRENT_VERSION()")
                cur.fetchone()
            logger.info("Connection test passed.")
            return True
        except Exception as exc:
            logger.error("Connection test failed: %s", exc)
            return False

    # ---------------------- Query execution ----------------------------
    def execute_query(self, query: str, params: Optional[Union[tuple, dict]] = None) -> List[tuple]:
        """Executes a query and returns all rows as tuples."""
        with self.cm.cursor() as cur:
            cur.execute(query, params) if params else cur.execute(query)
            return cur.fetchall()

    def execute_query_dict(self, query: str, params: Optional[Union[tuple, dict]] = None) -> List[Dict[str, Any]]:
        """Executes a query and returns all rows as list of dicts."""
        with self.cm.cursor(dict_cursor=True) as cur:
            cur.execute(query, params) if params else cur.execute(query)
            return cur.fetchall()

    def execute_scalar(self, query: str, params: Optional[Union[tuple, dict]] = None) -> Any:
        """Executes a query and returns a single scalar value (first col of first row)."""
        with self.cm.cursor() as cur:
            cur.execute(query, params) if params else cur.execute(query)
            row = cur.fetchone()
            return row[0] if row else None

    # ---------------------- Syntax / plan validation --------------------
    def validate_syntax(self, query: str) -> Tuple[bool, str]:
        """Validates SQL syntax without executing it, via EXPLAIN USING TEXT."""
        try:
            with self.cm.cursor() as cur:
                cur.execute(f"EXPLAIN USING TEXT {query}")
                cur.fetchall()
            return True, "Query syntax is valid."
        except ProgrammingError as exc:
            return False, f"Syntax error: {exc}"

    def get_query_plan(self, query: str) -> List[tuple]:
        """Returns the query execution plan."""
        return self.execute_query(f"EXPLAIN USING TEXT {query}")

    def validate_query_returns_rows(self, query: str) -> bool:
        """Checks whether a query returns at least one row."""
        rows = self.execute_query(query)
        return len(rows) > 0

    # ---------------------- Object existence -----------------------------
    def table_exists(self, table: str, schema: Optional[str] = None, database: Optional[str] = None) -> bool:
        db = database or self.cm.config.database
        sch = schema or self.cm.config.schema
        query = f"""
            SELECT COUNT(*) FROM {db}.INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = %(schema)s AND TABLE_NAME = %(table)s
        """
        count = self.execute_scalar(query, {"schema": sch.upper(), "table": table.upper()})
        return bool(count and count > 0)

    def column_exists(
        self, table: str, column: str, schema: Optional[str] = None, database: Optional[str] = None
    ) -> bool:
        db = database or self.cm.config.database
        sch = schema or self.cm.config.schema
        query = f"""
            SELECT COUNT(*) FROM {db}.INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %(schema)s AND TABLE_NAME = %(table)s AND COLUMN_NAME = %(column)s
        """
        count = self.execute_scalar(
            query, {"schema": sch.upper(), "table": table.upper(), "column": column.upper()}
        )
        return bool(count and count > 0)

    def validate_schema_columns(
        self,
        table: str,
        expected_columns: List[str],
        schema: Optional[str] = None,
        database: Optional[str] = None,
    ) -> Tuple[bool, List[str]]:
        """Validates that all expected columns exist in the table. Returns (passed, missing_columns)."""
        db = database or self.cm.config.database
        sch = schema or self.cm.config.schema
        query = f"""
            SELECT COLUMN_NAME FROM {db}.INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %(schema)s AND TABLE_NAME = %(table)s
        """
        rows = self.execute_query(query, {"schema": sch.upper(), "table": table.upper()})
        actual_columns = {r[0].upper() for r in rows}
        missing = [c for c in expected_columns if c.upper() not in actual_columns]
        return (len(missing) == 0, missing)

    def validate_data_type(
        self,
        table: str,
        column: str,
        expected_type: str,
        schema: Optional[str] = None,
        database: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Validates a column's data type matches the expected type (case-insensitive substring match)."""
        db = database or self.cm.config.database
        sch = schema or self.cm.config.schema
        query = f"""
            SELECT DATA_TYPE FROM {db}.INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %(schema)s AND TABLE_NAME = %(table)s AND COLUMN_NAME = %(column)s
        """
        actual_type = self.execute_scalar(
            query, {"schema": sch.upper(), "table": table.upper(), "column": column.upper()}
        )
        if actual_type is None:
            return False, f"Column {column} not found in {table}."
        passed = expected_type.upper() in actual_type.upper()
        return passed, f"Expected: {expected_type}, Actual: {actual_type}"

    # ---------------------- Row-level data validations --------------------
    def get_row_count(self, table: str, where: Optional[str] = None) -> int:
        clause = f" WHERE {where}" if where else ""
        return self.execute_scalar(f"SELECT COUNT(*) FROM {table}{clause}")

    def validate_row_count(
        self,
        table: str,
        expected_min: Optional[int] = None,
        expected_max: Optional[int] = None,
        where: Optional[str] = None,
    ) -> Tuple[bool, str]:
        count = self.get_row_count(table, where)
        if expected_min is not None and count < expected_min:
            return False, f"Row count {count} is below expected minimum {expected_min}."
        if expected_max is not None and count > expected_max:
            return False, f"Row count {count} is above expected maximum {expected_max}."
        return True, f"Row count {count} is within expected bounds."

    def validate_no_nulls(self, table: str, column: str, where: Optional[str] = None) -> Tuple[bool, int]:
        """Returns (passed, null_count) — passed is True if no NULLs found."""
        base = f"{column} IS NULL"
        clause = f"{base} AND ({where})" if where else base
        null_count = self.execute_scalar(f"SELECT COUNT(*) FROM {table} WHERE {clause}")
        return (null_count == 0, null_count)

    def validate_no_duplicates(self, table: str, columns: List[str]) -> Tuple[bool, int]:
        """Checks for duplicate rows based on given column(s). Returns (passed, duplicate_group_count)."""
        cols = ", ".join(columns)
        query = f"""
            SELECT COUNT(*) FROM (
                SELECT {cols}, COUNT(*) AS cnt
                FROM {table}
                GROUP BY {cols}
                HAVING COUNT(*) > 1
            )
        """
        dup_count = self.execute_scalar(query)
        return (dup_count == 0, dup_count)

    def validate_referential_integrity(
        self, child_table: str, child_column: str, parent_table: str, parent_column: str
    ) -> Tuple[bool, int]:
        """Checks that every non-null child_column value exists in parent_column.
        Returns (passed, orphan_row_count)."""
        query = f"""
            SELECT COUNT(*) FROM {child_table} c
            WHERE c.{child_column} IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM {parent_table} p WHERE p.{parent_column} = c.{child_column}
              )
        """
        orphan_count = self.execute_scalar(query)
        return (orphan_count == 0, orphan_count)

    def validate_value_in_set(
        self, table: str, column: str, allowed_values: List[Any]
    ) -> Tuple[bool, int]:
        """Checks that all values in a column belong to an allowed set. Returns (passed, violation_count)."""
        formatted = ", ".join(
            f"'{v}'" if isinstance(v, str) else str(v) for v in allowed_values
        )
        query = f"SELECT COUNT(*) FROM {table} WHERE {column} NOT IN ({formatted}) AND {column} IS NOT NULL"
        violations = self.execute_scalar(query)
        return (violations == 0, violations)

    def validate_column_range(
        self,
        table: str,
        column: str,
        min_val: Optional[Union[int, float]] = None,
        max_val: Optional[Union[int, float]] = None,
    ) -> Tuple[bool, int]:
        """Checks that all values in a numeric column fall within [min_val, max_val]. Returns (passed, violation_count)."""
        conditions = []
        if min_val is not None:
            conditions.append(f"{column} < {min_val}")
        if max_val is not None:
            conditions.append(f"{column} > {max_val}")
        if not conditions:
            return True, 0
        where_clause = " OR ".join(conditions)
        query = f"SELECT COUNT(*) FROM {table} WHERE ({where_clause}) AND {column} IS NOT NULL"
        violations = self.execute_scalar(query)
        return (violations == 0, violations)

    def compare_row_counts(self, table1: str, table2: str) -> Tuple[bool, int, int]:
        """Compares row counts between two tables. Returns (equal, count1, count2)."""
        count1 = self.get_row_count(table1)
        count2 = self.get_row_count(table2)
        return (count1 == count2, count1, count2)

    # ---------------------- Privileges ----------------------------------
    def validate_privileges(self, role: Optional[str] = None) -> List[tuple]:
        """Returns the grants for the current role (or a specified role)."""
        role_name = role or self.cm.config.role
        if role_name:
            return self.execute_query(f"SHOW GRANTS TO ROLE {role_name}")
        return self.execute_query("SHOW GRANTS")

    # ---------------------- Generic custom validation ---------------------
    def run_custom_validation(self, query: str, expected_result: Any) -> Tuple[bool, Any]:
        """Runs a custom scalar query and compares to an expected result. Returns (passed, actual_result)."""
        actual = self.execute_scalar(query)
        return (actual == expected_result, actual)


# --------------------------------------------------------------------------
# Demo / Example usage
# --------------------------------------------------------------------------
def main():
    """Example usage of the connection manager and validator.
    Adjust table/column names to match your environment before running."""
    conn_manager = SnowflakeConnectionManager()

    with conn_manager:
        validator = SQLValidator(conn_manager)

        # 1. Connectivity check
        print("Connection OK:", validator.test_connection())

        # 2. Syntax validation
        ok, msg = validator.validate_syntax("SELECT 1")
        print("Syntax check:", ok, msg)

        # 3. Example table validations (replace with real table/column names)
        # print(validator.table_exists("MY_TABLE"))
        # print(validator.column_exists("MY_TABLE", "MY_COLUMN"))
        # print(validator.validate_row_count("MY_TABLE", expected_min=1))
        # print(validator.validate_no_nulls("MY_TABLE", "MY_COLUMN"))
        # print(validator.validate_no_duplicates("MY_TABLE", ["ID"]))
        # print(validator.validate_referential_integrity("ORDERS", "CUSTOMER_ID", "CUSTOMERS", "ID"))
        # print(validator.validate_schema_columns("MY_TABLE", ["ID", "NAME", "CREATED_AT"]))
        # print(validator.validate_data_type("MY_TABLE", "ID", "NUMBER"))


if __name__ == "__main__":
    main()
