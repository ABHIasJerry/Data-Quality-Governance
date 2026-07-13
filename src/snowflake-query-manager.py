# pip install tabulate

import os
import snowflake.connector
from dotenv import load_dotenv
from datetime import datetime
from tabulate import tabulate # For nice formatting

load_dotenv()

def run_custom_query(query, use_sso=True):
    params = {
        "user": os.getenv("SF_USER"),
        "account": os.getenv("SF_ACCOUNT"),
        "warehouse": os.getenv("SF_WAREHOUSE"),
        "database": os.getenv("SF_DATABASE"),
        "role": os.getenv("SF_ROLE"),
    }
    if use_sso: params["authenticator"] = "externalbrowser"
    else: params["password"] = os.getenv("SF_PASSWORD")

    conn = snowflake.connector.connect(**params)
    
    try:
        cursor = conn.cursor()
        print(f"\nExecuting query...")
        cursor.execute(query)

        # Get the unique Snowflake Query ID
        query_id = cursor.sfqid
        print(f"Query ID: {query_id}")
        
        # Fetch results
        results = cursor.fetchall()
        columns = [col[0] for col in cursor.description]
        
        # 1. Nicely formatted output for Terminal
        print(f"\n{'='*20} QUERY RESULTS (ID: {query_id}) {'='*20}")
        print(tabulate(results, headers=columns, tablefmt="grid"))
        
        # 2. Save to output file
        output_filename = f"output_{query_id}.txt"
        with open(output_filename, "w") as f:
            f.write(f"<?> Query ID: {query_id}\n")
            f.write(f"<?> Timestamp: {datetime.now()}\n")
            f.write(f"<Q> Query: {query}\n\n")
            f.write(tabulate(results, headers=columns, tablefmt="simple"))
            
        print(f"\n[✓] Results also saved to: {output_filename}")
        # Print to Terminal and File
        print(f"\n--- RESULTS ---")
        print(header)
        for row in results:
            row_str = " | ".join(str(val) for val in row)
            print(row_str)       

    except Exception as e:
        print(f"\n[!] Error: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    user_query = input("Enter your SQL query: ")
    
    # Simple safety filter
    destructive_keywords = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'UPDATE', 'INSERT', 'CREATE', 'REPLACE', 'GRANT', 'REVOKE']
    if any(keyword in user_query.upper() for keyword in destructive_keywords):
        print("\n[!] BLOCKED: Destructive/Modification command detected. Only SELECT statements are permitted.")
    else:
        run_custom_query(user_query)
