import csv
import datetime
import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import base64
from io import BytesIO

# --- 1. SMART LOGGER CLASS ---
class Logger:
    def __init__(self, log_dir="logs"):
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_file = open(os.path.join(log_dir, f"run_{timestamp}.txt"), "a")
        self.terminal = sys.stdout
        sys.stdout = self
        sys.stderr = self

    def write(self, message):
        self.terminal.write(message)
        self.log_file.write(message)
        self.log_file.flush()

    def flush(self): pass

# Initialize Logger
Logger()

# --- 2. REPORT GENERATOR CLASS ---
class TestReporter:
    def __init__(self, csv_filename="test_results.csv"):
        self.csv_filename = csv_filename
        self.results = []
        self.fields = ['TestID', 'Testcase name', 'Test description', 'Tested by', 'test date', 'run count', 'test status', 'comments']
        
        # Create CSV header if not exists
        if not os.path.exists(self.csv_filename):
            with open(self.csv_filename, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.fields)
                writer.writeheader()

    def add_result(self, data):
        """Append a single test result to the CSV file immediately."""
        self.results.append(data)
        with open(self.csv_filename, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.fields)
            writer.writerow(data)
        print(f"Logged: {data['Testcase name']} - {data['test status']}")

# --- 3. EXECUTION LOGIC ---
reporter = TestReporter()

# Mocking a test run sequence
test_sequence = [
    {'TestID': '001', 'Testcase name': 'Login', 'Test description': 'Verify login', 'Tested by': 'Admin', 'test date': '2026-07-18', 'run count': 1, 'test status': 'Pass', 'comments': 'OK'},
    {'TestID': '002', 'Testcase name': 'Logout', 'Test description': 'Verify logout', 'Tested by': 'Admin', 'test date': '2026-07-18', 'run count': 1, 'test status': 'Fail', 'comments': 'Timeout'}
]

print("--- Starting Test Execution ---")
for test in test_sequence:
    # --- HERE YOU WOULD RUN YOUR ACTUAL TEST CODE ---
    # Example: status = run_my_test(test)
    reporter.add_result(test)

print("--- All tests completed. Generating HTML Dashboard ---")

# --- 4. HTML GENERATION (Same as before) ---
def generate_html_report(csv_file):
    df = pd.read_csv(csv_file)
    # ... [Insert the HTML/Bootstrap generation code here as provided previously] ...
    print("HTML Report successfully exported.")

generate_html_report('test_results.csv')
