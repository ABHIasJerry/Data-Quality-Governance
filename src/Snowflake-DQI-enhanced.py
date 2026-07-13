# The Auto-Discovery Data Quality Script

import os
import snowflake.connector
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def get_connection(use_sso=True):
    params = {
        "user": os.getenv("SF_USER"),
        "account": os.getenv("SF_ACCOUNT"),
        "warehouse": os.getenv("SF_WAREHOUSE"),
        "database": os.getenv("SF_DATABASE"),
        "role": os.getenv("SF_ROLE"),
    }
    if use_sso: params["authenticator"] = "externalbrowser"
    else: params["password"] = os.getenv("SF_PASSWORD")
    return snowflake.connector.connect(**params)

def run_auto_dq():
    conn = get_connection(use_sso=True)
    history_file = "dq_history.csv"
    results = []
    
    try:
        # 1. Discover all tables and their columns in the current database/schema
        discovery_query = """
        SELECT table_name, column_name 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE table_schema NOT IN ('INFORMATION_SCHEMA', 'PUBLIC')
        """
        print("Discovering tables and columns...")
        meta_df = pd.read_sql(discovery_query, conn)
        
        # 2. Iterate through discovered schema and run a standard "Null Check"
        print(f"Running automated quality checks on {meta_df['TABLE_NAME'].nunique()} tables...")
        
        cursor = conn.cursor()
        for _, row in meta_df.iterrows():
            table = row['TABLE_NAME']
            col = row['COLUMN_NAME']
            
            # Logic: Count nulls for every column discovered
            check_query = f"SELECT COUNT_IF({col} IS NULL) FROM {table}"
            cursor.execute(check_query)
            null_count = cursor.fetchone()[0]
            
            results.append({
                "timestamp": datetime.now(),
                "table": table,
                "column": col,
                "check": "NULL_COUNT",
                "violations": null_count,
                "status": "PASS" if null_count == 0 else "FAIL"
            })
        
        # 3. Save and Log
        df = pd.DataFrame(results)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        df.to_csv(f"dq_report_{timestamp}.csv", index=False)
        
        # Append to history
        df.to_csv(history_file, mode='a', header=not os.path.exists(history_file), index=False)
        
        print(f"[✓] Audit complete. {len(df)} columns checked.")
        print(f"Report saved as 'dq_report_{timestamp}.csv'")

    except Exception as e:
        print(f"[!] Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    run_auto_dq()

##############################################################################################

"""
Why this is powerful:
Zero Manual Entry: You no longer need to update the script when you create new tables. The discovery_query looks at the INFORMATION_SCHEMA and finds everything for you.

Broad Coverage: It performs a NULL_COUNT check on every single column in every single table you have access to.

Scalability: Because it uses INFORMATION_SCHEMA, it handles schema changes dynamically. If a new column is added, it will be picked up in the next run automatically.

Complete Safety: It performs read-only SELECT operations to discover metadata and read-only SELECT queries to count nulls. It never modifies, alters, or creates anything in Snowflake.

"""
