# ---------------------------------------------------------------------------------------------------------
# @file		 Debug_test_case.py
# @author	 Abhinaba Ghosh
# @date		 24/01/2023
# @brief	 Individual testcase runner for testing/debugging.
# @attention Copyright (C) 2023-24 | DM Team
# @version   2.0.1
# ----------------------------------------------------------------------------------------------------------
# IMPORTS
import os
import time
import traceback
import platform
import Key_Cycle
from uiautomator import device
from AutomatedTestCases import testcase
from AutomatedTestCases.testcase import logger
from DMAutomatedTest.DMHelper.TestCaseHelper import TestCaseHelper
from DMAutomatedTest.DMTestCases import *


# RUNNER-FUNCTION
def run_test(test_module, test_id):
    # print('[REBOOT] > System will commence power cycle... ')
    # Key_Cycle.reboot()
    # time.sleep(120)
    # Key_Cycle.system_volume_down()
    # time.sleep(2)
    print('[TestRunner] > Getting system build details... ')
    os.system('adb shell input tap 990 45')
    device(resourceId='com.cnh.android.cardmanager:id/tab_menu_1').click()
    build = device(resourceId='com.cnh.android.cardmanager:id/card_description')
    system_build = build.info['text']
    build_number = system_build
    my_system = platform.uname()
    machine_id = my_system.node
    tester_name = machine_id
    print("[TestRunner] > System Build :", build_number, " ; Tested By: ", tester_name)
    logger = testcase.logger(tester_name, build_number, test_module, upload_results=False)
    start_time = time.time()
    try:
        testcase_selected = eval(f'{test_module}.{test_id}()')
        print(f'[TestRunner] > Test case Running {test_module}::{test_id}')
        logger.start_logging_new_run(start_time=start_time, run_number=0, test_case_name=test_id)
        status = testcase.testcase_runner(testcase_selected, run_num=0, given_logger=logger, log_when_true=True)
        capture_logs = False
        if not status:
            capture_logs = True  # make true
        logger.end_current_run_logging(run_number=0, test_case_name=test_id,
                                       capture_logs=capture_logs)
    except NameError as not_found:
        print(
            f'[TestRunner] > Test Case not found :', str(not_found))
        traceback.format_exc()
    except Exception as E:
        print('[TestRunner] > Test case Failed :', str(E))
        traceback.format_exc()
        logger.end_current_run_logging(run_number=0, test_case_name=test_id)
    end_time = time.strftime('%H Hours, %M Min, %S Sec', time.gmtime(time.time() - start_time))
    print(f' Total Execution Time : {end_time} '.center(150, '='))
    print(f'[TestRunner] > Creating HTML Report : {test_module}')
    logger.html_report_object.create_html_test_report(test_case="DM", test_suite_flag=True)
    print(f'[TestRunner] > Successfully created HTML Report ')


# MAIN
if __name__ == '__main__':
    test_module = 'TestCases_DMSANITY'
    test_name = 'test_TC_DM_Sanity_064'
    run_test(test_module, test_name)

# ---------------------------------------------- END ---------------------------------------------------------------- #
