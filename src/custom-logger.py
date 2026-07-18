import sys
import datetime
import os

class Logger:
    def __init__(self, log_directory="logs"):
        self.log_directory = log_directory
        if not os.path.exists(self.log_directory):
            os.makedirs(self.log_directory)
            
        # Create filename with timestamp
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.filename = os.path.join(self.log_directory, f"log_{timestamp}.txt")
        self.terminal = sys.stdout
        self.log_file = open(self.filename, "a", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.log_file.write(message)
        self.log_file.flush() # Ensure it writes to file immediately

    def flush(self):
        self.terminal.flush()
        self.log_file.flush()

# --- HOW TO USE IT ---

# 1. Initialize the logger at the very top of your script
sys.stdout = Logger()

# 2. Everything you print now goes to both Terminal and the .txt file
print("Starting the test report generation process...")
print(f"Timestamp: {datetime.datetime.now()}")

# ... your existing code here ...

print("Report generated successfully.")
