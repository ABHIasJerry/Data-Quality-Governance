# ---------------------------------------------------------------------------------------------------------------------
# @file		 TestCases_GOLD.py
# @author	 Abhinaba Ghosh
# @date		 123456789
# @brief	 xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# @attention Copyright (C)2026
# @version   V1.0
# ----------------------------------------------------------------------------------------------------------------------
# Imports and Module Loaders
import json
import os
import threading
import time
import traceback
from tqdm import tqdm
from queue import Queue
from AutomatedTestCases.testcase import base_testcase
from QAbebvuie.QAHelper import DMConstants
from QAbebvuie.QAHelper.Connector import SFConnector
from QAbebvuie.QAHelper.TestCaseHelper import TestCaseHelper
from Map import Map_helper
from QAbebvuie.QAHelper import TestSuitConfig


Green = "\033[92m{}\033[00m"
Red = "\033[91m{}\033[00m"

class test_TC_DM_GOLD_001(base_testcase):

    def __init__(self, timeout=300):
        self.test_name = "test_TC_DM_GOLD_001"
        self.test_description = "to check....."
        self.timeout = timeout
        self.time_completed = time.time()
        self.elapsed_time = 0
        self.project = "MADS"
        self.id = "83195"
        super(base_testcase, self).__init__()
        self.final_result = True

    def run(self):
        test_case = TestCaseHelper(self.test_name)
        start_time = time.time()
        try:
            # ------------------------ 1.start -----------------------
            test_case.xyz()
            test_case.xyz2()
          # ------------------------ 2.Final result and logging report file -----------------------
            self.result_description = f""
            self.result = True
            print(Green.format(f'[{test_case.test_case_name}] > EXECUTION COMPLETED SUCCESSFULLY'))
        except Exception:
            self.result_description = traceback.format_exc()
            self.result = False
            print(Red.format(f'[{test_case.test_case_name}] > EXECUTION STOPPED WITH ERROR'))
        finally:
            self.time_completed = time.time() - start_time
