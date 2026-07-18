import csv
import datetime
import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import base64
from io import BytesIO

# --- 1. SMART LOGGER: Redirects prints to file & terminal ---
class Logger:
    def __init__(self, log_dir="logs"):
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_file = open(os.path.join(log_dir, f"execution_log_{timestamp}.txt"), "a")
        self.terminal = sys.stdout
        sys.stdout = self
        sys.stderr = self

    def write(self, message):
        self.terminal.write(message)
        self.log_file.write(message)
        self.log_file.flush()

    def flush(self): pass

# --- 2. TEST REPORTER: Manages CSV state ---
class TestManager:
    def __init__(self, csv_file="test_results.csv"):
        self.csv_file = csv_file
        self.fields = ['TestID', 'Testcase name', 'Test description', 'Tested by', 'test date', 'run count', 'test status', 'comments']
        # Initialize CSV with headers
        with open(self.csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.fields)
            writer.writeheader()

    def update_result(self, test_data):
        """Saves individual test result to CSV immediately."""
        with open(self.csv_file, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.fields)
            writer.writerow(test_data)
        print(f"Result Saved: {test_data['Testcase name']} -> {test_data['test status']}")

# --- 3. HTML GENERATOR: Final summary ---
def finalize_html_report(csv_file):
    df = pd.read_csv(csv_file)
    status_counts = df['test status'].value_counts()
    
    # Pie Chart
    plt.figure(figsize=(5, 5))
    plt.pie(status_counts, labels=status_counts.index, autopct='%1.1f%%', colors=['#28a745', '#dc3545', '#ffc107'])
    buffer = BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')
    chart_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close()

    # Generate HTML
    html = f"""
    <!DOCTYPE html>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <body class="bg-light p-5">
        <div class="container bg-white p-4 shadow rounded">
            <h1>Test Run Final Report</h1>
            <img src="data:image/png;base64,{chart_base64}" class="img-fluid mb-4">
            {df.to_html(classes='table table-striped', index=False)}
        </div>
    </body>
    """
    with open("final_report.html", "w") as f: f.write(html)
    print("\n--- Final HTML Report Generated: final_report.html ---")

# --- EXECUTION FLOW ---
Logger() # Start logging
tm = TestManager()

# Simulate 10 test cases
for i in range(1, 11):
    print(f"\n--- Running Test {i} ---")
    # ... your test automation logic here ...
    result = {
        'TestID': f'T{i:03}', 
        'Testcase name': f'Sample Test {i}', 
        'Test description': 'Validation step', 
        'Tested by': 'Automation', 
        'test date': datetime.date.today(), 
        'run count': 1, 
        'test status': 'Pass' if i % 3 != 0 else 'Fail', 
        'comments': 'Success' if i % 3 != 0 else 'Validation Error'
    }
    tm.update_result(result)

# Finalize
finalize_html_report("test_results.csv")
