# QATestSuite -> Runner

# ---------------------------------------------------------------------------------------------------------
# @file		 QASelectiveRunner.py
# @author	 Abhinaba Ghosh
# @date		 123456789
# @brief	 DM Selective/All testcase runner for testing/debugging.
# @attention Copyright (C) 
# @version   1
# ----------------------------------------------------------------------------------------------------------
import os
import sys
import time
from datetime import datetime
import pandas as pd
from uiautomator import device
from AutomatedTestCases import testcase
from DMAutomatedTest.DMTestCases import *
from DMAutomatedTest.DMHelper import DMConstants


# LOGGER
class Logger(object):
    def __init__(self, file_path, filename):
        self.terminal = sys.stdout
        if not os.path.isdir(file_path):
            os.makedirs(file_path, exist_ok=True)
        file_path = os.path.abspath(file_path + '/' + filename)
        self.log = open(file_path, "a", encoding='utf8')

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        pass


# RUNNER-FUNCTION
class TestRunner:
    script_mapping = {'SANITY': 'TestCases_DMSANITY',
                      'CTR': 'TestCases_DMCTR',
                      'FRM': 'TestCases_DMFRM',
                      'GGP_S': 'TestCases_DMGGP_S',
                      'GGP_F': 'TestCases_DMGGP_F',
                      'GPN': 'TestCases_DMGPN',
                      'PDT': 'TestCases_DMPDT',
                      'PFD': 'TestCases_DMPFD',
                      'TSK': 'TestCases_DMTSK',
                      'SHP': 'TestCases_DMSHP',
                      'PRODUCT': 'TestCases_DMPRODUCT',
                      'APD': 'TestCases_DMTSK',
                      'OPT': 'TestCases_DMOPT',
                      'AIR_CART_AFTER_SANITY': 'TestCases_DMAIRCART_AFTER_SANITY',
                      'SST': 'TestCases_DMSystem_SANITY',
                      'DFT': 'TestCases_DMDEFECTS',
                      'STRESS': 'TestCases_DMApplication_STRESS',
                      'AGDNA': 'TestCases_DMAGDNA'
                      }

    def __init__(self, test_suite_excel: str):
        """
        Init Test Runner with configuration
        Args:
            test_suite_excel: The name of test suits configuration
        """
        self.test_suite_excel = os.path.abspath(test_suite_excel)

        self.build_details_columns = ['Build Key', 'Value']
        self.module_details_columns = ['Script Name', 'Execute']
        self.script_path = os.path.abspath(os.path.dirname(__file__))
        self.passed = 0
        self.failed = 0
        self.total = 0
        self.not_found = 0

    def get_build_number(self):
        """
        Get build number from display
        Returns:

        """
        os.system('adb shell input tap 990 45')
        device(resourceId='com.cnh.android.cardmanager:id/tab_menu_1').click()
        system_build = device(resourceId='com.cnh.android.cardmanager:id/card_description')
        if system_build.exists:
            return system_build.info['text']

    def extract_data_excel(self) -> tuple:
        """
        Extract Data from Excel
        Returns:
            tuple : Returns Tuple of build details and module details
        """
        print(f"[TestRunner] > Reading Excel file")
        excel_raw_data = pd.read_excel(self.test_suite_excel, sheet_name='Modules', engine='openpyxl').fillna('NA')
        separate_config_table_index = list(excel_raw_data['Details']).index('Script Name')

        build_details = excel_raw_data.iloc[0:separate_config_table_index - 1, :2]
        module_details = excel_raw_data.iloc[(separate_config_table_index - 1) + 2:, :2]

        build_details.columns = self.build_details_columns
        module_details.columns = self.module_details_columns

        build_details = build_details.to_dict(orient='record')
        module_details = module_details.to_dict(orient='record')
        print(f"[TestRunner] > Fetch Details from Excel file")
        return build_details, module_details

    def get_test_cases(self, test_module: str, is_selected: bool = True) -> list:
        """
        Read all test cases which marked as YES in module tab of script
        Args:
            test_module: The name worksheet in excel
            is_selected : Get test cases which mark execute as YES

        Returns:
            str : Return String of test cases

        """
        print(f"[TestRunner] > Reading Test Cases for Module : {test_module}")
        selected_test_cases_data = pd.read_excel(self.test_suite_excel, sheet_name=test_module)
        if is_selected:
            script_filter = selected_test_cases_data.loc[selected_test_cases_data['Execute'] == "YES"]
        else:
            script_filter = selected_test_cases_data
        test_cases = []
        for index, item in script_filter.iterrows():
            test_cases.append(item['Test Case Name'])
        return test_cases

    def start_execution(self) -> None:
        """
        Main Execution function
        Returns:
            None :
        """
        start_time = time.time()
        build_details, module_details = self.extract_data_excel()
        build_number = self.get_build_number()
        if build_number is None:
            build_number = build_details[0]['Value']
        print(f'[TestRunner] > Software Build [{build_number}]')
        tester_name = build_details[1]['Value']
        execution_log_time = datetime.now().strftime('%y-%m-%d-%H-%M')
        sys.stdout = Logger(file_path=DMConstants.EXECUTION_LOGS, filename=f'{execution_log_time}_stdout_logs.txt')
        for item in module_details:
            script_name = item['Script Name']
            execution_type = item['Execute']
            if execution_type.lower() == 'none':
                continue
            test_module = self.script_mapping.get(script_name, None)
            if test_module is not None:
                test_list = []
                if execution_type.lower() == 'selective':
                    test_list = self.get_test_cases(script_name)
                if execution_type.lower() == 'all':
                    test_list = self.get_test_cases(script_name, is_selected=False)
                print(f'[TestRunner] > Test Cases Found {test_module} : {len(test_list)}')
                logger = testcase.logger(tester_name, build_number, test_module)
                start_time = time.time()
                for test_id in test_list:
                    print(f' {test_id} '.center(150, '#'))
                    try:
                        self.total += 1
                        testcase_selected = eval(f'{test_module}.{test_id}()')
                        print(f'[TestRunner] > Test case Running {test_module}::{test_id}')
                        logger.start_logging_new_run(start_time=start_time, run_number=0, test_case_name=test_id)
                        status = testcase.testcase_runner(testcase_selected, run_num=0, given_logger=logger)
                        if status:
                            self.passed += 1
                            capture_logs = False
                        else:
                            self.failed += 1
                            capture_logs = True  # make True
                        logger.end_current_run_logging(run_number=0, test_case_name=test_id,
                                                       capture_logs=capture_logs)
                    except (NameError, AttributeError) as not_found:
                        print(
                            f'[TestRunner] > Test Case not found :', str(not_found))
                        self.not_found += 1
                    except Exception as E:
                        self.failed += 1
                        print('[TestRunner] > Test case Failed :', str(E))
                        logger.end_current_run_logging(run_number=0, test_case_name=test_id, capture_logs=True)
            else:
                print(f'[TestRunner] > Module Not Found : {test_module}')
            os.system('adb kill-server')
            print(f'[TestRunner] > Creating HTML Report : {test_module}')
            logger.fs_fancy_report("DM")
            print(f'[TestRunner] > Successfully created HTML Report ')
            print(' Execution Status '.center(150, '='))
            print(
                f' Total : {self.total} , Passed : {self.passed} , Failed : {self.failed} , Skipped : {self.not_found} '.center(
                    150, '='))
            end_time = time.strftime('%H Hours, %M Min, %S Sec', time.gmtime(time.time() - start_time))
            print(f' Total Execution Time : {end_time} '.center(150, '='))


# MAIN
if __name__ == '__main__':
    test_suite = "DM_TestSuite.xlsx"
    runner = TestRunner(test_suite)
    runner.start_execution()

# ---------------------------------------------- END ---------------------------------------------------------------- #
