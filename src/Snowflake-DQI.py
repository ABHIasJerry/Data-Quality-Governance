import os
import snowflake.connector
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# Load credentials
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

def run_dq_framework():
    conn = get_connection(use_sso=True)
    history_file = "dq_history.csv"
    
    # 1. Define Business Rules (Customize these for your specific tables)
    # The dictionary keys are Table Names, values are the SQL logic to find bad data
    dq_rules = {
        "CUSTOMERS": {
            "No Null Emails": "COUNT_IF(email IS NULL)",
            "Duplicate IDs": "COUNT(id) - COUNT(DISTINCT id)"
        },
        "ORDERS": {
            "Future Order Dates": "COUNT_IF(order_date > CURRENT_DATE())",
            "Negative Amounts": "COUNT_IF(amount < 0)"
        }
    }

    results = []
    
    try:
        cursor = conn.cursor()
        print(f"--- Starting Data Quality Run: {datetime.now()} ---")
        
        for table, rules in dq_rules.items():
            for rule_name, logic in rules.items():
                query = f"SELECT {logic} AS violation_count FROM {table}"
                cursor.execute(query)
                count = cursor.fetchone()[0]
                
                status = "PASS" if count == 0 else "FAIL"
                print(f"Table: {table} | Rule: {rule_name} | Status: {status} ({count} issues)")
                
                results.append({
                    "timestamp": datetime.now(),
                    "table": table,
                    "rule": rule_name,
                    "violations": count,
                    "status": status
                })
        
        # 2. Save current run
        df = pd.DataFrame(results)
        df.to_csv(f"dq_report_{datetime.now().strftime('%Y%m%d')}.csv", index=False)
        
        # 3. Append to History (Trend Tracking)
        if os.path.exists(history_file):
            df.to_csv(history_file, mode='a', header=False, index=False)
        else:
            df.to_csv(history_file, index=False)
            
        print(f"\n[✓] Quality audit complete. History updated in {history_file}")

    except Exception as e:
        print(f"[!] Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    run_dq_framework()
#################################################################################################

"""
Features of this Integral Script:
Rule Mapping: The dq_rules dictionary allows you to define different checks for different tables in one place.

Trend Tracking: Every time you run this, it appends the results to dq_history.csv. You can open this file in Excel/Tableau to see if your violation_count is going down over time.

Automated Status: It automatically flags a "PASS" or "FAIL" based on whether the violation_count is 0.

Non-Destructive: It uses only SELECT queries. The only action it performs is saving a local file to your computer; it never alters or touches the data within Snowflake.

How to use this:
Modify dq_rules: Simply add your tables and your specific logic (e.g., "TABLE_NAME": {"Rule Name": "SQL Logic"}).

Scale: If you have 100 tables, you can replace the hardcoded dq_rules dictionary with a function that queries INFORMATION_SCHEMA.TABLES to auto-discover tables and run default checks (like COUNT_IF(col IS NULL)) for every single table automatically.

"""
