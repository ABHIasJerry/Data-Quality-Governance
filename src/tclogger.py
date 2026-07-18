import collections
import csv
import os
import re
import shutil
import sys
import time
import zipfile
from datetime import datetime
import pandas as pd
from azure.storage.blob.blockblobservice import BlockBlobService
from configparser import ConfigParser
import Helper
import tools
import Html_TestResult_LT
from DMAutomatedTest.DMHelper import DMConstants
from FieldSync import FS_Constants as FSConstants
from AutomatedTestCases.test_case_utilities import StreamToFileRouter
from AutomatedTestCases.testcase.resource_monitor import ProcessRecorderManager

import Helpers.canalyzer.functionality as can_simulation
import Helpers.MultiDisplayManagment as MultiDisplay
from Helpers.log_collection import PCMLogsCollector, DisplayLogsCollector
from Helpers import ColorPrint, Paths

# TODO: Used by DM team as part of Helper functions
current_results_path = None
run_count = None


class LoggerInterface:
    """
    This object captures the attributes and methods used by the Test Runner class in Utilities.py. It is intended to
    help keep track of what attributes and methods are used for smoke and sanity testing.
    """

    results_name = ""
    current_run_log_directory = ""

    def __init__(self, tester_name, build_number, main_test_name, bootup_time_test_running=False, upload_results=False):
        ...

    def startCanLogging(self, run_number, com):
        ...

    def report_dir(self, run_number, lang):
        ...

    def start_logging_new_run(self, start_time: float, run_number: int,
                              test_case_name='', start_pcm_logging=True, language='English'):
        ...

    def end_current_run_logging(self, run_number, test_case_name='', capture_logs=True, language='English'):
        ...

    def remove_file(self, file):
        ...

    def stopCanLogging(self, run_number, com, getLogs=False, type1=""):
        ...


def _get_results_file_name(main_test_name, results_name):
    if main_test_name.startswith('TestCases_DM'):
        Helper.set_os_dir(DMConstants.REPORTS)
        return DMConstants.REPORTS + f'/{results_name}.csv'
    
    elif main_test_name.__contains__('FieldSync'):  # TODO: use module variable
        Helper.set_os_dir(FSConstants.ARTIFACTS)
        Helper.test_results_dir = FSConstants.ARTIFACTS
        return FSConstants.ARTIFACTS + "\\" + results_name + "\\" + results_name + ".csv"
    
    else:
        return f"{Paths.TEST_RESULTS}\\{results_name}\\{results_name}.csv"


def _set_cwd_based_on_testing_module(main_test_name, results_name):
    if main_test_name.startswith('TestCases_DM'):
        Helper.set_os_dir(DMConstants.ARTIFACTS + f'/{results_name}')
    elif main_test_name.startswith('FieldSync'):
        Helper.set_os_dir(FSConstants.ARTIFACTS + "\\" + results_name)
    else:
        Helper.set_os_dir(f"{Paths.TEST_RESULTS}\\{results_name}")


def _get_current_run_log_directory(test_case_name, results_name, run_number):
    if test_case_name.__contains__("FieldSync"):  # TODO: use module variable
        Helper.test_results_dir = FSConstants.ARTIFACTS
        return FSConstants.ARTIFACTS + "\\" + results_name + "\\" + "run_" + str(run_number)

    elif test_case_name.startswith('test_TC_DM'):  # TODO: use module variable
        return os.path.abspath(DMConstants.ARTIFACTS + f'/{results_name}/{test_case_name}')

    else:
        return f"{Paths.TEST_RESULTS}\\{results_name}\\run_{run_number}"
    

def _create_run_output_file_path(test_case_name, run_number, results_name):
    if not test_case_name.startswith('test_TC_DM'):
        filename = f"{Paths.TEST_RESULTS}\\{results_name}\\run_{run_number}\\run_{run_number}_testrun_output.txt"
        # Done setting where the test run output will be logged.

        # Re-route system output to be captured in run logs.
        sys.stdout = StreamToFileRouter(filename, sys.stdout)
        sys.stderr = StreamToFileRouter(filename, sys.stderr)


def _get_screenshot_directory(test_case_name, results_name, run_number, language):
    testing_config = ConfigParser()
    testing_config.read(Paths.MAIN_CONFIG)
    module = testing_config['Test info']['sel_module']
    feature = testing_config['Test info']['sel_feature']

    if test_case_name.__contains__("FieldSync"):  # TODO: use module variable
        screen_shot_dir = FSConstants.ARTIFACTS + "\\" + results_name + "\\" + "run_" + str(run_number) + "\\" + "screenshots_misc"

    elif test_case_name.startswith('test_TC_DM'):  # TODO: use module variable
        screen_shot_dir = os.path.abspath(DMConstants.ARTIFACTS + f'/{results_name}/{test_case_name}/screenshots_misc')

    elif feature == "Language Translation":
        screen_shot_dir = f"{Paths.TEST_RESULTS}\\{results_name}\\run_{run_number}\\screenshots_misc\\{language}"

    else:
        screen_shot_dir = f"{Paths.TEST_RESULTS}\\{results_name}\\run_{run_number}\\screenshots_misc"

    return screen_shot_dir


def _set_cwd_to_snapshot_directory(test_case_name, results_name, run_number, language):
    testing_config = ConfigParser()
    testing_config.read(Paths.MAIN_CONFIG)
    module = testing_config['Test info']['sel_module']
    feature = testing_config['Test info']['sel_feature']
    
    if test_case_name.__contains__("FieldSync"):  # TODO: use module variable
        # Set current working directory to FieldSync's artifact directory and take a snapshot.
        screen_shot_dir = os.path.abspath(FSConstants.ARTIFACTS + f'/{results_name}')
        Helper.set_os_dir(screen_shot_dir)
        Helper.snapshot(str(run_number) + "_errorSnapShot")

    elif test_case_name.startswith('test_TC_DM'):  # TODO: use module variable
        # Set current working directory to Data Management's artifact directory and take a snapshot.
        screen_shot_dir = os.path.abspath(DMConstants.ARTIFACTS + f'/{results_name}/{test_case_name}')
        Helper.set_os_dir(screen_shot_dir)
        Helper.snapshot("SnapShot")

    elif feature == "Language Translation":
        # Define path for snapshots when running Language Translation.
        screen_shot_dir = f"{Paths.TEST_RESULTS}\\{results_name}\\run_{run_number}\\screenshots_misc\\{language}"
        Helper.set_os_dir(screen_shot_dir)
        Helper.snapshot(str(run_number) + "_errorSnapShot")

    else:
        # Define path for snapshots when not running Language Translation.
        screen_shot_dir = f"{Paths.TEST_RESULTS}\\{results_name}\\run_{run_number}\\screenshots_misc"
        Helper.set_os_dir(screen_shot_dir)
        Helper.snapshot(str(run_number) + "_errorSnapShot")


def _create_test_report(results_name, test_case_name, language, run_number):
    # Create test report at the root of the test report directory.
    # Set the current run log directory and make it the current working directory.
    current_run_log_directory = f"{Paths.TEST_RESULTS}\\{results_name}"
    Helper.set_os_dir(current_run_log_directory)
    # Done setting the current run log directory and make it the current working directory.

    # Create report.
    html_report_object = tools.HtmlTestReport()
    html_report_object.create_html_test_report(csv_file_full_name=None, test_case=test_case_name, language=language,
                                               results_name=results_name, test_suite_flag=True)
    # Done creating test report at the root of the test report directory.

    # Set current working directory to the current run directory.
    current_run_log_directory = f"{Paths.TEST_RESULTS}\\{results_name}\\run_{run_number}"
    Helper.set_os_dir(current_run_log_directory)
    return current_run_log_directory
    # Done setting the current working directory to the current run directory.


@Paths.protect_cwd
def _copy_csv_data_to_xlsx(results_name: str):
    current_run_log_directory = f"{Paths.TEST_RESULTS}\\{results_name}"
    Helper.set_os_dir(current_run_log_directory)

    cwd = os.getcwd()
    all_files = os.listdir(cwd)
    csv_files = [f for f in all_files if f.endswith('.csv')]
    csv_file_path = os.path.join(cwd, csv_files[0])
    filepath = os.path.join(current_run_log_directory, csv_files[0].strip('.csv') + '.xlsx')
    directory, filename = os.path.split(filepath)
    xlsx_filename = filename.replace(' ', '_')
    xlsx_filename_and_path = os.path.join(directory, xlsx_filename)

    try:
        df = pd.read_csv(csv_file_path)
        df.to_excel(xlsx_filename_and_path, index=False, engine='openpyxl')
    except ImportError:
        ColorPrint.error("The 'openpyxl' package is not installed. XLSX test report will not be generated")


class logger:
    """
    logger class for use with the testcase class. This class uses the data structure defined in the base_testcase
    To log testcase results.

    The format for logging is defined in an ordered dictionary in the classes init function. This data dictionary, must
    be matched to data contained in the test case class this is done in the log function.

    The start_logging_new_run function does any setup and startup logging that is needed. For example this is where the
    logcat is started

    The end_current_run_logging collects any logs needed before reboot of that key cycle

    Attributes:
        start_time (double):                Start time of current key cycle used for logging
        results_name:                       Name of results file
        results_file_name:                  full path directory of results file
        current_run_log_directory:          full path of currently run log files

    methods:
        create_result_file():       Creates a results file if it does not exist
        log(run_number, testcase):  logs data from a testcase class to the results file
        start_logging_new_run(start_time, run_number):  starts a new logging run, which creates a new log directory for that run
        end_current_run_logging(run_number):      stops and pulls logs for current run
        cleanCanLogDir(run_number):               removes can logging files
        startCanLogging(run_number):              starts can logging through CANalyzer
        stopCanLogging():                         stops can logging through CANalyzer

    """

    def __init__(self, tester_name, build_number, main_test_name, bootup_time_test_running=False, upload_results=False):
        if not isinstance(tester_name, str):
            raise ValueError("tester_name must be a string")
        if not isinstance(main_test_name, str):
            raise ValueError("name must be a string")
        # Simple regular expression to check build
        build_check = re.compile(r"\d+.\d+.\d+.\d+")
        if not build_check.match(build_number):
            raise ValueError("Build Number must be in format x+.x+.x+.x+", build_number)

        self.failed_result_in_run = False
        self.current_run_log_directory = None
        self.upload_results = upload_results
        self.build_number = str(build_number)
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        self.process_manager = ProcessRecorderManager()

        # using an ordered dictionary, the order of adding to the dictionary is the order of the columns in the
        # results file.
        # TODO: Move data_to_log to its own object representation.
        self.data_to_log = collections.OrderedDict()
        self.data_to_log["Unique ID"] = ''
        self.data_to_log["Tester"] = tester_name
        self.data_to_log["Build"] = build_number
        self.data_to_log["Main Test Name"] = main_test_name
        self.data_to_log["Run Number"] = ''
        self.data_to_log["Language"] = ''
        self.data_to_log["Test Case Id"] = ''
        self.data_to_log["Time Taken from Key ON"] = ''
        self.data_to_log["Feature_Level_Category"] = ''
        self.data_to_log["Test Case Name"] = ''
        self.data_to_log["Test Description"] = ''
        self.data_to_log["Result Description"] = ''
        self.data_to_log["Result"] = ''
        self.data_to_log["Execution Time"] = ''
        self.data_to_log["Comments"] = ''
        self.data_to_log["fail img path"] = ''
        self.unique_id_for_run_number = datetime.now().strftime('%y-%m-%d-%H-%M')

        self.results_file = ""
        self.start_time = 0
        self.results_name = build_number + "_" + main_test_name + "_" + datetime.now().strftime('%y-%m-%d-%H-%M-%S')

        # Set results_file_name based on test suite executing.
        self.results_file_name = _get_results_file_name(main_test_name, self.results_name)

        # Set cwd for testing output based on test suite executing.
        _set_cwd_based_on_testing_module(main_test_name, self.results_name)

        # Create report files
        self.create_result_file()  # This should be part of the builder for data_to_log

    def create_result_files(self, results_file_name, lang):
        # This creates the result files for Language translation files.
        # This is called by report_dir method.
        """Creates a result file for the test suit, should be used with logTestCase to report testcase results"""
        # Create file if it doesn't exist; if the file exists don't do anything
        os.makedirs(results_file_name + "\\Report\\")
        self.results_file = results_file_name + "\\Report\\" + lang + ".csv"
        # print(f"result file name =======> {self.results_file}")
        if len(self.results_file) > 255:
            print("File name length is exceeding more than 255 characters  ")
        if not os.path.exists(self.results_file):
            with open(self.results_file, 'w', newline='', encoding='utf-8-sig') as file:
                # Write header for data, this needs to match what is used in the log
                csv_writer = csv.writer(file)
                csv_writer.writerow(list(self.data_to_log.keys()))

    def create_result_file(self):
        # This creates the result files for non Language Translation reports.
        # This is called every time a loger instance is created.
        """Creates a result file for the test suit, should be used with logTestCase to report testcase results"""
        # Create file if it doesn't exist; if the file exists don't do anything
        if not os.path.exists(self.results_file_name):
            with open(self.results_file_name, 'w', newline='', encoding='utf-8-sig') as file:
                # Write header for data, this needs to match what is used in the log
                csv_writer = csv.writer(file)
                csv_writer.writerow(list(self.data_to_log.keys()))

    def start_logging_new_run(self, start_time: float, run_number: int,
                              test_case_name='', start_pcm_logging=True, language='English'):
        # Notes:
        # - The "test_case_name" is in reality the test suite name.
        # Used outside Test Runner

        display_manager = MultiDisplay.DisplayManager()

        self.failed_result_in_run = False
        self.start_time = start_time

        global current_results_path, run_count

        # Set the directory that will contain the run results.
        self.current_run_log_directory = _get_current_run_log_directory(test_case_name, self.results_name, run_number)
        Helper.set_os_dir(self.current_run_log_directory)
        # Done Setting the directory that will contain the run results.

        # Set the file where the test run output will be logged.
        _create_run_output_file_path(test_case_name, run_number, self.results_name)

        for display in display_manager.displays:
            serial = display.serial

            # Create directory to store display logs.
            display_type = display_manager.get_display_type_as_string(display.type)
            display_logs_directory = self.current_run_log_directory + "\\Display_Data\\" + display_type + "_Display_Logs"
            Helper.set_os_dir(display_logs_directory)
            time.sleep(3)
            # Done creating display log directory.

            # Create clean temporary DM file structure.
            DisplayLogsCollector.create_tmp_file_structure(serial)
            # Done creating clean temporary DM file structure.

            # Create display sub-processes to log info.
            self.process_manager.start_recording_display(run_number, serial, display_type)
            # Done creating display sub-processes.

        # Restore current working directory after it was changed by the display setup.
        Helper.set_os_dir(self.current_run_log_directory)

        if start_pcm_logging:
            # Create pcm sub-processes to log info.
            time_stamp = datetime.now().strftime("%m_%d_%Y_%H_%M_%S")
            PCMLogsCollector.get_previous_pcm_logs(self.current_run_log_directory, time_stamp)
            self.process_manager.start_recording_pcm(run_number)
            # Done creating pcm sub-processes.

        # Create the screenshot directory for the different types of test suites.
        screen_shot_dir = _get_screenshot_directory(test_case_name, self.results_name, run_number, language)
        Helper.set_os_dir(screen_shot_dir)
        # Done creating screenshot directory.

        # Set values to be returned TODO: Need to figure out why we need to return these
        current_results_path = os.path.dirname(self.current_run_log_directory)
        run_count = run_number
        return current_results_path, run_count

    def pull_logs_from_pcm(self):
        try:
            pcm_data_directory = self.current_run_log_directory + "\\" + "PCM_Data"
            Helper.set_os_dir(pcm_data_directory)
            self.process_manager.pull_pcm_recordings(pcm_data_directory)
            PCMLogsCollector.get_all_logs(pcm_data_directory)

        except Exception as e:
            ColorPrint.output("red", f"An exception occurred while pulling the logs from the system:\n{e}")

    def pull_logs_from_displays(self):
        display_manager = MultiDisplay.DisplayManager()

        # Stop recording resource consumption. Otherwise, ADB process spike will be captured for pulling logs.
        for display in display_manager.displays:
            self.process_manager.stop_recording_display(display.serial)

        display_data_directory = self.current_run_log_directory + "\\" + "Display_Data"

        # Pull logs from display.
        for display in display_manager.displays:
            try:
                display_type = display_manager.get_display_type_as_string(display.type)
                display_logs_directory = display_data_directory + "\\" + display_type + "_Display_Logs"
                Helper.set_os_dir(display_logs_directory)

                serial_number = display.serial
                DisplayLogsCollector.get_all_logs(serial_number)

            except Exception as e:
                ColorPrint.output("red", f"An exception occurred while pulling the logs from display {display.serial}:"
                                         f"{e}")

    def end_current_run_logging(self, run_number, test_case_name='', capture_logs=True, language='English'):
        # Set the current working directory to the test result path, based on test suite name.
        self.current_run_log_directory = _get_current_run_log_directory(test_case_name, self.results_name, run_number)
        Helper.set_os_dir(self.current_run_log_directory)
        # Done setting the current working directory  for the test results.

        if self.upload_results:
            self.upload_results_file(run_number)

        # Set snapshot directory as the current working directory.
        _set_cwd_to_snapshot_directory(test_case_name, self.results_name, run_number, language)
        # Done setting the snapshot directory as the current working directory.

        if capture_logs:
            self.pull_logs_from_pcm()

        if test_case_name.__contains__("FieldSync"):  # TODO: use module variable
            Helper.test_results_dir = FSConstants.ARTIFACTS

        if test_case_name.__contains__("LT"):  # TODO: use feature variable
            # TODO: Get in touch with Language Translation team to clean their report generation.
            print("check3", test_case_name)
            print(f"We are in LT report creation!!! {language}")
            # Set current run log directory to be at the root of the test results' directory.
            self.current_run_log_directory = f"{Paths.TEST_RESULTS}\\{self.results_name}"
            Helper.set_os_dir(self.current_run_log_directory)
            # Done setting current working directory to the parent of the test results' directory.

            # Creating report
            print("In report = = = " + language)
            self.fs_fancy_report_LT(test_case_name, language=language)
            # Done creating report.

            # Create current run log directory...
            self.current_run_log_directory = f"{Paths.TEST_RESULTS}\\{self.results_name}\\run_{run_number}"
            Helper.set_os_dir(self.current_run_log_directory)
            # Done creating current run log directory.

        else:
            self.current_run_log_directory = _create_test_report(self.results_name, test_case_name, language, run_number)

        if capture_logs:
            self.pull_logs_from_displays()
            _copy_csv_data_to_xlsx(self.results_name)

            if self.upload_results:
                self.upload_results_file(run_number)
            if test_case_name.__contains__("FieldSync"):  # TODO: use module variable
                screen_shot_dir = FSConstants.ARTIFACTS + "\\" + self.results_name + "\\" + "run_" + str(
                    run_number) + "\\" + "screenshots_misc"
                Helper.set_os_dir(screen_shot_dir)
                Helper.snapshot(str(run_number) + "_errorSnapShot")
            elif test_case_name.startswith('test_TC_DM'):  # TODO: use module variable
                self.current_run_log_directory = os.path.abspath(
                    DMConstants.ARTIFACTS + f'/{self.results_name}/{test_case_name}')
                Helper.set_os_dir(self.current_run_log_directory)
                Helper.snapshot("SnapShot")
            elif language != 'English':  # TODO: use feature variable
                screen_shot_dir = f"{Paths.TEST_RESULTS}\\{self.results_name}\\run_{run_number}\\screenshots_misc\\{language}"
                Helper.set_os_dir(screen_shot_dir)
                Helper.snapshot(str(run_number) + "_errorSnapShot")
            else:
                screen_shot_dir = f"{Paths.TEST_RESULTS}\\{self.results_name}\\run_{run_number}\\screenshots_misc"
                Helper.set_os_dir(screen_shot_dir)
                Helper.snapshot(str(run_number) + "_errorSnapShot")

        # Restore system output to original state to stop capturing output to run files
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr

    def log(self, run_number, testcase, duration=0, language='English'):
        """"Uses the properties of test case to log the result of the test case
            create_result_file should be used in order create the correct result file"""
        # TODO: Investigate/fix 'test_case_name' since test cases actually use 'test_name'
        # This writes to csv file that collects results.

        try:
            # Determine if it is going to write to LT or regular test file.
            if hasattr(testcase, 'test_case_name') and testcase.test_case_name.__contains__("LT"):
                tmp_file = open(self.results_file, 'a', newline='', encoding='utf-8-sig')
            else:
                tmp_file = open(self.results_file_name, 'a', newline='', encoding='utf-8-sig')

            # Write test case result.
            if testcase.result:
                self.data_to_log["Result"] = "PASS"
            else:
                self.data_to_log["Result"] = "FAIL"
                self.failed_result_in_run = True

            # Write "unique id" but it is just a time stamp.
            self.data_to_log["Unique ID"] = datetime.now().strftime('%y-%m-%d-%H-%M-%S')

            # Write language used for execution.
            self.data_to_log["Language"] = language

            # Add test case ID
            if hasattr(testcase, 'project') and hasattr(testcase, 'id'):
                if testcase.project == "" or testcase.id == "":
                    # project and id fields exist but are empty --> Not able to link
                    self.data_to_log["Test Case Id"] = 'No Linked Id'
                else:
                    # The project and id fields exist and are not empty --> Good to make a link
                    self.data_to_log["Test Case Id"] = f'{testcase.project}-{testcase.id}'
            else:
                # project and id fields do not exist --> testcase has not been modified yet
                self.data_to_log["Test Case Id"] = 'TBD'

            # Need to add teh date time unique id so that combining result files will have unique run numbers
            self.data_to_log["Run Number"] = str(run_number) + "_" + self.unique_id_for_run_number

            # Write test case name.
            # self.data_to_log["Test Case Name"] = testcase.test_name
            if hasattr(testcase, 'test_name') and '>' in testcase.test_name:
                self.data_to_log["Test Case Name"] = testcase.test_name.replace('>', '')
            elif hasattr(testcase, 'test_case_name') and testcase.test_case_name.__contains__("LT"):
                self.data_to_log["Test Case Name"] = testcase.test_case_name
            else:
                self.data_to_log["Test Case Name"] = testcase.__class__.__name__

            # TODO add testcase data once everyone implements it
            self.data_to_log["Feature Level Category"] = ''

            # Write Time Taken from Key ON.
            if testcase.__class__.__name__.startswith('test_TC_DM_'):
                self.data_to_log["Time Taken from Key ON"] = str(testcase.time_completed)
            elif testcase.__class__.__name__.startswith('FieldSync'):
                self.data_to_log["Time Taken from Key ON"] = str(testcase.time_completed - self.start_time)
            else:
                self.data_to_log["Time Taken from Key ON"] = str(testcase.time_completed - self.start_time)

            self.data_to_log["Test Description"] = testcase.test_description
            self.data_to_log["Result Description"] = testcase.result_description
            self.data_to_log["Execution Time"] = duration

            if hasattr(testcase, 'test_case_name') and testcase.test_case_name.__contains__("LT"):
                self.data_to_log["Comments"] = testcase.comment
                self.data_to_log["fail img path"] = testcase.fail_img_path

            csv_writer = csv.writer(tmp_file)
            csv_writer.writerow(list(self.data_to_log.values()))
            tmp_file.close()
        except Exception as e:
            print(e)

    def upload_results_file(self, run_number):
        # TODO: The blob service is not used as far as I know and should move to own module for report uploading.
        try:
            # Create the BlockBlockService that is used to call the Blob service for the storage account
            block_blob_service = BlockBlobService(account_name='brettmcclelland',
                                                  account_key='4AVgLgLKw+y4zK8amwAqCarsaroXxLS0AIglcFVjkXfMdTGQaUBOOFLLZuOe3QZBsDS6hGG3o7Rx7+kQk5eWpA==')
            block_blob_service.set_proxy('10.243.134.19', port=8080)

            # Create a container with same name as main test
            print(("Creating_Container: ", self.data_to_log["Main Test Name"].strip().replace("_", "-").lower()))
            testsuite_container_name = self.data_to_log["Main Test Name"].strip().replace("_", "-").lower()
            block_blob_service.create_container(testsuite_container_name)

            # Set the permission so the blobs are public.
            # TODO Do we need this? It doesn't work
            # block_blob_service.set_container_acl(testsuite_container_name, public_access=PublicAccess.Container)

            print(("\nUploading to Blob storage as blob" + self.results_name))

            # Upload the created file, use local_file_name for the blob name
            block_blob_service.create_blob_from_path(testsuite_container_name, self.results_name + ".csv",
                                                     self.results_file_name)
            print(("Uploaded " + self.results_file_name + " to Azure"))

            if self.failed_result_in_run:
                # Upload Logcat
                logcat_container_name = "failed-logcats"
                block_blob_service.create_container(logcat_container_name)
                # TODO Delete Causes Exception
                # block_blob_service.set_container_acl(logcat_container_name, public_access=PublicAccess.Container)
                logcat_name = "run_" + str(run_number) + "_logcat.txt"
                logcat_upload = "run_" + self.data_to_log["Run Number"] + "_logcat.txt"
                block_blob_service.create_blob_from_path(logcat_container_name, logcat_upload, logcat_name)
                print(("Uploaded " + logcat_name + " to Azure"))

                # Upload Logs
                zfname = self.results_name + ".zip"
                zip = zipfile.ZipFile(zfname, 'w')
                files = [f for f in os.listdir('.') if os.path.isfile(f)]
                for f in files:
                    zip.write(f)
                zip.close()
                print((" Uploading " + zfname + " to Azure"))
                block_blob_service.create_blob_from_path(testsuite_container_name, zfname, zfname)

        except Exception as e:
            print("Could not upload file to Azure")
            print(e)

    def startCanLogging(self, run_number, com, type1=""):
        # TODO: Review calls to this function to point to can_simulation module.
        can_simulation.start_can_logging(run_number, type1)

    def stopCanLogging(self, run_number, com, getLogs=False, type1=""):
        """
        Used to stop the simulation from logging.

        Args:
            com: Intended to be the communication interface with the simulation
            getLogs (bool): Should simulation logs be moved to run folder.
            run_number (int): No longer needed. Used to be required as part of get_canalyzer_logs()
            type1 (str): No longer needed. Used to be required as part of get_canalyzer_logs()

        Note:
            The run_number and type1 were not removed due to stopCanLogging being used across the testscript project.
            However, as of 1/19/2023 get_canalyzer_logs is only used inside this function.
        """
        # TODO: Review calls to this function to point to can_simulation module. Also review remove getLogs arg from
        #  callers to avoid overloading the "stop" action with also pulling the logs.
        can_simulation.stop_can_logging()
        if getLogs:
            try:
                can_simulation.get_canalyzer_latest_log(self.current_run_log_directory)
            except Exception as e:
                print(e)

    def fs_fancy_report_LT(self, test_case=None, language='English'):
        # TODO: Clean this code. This is supposed to be only called by the Language Translation (LT) team. Therefore,
        #  the logic in here making reference to modules outside of LT is difficult to understand if it is used at all.
        """" This method responsible for creating .HTML reports for language translation.
        """
        html_obj = Html_TestResult_LT.HTMLModule()
        application_name = None
        try:

            if test_case.__contains__("FieldSync"):  # TODO: use module variable
                csv_raw = pd.read_csv(
                    FSConstants.ARTIFACTS + "\\" + self.results_name + "\\" + self.results_name + ".csv",
                    index_col=False, usecols=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13], encoding='utf-8-sig')
            elif test_case == 'DM':  # TODO: use module variable
                csv_raw = pd.read_csv(
                    DMConstants.REPORTS + "\\" + self.results_name + ".csv",
                    index_col=False, usecols=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13], encoding='utf-8-sig')
            elif test_case.__contains__("LT"):  # TODO: use module variable
                csv_raw = pd.read_csv(
                    self.results_file, index_col=False, usecols=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
                    encoding='utf-8-sig')
            else:
                if getattr(sys, 'frozen', False):
                    csv_raw = pd.read_csv(
                        os.path.dirname(
                            sys.executable) + "\\TestResults\\" + self.results_name + "\\" + self.results_name + ".csv",
                        index_col=False, usecols=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13], encoding='utf-8-sig')
                else:
                    csv_raw = pd.read_csv(
                        Helper.test_results_dir + "\\" + self.results_name + "\\" + self.results_name + ".csv",
                        index_col=False, usecols=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13], encoding='utf-8-sig')

            df = csv_raw.head()
            csv_result = csv_raw['Result'].value_counts()
            csv_labels = csv_result.index
            Fail_case_obj = csv_raw[csv_raw['Result'] == 'FAIL']
            Total_fail_count = len(Fail_case_obj)
            Pass_case_obj = csv_raw[csv_raw['Result'] == 'PASS']
            Total_Pass_count = len(Pass_case_obj)
            Total_test_cases = len(csv_raw)
            run_num = str(csv_raw[str('Run Number')][Total_test_cases - 1])
            Total_run_count = str(run_num[0:run_num.find("_")])
            print("total no of runs:", Total_run_count)
            Tester_name = str(csv_raw[str('Tester')][Total_test_cases - 1])
            if test_case == 'DM':
                results_name = DMConstants.REPORTS + '\\' + self.results_name + "_Final_Report.html"
            elif test_case.__contains__("LT"):  # TODO: use module variable
                results_name = Helper.test_results_dir + "\\" + self.results_name + "\\" + "run_1" + "\\screenshots_misc" + "\\" + language + "\\Report\\" + language + ".html"
            else:
                if getattr(sys, 'frozen', False):
                    results_name = os.path.dirname(
                        sys.executable) + "\\TestResults\\" + self.results_name + "\\" + self.results_name + "_Final_Report.html"
                else:
                    results_name = Helper.test_results_dir + "\\" + self.results_name + "\\" + self.results_name + "_Final_Report.html"
            application_name = str(csv_raw[str('Main Test Name')][Total_test_cases - 1])
            if test_case != None:
                html_obj.initialize(test_case, results_name)
            else:
                html_obj.initialize(application_name, results_name)
            build_number = self.build_number
            html_obj.summary(build_number, Tester_name, Total_test_cases, int(Total_run_count))
            pychart_with_data = html_obj.CreatePieChart(csv_result, csv_labels)
            html_obj.pychart_image_insert(pychart_with_data)
            displays_list = Helper.get_all_displays()
            html_obj.device_list_with_folders(displays_list)
            html_obj.current_directory_link()
            ################################################################################################
            test_result_directory = Paths.TEST_RESULTS

            if Total_fail_count > 0:
                html_obj.screen_name("Fail Test cases")
                html_obj.table_Start()
                for row_index in Fail_case_obj.index:
                    data = []
                    data.append(str(csv_raw[str('Unique ID')][row_index]))
                    data.append(str(csv_raw[str('Main Test Name')][row_index]))  # Run Number
                    data.append(str(csv_raw[str('Run Number')][row_index]))
                    data.append(str(csv_raw[str('Language')][row_index]))
                    # data.append(language)
                    data.append(str(csv_raw[str('Time Taken from Key ON')][row_index]))
                    data.append(str(csv_raw[str('Test Case Name')][row_index]))
                    # data.append(test_case)
                    data.append(str(csv_raw[str('Test Description')][row_index]).replace(";", "<br>"))
                    data.append(str(csv_raw[str('Result Description')][row_index]))
                    data.append(str(csv_raw[str('Result')][row_index]))
                    data.append(str(csv_raw[str('Execution Time')][row_index]))
                    data.append(str(csv_raw[str('Comments')][row_index]))
                    run_num = str(csv_raw[str('Run Number')][row_index])
                    run_num_str = str(run_num[0:run_num.find("_")])
                    fail_img_path = os.path.join(test_result_directory, self.results_name, "run_1",
                                                 "screenshots_misc", str(csv_raw[str('Language')][row_index]),
                                                 str(csv_raw[str('fail img path')][row_index]))
                    if os.path.exists(fail_img_path):
                        converted_image_data = html_obj.ConvertImage_ToBase64(fail_img_path)
                        html_obj.fail_table_update(data, str(converted_image_data))
                    else:
                        html_obj.fail_table_update(data)
                html_obj.table_end()
                html_obj.panelend()
            html_obj.screen_name("Total Test cases Results")
            html_obj.table_Start()
            for row_index in csv_raw.index:
                data = []
                data.append(str(csv_raw[str('Unique ID')][row_index]))
                data.append(str(csv_raw[str('Main Test Name')][row_index]))  # Run Number
                data.append(str(csv_raw[str('Run Number')][row_index]))
                data.append(str(csv_raw[str('Language')][row_index]))
                data.append(str(csv_raw[str('Time Taken from Key ON')][row_index]))
                data.append(str(csv_raw[str('Test Case Name')][row_index]))
                # data.append(test_case)
                data.append(str(csv_raw[str('Test Description')][row_index]).replace(";", "<br>"))
                data.append(str(csv_raw[str('Result Description')][row_index]))
                data.append(str(csv_raw[str('Result')][row_index]))
                data.append(str(csv_raw[str('Execution Time')][row_index]))
                data.append(str(csv_raw[str('Comments')][row_index]))
                html_obj.table_update(data)
            html_obj.table_end()
            html_obj.panelend()

            if Fail_case_obj.empty:
                print("No Test cases fails are available")
            else:
                print("fails test cases are available")
        except BaseException as Err:
            print(Err)
        finally:
            html_obj.summaryresult()
            html_obj.close(application_name)

    def report_dir(self, run_number, lang):
        """"
        This method create lang folder in screenshots_misc folder, we use this folder to store screenshots and the
        report folder.
        """
        screen_shot_dir = f"{Paths.TEST_RESULTS}\\{self.results_name}\\run_{run_number}\\screenshots_misc\\{lang}"
        Helper.set_os_dir(screen_shot_dir)
        self.create_result_files(screen_shot_dir, lang)

    def remove_file(self, file):
        if os.path.exists(file):
            os.remove(file)
        else:
            print("The file does not exist")
