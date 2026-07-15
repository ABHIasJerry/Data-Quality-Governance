# QAHelper -> TestCaseHelper.py

import base64
import json
import os

class CommonFunctions:
    def __init__(self, test_case_name):
        self.test_case_name = test_case_name

    @staticmethod
  def xyz():
    """ a static function """
  abc = ""
  return abc

class HelperException(Exception):
    def __init__(self, test_helper, msg):
        self.test_helper = test_helper
        self.msg = msg
        self.__capture_screenshot()
        self.__capture_logs()
        print(f'[{self.test_helper.test_case_name}] > Test case failed : {msg}')
      
    def __capture_screenshot(self):
      screen_capture = f'adb shell screencap -p /sdcard/screencap.png'
      screen_capture_pull = f'adb pull /sdcard/screencap.png {self.test_helper.logger.display_logs_path}/Screenshot.png'
      delete_screen_capture = 'adb shell rm /sdcard/screencap.png'

      os.system(screen_capture)
      time.sleep(2)
      os.system(screen_capture_pull)
      time.sleep(2)
      os.system(delete_screen_capture)

  def __capture_logs(self):
      self.test_helper.logger.logs_collector()
      self.test_helper.stop_logging()

  def __str__(self):
      return self.msg

  def __repr__(self):
      return f'[{self.test_helper.test_case_name}] : {self.msg}]'


class TestCaseHelper:
    """
        TestHelper Class provides all the necessary functionality to create testcases

        >>> test = TestCaseHelper(test_case_name='testcase_name')
        >>> test.click_settings()

    """

    def __init__(self, test_case_name: str) -> object:
        self.test_case_name = test_case_name
        self.test_case_data_dir = ''
        self.data_container_dir = None
        self.import_directory, self.export_directory, self.ref_image_directory = self.get_import_export_directory()
        self.logger = None
        self.com = None
        self.expand_dm_tree_items = []
        self.file_zip_name = None

        self.common_functions = CommonFunctions(test_case_name)
        # self.handle_pop_ups()

    def get_import_export_directory(self):
        """

        Returns:

        """
        try:
            import_directory = DMConstants.IMPORT_DIR_META['_'.join(self.test_case_name.split('_')[3:-1])]
        except:
            import_directory = DMConstants.IMPORT_DIR_META.get('Default', '')
        export_directory = import_directory.replace('Import', 'Export')
        os.makedirs(export_directory, exist_ok=True)
        ref_image_directory = import_directory.replace('Import', 'ReferenceImage')
        if not os.path.isdir(DMConstants.DATA_CONTAINERS):
            os.makedirs(DMConstants.DATA_CONTAINERS, exist_ok=True)
        self.data_container_dir = os.path.abspath(DMConstants.DATA_CONTAINERS + f'/{self.test_case_name}')
        os.system('adb shell mkdir /tmp/datamanagement > NUL')
        os.system('adb shell su -c chmod -R 0777 /tmp/datamanagement > NUL')
        os.system('adb shell mkdir /tmp/datamanagement/TASKDATA > NUL')
        return import_directory, export_directory, ref_image_directory

    # TODO : decypt
    def init_test_case(self, log_time):
        """
        Init test case with logger folders
        Args:
            log_time: time of log to crete folder

        Returns:
            None
        """
        self.test_case_data_dir = os.path.abspath(DMConstants.ARTIFACTS + f'/{log_time}/{self.test_case_name}')
        self.create_data_folder()
        self.start_logging(log_time)

    def cleanup_test_case(self):
        """
        Stop Logging
        Returns:
            None
        """
        self.stop_logging()

    # TODO : decrpt
    def create_data_folder(self):
        """
        Create logger folders
        Returns:
            None
        """
        os.makedirs(self.test_case_data_dir, exist_ok=True)
        print(f"[{self.test_case_name}] > Test Data Folder created at {self.test_case_data_dir}")

    def log_step_excel(self, logger, **data):

        class Result:
            def __init__(self, **data):
                self.result = data.get('result', '')
                self.unique_id = data.get('unique_id', '')
                self.run_number = data.get('run_number', '')
                self.test_case_name = data.get('test_case_name', '')
                self.time_taken_after_key_on = data.get('time_taken_after_key_on', '')
                self.test_description = data.get('test_description', '')
                self.result_description = data.get('result_description', '')
                self.execution_time = data.get('execution_time', 0)
                self.time_completed = data.get('time_completed', 0)
                # self.tes_case_id = data.get('tes_case_id', '')

        logger.log(0, Result(**data), data.get('time_completed', 0))

    def log_step_excel_LT(self, logger, lang, **data):

        class Result:
            def __init__(self, **data):
                self.results_name = "03.40.01.2400_Aircart LT String Validation" + "_" + datetime.now().strftime(
                    '%y-%m-%d-%H-%M-%S')

                self.result = data.get('result', '')
                self.unique_id = data.get('unique_id', '')
                self.run_number = data.get('run_number', '')
                self.test_case_name = data.get('test_case_name', '')
                self.time_taken_after_key_on = data.get('time_taken_after_key_on', '')
                self.test_description = data.get('test_description', '')
                self.result_description = data.get('result_description', '')
                self.execution_time = data.get('execution_time', 0)
                self.time_completed = data.get('time_completed', 0)
                self.fail_img_path = data.get('fail_img_path', '')
                self.comment = data.get('comment', '')

        LanguageNames = {'eng': 'English', 'deu': 'German', 'nld': 'Dutch', 'tur': 'Turkish', 'dan': 'Danish',
                         'est': 'Estonian', 'spa': 'Spanish', 'spa+eng': 'Mexican Spanish', 'fra': 'French',
                         'hrv': 'Croatian', 'ita': 'Italian', 'lat': 'Latvian', 'lit': 'Lithuanian',
                         'hun': 'Hungarians',
                         'nor': 'Norwegian', 'pol': 'Polish', 'por': 'Portuguese', 'por+eng': 'Brazilian Portuguese',
                         'ron': 'Romanian', 'slk': 'Slovak', 'slv': 'Slovenian', 'fin': 'Finnish', 'swe': 'Swedish',
                         'ces': 'Czech', 'ell': 'Greek', 'srp': 'Serbian', 'bul': 'Bulgarian', 'rus': 'Russian',
                         'ara': 'Arabic', 'tha': 'Thai', 'chi_sim': 'Chinese', 'jpn': 'Japanese', 'ukr': 'Ukrainian'}
        logger.log(0, Result(**data), data.get('time_completed', 0),
                   language=LanguageNames.get(lang, " ".join(word.capitalize() for word in lang.split())))

    def start_logging(self, log_time):
        """
        Start logging threads in bg
        Args:
            log_time: time of log

        Returns:
            None
        """
        self.logger = Logger.Logger(test_case_name=self.test_case_name, log_time=log_time,
                                    display_logs_path=self.test_case_data_dir, pcm_logs_path=self.test_case_data_dir)
        self.logger.start()

    def stop_logging(self):
        """
        Stop logging threads
        Returns:
            None
        """
        self.logger.stop()

    def collect_system_logs(self):
        """
        Collect Logs from display and pcm
        Returns:
            None
        """
        self.logger.logs_collector()

    def click_settings(self):
        """
        Click on setting menu of display
        Returns:
            bool : Clicked or not
        """
        print(f'[{self.test_case_name}] > Clicking on settings')
        Helper.clear_popups()
        time.sleep(2)
        CommonFunctions.tap_ui_auto(990, 45)
        if self.wait_to_appear(item_text='Menu'):
            print(f'[{self.test_case_name}] > Clicked on settings')
            return True
        else:
            print(f'[{self.test_case_name}] > Failed to clicked on settings')
        raise Exception('Click on setting icon failed')

