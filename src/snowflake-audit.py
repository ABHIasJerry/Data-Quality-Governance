# pip install snowflake-connector-python python-dotenv pandas
# SF_USER=your_username
# SF_PASSWORD=your_password
# SF_ACCOUNT=your_account_identifier
# SF_WAREHOUSE=your_warehouse
# SF_DATABASE=your_database
# SF_SCHEMA=your_schema
# SF_ROLE=your_role
# ####################################################################

import os
import snowflake.connector
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime # Add this import at the top

# Load credentials from .env
load_dotenv()

def get_connection(use_sso=False):
    """Establishes a read-only connection to Snowflake."""
    params = {
        "user": os.getenv("SF_USER"),
        "account": os.getenv("SF_ACCOUNT"),
        "warehouse": os.getenv("SF_WAREHOUSE"),
        "database": os.getenv("SF_DATABASE"),
        "role": os.getenv("SF_ROLE"),
    }
    
    if use_sso:
        params["authenticator"] = "externalbrowser"
    else:
        params["password"] = os.getenv("SF_PASSWORD")
        
    return snowflake.connector.connect(**params)

def extract_metadata(output_file="snowflake_metadata.csv", use_sso=True):
    """
    Queries read-only system views to generate table and column metadata.
    Does not perform any operations that could modify or impact user data.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"{output_base_name}_{timestamp}.csv"
    conn = None
    try:
        print("Establishing connection to Snowflake...")
        conn = get_connection(use_sso=use_sso)
        
        # Querying INFORMATION_SCHEMA (Read-only metadata views)
        # Filters out internal schemas and focuses on user-defined base tables
        query = """
        SELECT 
            t.table_catalog AS database_name,
            t.table_schema AS schema_name,
            t.table_name,
            c.column_name,
            c.data_type,
            c.character_maximum_length,
            c.numeric_precision,
            c.is_nullable,
            c.column_default,
            c.comment AS column_comment,
            t.row_count,
            t.bytes,
            t.created AS date_created,
            t.last_altered AS date_modified,
            t.table_type
        FROM INFORMATION_SCHEMA.TABLES t
        JOIN INFORMATION_SCHEMA.COLUMNS c 
          ON t.table_name = c.table_name 
          AND t.table_schema = c.table_schema
        WHERE t.table_schema NOT IN ('INFORMATION_SCHEMA', 'PUBLIC')
          AND t.table_type = 'BASE TABLE'
        ORDER BY t.table_schema, t.table_name, c.ordinal_position;
        """
        
        print("Extracting metadata (Read-only operation)...")
        df = pd.read_sql(query, conn)
        
        if not df.empty:
            df.to_csv(output_file, index=False)
            print(f"Successfully generated snowflake audit report: {output_file}")
            print(f"Total rows retrieved: {len(df)}")
        else:
            print("No metadata found for the current configuration.")
            
    except Exception as e:
        print(f"Error during execution: {e}")
        
    finally:
        if conn:
            conn.close()
            print("Connection closed.")

if __name__ == "__main__":
    # Change use_sso to False if you prefer password-based authentication
    extract_metadata(use_sso=True)
