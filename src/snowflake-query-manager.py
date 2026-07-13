import os
import snowflake.connector
from dotenv import load_dotenv
from datetime import datetime

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
        print(f"Executing query...")
        cursor.execute(query)
        
        # Get the unique Snowflake Query ID
        query_id = cursor.sfqid
        print(f"Query ID: {query_id}")
        
        # Fetch results
        results = cursor.fetchall()
        columns = [col[0] for col in cursor.description]
        
        # Prepare Output
        output_filename = f"output_{query_id}.txt"
        with open(output_filename, "w") as f:
            # Write Header
            header = " | ".join(columns)
            f.write(f"Query ID: {query_id}\nTimestamp: {datetime.now()}\n\n{header}\n" + "-"*30 + "\n")
            
            # Print to Terminal and File
            print(f"\n--- RESULTS ---")
            print(header)
            for row in results:
                row_str = " | ".join(str(val) for val in row)
                print(row_str)
                f.write(row_str + "\n")
        
        print(f"\nResult saved to: {output_filename}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    # Supply your query here
    user_query = input("Enter your SQL query: ")
    
    # Safety Check: Basic prevention of destructive keywords
    destructive_keywords = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'UPDATE', 'INSERT', 'CREATE', 'REPLACE']
    if any(keyword in user_query.upper() for keyword in destructive_keywords):
        print("BLOCKED: Destructive command detected. Only SELECT statements are allowed.")
    else:
        run_custom_query(user_query)
