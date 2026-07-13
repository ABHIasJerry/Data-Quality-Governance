##########################################################################
"""
{
    "ORDERS": {
        "Negative Order Amounts": "amount < 0",
        "Future Order Dates": "order_date > CURRENT_DATE()",
        "Incomplete Shipping Address": "shipping_address IS NULL OR zip_code IS NULL",
        "Orphaned Orders": "customer_id NOT IN (SELECT id FROM CUSTOMERS)"
    }
    "CUSTOMERS": {
        "Invalid Email Format": "email NOT LIKE '%@%.%'",
        "Short Phone Number": "LEN(phone) < 10"
    }
}

"""
# Save the business rules in a dq_rules.json file and use it efficiently.

"""
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USER=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
ALERT_RECIPIENT=recipient@example.com
"""
# save the email alert config in a .env
#######################################################################

import os
import json
import smtplib
import snowflake.connector
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from email.message import EmailMessage

load_dotenv()

# --- CONFIGURATION ---
def get_connection():
    return snowflake.connector.connect(
        user=os.getenv("SF_USER"),
        account=os.getenv("SF_ACCOUNT"),
        warehouse=os.getenv("SF_WAREHOUSE"),
        database=os.getenv("SF_DATABASE"),
        role=os.getenv("SF_ROLE"),
        authenticator="externalbrowser"
    )

def load_rules(file_path="dq_rules.json"):
    try:
        with open(file_path, "r") as f: return json.load(f)
    except: return {}

def send_alert(report_file, failure_count):
    msg = EmailMessage()
    msg.set_content(f"Data Quality Audit completed. Found {failure_count} failures. See attached.")
    msg['Subject'] = 'ALERT: Snowflake Data Quality Issues'
    msg['From'] = os.getenv("EMAIL_USER")
    msg['To'] = os.getenv("ALERT_RECIPIENT")

    with open(report_file, 'rb') as f:
        msg.add_attachment(f.read(), maintype='application', subtype='csv', filename=report_file)

    with smtplib.SMTP(os.getenv("SMTP_SERVER"), int(os.getenv("SMTP_PORT"))) as s:
        s.starttls()
        s.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASSWORD"))
        s.send_message(msg)

# --- MAIN LOGIC ---
def run_integrated_audit():
    rules = load_rules()
    conn = get_connection()
    cursor = conn.cursor()
    results = []
    
    # 1. Discover all tables
    meta_df = pd.read_sql("SELECT table_name FROM INFORMATION_SCHEMA.TABLES WHERE table_type = 'BASE TABLE'", conn)
    
    for table in meta_df['TABLE_NAME'].unique():
        # A. Custom JSON Rules
        if table in rules:
            for rule_name, condition in rules[table].items():
                cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE {condition}")
                count = cursor.fetchone()[0]
                results.append({"table": table, "rule": rule_name, "violations": count, "status": "FAIL" if count > 0 else "PASS"})

        # B. Auto Null Checks
        cols = pd.read_sql(f"SELECT column_name FROM INFORMATION_SCHEMA.COLUMNS WHERE table_name = '{table}'", conn)
        for col in cols['COLUMN_NAME']:
            cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE {col} IS NULL")
            count = cursor.fetchone()[0]
            results.append({"table": table, "rule": f"Null Check: {col}", "violations": count, "status": "FAIL" if count > 0 else "PASS"})

    # 2. Save Reports
    df = pd.DataFrame(results)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_name = f"dq_report_{timestamp}.csv"
    df.to_csv(report_name, index=False)
    
    # Update History
    df.insert(0, 'timestamp', datetime.now())
    df.to_csv("dq_history.csv", mode='a', header=not os.path.exists("dq_history.csv"), index=False)

    # 3. Alerting
    if (df['status'] == 'FAIL').any():
        send_alert(report_name, (df['status'] == 'FAIL').sum())
        
    conn.close()
    print(f"[✓] Audit complete. Report: {report_name}")

if __name__ == "__main__":
    run_integrated_audit()
#######################################################################

"""
Why this is the "Pro" way to do it:
Separation of Concerns: Your data engineering team can maintain the dq_rules.json file without needing to know Python.

Safety: The script is still strictly read-only. It reads the file, executes SELECT statements, and writes a local CSV.

Scalability: You can easily expand this to handle dozens of tables and hundreds of rules by just adding lines to the JSON file.

One final piece of advice: If your tables grow very large, you might want to add a LIMIT to your null checks or business rules (e.g., WHERE {condition} LIMIT 100) so the script doesn't spend too much time scanning massive tables if you only care about identifying that there is a problem, rather than counting every single instance.

"""
