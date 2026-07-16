import os
import pathlib
import sys
import subprocess
import threading
import time
import sys
from datetime import datetime
from tkinter import *
from tkinter import _setit
from tkinter.messagebox import showinfo
from tkinter.ttk import Progressbar
from py._builtin import execfile

from DMAutomatedTest.DataPersistent import Constants
from DMAutomatedTest.DataPersistent.Data_Helper import DataHelper


class LoggerMain(object):
    """
        Log msg to tkinter ui, log file and
    """

    def __init__(self, tkinter_text, log_file_path):
        self.terminal = sys.stdout
        self.tkinter_logs = tkinter_text
        self.log_file = open(log_file_path, "a", encoding='utf8')

    def run_thread(self, function_name, *data):
        """
            Run Thread for multiple scenario
        Args:
            function_name (str) : Which function to run
        """
        if function_name == 'validate_database':
            thread = threading.Thread(target=self.validate_databases)
            thread.start()
        elif function_name == 'generate_report':
            thread = threading.Thread(target=self.generate_report)
            thread.start()
        else:
            print('not found')

          def validate_databases(self):
        """
        Validate database tables and schema
        """
        from_schema = self.old_schema.get().strip()
        to_schema = self.new_schema.get().strip()
        self.close_popup()

        print(''.center(140, '*'))
        print(' Verifying Database '.center(139, ' '))
        print(''.center(140, '*'))
        print(f'[Automation Main] > Verifying database')
        result, error = self.data_helper.verify_database(from_schema, to_schema)
        if result is None:
            showinfo("Error", error)
        else:
            print(f'[Automation Main] > Database verification completed')
            print(f'[Automation Main] > Storing results files')
            json_file_path = self.report_folder + f'/database_verify_result.json'
            self.data_helper.store_json_data_file(json_file_path, result)
            print(f'[Automation Main] > Stored result at : {json_file_path}')
            self.btn_generate_report["state"] = "normal"
            showinfo("Validation Status", "Successfully completed validation")

    def generate_report(self):
        """
        Generate Report after execution
        """
        print(''.center(140, '*'))
        print(' Generating Report '.center(139, ' '))
        print(''.center(140, '*'))
        json_file_path = self.report_folder + f'/database_verify_result.json'
        excel_report = json_file_path.replace('database_verify_result.json', 'Report.xlsx')
        html_report = json_file_path.replace('database_verify_result.json', 'Report.html')
        self.data_helper.create_excel_report(json_file_path, excel_report)
        self.data_helper.create_html_report(json_file_path, html_report)
        showinfo("Report Generation Status", "Successfully completed report generation")


if __name__ == '__main__':
    app = AutomationMain()
    app.init_dashboard()
