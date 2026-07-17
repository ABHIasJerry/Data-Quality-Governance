# QAHelper -> TestCaseHelper.py

# IMPORTS
import base64
import json
import os
import shutil
import subprocess
import time
import zipfile
import schedule
import datetime
from ctypes import c_char_p
from datetime import datetime
from multiprocessing import Process, Manager, Queue
from typing import List, Dict, Union
from pywinauto.application import Application
from datetime import datetime
from datetime import date
from pytz import timezone
import selenium
import DMAutomatedTest
from Telematics import locators
import configparser
import Helper
import cv2
import numpy
from selenium import webdriver
from PIL import Image
from filehash import FileHash
from pytesseract import pytesseract
from selenium.common.exceptions import ElementNotVisibleException, ElementNotSelectableException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys
from uiautomator import JsonRPCError
from uiautomator import device
import sys
from DMAutomatedTest.DMHelper import DMConstants, Logger, TestSuitConfig
from DMAutomatedTest.DMHelper import XMLOperations
from DMAutomatedTest.DMHelper.Connector import DBConnector, SSHConnector, SQLiteConnector
from DMAutomatedTest.DMHelper.DataModel import ModelConstants
from ISOBUS.ISOBUS_helper import COMIsobusInterface
import AutomatedTestCases.UDWs_testcases as udw_testcase
from Screen import COM_interface
import Helpers.MultiDisplayManagment as MultiDisplay
Display = MultiDisplay.DisplayManager()
global P_window_launch_time
global M_save_timer
global M_window_launch_time
global P_save_timer


class CommonFunctions:
    def __init__(self, test_case_name):
        self.test_case_name = test_case_name

    @staticmethod
    def tap_ui_auto(x: int, y: int):
        """
        UI automator tap function for display
        Args:
            x: x co-ordinate of display
            y: y co-ordinate of display

        Returns:
            bool : Successfully clicked or not
        """
        status = Display.active_display_uiautomator.click(x, y)
        return status

    def tap_adb(self, x, y):
        """
        Tap Using ADB cmd
        Args:
            x: x co-ordinate of display
            y: y co-ordinate of display

        Returns:
            bool : Successfully clicked or not
        """
        tap_cmd = 'adb -s' + ' ' + Display.active_display + f' shell input tap {x} {y}'
        status = os.system(tap_cmd)
        if status == 0:
            print(f'[{self.test_case_name}] > Tap adb : [x : {x}, y : {y}]')
            return True
        return False

    def drag_screen(self, x1, y1, x2, y2):
        """
        drag Using ADB cmd
        Args:
            x1: x co-ordinate of display
            y1: y co-ordinate of display
            x2: x co-ordinate of display
            y2: y co-ordinate of display
        Returns:
            bool : Successfully clicked or not
        """
        tap_cmd = f'adb shell input touchscreen swipe {x1} {y1} {x2} {y2}'
        status = os.system(tap_cmd)
        if status == 0:
            print(f'[{self.test_case_name}] > Tap adb : [x1 : {x1}, y1 : {y1}, x2 : {x2}, y2 : {y2}]')
            return True
        return False

    def long_press(self, x, y):
        """
        drag Using ADB cmd
        Args:
            x: x co-ordinate of display
            y: y co-ordinate of display
        Returns:
            bool : Successfully clicked or not
        """
        tap_cmd = f'adb shell input touchscreen swipe {x} {y} {x} {y} 8000'
        status = os.system(tap_cmd)
        if status == 0:
            print(f'[{self.test_case_name}] > Tap adb : [x : {x}, y : {y}]')
            return True
        return False

    def tap_using_ui_item(self, resource_id=None, item_text=None, timeout=15):
        """
        Tap on UI widget of ui automator
        Args:
            resource_id: the resource id of widget
            item_text: text of widget
            timeout: wait for element to appear

        Returns:
            bool : Successfully tap or not
        """
        status = False
        start_time = time.perf_counter()
        while True:
            element = None
            if resource_id is not None and item_text is None:
                element = Display.active_display_uiautomator(resourceId=resource_id)
            elif resource_id is None and item_text is not None:
                element = Display.active_display_uiautomator(text=item_text)
            elif resource_id is not None and item_text is not None:
                element = Display.active_display_uiautomator(resourceId=resource_id, text=item_text)
            if element is None:
                raise Exception('Provide resource id or text of element')
            time.sleep(2)
            if element.exists:
                status = element.click()
                break
            time.sleep(1)
            del element
            elapsed_time = time.perf_counter() - start_time
            if elapsed_time >= timeout:
                break
        print(
            f'[{self.test_case_name}] > Tap on UI item , Resource :{resource_id}, text : {item_text} ,Status : {status}')
        return status


class HelperException(Exception):
    def __init__(self, test_helper, msg):
        self.test_helper = test_helper
        self.msg = msg
        self.__capture_screenshot()
        self.__capture_logs()
        self.test_helper.ack_deleted_pop_up()
        self.__dump_ui_auto_xml()
        print(f'[{self.test_helper.test_case_name}] > Test case failed : {msg}')

    def __dump_ui_auto_xml(self):
        Display.active_display_uiautomator.dump(filename=f'{self.test_helper.logger.display_logs_path}/UI_hierarchy.xml', pretty=True)

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
                         'hrv': 'Croatian', 'ita': 'Italian', 'lat': 'Latvian', 'lit': 'Lithuanian', 'hun': 'Hungarians',
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

    def handle_pop_ups(self, name=None):
        """
        handle pop up
        """
        target_image_path = self.click_screenshot_display()
        image = cv2.imread(target_image_path)
        handle_pop_ups = DMConstants.POP_UP_LIST
        single = False
        if name is not None:
            name_data = DMConstants.POP_UP_LIST.get(name)
            if name_data is not None:
                handle_pop_ups[name] = name_data
                single = True

        for name, info in handle_pop_ups.items():
            template = cv2.imread(os.path.abspath(f'{DMConstants.REFERENCE_IMAGES}/PopUps/{info["path"]}'))
            if image.shape[0] >= template.shape[0] and image.shape[1] >= template.shape[1] and image.shape[2] >= \
                    template.shape[2]:
                result1 = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
                match = cv2.minMaxLoc(result1)[1]
                print(f'[{self.test_case_name}] > Handling pop-up : [{name}] , match [{match * 100}]')
                if match >= 0.98:
                    tap = info.get('tap')
                    text = info.get('text')
                    if tap:
                        self.common_functions.tap_adb(*tap.split(' '))
                    elif text:
                        self.common_functions.tap_using_ui_item(item_text=text)
                    if single:
                        return True
                    continue
        return False

    def click_screenshot_display(self, is_test_case_screenshot: bool = False, screenshot_name: str = 'screenshot',
                                 include_time: bool = False):
        """
        Click screenshot of display
        Returns:
            str : The path of screenshot captured
        """
        try:
            print(f'[{self.test_case_name}] > Capturing Screenshot')
            screenshot_name = screenshot_name.replace(' ', '_')
            if include_time:
                screenshot_name += datetime.now().strftime('_%d_%m_%y_%H_%M_%S')

            if not is_test_case_screenshot:
                if not os.path.isdir(DMConstants.TEMP_SCREENSHOT):
                    os.makedirs(DMConstants.TEMP_SCREENSHOT, exist_ok=True)
                screenshot_path = f'{DMConstants.TEMP_SCREENSHOT}/{screenshot_name}.png'
            else:
                if not os.path.isdir(DMConstants.TEST_CASE_SCREENSHOT + f'/{self.test_case_name}'):
                    os.makedirs(DMConstants.TEST_CASE_SCREENSHOT + f'/{self.test_case_name}', exist_ok=True)
                screenshot_path = f'{DMConstants.TEST_CASE_SCREENSHOT}/{self.test_case_name}/{screenshot_name}.png'

            if len(Display.displays) > 1:

                screen_capture = f'adb -s' + ' ' + Display.active_display + ' shell screencap -p /sdcard/screencap.png'
                screen_capture_pull = f'adb -s' + ' ' + Display.active_display + ' pull /sdcard/screencap.png "{screenshot_path}" > NUL'
                delete_screen_capture = 'adb -s' + ' ' + Display.active_display + ' shell rm /sdcard/screencap.png'
            else:
                screen_capture = f'adb shell screencap -p /sdcard/screencap.png'
                screen_capture_pull = f'adb pull /sdcard/screencap.png "{screenshot_path}" > NUL'
                delete_screen_capture = 'adb shell rm /sdcard/screencap.png'

            if os.system(screen_capture) != 0:
                raise Exception('Failed to capture screenshot')
            time.sleep(2)
            print(f'[{self.test_case_name}] > Saving Screenshot to local disk')
            if os.system(screen_capture_pull) != 0:
                raise Exception('Failed to pull screenshot')
            time.sleep(2)
            os.system(delete_screen_capture)
            time.sleep(1)
            return screenshot_path

        except Exception:
            raise Exception('Failed to capture Screenshot')

    def basic_waiting_timer(self, wait_time_sec=0, interval=16, custom_msg='Time Wait Remaining'):
        """

        Args:
            interval:
            wait_time_sec:
            custom_msg:

        Returns:

        """
        print(
            f'[{self.test_case_name}] > Custom timer wait, Waiting for [{wait_time_sec}] Sec')
        start_time = time.perf_counter()
        while True:
            time.sleep(interval)
            elapsed_time = time.perf_counter() - start_time
            if elapsed_time >= wait_time_sec:
                break
            remaining_time = wait_time_sec - elapsed_time
            print(
                f'[{self.test_case_name}] > {custom_msg} | Elapsed time : {elapsed_time} sec, Remaining time: {remaining_time}')
        return True

    # ---------------------------- Basic Helper Functions ----------------------------

    def image_comparison(self, reference, image=None, image_crop=None, threshold=0.98):
        """

        Args:
            image:
            reference:
            image_crop:
            threshold:

        Returns:

        """
        if image is None:
            image = self.click_screenshot_display()
        if image_crop is not None:
            image = self.crop_image(image, *image_crop)
        image = cv2.imread(image)
        template = cv2.imread(reference)
        if image.shape[0] >= template.shape[0] and image.shape[1] >= template.shape[1] and image.shape[2] >= \
                template.shape[2]:
            result1 = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
            match = cv2.minMaxLoc(result1)[1]
            if match >= threshold:
                print(f'[{self.test_case_name}] > Image Comparison , Match [{match}], Threshold [{threshold}]')
                return True
            else:
                print(f'[{self.test_case_name}] > Image Comparison , Match [{match}], Threshold [{threshold}]')
                return False
        raise Exception('Reference image size is small than Cropped image')

    def crop_image(self, image, left, top, width, height):
        """
            Crop image using latest screenshot
        Args:
            top (int) : The x co-ordinate of start
            left (int) : The y co-ordinate of start
            width (int) : The width of crop
            height (int) : The height of crop
        Returns:
            str : Cropped image path
        Examples:

        """
        screen_shot_path = os.path.abspath(image)
        img = Image.open(screen_shot_path)
        area = (left, top, width + left, height + top)
        cropped_img = img.crop(area)
        cropped_path = os.path.abspath(DMConstants.TEMP_SCREENSHOT + '/crop_image.png')
        cropped_img.save(cropped_path)
        return cropped_path

    def find_image_co_ordinates(self, reference_image, threshold=0.8, take_screenshot=True):
        """

        Args:
            threshold:
            reference_image:

        Returns:

        """
        first = True
        found = []
        print(f'[{self.test_case_name}] > Finding icon co-ordinates')
        screenshot_path = os.path.abspath(DMConstants.TEMP_SCREENSHOT + f'/screenshot.png')
        if take_screenshot:
            screenshot_path = self.click_screenshot_display()
        img_rgb = cv2.imread(screenshot_path)
        img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)
        template = cv2.imread(reference_image, 0)
        w, h = template.shape[::-1]
        adjust_center_w = w / 2
        adjust_center_h = h / 2
        print(f'[{self.test_case_name}] > Matching icon with screenshot')
        res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
        loc = numpy.where(res >= threshold)
        for pt in zip(*loc[::-1]):
            res = []
            x, y = pt
            if first:
                found.append((x, y))
                first = False
                continue

            for f in found:
                x1, y1 = f
                abs_diff_x = abs(x1 - x)
                abs_diff_y = abs(y1 - y)

                if abs_diff_x < 5 and abs_diff_y < 5:
                    res.append(True)
                else:
                    res.append(False)

            if not any(res):
                found.append((x, y))

        found = [(x + adjust_center_w, y + adjust_center_h) for x, y in found]
        print(f'[{self.test_case_name}] > Successfully completed icon co-ordinated finding')
        return found

    def click_image_icons(self, reference_image_name, is_common=False, click_index=None, long_press=False,
                          threshold=0.8, take_screenshot=True):
        """

        Args:
            take_screenshot:
            threshold:
            reference_image_name:
            is_common:
            click_index:
            long_press:

        Returns:

        """
        print(f'[{self.test_case_name}] > Clicking icon on display [{reference_image_name}]')
        reference_image = self.ref_image_directory + f'/{reference_image_name}.png'
        if not is_common:
            reference_image = self.ref_image_directory + f'/{self.test_case_name}/{reference_image_name}.png'
        co_ordinates = self.find_image_co_ordinates(reference_image, threshold, take_screenshot)
        print(f'[{self.test_case_name}] > Found Icons : {len(co_ordinates)}')
        if len(co_ordinates) == 0:
            return False
        if click_index is None:
            for x, y in co_ordinates:
                if long_press:
                    print(f'[{self.test_case_name}] > Long Press,  x : [{x} ], y : [{y}]')
                    os.system(f'adb shell input touchscreen swipe {x} {y} {x} {y} 8000')
                else:
                    self.common_functions.tap_adb(x, y)
        else:
            for idx in click_index:
                try:
                    x, y = co_ordinates[int(idx)]
                    print(f'[{self.test_case_name}] > Clicking icon index : [{idx}]')
                    if long_press:
                        print(f'[{self.test_case_name}] > Long Press,  x : [{x} ], y : [{y}]')
                        os.system(f'adb shell input touchscreen swipe {x} {y} {x} {y} 8000')
                    else:
                        self.common_functions.tap_adb(x, y)
                except:
                    raise Exception(f'Icon not found at index [{idx}]')

        return True

    def wait_to_appear(self, resource_id: str = None, item_text: str = None, timeout: int = 15):
        """
        Wait for element to appear on display
        Args:
            resource_id: The resource id of element
            item_text: Text of the element
            timeout: Wait to appear element on display

        Returns:
            bool : the status of element is visible or not
        """
        status = False
        start_time = time.perf_counter()
        while True:
            element_exist = None
            if resource_id is not None and item_text is None:
                element_exist = Display.active_display_uiautomator(resourceId=resource_id)
            elif resource_id is None and item_text is not None:
                element_exist = Display.active_display_uiautomator(text=item_text)
            elif resource_id is not None and item_text is not None:
                element_exist = Display.active_display_uiautomator(resourceId=resource_id, text=item_text)
            time.sleep(2)
            if element_exist is not None and element_exist.exists:
                status = True
                break
            time.sleep(3.5)
            del element_exist
            elapsed_time = time.perf_counter() - start_time
            remaining_time = timeout - elapsed_time
            print(
                f'[{self.test_case_name}] > Waiting for UI element...| Timeout in [{remaining_time} sec]')
            if elapsed_time >= timeout:
                break
        print(
            f'[{self.test_case_name}] > Element status, Found : {status},Text : {item_text}, Resource Id : {resource_id}')
        return status

    def click_settings(self):
        """
        Click on setting menu of display
        Returns:
            bool : Clicked or not
        """
        print(f'[{self.test_case_name}] > Clicking on settings')
        self.handle_pop_ups()
        time.sleep(2)
        CommonFunctions.tap_ui_auto(990, 45)
        if self.wait_to_appear(item_text='Menu'):
            print(f'[{self.test_case_name}] > Clicked on settings')
            return True
        else:
            print(f'[{self.test_case_name}] > Failed to clicked on settings')
        raise Exception('Click on setting icon failed')

    def set_active_user(self, username: str = None):
        """
        Long press for active user at RunScreen Layout
        Returns:
            username : name of the user to set
        """
        print(f'[{self.test_case_name}] > Setting of user profile from Run screen')
        print(f'[{self.test_case_name}] > Tapping on profile icon')
        self.common_functions.tap_adb(800, 45)
        find_button = self.wait_to_appear(resource_id="com.cnh.android.user:id/id_title", item_text='User Profile')
        if find_button:
            print(f'[{self.test_case_name}] > Switching user profile')
            self.common_functions.tap_using_ui_item(resource_id="com.cnh.android.user:id/id_button_switch_user",
                                                    item_text='Switch User')
            self.wait_to_appear(item_text='Select User')
            self.common_functions.tap_using_ui_item(resource_id="com.cnh.android.user:id/id_user_name",
                                                    item_text=username)
            self.wait_to_appear(item_text='Login | Confirm User')
            self.common_functions.tap_using_ui_item(resource_id="com.cnh.android.user:id/btFirst", item_text='Login')
            print(f'[{self.test_case_name}] > Logging in to profile: ', username)
            self.wait_to_appear(item_text='Engine Speed')
            print(f'[{self.test_case_name}] > Switched username profile to :', username)
        else:
            print(f'[{self.test_case_name}] > Failed to switch username profile to :', username)
        time.sleep(1)
        print(f'[{self.test_case_name}] > Long pressing on Run1 to enter Edit Mode.')
        self.common_functions.long_press(290, 775)
        time.sleep(5)
        self.common_functions.tap_adb(715, 490)
        time.sleep(2)
        print(f'[{self.test_case_name}] > Edit Mode: Clicked on Yes')
        ready = self.wait_to_appear(resource_id="com.cnh.android.screenmanager:id/layoutBtn")
        if ready:
            print(f'[{self.test_case_name}] > Tapping on screen-manager icon')
            self.common_functions.tap_adb(1143, 743)
            self.wait_to_appear(resource_id="com.cnh.android.screenmanager:id/udwEditName")
            self.common_functions.tap_using_ui_item(resource_id="com.cnh.android.screenmanager:id/udwEditName",
                                                    item_text='Steering Rate')
            time.sleep(1)
            self.common_functions.tap_using_ui_item(resource_id="com.cnh.android.screenmanager:id/doneBtn")
            print(f'[{self.test_case_name}] > Clicked on done and applying custom settings')
        else:
            print(f'[{self.test_case_name}] > Failed to apply custom settings')

    def verify_active_user(self, username: str = None):
        """
                Active user validation
                Returns:
                    username : verify name of the user already set
                """
        print(f'[{self.test_case_name}] > Verifying user profile from Run screen')
        print(f'[{self.test_case_name}] > Tapping on profile icon')
        self.common_functions.tap_adb(800, 45)
        popup_detect = self.wait_to_appear(resource_id="com.cnh.android.screenmanager:id/tvTitle",
                                           item_text='Closing Edit Screen Layout')
        if popup_detect:
            print(f'[{self.test_case_name}] > Closing Edit window popup detected, handling..... ')
            self.common_functions.tap_using_ui_item(resource_id="com.cnh.android.screenmanager:id/btFirst",
                                                    item_text="OK")
        time.sleep(5)
        find_button = self.wait_to_appear(resource_id="com.cnh.android.user:id/id_title", item_text='User Profile')
        if find_button:
            get = self.wait_to_appear(resource_id="com.cnh.android.user:id/id_user_name", item_text=username)
            if get:
                print(f'[{self.test_case_name}] > Username is set to: ', username)
                print(f'[{self.test_case_name}] > Active user validation is successful')
                self.common_functions.tap_using_ui_item(resource_id="com.cnh.android.user:id/id_button_close")
                return True
            else:
                self.click_screenshot_display()
                print(f'[{self.test_case_name}] > Username does not match')
        raise Exception('Failed to verify active user')

    def create_new_user_profile(self, username: str = None):
        """
        Active user setting
        Returns:
            username : Create new name of the user
        """
        print(f'[{self.test_case_name}] > Creating new user profile from Run screen')
        print(f'[{self.test_case_name}] > Tapping on profile icon')
        self.common_functions.tap_adb(800, 45)
        find_button = self.wait_to_appear(resource_id="com.cnh.android.user:id/id_title", item_text='User Profile')
        if find_button:
            self.common_functions.tap_adb(1115, 677)
            print(f'[{self.test_case_name}] > Clicked on User Management')
            time.sleep(5)
            create = self.wait_to_appear(resource_id='com.cnh.android.user:id/id_create_user',
                                         item_text='+ Create User')
            if create:
                self.common_functions.tap_using_ui_item(resource_id='com.cnh.android.user:id/id_create_user',
                                                        item_text='+ Create User')
                time.sleep(5)
                input = self.wait_to_appear(resource_id='com.cnh.android.user:id/id_user_name',
                                            item_text='Enter Username Here')
                if input:
                    text_feed = Display.active_display_uiautomator(resourceId="com.cnh.android.user:id/id_user_name")
                    text_feed.click()
                    text_feed.clear_text()
                    text_feed.set_text(username)
                    time.sleep(3)
                    self.common_functions.tap_adb(1130, 685)
                    time.sleep(5)
                    self.common_functions.tap_using_ui_item(resource_id='com.cnh.android.user:id/id_button_save',
                                                            item_text='Save')
                    print(f'[{self.test_case_name}] > New user: {username} is created successfully')
                    time.sleep(3)
                else:
                    print(f'[{self.test_case_name}] > Input Username tab is not found')
                print(f'[{self.test_case_name}] > Verifying New user created in list')
                get = self.wait_to_appear(resource_id='com.cnh.android.user:id/id_user_name', item_text=username)
                if get:
                    print(f'[{self.test_case_name}] > {username} thus created found in list')
                else:
                    print(f'[{self.test_case_name}] > {username} searching in list')
                    while (1):
                        self.common_functions.drag_screen(1205, 600, 1205, 400)
                        scroll_to_find = self.wait_to_appear(resource_id='com.cnh.android.user:id/id_user_name',
                                                             item_text=username)
                        if scroll_to_find:
                            print(f'[{self.test_case_name}] > {username} thus created found in list')
                            break
                        else:
                            continue
                self.common_functions.tap_using_ui_item(resource_id="com.cnh.android.user:id/id_button_close")
                time.sleep(2)
                return True
            else:
                self.click_screenshot_display()
                print(f'[{self.test_case_name}] > Username does not match')
        raise Exception('Failed to verify active user')

    def userprofile_naming_conflict(self, username: str = None, naming_conflict=None):
        """
        Active user naming conflict
        Returns:
            username : Re-Create new name of the user to verify conflict
        """
        print(f'[{self.test_case_name}] > Creating new user profile from Run screen')
        print(f'[{self.test_case_name}] > Tapping on profile icon')
        self.common_functions.tap_adb(800, 45)
        find_button = self.wait_to_appear(resource_id="com.cnh.android.user:id/id_title", item_text='User Profile')
        if find_button:
            self.common_functions.tap_adb(1115, 677)
            print(f'[{self.test_case_name}] > Clicked on User Management')
            time.sleep(5)
            create = self.wait_to_appear(resource_id='com.cnh.android.user:id/id_create_user',
                                         item_text='+ Create User')
            if create:
                self.common_functions.tap_using_ui_item(resource_id='com.cnh.android.user:id/id_create_user',
                                                        item_text='+ Create User')
                time.sleep(5)
                input = self.wait_to_appear(resource_id='com.cnh.android.user:id/id_user_name',
                                            item_text='Enter Username Here')
                if input:
                    text_feed = Display.active_display_uiautomator(resourceId="com.cnh.android.user:id/id_user_name")
                    text_feed.click()
                    text_feed.clear_text()
                    text_feed.set_text(username)
                    time.sleep(3)
                    self.common_functions.tap_adb(1130, 685)
                    time.sleep(5)
                    self.common_functions.tap_using_ui_item(resource_id='com.cnh.android.user:id/id_button_save',
                                                            item_text='Save')
                    status = self.image_comparison(reference=naming_conflict, threshold=0.95)
                    if status:
                        print(f'[{self.test_case_name}] > Username: {username} exist already..')
                    else:
                        raise Exception('User profile name conflict verification failed')
                    time.sleep(3)
                else:
                    print(f'[{self.test_case_name}] > Input user profile name failed.')
                self.common_functions.tap_using_ui_item(resource_id="com.cnh.android.user:id/id_button_close")
                time.sleep(2)
                return True
            else:
                self.click_screenshot_display()
        raise Exception('Failed to verify User Profile Naming conflict')

    def delete_existing_user_profile(self, username: str = None):
        """
        Active user validation
        Returns:
            username : verify name of the user already set
        """
        print(
            f'[{self.test_case_name}] > Attempting to set default user profile first before deleting {username} Profile.')
        self.set_active_user(username='Owner')
        time.sleep(5)
        print(f'[{self.test_case_name}] > Tapping on profile icon')
        self.common_functions.tap_adb(800, 45)
        find_button = self.wait_to_appear(resource_id="com.cnh.android.user:id/id_title", item_text='User Profile')
        if find_button:
            self.common_functions.tap_adb(1115, 677)
            print(f'[{self.test_case_name}] > Clicked on User Management')
            time.sleep(5)
            wait = self.wait_to_appear(resource_id='com.cnh.android.user:id/id_create_user',
                                       item_text='+ Create User')
            if wait:
                print(f'[{self.test_case_name}] > {username} searching in list')
                find = self.wait_to_appear(resource_id='com.cnh.android.user:id/id_user_name', item_text=username)
                if find:
                    Display.active_display_uiautomator(resourceId="com.cnh.android.user:id/id_user_list").child(
                        resourceId="com.cnh.android.user:id/id_user_name", text=username).sibling(
                        resourceId="com.cnh.android.user:id/id_user_options").child(
                        className="android.widget.FrameLayout", index=2).click()
                    self.wait_to_appear(resource_id='com.cnh.android.user:id/btFirst', item_text='Delete User')
                    self.common_functions.tap_using_ui_item(resource_id='com.cnh.android.user:id/btFirst',
                                                            item_text='Delete User')
                    print(f'[{self.test_case_name}] > {username} Profile is successfully deleted from list.')
                else:
                    while (1):
                        self.common_functions.drag_screen(1205, 600, 1205, 400)
                        scroll_to_find = self.wait_to_appear(resource_id='com.cnh.android.user:id/id_user_name',
                                                             item_text=username)
                        if scroll_to_find:
                            Display.active_display_uiautomator(resourceId="com.cnh.android.user:id/id_user_list").child(
                                resourceId="com.cnh.android.user:id/id_user_name", text=username).sibling(
                                resourceId="com.cnh.android.user:id/id_user_options").child(
                                className="android.widget.FrameLayout", index=2).click()
                            self.wait_to_appear(resource_id='com.cnh.android.user:id/btFirst', item_text='Delete User')
                            self.common_functions.tap_using_ui_item(resource_id='com.cnh.android.user:id/btFirst',
                                                                    item_text='Delete User')
                            print(f'[{self.test_case_name}] > {username} Profile is successfully deleted from list.')
                            break
                self.common_functions.tap_using_ui_item(resource_id="com.cnh.android.user:id/id_button_close")
                time.sleep(2)
                return True
            else:
                self.click_screenshot_display()
                print(f'[{self.test_case_name}] > Username does not match')
        raise Exception('Failed to verify active user')

    def click_goto_import(self):
        """
        Click on Go To Import menu of display
        Returns:
            bool : Clicked or not
        """
        print(f'[{self.test_case_name}] > Clicking on Go to Import')
        CommonFunctions.tap_ui_auto(898, 299)
        if self.wait_to_appear(item_text='Select All'):
            print(f'[{self.test_case_name}] > Clicked on Go to Import')
            return True
        else:
            print(f'[{self.test_case_name}] > Failed to click Go to Import')
        raise Exception('Click on Go to Import button failed')

    def click_operation_screen(self, timeout: int = 30):
        """
        Click on Home screen menu of display
        Returns:
            bool : Clicked or not
        """
        elapsed_time = 0
        start_time = time.time()
        print(f'[{self.test_case_name}] > Clicking on Home')
        self.common_functions.tap_adb(1089, 45)
        time.sleep(2)
        while not Display.active_display_uiautomator(text='Operations').exists and elapsed_time < timeout:
            elapsed_time = time.time() - start_time
            self.common_functions.tap_adb(1089, 45)
            time.sleep(.1)
            # time.sleep(1)
        if self.wait_to_appear(item_text='Operations'):
            print(f'[{self.test_case_name}] > Clicked on Home')
            return True
        else:
            print(f'[{self.test_case_name}] > Failed to clicked on Home')
        raise Exception('Click on Home icon failed')

    def click_on_data_card_bm(self, is_tree_appear_time: bool = False):
        """
        Click on data card menu of display
                is_tree_appear_time for bm time capture
        Returns:
            bool : Clicked or not
        """
        global data_launch_time, datacard_view, stop_dataview_time
        adb_process_delay = int(2)  # Agreed time for adb delay is 2 seconds.
        print(f'[{self.test_case_name}] > Clicking on Data Card Menu')
        status = self.common_functions.tap_using_ui_item(resource_id="com.cnh.android.cardmanager:id/card_title",
                                                         item_text="Data")
        start_appear_timer = time.time()
        if status:
            if self.wait_to_appear(item_text='Data | Data Management'):
                print(f'[{self.test_case_name}] > Datacard menu view confirmed.')
                stop_dataview_time = time.time()
            else:
                pass
            if self.wait_to_appear(resource_id='com.cnh.pf.android.data.management:id/tree_list_item_text',
                                   item_text='Grower/Farm/Field/Task'):
                print(f'[{self.test_case_name}] > Clicked on Data Card Menu')
                stop_appear_timer = time.time()
                if is_tree_appear_time:
                    Red = "\033[91m{}\033[00m"
                    datacard_view = stop_dataview_time - start_appear_timer - adb_process_delay
                    data_launch_time = stop_appear_timer - start_appear_timer - adb_process_delay
                    print(
                        (Red).format(f'[{self.test_case_name}] > DataCard view Launch Time: [{datacard_view} seconds]'))
                    print((Red).format(f'[{self.test_case_name}] > DataCard Launch Time: [{data_launch_time} seconds]'))
                    return data_launch_time, datacard_view, True
                return True
            else:
                print(f'[{self.test_case_name}] > Failed to clicked Data Card Menu')
        raise Exception('Failed to click card menu')

    def click_on_data_card(self):
        """
        Click on data card menu of display
        Returns:
            bool : Clicked or not
        """
        from DMAutomatedTest.DMTestSuite import Key_Cycle
        print(f'[{self.test_case_name}] > Clicking on Data Card Menu')
        self.wait_to_appear(resource_id="com.cnh.android.cardmanager:id/card_title", item_text="Data")
        status = self.common_functions.tap_using_ui_item(resource_id="com.cnh.android.cardmanager:id/card_title",
                                                         item_text="Data")
        time.sleep(2)
        self.click_menu_tab('Data Management')
        if status:
            check_GFFT = self.wait_to_appear(resource_id='com.cnh.pf.android.data.management:id/tree_list_item_text',
                                             item_text='Grower/Farm/Field/Task', timeout=60)
            if not check_GFFT:
                screenshot = self.click_screenshot_display(is_test_case_screenshot=True,
                                                           screenshot_name='error_in_Data_Management_screenshot')
                reference = os.path.abspath(DMConstants.REFERENCE_IMAGES + '/import_in_progress_error.png')
                reference1 = os.path.abspath(DMConstants.REFERENCE_IMAGES + '/spinner_error.png')
                import_in_progress_error = self.image_comparison(reference=reference, image=screenshot, threshold=0.9)
                spinner_error = self.image_comparison(reference=reference1, image=screenshot, threshold=0.75)
                print(import_in_progress_error, spinner_error)
                if import_in_progress_error:
                    print(
                        f'[{self.test_case_name}] > Due to Grower/Farm/Field/Task Not visible -> [import_in_progress_error observed] hence key cycling]')

                    print('[Power Cycle] : Commencing power sequence. Key_Cycling.......')
                    Key_Cycle.reboot()
                    print('[Display Down] : Wait for 2 mins to load display fully..')
                    time.sleep(120)
                    print('[Display Up] : Display loaded.')
                    time.sleep(2)
                    print('[POP-UP] : Handling pop-ups')
                    self.handle_pop_ups()
                    time.sleep(3)

                    self.click_settings()
                    print(
                        f'[{self.test_case_name}] > Due to Grower/Farm/Field/Task Not visible [import_in_progress_error observed] Data Card Going to Launch in Second attempt')

                    self.wait_to_appear(resource_id="com.cnh.android.cardmanager:id/card_title", item_text="Data")
                    status = self.common_functions.tap_using_ui_item(
                        resource_id="com.cnh.android.cardmanager:id/card_title", item_text="Data")
                    self.click_menu_tab('Data Management')
                    if self.wait_to_appear(resource_id='com.cnh.pf.android.data.management:id/tree_list_item_text',
                                           item_text='Grower/Farm/Field/Task', timeout=60):
                        Helper.prRed(
                            f'[{self.test_case_name}] > [import_in_progress_error observed] Hence [Key cycle] performed -> Data Crd Successfully Launched in Second attempt and Grower/Farm/Field/Task Appear')
                        # return True
                        # This Exception Because import_in_progress_error Senario is comes under Defect category.
                        raise Exception(
                            f'[import_in_progress_error observed] Hence [Key cycle] performed -> Data Crd Successfully Launched in Second attempt and Grower/Farm/Field/Task Appear')
                    else:
                        print(
                            f'[{self.test_case_name}] > [import_in_progress_error observed] Hence [Key cycle] performed -> Failed to clicked Data Card Menu-> Grower/Farm/Field/Task Not Appear')
                        raise Exception(
                            f'[import_in_progress_error observed] Hence [Key cycle] performed -> Failed to clicked Data Card Menu-> Grower/Farm/Field/Task Not Appear')
                elif spinner_error:
                    check_GFFT_status = self.wait_to_appear(
                        resource_id='com.cnh.pf.android.data.management:id/tree_list_item_text',
                        item_text='Grower/Farm/Field/Task', timeout=500)
                    if check_GFFT_status:
                        print("After Wait long time Grower/Farm/Field/Task Appear")
                        Helper.prGreen(
                            f'[{self.test_case_name}] > Data Crd Successfully Launched After Wait long time Grower/Farm/Field/Task Appear')
                        return True
                    else:
                        print(
                            f'[{self.test_case_name}] > Due to Grower/Farm/Field/Task Not visible [spinner_error observed] hence key cycling]')

                        print('[Power Cycle] : Commencing power sequence. Key_Cycling.......')
                        Key_Cycle.reboot()
                        print('[Display Down] : Wait for 2 mins to load display fully..')
                        time.sleep(120)
                        print('[Display Up] : Display loaded.')
                        time.sleep(2)
                        print('[POP-UP] : Handling pop-ups')
                        self.handle_pop_ups()
                        time.sleep(3)

                        self.click_settings()
                        print(
                            f'[{self.test_case_name}] > Due to Grower/Farm/Field/Task Not visible [spinner_error observed] Data Card Going to Launch in Second attempt')

                        self.wait_to_appear(resource_id="com.cnh.android.cardmanager:id/card_title", item_text="Data")
                        status = self.common_functions.tap_using_ui_item(
                            resource_id="com.cnh.android.cardmanager:id/card_title", item_text="Data")
                        self.click_menu_tab('Data Management')
                        if self.wait_to_appear(resource_id='com.cnh.pf.android.data.management:id/tree_list_item_text',
                                               item_text='Grower/Farm/Field/Task', timeout=60):
                            Helper.prRed(
                                f'[{self.test_case_name}] >[spinner_error observed] Hence [Key cycle] performed-> Data Crd Successfully Launched in Second attempt and Grower/Farm/Field/Task Appear')
                            # return True
                            # This Exception Because spinner_error Senario is comes under Defect category.
                            raise Exception(
                                f'[spinner_error observed] Hence [Key cycle] perform -> Data Crd Successfully Launched in Second attempt and Grower/Farm/Field/Task appear')
                        else:
                            print(
                                f'[{self.test_case_name}] > [spinner_error observed] Hence [Key cycle] performed -> Failed to clicked Data Card Menu -> and Grower/Farm/Field/Task Not Appear')
                            raise Exception(
                                f'[spinner_error observed] Hence [Key cycle] performed -> Failed to clicked Data Card Menu -> and Grower/Farm/Field/Task Not Appear')
                else:
                    self.close_data_screen()
                    print(
                        f'[{self.test_case_name}] > Due to Grower/Farm/Field/Task Not visible Data Crd Close and Launch in Second attempt')
                    self.wait_to_appear(resource_id="com.cnh.android.cardmanager:id/card_title", item_text="Data")
                    self.common_functions.tap_using_ui_item(resource_id="com.cnh.android.cardmanager:id/card_title",
                                                            item_text="Data")
                    self.click_menu_tab('Data Management')
                    if self.wait_to_appear(resource_id='com.cnh.pf.android.data.management:id/tree_list_item_text',
                                           item_text='Grower/Farm/Field/Task', timeout=60):
                        Helper.prGreen(f'[{self.test_case_name}] > Data Crd Successfully Launched in Second attempt')
                        return True
                    else:
                        print(f'[{self.test_case_name}] > Failed to clicked Data Card Menu in Second attempt')
                        raise Exception('Failed to clicked Data Card Menu in Second attempt')
            else:
                print(f'[{self.test_case_name}] > Successfully Clicked on Data Card Menu')
                return True
        else:
            Helper.prRed(f'[{self.test_case_name}] > Failed to Load Data Card')
            raise Exception('Failed to clicked Data Card')

    def click_menu_tab(self, tab_name: str):
        """
        Click on data card menus
        Args:
            tab_name: The menu name of data card
        Returns:
            bool : Clicked or not
        """
        print(f'[{self.test_case_name}] > Clicking on tab Menu ({tab_name}) ')
        tab_details_co_ordinates = {
            'Data Management': (1200, 200),
            'Inbox': (1200, 300),
            'Import': (1200, 400),
            'Export': (1200, 500),
            'Product Library': (1200, 600),
            'Crop Type Filter': (1200, 700),
        }
        if tab_name == 'Data Management':
            Display.active_display_uiautomator.swipe(1200, 180, 1200, 670)
        elif tab_name == 'Crop Type Filter':
            Display.active_display_uiautomator.swipe(1200, 670, 1200, 180)
            tab_details_co_ordinates = {
                'Inbox': (1200, 200),
                'Import': (1200, 300),
                'Export': (1200, 400),
                'Product Library': (1200, 500),
                'Crop Type Filter': (1200, 600),
            }
        tab_status = self.common_functions.tap_adb(*tab_details_co_ordinates[tab_name])
        time.sleep(0.5)
        view_status = self.wait_to_appear(item_text=f'Data | {tab_name}')
        if tab_status or view_status:
            print(f'[{self.test_case_name}] > Successfully clicked on tab Menu ({tab_name}) ')
            return True
        raise Exception(f'Failed clicked on tab Menu ({tab_name})')

    def close_data_screen(self):
        """
        Close data screen
        Returns:
            None
        """
        print(f'[{self.test_case_name}] > Closing Data management')
        self.common_functions.tap_using_ui_item(resource_id='com.cnh.pf.android.data.management:id/tab_activity_close')

    def close_implement_screen(self):
        """
        Close implement screen
        Returns:
            None
        """
        print(f'[{self.test_case_name}] > Closing Implement Screen')
        self.common_functions.tap_using_ui_item(resource_id="com.cnh.pf.phoenixapp:id/tab_activity_close")

    def close_setting_screen(self):
        """
        Close setting screen
        Returns:
            None
        """
        print(f'[{self.test_case_name}] > Closing Setting menu')
        self.common_functions.tap_using_ui_item(resource_id='com.cnh.android.cardmanager:id/card_close_button')

    def close_operation_screen(self):
        """
        Close home screen
        Returns:
            None
        """
        print(f'[{self.test_case_name}] > Closing Menu screen')
        self.common_functions.tap_using_ui_item(resource_id="com.cnh.pf.phoenixapp:id/home_screen_close_btn")

    def go_back_to_menu(self):
        """
        Click on back menu
        Returns:
            None
        """
        print(f'[{self.test_case_name}] > Clicking back to Menu')
        self.common_functions.tap_using_ui_item(item_text='Menu')

    def select_data_tree(self, timeout: int = 90):
        """
        Select DM data tree from Data Management Menu
        Args:
            timeout: wait for deletion
        Returns:
            bool : Successfully Selected or not
        """
        self.wait_to_appear(item_text='Grower/Farm/Field/Task')
        if Display.active_display_uiautomator(resourceId="com.cnh.pf.android.data.management:id/tree_list_item_text").count == 0:
            print(f'[{self.test_case_name}] > Nothing is there in DM Tree to Select')
            return True
        items_tree = ['Grower/Farm/Field/Task', 'Crop and Product Library']
        print(f'[{self.test_case_name}] > Deleting DM Tree from Data Management Tab')
        for item in items_tree:
            try:
                Display.active_display_uiautomator(resourceId="com.cnh.pf.android.data.management:id/tree_view_list").child_by_text(
                    item,
                    allow_scroll_search=True,
                    resourceId="com.cnh.pf.android.data.management:id/tree_list_item_text")
                self.common_functions.tap_using_ui_item(item_text=item)
            except:
                pass

    def delete_data_tree(self, timeout: int = 700, is_delete_timer: bool = False):
        """
        Delete DM data tree from Data Management Menu
        Args:
            timeout: wait for deletion

        Returns:
            bool : Successfully deleted or not
            :param is_delete_timer:
        """
        global delete_time
        delete_time = float(0)
        Red = "\033[91m{}\033[00m"
        self.wait_to_appear(item_text='Grower/Farm/Field/Task')
        if Display.active_display_uiautomator(resourceId="com.cnh.pf.android.data.management:id/tree_list_item_text").count == 0:
            print(f'[{self.test_case_name}] > Nothing is there in DM Tree to Delete')
            return True

        items_tree = ['Grower/Farm/Field/Task', 'Crop and Product Library']
        print(f'[{self.test_case_name}] > Deleting DM Tree from Data Management Tab')
        for item in items_tree:
            try:
                Display.active_display_uiautomator(resourceId="com.cnh.pf.android.data.management:id/tree_view_list").child_by_text(
                    item,
                    allow_scroll_search=True,
                    resourceId="com.cnh.pf.android.data.management:id/tree_list_item_text")
                self.common_functions.tap_using_ui_item(item_text=item)
            except:
                pass

        status_2 = self.common_functions.tap_using_ui_item(
            resource_id='com.cnh.pf.android.data.management:id/dm_delete_button')
        status_3 = self.common_functions.tap_using_ui_item(resource_id='com.cnh.pf.android.data.management:id/btFirst',
                                                           item_text='Delete')
        if not all([status_2, status_3]):
            raise Exception('Data tree deletion failed from Data management Tab')
        # print(f'[{self.test_case_name}] > Waiting to detect change implement warning..!')
        # time.sleep(3)
        # change_implement_status = self.wait_to_appear(resource_id="com.cnh.android.tractor:id/btFirst",
        #                                               item_text="Continue", timeout=10)
        # if change_implement_status:
        #     self.common_functions.tap_using_ui_item(resource_id="com.cnh.android.tractor:id/btFirst",
        #                                             item_text="Continue")
        # else:
        #     pass
        start_deletion_timer = time.time()
        delete_status = self.wait_to_appear(resource_id='com.cnh.pf.android.data.management:id/header_text',
                                            item_text='Select item(s) to edit, copy, or delete', timeout=timeout)
        stop_deletion_timer = time.time()
        if is_delete_timer:
            delete_time = stop_deletion_timer - start_deletion_timer
            print((Red).format(f'[{self.test_case_name}] > Delete Time: [{delete_time} seconds]'))
            return True
        ack_status = self.ack_deleted_pop_up()
        self.handle_pop_ups()
        if delete_status or ack_status:
            return delete_time, True
        raise Exception('Data tree deletion failed from Data management Tab')

    def delete_data_tree_implement(self, timeout: int = 700, is_delete_timer: bool = False):
        """
        Delete DM data tree from Data Management Menu
        Args:
            timeout: wait for deletion

        Returns:
            bool : Successfully deleted or not
            :param is_delete_timer:
        """
        global delete_time
        delete_time = float(0)
        Red = "\033[91m{}\033[00m"
        self.wait_to_appear(item_text='Grower/Farm/Field/Task')
        if Display.active_display_uiautomator(resourceId="com.cnh.pf.android.data.management:id/tree_list_item_text").count == 0:
            print(f'[{self.test_case_name}] > Nothing is there in DM Tree to Delete')
            return True

        items_tree = ['Grower/Farm/Field/Task', 'Crop and Product Library', 'Implements']
        print(f'[{self.test_case_name}] > Deleting DM Tree from Data Management Tab')
        for item in items_tree:
            try:
                Display.active_display_uiautomator(resourceId="com.cnh.pf.android.data.management:id/tree_view_list").child_by_text(
                    item,
                    allow_scroll_search=True,
                    resourceId="com.cnh.pf.android.data.management:id/tree_list_item_text")
                self.common_functions.tap_using_ui_item(item_text=item)
            except:
                pass

        status_2 = self.common_functions.tap_using_ui_item(
            resource_id='com.cnh.pf.android.data.management:id/dm_delete_button')
        status_3 = self.common_functions.tap_using_ui_item(resource_id='com.cnh.pf.android.data.management:id/btFirst',
                                                           item_text='Delete')
        if not all([status_2, status_3]):
            raise Exception('Data tree deletion failed from Data management Tab')
        print(f'[{self.test_case_name}] > Waiting to detect change implement warning..!')
        time.sleep(3)
        change_implement_status = self.wait_to_appear(resource_id="com.cnh.android.tractor:id/btFirst",
                                                      item_text="Continue", timeout=10)
        if change_implement_status:
            self.common_functions.tap_using_ui_item(resource_id="com.cnh.android.tractor:id/btFirst",
                                                    item_text="Continue")
        else:
            pass
        start_deletion_timer = time.time()
        delete_status = self.wait_to_appear(resource_id='com.cnh.pf.android.data.management:id/header_text',
                                            item_text='Select item(s) to edit, copy, or delete', timeout=timeout)
        stop_deletion_timer = time.time()
        if is_delete_timer:
            delete_time = stop_deletion_timer - start_deletion_timer
            print((Red).format(f'[{self.test_case_name}] > Delete Time: [{delete_time} seconds]'))
            return True
        ack_status = self.ack_deleted_pop_up()
        self.handle_pop_ups()
        if delete_status or ack_status:
            return delete_time, True
        raise Exception('Data tree deletion failed from Data management Tab')

    def ack_deleted_pop_up(self):
        """
        Acknowledge pop up after deleting DM tree
        Returns:
            bool : status of acknowledge
        """
        time.sleep(2)
        screenshot_path = self.click_screenshot_display()
        sc_image = Image.open(screenshot_path)

        reference_image_path = DMConstants.REFERENCE_IMAGES + '/pop_up_deleted.png'
        reference_image = Image.open(reference_image_path)
        w, h = reference_image.size
        crop_co_ordinates = (787, 87, w + 787, h + 87)
        cropped_img = sc_image.crop(crop_co_ordinates)
        cropped_image_path = DMConstants.TEMP_SCREENSHOT + '/cropped.png'
        cropped_img.save(cropped_image_path)

        print(f'[{self.test_case_name}] > Verifying Pop-up')
        cropped_match = cv2.imread(cropped_image_path)
        reference_match = cv2.imread(reference_image_path)
        res = cv2.matchTemplate(cropped_match, reference_match, cv2.TM_CCOEFF_NORMED)
        threshold = 0.8
        loc = numpy.where(res >= threshold)
        if loc[0].size > 0:
            print(f'[{self.test_case_name}] > Pop Up found')
            status = self.common_functions.tap_adb(1190, 344)
            time.sleep(1)
            if status:
                print(f'[{self.test_case_name}] > Pop up successfully acknowledged')
                return True
        else:
            print(f'[{self.test_case_name}] > Pop up not found : th {loc[0].size}')
            return False

    def change_run_screen(self, screen: int):
        """

        Args:
            screen:

        Returns:

        """
        max_runs = 7
        start_x = 320
        start_y = 760
        difference = 95
        run_screen = [(0, 0), (start_x, start_y)]
        for run in range(1, max_runs):
            start_x += difference
            run_screen.append((start_x, start_y))
        status = self.common_functions.tap_adb(run_screen[screen][0], run_screen[screen][1])
        if status:
            print(f'[{self.test_case_name}] > Run screen selected : [Run {screen}]')
            return True
        raise Exception(f'Failed to change run screen [Run {screen}]')

    def collapse_dmtree_items(self, item: str = None):
        """

        Args:
            item : pass the name of the tree item.
        Returns:

        """
        tab = self.wait_to_appear(item_text='Data | Data Management')
        if not tab:
            print(f'[{self.test_case_name}] > navigating to DM tab')
            self.click_menu_tab('Data Management')
        else:
            pass
        print(f'[{self.test_case_name}] > Collapsing DM tree items')
        while 1:
            find = self.wait_to_appear(item_text=item)
            if not find:
                os.system('adb shell input swipe 700 400 700 600')
            else:
                break
        item_found = Display.active_display_uiautomator(text=item)
        expand_icon = item_found.left(
            resourceId='com.cnh.pf.android.data.management:id/treeview_list_item_toggle')
        expand_icon.click()
        print(f'[{self.test_case_name}] > DM tree collapsed')

    def image_feature_comparison(self, show: bool = True, IMG1=None, IMG2=None, thresh=int()):
        """
                Args:
                    thresh : image paths and threshold in int().
                Returns:
                    bool: True/False
                """
        img1 = cv2.imread(IMG1, 0)
        img2 = cv2.imread(IMG2, 0)
        screen_res = 600, 400
        orb = cv2.ORB_create(nfeatures=1000)
        kp1, des1 = orb.detectAndCompute(img1, None)
        kp2, des2 = orb.detectAndCompute(img2, None)
        brute_force = cv2.BFMatcher()
        matches = brute_force.knnMatch(des1, des2, k=2)
        good_match = []
        bad_match = []
        for m, n in matches:
            if m.distance < 0.75 * n.distance:  # 75% match is acceptable
                good_match.append([m])
            if m.distance > 0.75 * n.distance:
                bad_match.append([n])
        img3 = cv2.drawMatchesKnn(img1, kp1, img2, kp2, good_match, None, flags=2)
        total_matches = len(good_match) + len(bad_match)
        percentage = (len(good_match) / total_matches) * 100
        round(percentage)
        if show:
            scale_width = screen_res[0] / img1.shape[1]
            scale_height = screen_res[1] / img1.shape[0]
            scale = min(scale_width, scale_height)
            window_width_2 = int(img3.shape[1] * scale)
            window_height_2 = int(img3.shape[0] * scale)
            cv2.namedWindow('Image Analytics', cv2.WINDOW_NORMAL)
            cv2.resizeWindow('Image Analytics', window_width_2, window_height_2)
            cv2.imshow('Image Analytics', img3)
            cv2.waitKey(2000)
        if percentage >= thresh:
            return True
        else:
            return False

    # ---------------------------- Import Functionality ----------------------------
    def get_vehicle_name(self):
        from pathlib import Path
        root = Path(__file__).parent.parent.parent
        root = str(root)
        a = os.path.abspath(root + f'/main_config.ini')
        from configparser import ConfigParser
        configure = ConfigParser()
        configure.read(a)
        veh = configure.get('Test info', 'sel_vehicle')
        print("Vehicle In Use : ", veh)
        return veh

    def verify_vehicle_name(self, name=None):
        print(f'[{self.test_case_name}] > Fetching vehicle model name....')
        get = self.wait_to_appear(resource_id="com.cnh.android.cardmanager:id/fivecards_pos1")
        if get:
            vehicle = Display.active_display_uiautomator(resourceId="com.cnh.android.cardmanager:id/fivecards_pos1").child(
                            resourceId="com.cnh.android.cardmanager:id/card_title", index="3").__getattr__('text')

            brand = Display.active_display_uiautomator(resourceId="com.cnh.android.cardmanager:id/fivecards_pos1").child(
                            resourceId="com.cnh.android.cardmanager:id/card_description", index="4").__getattr__('text')
            if brand == name:
                print(f'[{self.test_case_name}] > Current Vehicle is {vehicle} with brand {brand} ... [Matched]')
            else:
                raise Exception(f' > Current vehicle {vehicle} with different brand name. [Not Matched]')
        else:
            raise Exception('Vehicle details tab is not available on screen.')

    def push_data_to_display(self, import_folder: str = None, is_multiple: bool = False):
        """
        Push Data to display tmp folder
        Args:
            import_folder: folder containing TASKDATA.XML to import in display
            is_multiple: import more files other than TASKDATA.XML

        Returns:
            bool : Successfully completed or not
        """
        try:
            print(f'[{self.test_case_name}] > Pushing TaskData to Display')
            import_directory = self.import_directory
            if import_folder is not None:
                import_directory = os.path.abspath(import_folder)

            print(f'[{self.test_case_name}] > Removing XML from display')
            os.system('adb -s' + ' ' + Display.active_display + ' shell su -c rm -rf /tmp/datamanagement')
            os.system('adb -s' + ' ' + Display.active_display + ' shell mkdir /tmp/datamanagement')
            os.system('adb -s' + ' ' + Display.active_display + ' shell su -c chmod -R 0777 /tmp/datamanagement')
            os.system('adb -s' + ' ' + Display.active_display + ' shell mkdir /tmp/datamanagement/TASKDATA')

            print(f'[{self.test_case_name}] > Pushing data to TASKDATA')
            if import_folder is not None:
                # push_cmd = f'adb push "{import_directory}/." "/tmp/datamanagement/TASKDATA/" > NUL'
                push_cmd = 'adb -s' + ' ' + Display.active_display + f' push "{import_directory}/." "/tmp/datamanagement/TASKDATA/" > NUL'

            else:
                push_cmd = 'adb -s' + ' ' + Display.active_display + f' push "{import_directory}/{self.test_case_name}/TASKDATA.XML" "/tmp/datamanagement/TASKDATA/" > NUL'
                if is_multiple:
                    push_cmd = 'adb -s' + ' ' + Display.active_display + f' push "{import_directory}/{self.test_case_name}/." "/tmp/datamanagement/TASKDATA/" > NUL'
            status = os.system(push_cmd)
            if status != 0:
                raise Exception('Pushing data into display Failed , Check Import File path')
            else:
                print(f'[{self.test_case_name}] > Successfully pushed data to TASKDATA')
                return True
        except Exception as E:
            raise Exception(f'Push data to Display Failed : {str(E)}')

    def import_xml_validate(self, tree_item: Union[List[str], str] = 'Grower/Farm/Field/Task', handle_pop_ups=True,
                            tree_load_timeout=150, source='USB', is_kpi_timer: bool = False):
        """
        Import and validate XMl tree items
        Args:
            tree_item: Item to validate

        Returns:
            bool : Validation status
            :param is_kpi_timer:
        """
        global discovery_time
        print(f'[{self.test_case_name}] > Importing TASKDATA into display')
        status = self.common_functions.tap_using_ui_item(item_text='Select Import Source')
        if status:
            print(f'[{self.test_case_name}] > Selecting Import Source')
            status = self.common_functions.tap_using_ui_item(
                resource_id='com.cnh.pf.android.data.management:id/tree_list_item_simple', item_text=source)
            if status:
                print(f'[{self.test_case_name}] > Import source selected as ', source)
                if source == "Cloud":
                    status = self.common_functions.tap_adb(640, 440)
                else:
                    status = self.common_functions.tap_using_ui_item(
                        resource_id='com.cnh.pf.android.data.management:id/tree_list_item_simple', item_text='TASKDATA')
                if status:
                    print(f'[{self.test_case_name}] > TASKDATA is selected')
                    status = self.common_functions.tap_using_ui_item(
                        resource_id='com.cnh.pf.android.data.management:id/btFirst', item_text='Select')
                    if status:
                        print(f'[{self.test_case_name}] > TASKDATA is importing')
                        start_import_time = time.time()
                        status = self.wait_to_appear(
                            resource_id="com.cnh.pf.android.data.management:id/tree_list_item_simple",
                            item_text=tree_item, timeout=tree_load_timeout)
                        stop_import_time = time.time()
                        if status:
                            if handle_pop_ups: self.handle_pop_ups()
                            if is_kpi_timer:
                                discovery_time = stop_import_time - start_import_time
                                Red = "\033[91m{}\033[00m"
                                print((Red).format(
                                    f'[{self.test_case_name}] > Discovery Time : [{discovery_time} seconds]'))
                                print(f'[{self.test_case_name}] > TASKDATA is Successfully imported')
                                return True
                            print(f'[{self.test_case_name}] > TASKDATA is Successfully imported')
                            return True
                        else:
                            print(f'[{self.test_case_name}] > TASKDATA import operation is Failed')
                            return False
                    else:
                        raise Exception('Import Operation Failed .. TASKDATA Select Operation Failed')
                else:
                    raise Exception('Import Operation Failed .. TASKDATA not found')
            else:
                raise Exception('Import Operation Failed .. ' + source + ' not found')
        else:
            raise Exception('Import source button not available')

    def conflict_resolver(self, conflict_resolver_config: List[dict] = None):
        """
        Resolve Import conflict dialogue box
        Args:
            conflict_resolver_config: List of dict containing conflict items details in sequence ( check example)

        Returns:
            bool : status of resolver
        Examples:
            T = {'Name': 'Grower1', 'Operation': 'Cancel', 'verify_text': 'A Grower "Grower1" already exists'}
            T_1 = [T]
        """

        if isinstance(conflict_resolver_config, dict):
            conflict_resolver_config = [conflict_resolver_config]
        if self.wait_to_appear(resource_id=DMConstants.CONFLICT_BOX_RESOURCE_ID,
                               item_text=DMConstants.CONFLICT_BOX_TEXT, timeout=30):
            print(f'[{self.test_case_name}] > Conflict Found while importing TASKDATA')
            if conflict_resolver_config is not None and conflict_resolver_config != []:
                print(f'[{self.test_case_name}] > Conflict Resolving using Config order')
                for item in conflict_resolver_config:
                    verify_item = item.get('Name')
                    operation = item.get('Operation')
                    verify_text = item.get('verify_text')
                    select_all = item.get('Select all')

                    if verify_text is not None and not Display.active_display_uiautomator(text=verify_text).exists:
                        if Display.active_display_uiautomator(text='Cancel').exists:
                            self.common_functions.tap_using_ui_item(item_text='Cancel', timeout=4)
                            self.common_functions.tap_using_ui_item(item_text='Yes', timeout=4)
                        raise Exception(f'Expected Conflict : {verify_item} not Found')
                    else:
                        if operation != 'Cancel':
                            if select_all is not None and select_all:
                                Display.active_display_uiautomator(
                                    resourceId='com.cnh.pf.android.data.management:id/import_conflict_dialog_reuse_action_checkbox').click()
                            operation_widget = Display.active_display_uiautomator(text=operation, className='android.widget.Button')
                            time.sleep(1)
                            if operation_widget.exists:
                                status = operation_widget.click()
                                if status:
                                    print(
                                        f'[{self.test_case_name}] > Conflict resolved for {verify_item} with operation {operation}')
                                    time.sleep(1)
                                    continue
                            else:
                                print(
                                    f'[{self.test_case_name}] > Failed to resolved conflict for {verify_item} with operation {operation}')
                                if Display.active_display_uiautomator(text='Cancel').exists:
                                    self.common_functions.tap_using_ui_item(item_text='Cancel', timeout=4)
                                    self.common_functions.tap_using_ui_item(item_text='Yes', timeout=4)
                                raise Exception('All conflict not resolved')
                        else:
                            self.common_functions.tap_using_ui_item(item_text='Cancel')
                            self.common_functions.tap_using_ui_item(item_text='Yes')
                            break
                return True
            else:
                print(f'[{self.test_case_name}] > Conflict Resolving using common order')
                conflict_resolved = []
                while Display.active_display_uiautomator(text=DMConstants.CONFLICT_BOX_TEXT).exists:
                    order = {'Merge': "Merge", 'Skip': "Skip", 'Replace': "Replace",
                             'Keep Both': "Keep_Both"}
                    Display.active_display_uiautomator(
                        resourceId='com.cnh.pf.android.data.management:id/import_conflict_dialog_reuse_action_checkbox').click()
                    conflict_iter = False
                    self.click_screenshot_display()
                    for action, ref_image in order.items():
                        status = self.click_image_icons(reference_image_name=ref_image, take_screenshot=False)
                        if status:
                            conflict_iter = True
                            break
                        else:
                            conflict_iter = False
                    conflict_resolved.append(conflict_iter)
                    if not conflict_iter:
                        raise Exception('Failed to resolved conflict')
                if all(conflict_resolved):
                    return True
                return False
        else:
            print(f'[{self.test_case_name}] > Conflict Not Found while importing TASKDATA')
            return True

    def import_select_import_tree_items(self, tree_items: Union[List[str], str] = None,
                                        conflict_resolver: List[dict] = None, verify_item: str = None,
                                        timeout: int = 150, is_timer_required: bool = False, navigate_away=False):
        """
        Select import tree items and import data
        Args:
            tree_items: Select tree items from import screen
            conflict_resolver: The list of dict of conflict items details
            timeout: timeout for import xml
            verify_item: verify item for post import check
        Returns:
            bool : Status of import operation
            :param is_timer_required:
        """
        global actual_import_time_taken
        status = False
        if tree_items is None:
            status = self.common_functions.tap_using_ui_item(item_text='Select All')
            print(f'[{self.test_case_name}] > All tree items Selected')
        else:
            for item in tree_items:
                if '>>' in item:
                    status = self.import_selected_items(item)
                else:
                    status = self.common_functions.tap_using_ui_item(item_text=item)
                print(f'[{self.test_case_name}] > Tree item : {item} Selected')
        if status:
            time.sleep(2)
            import_selected = Display.active_display_uiautomator(resourceId="com.cnh.pf.android.data.management:id/import_selected_btn")
            if import_selected.exists:
                import_selected.click()
                time.sleep(5)
                if navigate_away:
                    print(f'[{self.test_case_name}] > Navigating away from Import screen')
                    self.click_settings()
                    self.click_on_data_card()
                    self.click_menu_tab("Import")
                    print(f'[{self.test_case_name}] > Returned back to Import screen')
                if conflict_resolver is not None:
                    status = self.conflict_resolver(conflict_resolver)
                if conflict_resolver is None or (conflict_resolver is not None and status):
                    start_time = time.perf_counter()
                    start_import_timer = time.time()
                    while True:
                        if Display.active_display_uiautomator(text="Select Import Source").info['enabled']:
                            status = self.wait_to_appear(item_text=verify_item)
                            stop_import_operation_timer = time.time()
                            self.handle_pop_ups()
                            if status:
                                actual_import_time_taken = stop_import_operation_timer - start_import_timer
                                if is_timer_required:
                                    Red = "\033[91m{}\033[00m"
                                    print((Red).format(
                                        f'[{self.test_case_name}] > Import Time : [{actual_import_time_taken} seconds]'))
                                    print(f'[{self.test_case_name}] > Import Completed with benchmark time')
                                    return True
                                print(f'[{self.test_case_name}] > Import Completed')
                                return True
                            print(f'[{self.test_case_name}] > Import Failed during XML processing ..')
                            return False
                        elapsed_time = time.perf_counter() - start_time
                        remaining_time = timeout - elapsed_time
                        print(
                            f'[{self.test_case_name}] > Import in progress..Please wait..| Timeout in [{remaining_time} sec]')
                        time.sleep(3)
                        if elapsed_time >= timeout:
                            print(f'[{self.test_case_name}] > Import Timeout.. Cancelling import.')
                            self.common_functions.tap_using_ui_item(item_text="Cancel")
                            time.sleep(5)
                            self.common_functions.tap_using_ui_item(item_text="Yes")
                            break
                    raise Exception('Import failed after timeout')
        raise Exception('Import Operation failed after timeout')

    def import_xml_into_display(self, import_tree: Union[str, list] = None, conflict_resolvers: List[dict] = None,
                                is_error: bool = False, import_timeout=500, tree_load_timeout=250, import_source='USB',
                                is_timer_required: bool = False, is_kpi_timer: bool = False, tree: str = None,
                                navigate_away: bool = False):
        """
        Import XML into display ( Check for import failure is handles)
        Args:
            tree_load_timeout: timeout for loading taskdata
            import_timeout: timeout for this operation
            import_tree: Select tree items from import tree
            conflict_resolvers: List of dict containing conflict items details
            is_error: Check for import failure

        Returns:
            bool : Status of import operation
        """
        if tree == None:
            verify_item = 'Grower/Farm/Field/Task'
        else:
            verify_item = tree
        if isinstance(import_tree, str):
            verify_item = import_tree
            if '>>' in import_tree:
                verify_item = import_tree.split('>>')[0]
            import_tree = [import_tree]
        elif isinstance(import_tree, list):
            if '>>' in import_tree[0]:
                verify_item = import_tree[0].split('>>')[0]

        status = self.import_xml_validate(tree_item=verify_item, tree_load_timeout=tree_load_timeout,
                                          source=import_source, is_kpi_timer=is_kpi_timer)
        if status:
            status = self.import_select_import_tree_items(tree_items=import_tree, conflict_resolver=conflict_resolvers,
                                                          verify_item=verify_item, timeout=import_timeout,
                                                          is_timer_required=is_timer_required,
                                                          navigate_away=navigate_away)

            if status and not is_error:
                return True
        if is_error and not status:
            return True
        if is_error:
            raise Exception('TASKDATA XML imported into display')
        else:
            print(f'[{self.test_case_name}] > Import failed')
            raise Exception('Import Operation failed')

    def import_xml_from_display_with_uncheck_items(self, import_tree: Union[str, list] = None, uncheck_items=None,
                                                   conflict_resolver: List[dict] = None, is_error: bool = False,
                                                   timeout: int = 500):
        """
        Import xml with excluding some items
        Args:
            timeout:
            uncheck_items
            import_tree:
            is_error:
            conflict_resolver:
        Returns:
            bool : status of export operation
        """
        verify_item = 'Grower/Farm/Field/Task'
        if isinstance(import_tree, str):
            verify_item = import_tree
            import_tree = [import_tree]
        elif isinstance(import_tree, list):
            verify_item = import_tree[0]

        status = self.import_xml_validate(tree_item=verify_item)
        if status:
            status = self.import_select_uncheck_items(uncheck_items=uncheck_items, conflict_resolver=conflict_resolver,
                                                      verify_item=verify_item, timeout=timeout)
            if status and not is_error:
                return True
        if is_error and not status:
            return True
        if is_error:
            raise Exception('TASKDATA XML imported into display')
        else:
            print(f'[{self.test_case_name}] > Import failed')
            raise Exception('Import Operation failed')

    def import_select_uncheck_items(self, uncheck_items: Union[str, list] = None, verify_item: str = None,
                                    conflict_resolver: List[dict] = None, timeout: int = 150):
        """
        Uncheck items from export tree
        Args:
            timeout:
            conflict_resolver:
            verify_item:
            uncheck_items: Items to uncheck

        Returns:
            bool : Status of operation

        """
        status_item = []
        status = self.common_functions.tap_using_ui_item(item_text='Select All')
        Display.active_display_uiautomator(resourceId="com.cnh.pf.android.data.management:id/tree_view_list").child(
            className="android.widget.LinearLayout", index="0").child(
            resourceId="com.cnh.pf.android.data.management:id/treeview_list_item_frame_layout", index="0").child(
            resourceId="com.cnh.pf.android.data.management:id/treeview_list_item_toggle", index="0").click()

        if status:
            for item in uncheck_items:
                element = Display.active_display_uiautomator(resourceId="com.cnh.pf.android.data.management:id/tree_view_list").child_by_text(item,
                                                                                                                  allow_scroll_search=True,
                                                                                                                  resourceId="com.cnh.pf.android.data.management:id/tree_list_item_simple")
                if element.exists:
                    status = element.click()
                    status_item.append(status)
                    print(f'[{self.test_case_name}] > Tree item : {item} , Unchecked : {status}')
                    continue
                status_item.append(False)
        if not all(status_item):
            raise Exception('Import Operation failed : Selection of one or more tree item failed')

        if status:
            time.sleep(2)
            import_selected = Display.active_display_uiautomator(resourceId="com.cnh.pf.android.data.management:id/import_selected_btn")
            if import_selected.exists:
                import_selected.click()
                time.sleep(2)
                if conflict_resolver is not None:
                    status = self.conflict_resolver(conflict_resolver)
                if conflict_resolver is None or (conflict_resolver is not None and status):
                    start_time = time.perf_counter()
                    while True:
                        if Display.active_display_uiautomator(text="Select Import Source").info['enabled']:
                            status = self.wait_to_appear(item_text=verify_item)
                            if status:
                                print(f'[{self.test_case_name}] > Import Completed')
                                return True
                            print(f'[{self.test_case_name}] > Import Failed during XML processing ..')
                            return False
                        print(f'[{self.test_case_name}] > Import in progress ...Please wait ...')
                        time.sleep(3)
                        elapsed_time = time.perf_counter() - start_time
                        if elapsed_time >= timeout:
                            break
                    raise Exception('Import failed after timeout')
        raise Exception('Import Operation failed')

    def import_selected_items(self, select_item):
        """

        Args:
            select_item:

        Returns:

        """
        tree_view = Display.active_display_uiautomator(resourceId='com.cnh.pf.android.data.management:id/tree_view_list')
        items_sp = select_item.split('>>')
        for item in items_sp:
            print(f'[{self.test_case_name}] > Searching Item : [{item}]')
            tree_view.child_by_text(item, allow_scroll_search=True)
            # os.system('adb shell input swipe 600 400 600 350')
            item_found = Display.active_display_uiautomator(text=item)
            expand_icon = item_found.left(
                resourceId='com.cnh.pf.android.data.management:id/treeview_list_item_toggle')
            if expand_icon is not None and expand_icon.exists and items_sp[-1] != item:
                print(f'[{self.test_case_name}] > Found Item : [{item}]')
                print(f'[{self.test_case_name}] > Checking for expand button')
                screenshot = self.click_screenshot_display(is_test_case_screenshot=True, screenshot_name='expand_icon')
                reference = os.path.abspath(DMConstants.REFERENCE_IMAGES + '/plus.png')
                ui_info = expand_icon.info
                left = ui_info['bounds']['left']
                top = ui_info['bounds']['top']
                width = ui_info['bounds']['right'] - ui_info['bounds']['left']
                height = ui_info['bounds']['bottom'] - ui_info['bounds']['top']
                box = (left, top, width, height)
                result = self.image_comparison(image=screenshot, reference=reference, image_crop=box)
                if result:
                    expand_icon.click()
                    print(f'[{self.test_case_name}] > Expand : [{item}]')
                else:
                    print(f'[{self.test_case_name}] > Already Expanded : [{item}]')
                continue
            else:
                if item_found.exists:
                    print(f'[{self.test_case_name}] > Found Item : [{item}]')
                    self.common_functions.tap_using_ui_item(item_text=item)
                    return True
                else:
                    return False
        return False

    # ---------------------------- Import Shape files ----------------------------
    def screen_stats_during_import(self, import_tree: Union[str, list] = None, tree_load_timeout=500,
                                   import_source='USB', tree: str = None, Screenshot=None, Refimg=None, Thresh=int()):

        """
        Import XML into display ( Check for import icon status ding handles)
        Args:
            tree_load_timeout: timeout for loading taskdata
        Returns:
            bool : Status of import screen condition
        """
        if tree == None:
            verify_item = 'Grower/Farm/Field/Task'
        else:
            verify_item = tree
        if isinstance(import_tree, str):
            verify_item = import_tree
            if '>>' in import_tree:
                verify_item = import_tree.split('>>')[0]
            import_tree = [import_tree]
        elif isinstance(import_tree, list):
            if '>>' in import_tree[0]:
                verify_item = import_tree[0].split('>>')[0]

        status = self.import_xml_validate(tree_item=verify_item, tree_load_timeout=tree_load_timeout,
                                          source=import_source, is_kpi_timer=False)
        self.common_functions.tap_using_ui_item(item_text='Select All')
        time.sleep(1)
        import_item = Display.active_display_uiautomator(resourceId="com.cnh.pf.android.data.management:id/import_selected_btn")
        import_item.click()
        time.sleep(2.5)
        if status:
            print(f'[{self.test_case_name}] > Verifying if icons are locked')
            self.click_screenshot_display()
            MATCH = self.image_feature_comparison(IMG1=Screenshot, IMG2=Refimg, thresh=Thresh)
            if MATCH:
                print(f'[{self.test_case_name}] > Icons are locked')
            else:
                raise Exception('Icons are not locked')

    def import_shapefile_into_display(self):
        """
        Import shapefile data into display
        Args:

        Returns:

        """
        status = self.import_xml_validate(tree_item='TASKDATA')
        if status:
            print(f'[{self.test_case_name}] > Shapefile Imported successfully')
            status = self.common_functions.tap_using_ui_item(item_text='Select All')
            if status:
                import_selected = Display.active_display_uiautomator(resourceId="com.cnh.pf.android.data.management:id/import_selected_btn")
                if import_selected.exists:
                    import_selected.click()
                    status = [self.wait_to_appear(item_text='Prescription'),
                              self.wait_to_appear(item_text='Boundary'),
                              self.wait_to_appear(item_text='MultiSwath')]
                    if all(status):
                        print(f'[{self.test_case_name}] > Shapefile Dialogue box appear')
                        return True
                raise Exception('Import Shapefile failed')
        else:
            raise Exception('Import Shapefile failed, CHeck Shapefile Data')

    def select_product_from_grid(self, products: List):
        """

        Args:
            products:
        """
        failed = products
        linear_layout = Display.active_display_uiautomator(className='android.widget.LinearLayout')
        for product_ins in range(linear_layout.count):
            product = Display.active_display_uiautomator(className='android.widget.LinearLayout', index=product_ins)
            try:
                text = \
                    product.child(resourceId='com.cnh.pf.android.data.management:id/product_selection_item_name').info[
                        'text']
                if text in products:
                    print(f'[{self.test_case_name}] > Product [{text}] found in product grid')
                    status = product.child(
                        resourceId='com.cnh.pf.android.data.management:id/product_select_item_checkbox').click()
                    if status:
                        failed.remove(text)
                        print(f'[{self.test_case_name}] > Product [{text}] selected successfully')
            except Exception as err:
                if len(failed) == 0:
                    break
        if len(failed) > 0:
            self.click_screenshot_display(is_test_case_screenshot=True, screenshot_name='Product_Selection_failed')
            self.common_functions.tap_using_ui_item(item_text='Cancel')
            self.common_functions.tap_using_ui_item(item_text='Cancel')
            self.common_functions.tap_using_ui_item(item_text='Yes')
            raise Exception('Failed to select all products')
        else:
            self.common_functions.tap_using_ui_item(item_text='Done')
            print(f'[{self.test_case_name}] > Product selection completed successfully')
            self.common_functions.tap_using_ui_item(item_text='Continue')

    def check_prescription_name(self, new_name: str):
        """

        Args:
            new_name:
        """
        print(f'[{self.test_case_name}] > Checking prescription name ')
        current_name_widget = Display.active_display_uiautomator(resourceId='com.cnh.pf.android.data.management:id/name_editor')
        current_name_prescription = current_name_widget.info['text']
        if current_name_prescription != new_name:
            print(f'[{self.test_case_name}] > Updating prescription Name to [{new_name}]')
            os.system('adb shell input swipe 310 235 665 235')
            for _ in range(len(current_name_prescription)):
                Display.active_display_uiautomator.press.delete()

            if len(current_name_prescription) > 20:
                os.system('adb shell input swipe 310 235 665 235')
                for _ in range(15):
                    Display.active_display_uiautomator.press.delete()

            current_name_widget.set_text(new_name)
            self.common_functions.tap_adb(1130, 690)
            print(f'[{self.test_case_name}] > Updated prescription name : [{new_name}]')
        else:
            print(f'[{self.test_case_name}] > Already match prescription name : [{new_name}]')

    def select_shapefile_gff_tree(self, gff: Dict[str, str], is_scroll: bool = True):
        """

        Args:
            gff:
            is_scroll: to perform scroll operation inside the picklist
        """
        self.wait_to_appear(resource_id='com.cnh.pf.android.data.management:id/tvHeaderText', item_text='Select Grower')
        n = 0
        for title, value in gff.items():
            print(f'[{self.test_case_name}] > Selecting [{title}] with [{value}]')
            time.sleep(4)
            # item_text = ["Select Grower", "Select Farm", "Select Field"]
            # selection = self.wait_to_appear(resource_id="com.cnh.pf.android.data.management:id/tvHeaderText",
            #                                 item_text=item_text[n])
            if n == 0:
                self.common_functions.tap_ui_auto(950, 315)
            elif n == 1:
                self.common_functions.tap_ui_auto(950, 420)
            elif n == 2:
                self.common_functions.tap_ui_auto(950, 520)
            time.sleep(2)
            status = self.common_functions.tap_using_ui_item(item_text=value)
            if status:
                print(f'[{self.test_case_name}] > Selected [{title}] with [{value}]')
            else:
                got = False
                if is_scroll:
                    for i in range(1, 20):
                        print(f'[{self.test_case_name}] > Scroll [{i}] to search [{value}]')
                        find = self.wait_to_appear(resource_id='com.cnh.pf.android.data.management:id/picklistItem',
                                                   item_text=value)
                        os.system('adb shell input swipe 1135 465 1135 400')
                        if find:
                            got = self.common_functions.tap_using_ui_item(item_text=value)
                            break
                if got:
                    print(f'[{self.test_case_name}] > Selected [{title}] with [{value}] with scroll')
                else:
                    self.common_functions.tap_using_ui_item(item_text='Add New')
                    time.sleep(1)
                    Display.active_display_uiautomator().set_text(value)
                    time.sleep(1)
                    self.common_functions.tap_adb(1130, 690)
                    time.sleep(2)
                    self.common_functions.tap_using_ui_item(item_text='Apply')
                    time.sleep(1)
                    self.common_functions.tap_adb(1269, 691)
                    print(f'[{self.test_case_name}] > Successfully created GFF item with value : {value}')
            n += 1

    def configure_product(self, product: Dict):
        """

        Args:
            product:

        Returns:

        """
        Display.active_display_uiautomator(scrollable=True).scroll(steps=5)
        print(f'[{self.test_case_name}] > Configuring Product Details')
        product_name = Display.active_display_uiautomator(resourceId='com.cnh.pf.android.data.management:id/shapefile_product_name').info['text']
        if product_name != product['Shapefile product']:
            raise Exception(f'Failed to match prescription product Name : [{product["Shapefile product"]}]')

        print(f'[{self.test_case_name}] > Configuring Form')
        status = self.common_functions.tap_using_ui_item(item_text='Select Form')
        if status:
            try:
                Display.active_display_uiautomator(resourceId='com.cnh.pf.android.data.management:id/picklistPopupList').child_by_text(
                    product['Form'],
                    allow_scroll_search=True)
                status = self.common_functions.tap_using_ui_item(item_text=product['Form'])
                if status:
                    print(f'[{self.test_case_name}] > Configured Form to [{product["Form"]}]')
            except:
                raise Exception('Failed to set product form')

        print(f'[{self.test_case_name}] > Configuring prescription default rate')
        time.sleep(1)
        rate = Display.active_display_uiautomator(resourceId='com.cnh.pf.android.data.management:id/default_rate')
        if rate.exists:
            rate.click()
            rate.clear_text()
            status = rate.set_text(product['Rate'])
            time.sleep(2)
            if status:
                self.common_functions.tap_adb(1100, 628)
                print(f'[{self.test_case_name}] > Configured prescription rate to [{product["Rate"]}]')
            else:
                raise Exception('Failed to set prescription rate')
        else:
            raise Exception('Failed to set prescription rate, rate widget not found')

        print(f'[{self.test_case_name}] > Configuring rate unit')
        unit = Display.active_display_uiautomator(resourceId='com.cnh.pf.android.data.management:id/rate_unit')
        if unit.exists:
            time.sleep(0.5)
            unit.child(resourceId='com.cnh.pf.android.data.management:id/ivArrow').click()
            Display.active_display_uiautomator(resourceId='com.cnh.pf.android.data.management:id/picklistPopupList').child_by_text(product['Unit'],
                                                                                                       allow_scroll_search=True)
            status = self.common_functions.tap_using_ui_item(item_text=product['Unit'])
            if status:
                print(f'[{self.test_case_name}] > Configured prescription rate unit to [{product["Unit"]}]')
            else:
                raise Exception('Failed to set prescription rate unit')
        else:
            raise Exception('Failed to set prescription rate unit , unit widget not found')

    def import_shapefile_prescription(self, products: List[str] = None, prescription_config: Dict = None,
                                      is_product_selection: bool = False, timeout: int = 500, is_next: bool = False,
                                      is_prescription_import: bool = False, is_scroll: bool = True):
        """

        Args:
            products:
            prescription_config:
            is_product_selection:
            timeout:
            is_next:
            is_prescription_import

        Returns:

        """
        global Prescription_import_time
        status = self.common_functions.tap_using_ui_item(item_text='Prescription')
        if status:
            print(f'[{self.test_case_name}] > Prescription Config panel selected')
            try:
                if is_product_selection:
                    status = self.common_functions.tap_using_ui_item(item_text='Select Shapefile Prescriptions')
                    if status:
                        self.select_product_from_grid(products)
                self.select_shapefile_gff_tree(prescription_config['GFF'], is_scroll=is_scroll)
                time.sleep(5)
                Display.active_display_uiautomator.swipe(1240, 560, 1230, 250)
                time.sleep(5)
                products_info = prescription_config['Products']
                time.sleep(10)
                for ins in range(len(products_info)):
                    prescription_name_widget = Display.active_display_uiautomator(resourceId='com.cnh.pf.android.data.management:id/name_editor')
                    prescription_name_display = prescription_name_widget.info['text']
                    product_data = products_info.get(prescription_name_display)
                    if product_data is not None:
                        self.check_prescription_name(product_data['New Name'])
                        wait = self.wait_to_appear(item_text="Prescription preview loading")
                        if wait:
                            print(f'[{self.test_case_name}] > Prescription preview loading.')
                            while 1:
                                confirm = self.wait_to_appear(item_text="Prescription preview loading")
                                if confirm:
                                    print(f'[{self.test_case_name}] > Prescription preview loading.')
                                    continue
                                else:
                                    print(f'[{self.test_case_name}] > Prescription preview loaded.')
                                    break
                        else:
                            print(f'[{self.test_case_name}] > Prescription preview loaded.')
                        self.verify_reference_image(reference_image_name=product_data['Reference Image Name'],
                                                    crop=DMConstants.IMPORT_SCREEN_CROP_CO_ORDINATES)
                        self.configure_product(product_data)
                    else:
                        raise Exception(f'Prescription configuration not found [{prescription_name_display}]')
                    if len(products_info) - 1 != ins:
                        self.common_functions.tap_using_ui_item(item_text='Next Product')
            except Exception as Err:
                self.click_screenshot_display(is_test_case_screenshot=True, screenshot_name='Prescription_failed')
                self.common_functions.tap_using_ui_item(item_text='Cancel')
                self.common_functions.tap_using_ui_item(item_text='Yes')
                raise Exception(f'Failed : {str(Err)}')

            if is_next:
                status = self.common_functions.tap_using_ui_item(item_text='Next')
                if status:
                    print(f'[{self.test_case_name}] > Selecting Next.')
                    return
                else:
                    raise Exception('Import failed because Next button disable')
            else:
                self.common_functions.tap_using_ui_item(item_text='Finish')
                status_import = self.common_functions.tap_using_ui_item(item_text='Import')
                if status_import:
                    start_time = time.perf_counter()
                    while True:
                        if Display.active_display_uiautomator(text="Select Import Source").info['enabled']:
                            status = self.wait_to_appear(item_text='TASKDATA')
                            if status:
                                print(f'[{self.test_case_name}] > Import Completed')
                                return True
                            raise Exception('Import Failed during shapefile processing ..')
                        print(f'[{self.test_case_name}] > Import in progress ...Please wait ...')
                        time.sleep(3)
                        elapsed_time = time.perf_counter() - start_time
                        Prescription_import_time = elapsed_time
                        if is_prescription_import:
                            Red = "\033[91m{}\033[00m"
                            print((Red).format(
                                f'[{self.test_case_name}] > Prescription Import Time: [{Prescription_import_time} seconds]'))
                            return True
                        if elapsed_time >= timeout:
                            break
                    raise Exception('Import Failed after timeout')
                else:
                    raise Exception('Shapefile import failed')
        else:
            raise Exception('Prescription Config panel failed to select')

    def import_shapefile_prescription_without_selection(self, timeout: int = 500,  prescription_config: Dict = None,
                                                        is_prescription_import: bool = False):
        """
        Args:
        Returns:
        """
        status = self.common_functions.tap_using_ui_item(item_text='Prescription')
        if status:
            print(f'[{self.test_case_name}] > Prescription Config panel selected')
            time.sleep(5)
            self.select_shapefile_gff_tree(prescription_config['GFF'], is_scroll=True)
            time.sleep(5)
            is_next = self.wait_to_appear(item_text='Next')
            if is_next:
                status = self.common_functions.tap_using_ui_item(item_text='Next')
                if status:
                    print(f'[{self.test_case_name}] > Selecting Next.')

                else:
                    self.click_screenshot_display(is_test_case_screenshot=True, screenshot_name='Prescription_failed')
                    self.common_functions.tap_using_ui_item(item_text='Cancel')
                    self.common_functions.tap_using_ui_item(item_text='Yes')
                    raise Exception('Import failed because Next button disable')
            else:
                self.common_functions.tap_using_ui_item(item_text='Finish')
                status_import = self.common_functions.tap_using_ui_item(item_text='Import')
                if status_import:
                    start_time = time.perf_counter()
                    while True:
                        if Display.active_display_uiautomator(text="Select Import Source").info['enabled']:
                            status = self.wait_to_appear(item_text='TASKDATA')
                            if status:
                                print(f'[{self.test_case_name}] > Import Completed')
                                return True
                            raise Exception('Import Failed during shapefile processing ..')
                        print(f'[{self.test_case_name}] > Import in progress ...Please wait ...')
                        time.sleep(3)
                        elapsed_time = time.perf_counter() - start_time
                        Prescription_import_time = elapsed_time
                        if is_prescription_import:
                            Red = "\033[91m{}\033[00m"
                            print((Red).format(
                                f'[{self.test_case_name}] > Prescription Import Time: [{Prescription_import_time} seconds]'))
                            return True
                        if elapsed_time >= timeout:
                            break
                    raise Exception('Import Failed after timeout')
                else:
                    self.click_screenshot_display(is_test_case_screenshot=True, screenshot_name='Prescription_failed')
                    self.common_functions.tap_using_ui_item(item_text='Cancel')
                    self.common_functions.tap_using_ui_item(item_text='Yes')
                    raise Exception('Shapefile import failed')
        else:
            raise Exception('Prescription Config panel failed to select')

    def interrupt_import_shapefile_prescription(self, products: List[str] = None, prescription_config: Dict = None,
                                                is_product_selection: bool = False, is_next: bool = False):

        """

        Args:
            products:
            prescription_config:
            is_product_selection:
            timeout:
            is_next:
            is_prescription_import

        Returns:

        """
        print(f'[{self.test_case_name}] > Prescription Config panel will be selected and then Canceled intentionally.')
        status = self.common_functions.tap_using_ui_item(item_text='Prescription')
        if status:
            print(f'[{self.test_case_name}] > Prescription Config panel selected')
            try:
                if is_product_selection:
                    status = self.common_functions.tap_using_ui_item(item_text='Select Shapefile Prescriptions')
                    if status:
                        self.select_product_from_grid(products)
                self.select_shapefile_gff_tree(prescription_config['GFF'])
                time.sleep(5)
                Display.active_display_uiautomator.swipe(1240, 560, 1230, 250)
                time.sleep(5)
                products_info = prescription_config['Products']
                time.sleep(10)
                for ins in range(len(products_info)):
                    prescription_name_widget = Display.active_display_uiautomator(resourceId='com.cnh.pf.android.data.management:id/name_editor')
                    prescription_name_display = prescription_name_widget.info['text']
                    product_data = products_info.get(prescription_name_display)
                    if product_data is not None:
                        self.check_prescription_name(product_data['New Name'])
                        self.verify_reference_image(reference_image_name=product_data['Reference Image Name'],
                                                    crop=DMConstants.IMPORT_SCREEN_CROP_CO_ORDINATES)
                        self.configure_product(product_data)
                    else:
                        raise Exception(f'Prescription configuration not found [{prescription_name_display}]')
                    if len(products_info) - 1 != ins:
                        self.common_functions.tap_using_ui_item(item_text='Next Product')
            except Exception as Err:
                self.click_screenshot_display(is_test_case_screenshot=True, screenshot_name='Prescription_failed')
                raise Exception(f'Failed : {str(Err)}')

            if is_next:
                status = self.common_functions.tap_using_ui_item(item_text='Next')
                if status:
                    return
                else:
                    raise Exception('Import failed because Next button disable')
            else:
                self.common_functions.tap_using_ui_item(item_text='Finish')
                status_import = self.common_functions.tap_using_ui_item(item_text='Cancel')
                if status_import:
                    self.wait_to_appear(item_text='Yes')
                    self.common_functions.tap_using_ui_item(resource_id='com.cnh.pf.android.data.management:id/btFirst',
                                                            item_text='Yes')
                    print(f'[{self.test_case_name}] > Import Canceled intentionally')

                else:
                    raise Exception('Cannot click to Cancel')
        else:
            raise Exception('Prescription Config panel failed to select')

    def import_shapefile_prescription_bm(self, products: List[str] = None, prescription_config: Dict = None,
                                         is_product_selection: bool = False, timeout: int = 150, is_next: bool = False,
                                         is_prescription_import: bool = False):
        """

        Args:
            products:
            prescription_config:
            is_product_selection:
            timeout:
            is_next:
            is_prescription_import

        Returns:

        """
        global Prescription_import_time
        # status = self.common_functions.tap_using_ui_item(item_text='Prescription')
        status = self.common_functions.tap_ui_auto(835, 215)
        time.sleep(3)
        if status:
            print(f'[{self.test_case_name}] > Prescription Config panel selected')
            try:
                if is_product_selection:
                    # status = self.common_functions.tap_using_ui_item(item_text='Select Shapefile Prescriptions')
                    status = self.common_functions.tap_ui_auto(980, 500)
                    time.sleep(3)
                    if status:
                        self.common_functions.tap_ui_auto(360, 390)
                        time.sleep(3)
                        print(f'[{self.test_case_name}] > Product Selected')
                        self.common_functions.tap_adb(1185, 695)
                        time.sleep(3)
                        self.common_functions.tap_adb(1185, 695)
                        time.sleep(3)
                print(f'[{self.test_case_name}] > Selecting Grower')
                self.common_functions.tap_ui_auto(950, 315)
                time.sleep(3)
                self.common_functions.tap_ui_auto(950, 360)
                time.sleep(3)
                print(f'[{self.test_case_name}] > Selecting Farm')
                self.common_functions.tap_ui_auto(950, 420)
                time.sleep(3)
                self.common_functions.tap_ui_auto(950, 460)
                time.sleep(3)
                print(f'[{self.test_case_name}] > Selecting Field')
                self.common_functions.tap_ui_auto(950, 520)
                time.sleep(3)
                self.common_functions.tap_ui_auto(950, 560)
                time.sleep(3)
                print(f'[{self.test_case_name}] > Selecting Product Form and Unit')
                self.common_functions.drag_screen(1070, 590, 1070, 290)
                time.sleep(2)
                self.common_functions.tap_adb(1200, 475)
                time.sleep(2)
                self.common_functions.tap_adb(1000, 525)
                time.sleep(2)
                self.common_functions.tap_adb(1165, 570)
                time.sleep(2)
                self.common_functions.tap_adb(1000, 525)
            except Exception as Err:
                self.click_screenshot_display(is_test_case_screenshot=True, screenshot_name='Prescription_failed')
                self.common_functions.tap_using_ui_item(item_text='Cancel')
                self.common_functions.tap_using_ui_item(item_text='Yes')
                raise Exception(f'Failed : {str(Err)}')

            if is_next:
                status = self.common_functions.tap_using_ui_item(item_text='Next')
                if status:
                    return
                else:
                    raise Exception('Import failed because Next button disable')
            else:
                self.common_functions.tap_using_ui_item(item_text='Finish')
                status_import = self.common_functions.tap_using_ui_item(item_text='Import')
                print(f'[{self.test_case_name}] > Starting to Import.....')
                start_counter = time.time()
                start_time = time.perf_counter()
                if status_import:
                    while True:
                        if Display.active_display_uiautomator(text="Select Import Source").info['enabled']:
                            status = self.wait_to_appear(item_text='TASKDATA')
                            if status:
                                break_time = time.time()
                                if is_prescription_import:
                                    Prescription_import_time = break_time - start_counter
                                    Red = "\033[91m{}\033[00m"
                                    print((Red).format(
                                        f'[{self.test_case_name}] > Prescription Import Time: [{Prescription_import_time} seconds]'))
                                    return True
                                print(f'[{self.test_case_name}] > Import Completed')
                                return True

                        elapsed_time = time.perf_counter() - start_time
                        remaining_time = timeout - elapsed_time
                        print(f'[{self.test_case_name}] > Import in progress ...Please wait ...[{remaining_time} sec]')
                        if elapsed_time >= timeout:
                            break
                    raise Exception('Import Failed after timeout')
                raise Exception('Import Failed during shapefile processing ..')
        else:
            raise Exception('Prescription Config panel failed to select')

    def import_shapefile_boundary(self, configuration: Dict, is_multiple_boundaries: bool = False, timeout: int = 120,
                                  is_boundary_import: bool = False, is_scroll: bool = True):
        """

        Args:
            is_multiple_boundaries:
            configuration:
            timeout:
            is_boundary_import

        Returns:

        """
        global Boundary_import_timer
        if not is_multiple_boundaries:
            current_name_widget = Display.active_display_uiautomator(resourceId='com.cnh.pf.android.data.management:id/name_editor')
            boundary_name = current_name_widget.info['text']
            configuration = {boundary_name: configuration}
        for iteration in range(len(configuration)):
            status = self.common_functions.tap_using_ui_item(item_text='Boundary')
            if status:
                try:
                    print(f'[{self.test_case_name}] > Boundary Config panel selected')
                    current_name_widget = Display.active_display_uiautomator(resourceId='com.cnh.pf.android.data.management:id/name_editor')
                    boundary_name = current_name_widget.info['text']
                    config_boundary = configuration.get(boundary_name)
                    if config_boundary is None:
                        raise Exception(f'Configuration not found for [{boundary_name}]')
                    print(f'[{self.test_case_name}] > Configuring boundary : [{boundary_name}]')
                    reference_image = config_boundary.pop('Reference Image Name')
                    new_name = config_boundary.pop('New Name')
                    if boundary_name != new_name:
                        print(f'[{self.test_case_name}] > Updating boundary Name to [{new_name}]')
                        os.system('adb shell input swipe 310 235 665 235')
                        for _ in range(len(boundary_name)):
                            Display.active_display_uiautomator.press.delete()

                        if len(boundary_name) > 20:
                            os.system('adb shell input swipe 310 235 665 235')
                            for _ in range(15):
                                Display.active_display_uiautomator.press.delete()

                        current_name_widget.set_text(new_name)
                        self.common_functions.tap_adb(1130, 690)
                        print(f'[{self.test_case_name}] > Updated boundary name : [{new_name}]')
                    self.select_shapefile_gff_tree(config_boundary, is_scroll=is_scroll)
                    self.verify_reference_image(reference_image, crop=DMConstants.IMPORT_SCREEN_CROP_CO_ORDINATES)
                except Exception as Err:
                    self.click_screenshot_display(is_test_case_screenshot=True, screenshot_name='Boundary_failed')
                    self.common_functions.tap_using_ui_item(item_text='Cancel')
                    self.common_functions.tap_using_ui_item(item_text='Yes')
                    raise Exception(f'Failed : {str(Err)}')

                if is_multiple_boundaries:
                    if len(configuration) - 1 != iteration:
                        self.common_functions.tap_using_ui_item(item_text='Next')
                    else:
                        self.common_functions.tap_using_ui_item(item_text='Finish')

        status_import = self.common_functions.tap_using_ui_item(item_text='Import')
        if status_import:
            start_time = time.perf_counter()
            while True:
                if Display.active_display_uiautomator(text="Select Import Source").info['enabled']:
                    status = self.wait_to_appear(item_text='TASKDATA')
                    if status:
                        print(f'[{self.test_case_name}] > Import Completed')
                        return True
                    raise Exception('Import Failed during shapefile processing ..')
                print(f'[{self.test_case_name}] > Import in progress ...Please wait ...')
                time.sleep(3)
                elapsed_time = time.perf_counter() - start_time
                Boundary_import_timer = elapsed_time
                if is_boundary_import:
                    Red = "\033[91m{}\033[00m"
                    print((Red).format(
                        f'[{self.test_case_name}] > Boundary Import Time: [{Boundary_import_timer} seconds]'))
                    return True
                if elapsed_time >= timeout:
                    break
            raise Exception('Import failed after timeout')

    def import_shapefile_boundary_bm(self, configuration: Dict, is_multiple_boundaries: bool = False,
                                     timeout: int = 120,
                                     is_boundary_import: bool = False):
        """

        Args:
            is_multiple_boundaries:
            configuration:
            timeout:
            is_boundary_import

        Returns:

        """
        global Boundary_import_timer

        if isinstance(configuration, dict):
            configuration = [configuration]
        # if not is_multiple_boundaries:
        #     current_name_widget = Display.active_display_uiautomator(resourceId='com.cnh.pf.android.shapefile:id/name_editor')
        #     boundary_name = current_name_widget.info['text']
        #     configuration = {boundary_name: configuration}
        for iteration in range(len(configuration)):
            status = self.common_functions.tap_using_ui_item(item_text='Boundary')
            if status:
                try:
                    print(f'[{self.test_case_name}] > Boundary Config panel selected')
                    time.sleep(5)
                    print(f'[{self.test_case_name}] > Selecting Grower')
                    self.common_functions.tap_ui_auto(950, 315)
                    time.sleep(3)
                    self.common_functions.tap_ui_auto(950, 360)
                    time.sleep(3)
                    print(f'[{self.test_case_name}] > Selecting Farm')
                    self.common_functions.tap_ui_auto(950, 420)
                    time.sleep(3)
                    self.common_functions.tap_ui_auto(950, 460)
                    time.sleep(3)
                    print(f'[{self.test_case_name}] > Selecting Field')
                    self.common_functions.tap_ui_auto(950, 520)
                    time.sleep(3)
                    self.common_functions.tap_ui_auto(950, 560)
                    time.sleep(3)
                except Exception as Err:
                    self.click_screenshot_display(is_test_case_screenshot=True, screenshot_name='Boundary_failed')
                    self.common_functions.tap_using_ui_item(item_text='Cancel')
                    self.common_functions.tap_using_ui_item(item_text='Yes')
                    raise Exception(f'Failed : {str(Err)}')

                if is_multiple_boundaries:
                    if len(configuration) - 1 != iteration:
                        self.common_functions.tap_using_ui_item(item_text='Next')
                    else:
                        self.common_functions.tap_using_ui_item(item_text='Finish')

        status_import = self.common_functions.tap_using_ui_item(item_text='Import')
        print(f'[{self.test_case_name}] > Starting to Import.......')
        start_counter = time.time()
        start_time = time.perf_counter()
        if status_import:
            while True:
                if Display.active_display_uiautomator(text="Select Import Source").info['enabled']:
                    status = self.wait_to_appear(item_text='TASKDATA')
                    if status:
                        break_time = time.time()
                        if is_boundary_import:
                            Boundary_import_timer = break_time - start_counter
                            Red = "\033[91m{}\033[00m"
                            print((Red).format(
                                f'[{self.test_case_name}] > Boundary Import Time: [{Boundary_import_timer} seconds]'))
                            return True
                        print(f'[{self.test_case_name}] > Import Completed')
                        return True
                elapsed_time = time.perf_counter() - start_time
                remaining_time = timeout - elapsed_time
                print(f'[{self.test_case_name}] > Import in progress ...Please wait ...[{remaining_time}sec]')
                if elapsed_time >= timeout:
                    break
            raise Exception('Import failed after timeout')
        raise Exception('Import Failed during shapefile processing ..')

    def import_shapefile_multi_swath(self, configuration: Dict, is_multiple_files: bool = False, timeout: int = 120,
                                     is_multiswath_import: bool = False, is_scroll: bool = True, conflict_resolver=None,
                                     conflict: bool = False):
        """

        Args:
            is_multiple_files:
            configuration:
            timeout:
            is_multiswath_import

        Returns:

        """
        global Multiswath_import_timer
        if isinstance(configuration, dict):
            configuration = [configuration]

        for iteration, details in enumerate(configuration):
            status = self.common_functions.tap_using_ui_item(
                resource_id='com.cnh.pf.android.data.management:id/multiswath_type',
                item_text='MultiSwath')
            if status:
                try:
                    print(f'[{self.test_case_name}] > MultiSwath Config panel selected')
                    current_name_widget = Display.active_display_uiautomator(resourceId='com.cnh.pf.android.data.management:id/name_editor')
                    reference_image = details.pop('Reference Image Name')
                    new_name = details.pop('New Name')
                    if current_name_widget.info['text'] != new_name:
                        print(f'[{self.test_case_name}] > Updating multiSwath Name to [{new_name}]')
                        os.system('adb shell input swipe 310 235 665 235')
                        for _ in range(len(current_name_widget.info['text'])):
                            Display.active_display_uiautomator.press.delete()
                        current_name_widget.set_text(new_name)
                        self.common_functions.tap_adb(1130, 690)
                        print(f'[{self.test_case_name}] > Updated multiSwath name : [{new_name}]')
                    self.select_shapefile_gff_tree(details, is_scroll=is_scroll)
                    self.verify_reference_image(reference_image, crop=DMConstants.IMPORT_SCREEN_CROP_CO_ORDINATES)
                except Exception as Err:
                    self.click_screenshot_display(is_test_case_screenshot=True, screenshot_name='Multiswath_failed')
                    self.common_functions.tap_using_ui_item(item_text='Cancel')
                    self.common_functions.tap_using_ui_item(item_text='Yes')
                    raise Exception(f'Failed : {str(Err)}')

                if is_multiple_files:
                    if len(configuration) - 1 != iteration:
                        self.common_functions.tap_using_ui_item(item_text='Next')
                        continue
                    else:
                        self.common_functions.tap_using_ui_item(item_text='Finish')

                status_import = self.common_functions.tap_using_ui_item(item_text='Import')
                if status_import:
                    start_time = time.perf_counter()
                    if conflict:
                        print(f'[{self.test_case_name}] > Import process is handling conflict now ...')
                        self.conflict_resolver(conflict_resolver)
                    while True:
                        if Display.active_display_uiautomator(text="Select Import Source").info['enabled']:
                            status = self.wait_to_appear(item_text='TASKDATA')
                            if status:
                                print(f'[{self.test_case_name}] > Import Completed')
                                return True
                            raise Exception('Import Failed during shapefile processing ..')
                        print(f'[{self.test_case_name}] > Import in progress ...Please wait ...')
                        time.sleep(3)
                        elapsed_time = time.perf_counter() - start_time
                        Multiswath_import_timer = elapsed_time
                        if is_multiswath_import:
                            Red = "\033[91m{}\033[00m"
                            print((Red).format(
                                f'[{self.test_case_name}] > Multiswath Import Time: [{Multiswath_import_timer} seconds]'))
                            return True
                        if elapsed_time >= timeout:
                            break
                    raise Exception('Import failed after timeout')
            else:
                raise Exception('Multiswath Config panel failed to select')

    def import_shapefile_multi_swath_bm(self, configuration: Dict, is_multiple_files: bool = False, timeout: int = 120,
                                        is_multiswath_import: bool = False):
        """

        Args:
            is_multiple_files:
            configuration:
            timeout:
            is_multiswath_import

        Returns:

        """
        global Multiswath_import_timer
        if isinstance(configuration, dict):
            configuration = [configuration]

        for iteration, details in enumerate(configuration):
            status = self.common_functions.tap_using_ui_item(item_text='MultiSwath')
            if status:
                try:
                    print(f'[{self.test_case_name}] > MultiSwath Config panel selected')
                    # current_name_widget = Display.active_display_uiautomator(resourceId='com.cnh.pf.android.shapefile:id/name_editor')
                    # # reference_image = details.pop('Reference Image Name')
                    # new_name = details.pop('New Name')
                    # if current_name_widget.info['text'] != new_name:
                    #     print(f'[{self.test_case_name}] > Updating multiswath Name to [{new_name}]')
                    #     os.system('adb shell input swipe 310 235 665 235')
                    #     for _ in range(len(current_name_widget.info['text'])):
                    #         Display.active_display_uiautomator.press.delete()
                    #     current_name_widget.set_text(new_name)
                    #     self.common_functions.tap_adb(1130, 690)
                    #     print(f'[{self.test_case_name}] > Updated multiswath name : [{new_name}]')
                    time.sleep(5)
                    print(f'[{self.test_case_name}] > Selecting Grower')
                    self.common_functions.tap_ui_auto(950, 315)
                    time.sleep(3)
                    self.common_functions.tap_ui_auto(950, 360)
                    time.sleep(3)
                    print(f'[{self.test_case_name}] > Selecting Farm')
                    self.common_functions.tap_ui_auto(950, 420)
                    time.sleep(3)
                    self.common_functions.tap_ui_auto(950, 460)
                    time.sleep(3)
                    print(f'[{self.test_case_name}] > Selecting Field')
                    self.common_functions.tap_ui_auto(950, 520)
                    time.sleep(3)
                    self.common_functions.tap_ui_auto(950, 560)
                    time.sleep(3)
                except Exception as Err:
                    self.click_screenshot_display(is_test_case_screenshot=True, screenshot_name='Multiswath_failed')
                    self.common_functions.tap_using_ui_item(item_text='Cancel')
                    self.common_functions.tap_using_ui_item(item_text='Yes')
                    raise Exception(f'Failed : {str(Err)}')

                if is_multiple_files:
                    if len(configuration) - 1 != iteration:
                        self.common_functions.tap_using_ui_item(item_text='Next')
                        continue
                    else:
                        self.common_functions.tap_using_ui_item(item_text='Finish')

                checkpoint = self.common_functions.tap_using_ui_item(item_text='Import')
                print(f'[{self.test_case_name}] > Starting to Import.....')
                start_time = time.perf_counter()
                start_counter = time.time()
                if checkpoint:
                    while True:
                        if Display.active_display_uiautomator(text="Select Import Source").info['enabled']:
                            confirm = self.wait_to_appear(item_text='TASKDATA')
                            if confirm:
                                break_time = time.time()
                                if is_multiswath_import:
                                    Multiswath_import_timer = break_time - start_counter
                                    Red = "\033[91m{}\033[00m"
                                    print((Red).format(
                                        f'[{self.test_case_name}] > Multiswath Import Time: [{Multiswath_import_timer} seconds]'))
                                    return True
                                print(f'[{self.test_case_name}] > Import Completed')
                                return True
                        elapsed_time = time.perf_counter() - start_time
                        remaining_time = timeout - elapsed_time
                        print(f'[{self.test_case_name}] > Import in progress ...Please wait ...[{remaining_time} sec]')
                        if elapsed_time >= timeout:
                            break
                    raise Exception('Import failed after timeout')
                raise Exception('Import Multiswath did not happen properly.')
            else:
                raise Exception('Multiswath Config panel failed to select')

    # ---------------------------- Export Functionality ----------------------------

    def export_xml_from_display(self, export_folder: str = None, export_tree: str = None,
                                export_destination: str = None, is_multiple: bool = False, verify_export: bool = True,
                                export_only: bool = False, is_export_time: bool = False):
        """
        Export TASKDATA.XML from display to local folder
        Args:
            export_folder: Path of local disk
            export_tree: Item list to be selected from export tree
            export_destination: destination of export ( Default : AFS Pro 1200)
            is_multiple: Pull multiple files from /tmp/data management
            verify_export: verify export folder
            export_only : export without importing any data previously
            is_export_time : time required for the export process
            is_kpi_selector: for excel reporting

        Returns:
            bool : status of export operation

        """
        global Export_Time
        status = self.export_select_tree_items(tree_items=export_tree)
        if status:
            time.sleep(1)
            status = self.select_export_destination(export_destination)
            if status:
                time.sleep(2)
                export_selected = Display.active_display_uiautomator(resourceId="com.cnh.pf.android.data.management:id/export_selected_btn",
                                         enabled="true")
                if export_selected.exists:
                    export_selected.click()
                    time.sleep(2)
                    start_export_timer = time.time()
                    status_export = False
                    for times in range(0, 50):
                        process_overlay = Display.active_display_uiautomator(resourceId='com.cnh.pf.android.data.management:id/process_overlay')
                        if not process_overlay.exists:
                            stop_export_timer = time.time()
                            Export_Time = stop_export_timer - start_export_timer
                            time.sleep(1)
                            print(f'[{self.test_case_name}] > Export Completed')
                            status_export = True
                            if is_export_time:
                                Red = "\033[91m{}\033[00m"
                                print((Red).format(f'[{self.test_case_name}] > Export Time: [{Export_Time} seconds]'))
                                return True
                            break
                        del process_overlay
                        print(f'[{self.test_case_name}] > Export in progress ...Please wait ...')
                        time.sleep(3)

                    if export_destination == 'AFS Connect':
                        return True

                    if status_export:
                        time.sleep(1)
                        self.pull_data_from_display(export_folder=export_folder, is_multiple=is_multiple,
                                                    verify_export=verify_export, export_only=export_only)
                        print(f'[{self.test_case_name}] > TASKDATA Successfully Completed')
                        return True
            else:
                raise Exception('Export destination selection failed')
        else:
            raise Exception('Export tree item selection failed')
        raise Exception('Export Operation failed')

    def export_xml_from_display_with_uncheck_items(self, export_folder: str = None, uncheck_items: List = None,
                                                   export_destination: str = None, is_multiple: bool = False,
                                                   verify_export: bool = False):
        """
        Export xml with excluding some items
        Args:
            export_folder: Path of local disk
            uncheck_items: Items to excluded from export tree
            export_destination: destination of export ( Default : AFS Pro 1200)
            is_multiple: Pull multiple files from /tmp/datamanagement
            verify_export: verify export folder

        Returns:
            bool : status of export operation
        """
        status = self.export_select_uncheck_items(uncheck_items=uncheck_items)
        if status:
            time.sleep(1)
            status = self.select_export_destination(export_destination)
            if status:
                time.sleep(2)
                export_selected = Display.active_display_uiautomator(resourceId="com.cnh.pf.android.data.management:id/export_selected_btn",
                                         enabled="true")
                if export_selected.exists:
                    export_selected.click()
                    time.sleep(2)
                    status_export = False
                    for times in range(0, 50):
                        process_overlay = Display.active_display_uiautomator(resourceId='com.cnh.pf.android.data.management:id/process_overlay')
                        if not process_overlay.exists:
                            print(f'[{self.test_case_name}] > Export Completed')
                            status_export = True
                            break
                        del process_overlay
                        print(f'[{self.test_case_name}] > Export in progress ...Please wait ...')
                        time.sleep(3)
                    if status_export:
                        time.sleep(1)
                        self.pull_data_from_display(export_folder=export_folder, is_multiple=is_multiple,
                                                    verify_export=verify_export)
                        print(f'[{self.test_case_name}] > TASKDATA Successfully Completed')
                        return True
            else:
                raise Exception('Export destination selection failed')
        else:
            raise Exception('Export tree item selection failed')
        raise Exception('Export Operation failed')

    def select_export_destination(self, destination: str = None):
        """
        Select Export destination
        Args:
            destination: Export destination of xml

        Returns:
            bool : status of operation

        """
        if destination is None:
            destination = 'AFS Pro 1200'
        status = self.common_functions.tap_using_ui_item(item_text="Select")
        if not status:
            status = self.common_functions.tap_using_ui_item(
                resource_id="com.cnh.pf.android.data.management:id/export_medium_picklist")
        if status:
            status = self.common_functions.tap_using_ui_item(item_text=destination)
            if status:
                print(f'[{self.test_case_name}] > Select Destination : {destination}')
                return True
            else:
                destination = 'IntelliView 12'
                get = self.common_functions.tap_using_ui_item(item_text=destination)
                if get:
                    print(f'[{self.test_case_name}] > Select Destination [Combine CXCR] : {destination}')
                    return True
                else:
                    raise Exception("Export destinations are different than expected.")
        raise Exception('Select Destination of export failed')

    def export_select_tree_items(self, tree_items: Union[List, str] = None):
        """
        Selecting export tree items
        Args:
            tree_items: Item to be selected from import tree

        Returns:
            bool : Status of operation
        """
        self.handle_pop_ups()
        self.wait_to_appear(item_text='Select All')
        final_status = False
        if tree_items is None:
            status = self.common_functions.tap_using_ui_item(item_text='Select All')
            print(f'[{self.test_case_name}] > All tree items Selected : {status}')
            if status:
                final_status = True
        elif isinstance(tree_items, list):
            status_item = []
            for item in tree_items:
                if '>>' in tree_items:
                    self.expand_specific_dm_tree_item(tree_item_hierarchy=item, tab='Export')
                    item = item.split('>>')[-1]
                status = self.common_functions.tap_using_ui_item(item_text=item)
                status_item.append(status)
                print(f'[{self.test_case_name}] > Tree item : {item} Selected : {status}')
            if all(status_item):
                final_status = True
        elif isinstance(tree_items, str):
            if '>>' in tree_items:
                self.expand_specific_dm_tree_item(tree_item_hierarchy=tree_items, tab='Export')
                tree_items = tree_items.split('>>')[-1]
            status = self.common_functions.tap_using_ui_item(item_text=tree_items)
            print(f'[{self.test_case_name}] > Tree item : {tree_items} Selected : {status}')
            if status:
                final_status = True
        if final_status:
            return True
        raise Exception('Export Operation failed : Selection of one or more tree item failed')

    def export_select_uncheck_items(self, uncheck_items: List = None):
        """
        Uncheck items from export tree
        Args:
            uncheck_items: Items to uncheck

        Returns:
            bool : Status of operation

        """
        status_item = []
        status = self.common_functions.tap_using_ui_item(item_text='Select All')
        Display.active_display_uiautomator(resourceId="com.cnh.pf.android.data.management:id/tree_view_list").child(
            className="android.widget.LinearLayout", index="0").child(
            resourceId="com.cnh.pf.android.data.management:id/treeview_list_item_frame_layout", index="0").child(
            resourceId="com.cnh.pf.android.data.management:id/treeview_list_item_toggle", index="0").click()

        if status:
            for item in uncheck_items:
                try:
                    element = Display.active_display_uiautomator(resourceId="com.cnh.pf.android.data.management:id/tree_view_list").child_by_text(
                        item, allow_scroll_search=True,
                        resourceId="com.cnh.pf.android.data.management:id/tree_list_item_simple")
                    # element = Display.active_display_uiautomator(resourceId="com.cnh.pf.android.data.management:id/tree_view_list").child(text=item, resourceId="com.cnh.pf.android.data.management:id/tree_list_item_simple")
                    if element.exists:
                        status = element.click()
                        status_item.append(status)
                        print(f'[{self.test_case_name}] > Tree item : {item} , Unchecked : {status}')
                        # continue
                    else:
                        Helper.prRed(
                            f'[{self.test_case_name}] > Tree item : [{item}] , Unchecked : False ->Not Found in Display')
                        status_item.append(False)
                except:
                    Helper.prRed(
                        f'[{self.test_case_name}] > Tree item : [{item}] , Unchecked : False ->Not Found in Display')
                    status_item.append(False)

        print(status_item)
        vehicle = self.get_vehicle_name()
        if vehicle == 'Combine':
            Helper.prRed(f'[{self.test_case_name}] > Vehicle configuration is skipped as vehicle is Combine.')
            return True
        else:
            if all(status_item):
                return True
            else:
                Helper.prRed('Selection of one or more tree item failed')
        # raise Exception('Export Operation failed : Selection of one or more tree item failed')

    def pull_data_from_display(self, export_folder: str = None, is_multiple: bool = False, verify_export: bool = True,
                               export_only: bool = False):
        """
        Pull data from display to local disk
        Args:
            export_only:
            export_folder: Path of export folder
            is_multiple: Pull multiple files other than TASKDATA.XML
            verify_export: Verify export folder

        Returns:
            bool : Status of export operation
        """
        try:
            import_export_verify = True
            if verify_export:
                print(f'[{self.test_case_name}] > Verifying import and export folder in display')
                os.system('adb shell su -c chmod -R 0777 /tmp/datamanagement')
                import_cmd = 'adb shell su -c find tmp/datamanagement -name TASKDATA.* -type d'
                export_cmd = 'adb shell su -c find tmp/datamanagement -name TASKDATA -type d'
                import_folder_output = subprocess.check_output(import_cmd).decode('utf8')
                export_folder_output = subprocess.check_output(export_cmd).decode('utf8')
                if export_only:
                    import_folder_output = 'random'
                if import_folder_output == '' and export_folder_output == '':
                    import_export_verify = False
                    raise Exception('Export folder not found in Display')
            if import_export_verify:
                print(f'[{self.test_case_name}] > Pulling TaskData to Display')
                if export_folder is not None:
                    export_path = os.path.abspath(export_folder)
                else:
                    export_path = os.path.abspath(f'{self.export_directory}/{self.test_case_name}')

                export_file = export_path + '/TASKDATA.XML'
                print(f'[{self.test_case_name}] > Creating Export folder')
                if not os.path.isdir(export_path):
                    os.makedirs(export_path, exist_ok=True)
                else:
                    shutil.rmtree(export_path)
                    os.makedirs(export_path, exist_ok=True)

                print(f'[{self.test_case_name}] > Pulling TASKDATA from Display')
                os.system('adb shell su -c chmod -R 777 /tmp/datamanagement/')
                pull_cmd = f'adb pull "/tmp/datamanagement/TASKDATA/TASKDATA.XML" "{export_file}" > NUL'
                if is_multiple:
                    pull_cmd = f'adb pull "/tmp/datamanagement/TASKDATA/." "{export_path}/" > NUL'
                status = os.system(pull_cmd)
                if status == 0:
                    print(f'[{self.test_case_name}] > Successfully pushed data to TASKDATA')
                    return
                raise Exception('Pulled data operation Failed')
        except Exception as E:
            raise Exception(f'Pull data to Display Failed : {str(E)}')

    def export_verify_tree_items(self, tree_items: list):
        """
        Expand DM Tree using specific path of DM tree
        Args:

        """
        print(f'[{self.test_case_name}] > Expanding and Collecting Tree items')
        self.wait_to_appear(resource_id='com.cnh.pf.android.data.management:id/tree_view_list')
        failed_items = []
        for item in tree_items:
            try:
                item_text = item.split('>>')[-1]
                self.expand_specific_dm_tree_item(tree_item_hierarchy=item, tab='Export')
                item_widget = Display.active_display_uiautomator(text=item_text)
                if not item_widget.exists:
                    failed_items.append({item: 'Item not found'})
            except Exception as Err:
                failed_items.append({item: f'Error : {str(Err)}'})

        if len(failed_items) > 0:
            raise Exception(f'Failed to validate below field : {failed_items}')

    # ---------------------------- Verify and validate dm tree items ----------------------------
    def create_swath_item_copy(self, swath_name: str = None):
        """
        Make a copy of swath of DM Tree
        Args:
            tree_items: Item to make a copy from DM tree

        Returns:
            status : todo

        """
        print(f'[{self.test_case_name}] > Attempting to copy item >> {swath_name}')
        status = self.wait_to_appear(resource_id='com.cnh.pf.android.data.management:id/tree_list_item_text',
                                     item_text=f'{swath_name}')
        if status:
            self.common_functions.tap_using_ui_item(
                resource_id='com.cnh.pf.android.data.management:id/tree_list_item_text', item_text=f'{swath_name}')
            self.wait_to_appear(resource_id='com.cnh.pf.android.data.management:id/mng_copy_button')
            print(f'[{self.test_case_name}] > Making copy of {swath_name}')
            self.common_functions.tap_using_ui_item(resource_id='com.cnh.pf.android.data.management:id/mng_copy_button')
            wait = self.wait_to_appear(resource_id='com.cnh.pf.android.data.management:id/btFirst', item_text='Next')
            if wait:
                self.common_functions.tap_using_ui_item(
                    resource_id='com.cnh.pf.android.data.management:id/btFirst', item_text='Next')
                print(f'[{self.test_case_name}] > Created copy {swath_name} in default location.')
            else:
                raise Exception(f'[{self.test_case_name}] > Failed to create copy of Swath.')
        self.wait_to_appear(resource_id='com.cnh.pf.android.data.management:id/btFirst', item_text='Done')
        time.sleep(0.5)
        self.common_functions.tap_using_ui_item(resource_id='com.cnh.pf.android.data.management:id/btFirst',
                                                item_text='Done')
        print(f'[{self.test_case_name}] > Created copy {swath_name} successfully.')

    def locate_and_transfer_swathcopy(self, locator: str = None):
        """
        Locate copy of swath of DM Tree
        Args:
            tree_items: Item  copy from DM tree

        Returns:
            status : todo

        """
        print(f'[{self.test_case_name}] > Finding copy item >>Swaths >> {locator}')
        status = self.wait_to_appear(resource_id='com.cnh.pf.android.data.management:id/tree_list_item_text',
                                     item_text=f'{locator}')
        if status:
            self.common_functions.tap_using_ui_item(
                resource_id='com.cnh.pf.android.data.management:id/tree_list_item_text', item_text=f'{locator}')
            self.wait_to_appear(resource_id='com.cnh.pf.android.data.management:id/mng_copy_button')
            print(f'[{self.test_case_name}] > Located copy of {locator}')
            self.common_functions.tap_using_ui_item(resource_id='com.cnh.pf.android.data.management:id/mng_copy_button')
            wait = self.wait_to_appear(resource_id='com.cnh.pf.android.data.management:id/btFirst', item_text='Next')
            if wait:
                self.common_functions.tap_using_ui_item(
                    resource_id='com.cnh.pf.android.data.management:id/btFirst', item_text='Next')
                print(f'[{self.test_case_name}] > Copied {locator} (2) in required location.')
            else:
                raise Exception(f'[{self.test_case_name}] > Failed to locate copy of Swath.')
            self.wait_to_appear(resource_id='com.cnh.pf.android.data.management:id/btFirst', item_text='Done')
            time.sleep(0.5)
            self.common_functions.tap_using_ui_item(resource_id='com.cnh.pf.android.data.management:id/btFirst',
                                                    item_text='Done')
            print(f'[{self.test_case_name}] > Created copy {locator} (2) successfully.')

    def edit_swath_copy(self, old_name: str = None, new_name: str = None):
        """
        Make a copy of swath of DM Tree
        Args:
            tree_items: Item to make a copy from DM tree

        Returns:
            status : todo

        """
        print(f'[{self.test_case_name}] > Attempting to edit item >>Swaths >> {old_name}')
        status = self.wait_to_appear(resource_id='com.cnh.pf.android.data.management:id/tree_list_item_text',
                                     item_text=f'{old_name}')
        if status:
            self.common_functions.tap_using_ui_item(
                resource_id='com.cnh.pf.android.data.management:id/tree_list_item_text', item_text=f'{old_name}')
            self.wait_to_appear(resource_id='com.cnh.pf.android.data.management:id/mng_edit_button')
            print(f'[{self.test_case_name}] > Rename copy to: [{new_name}]')
            self.common_functions.tap_using_ui_item(resource_id='com.cnh.pf.android.data.management:id/mng_edit_button')
            wait = self.wait_to_appear(resource_id='com.cnh.pf.android.data.management:id/btSecond', item_text='Cancel')
            if wait:
                text_feed = Display.active_display_uiautomator(className='android.widget.EditText')
                print(f'[{self.test_case_name}] > Renaming copy of {old_name} to new {new_name}.')
                text_feed.click()
                os.system("adb shell input keyevent KEYCODE_DEL")
                time.sleep(.5)
                text_feed.clear_text()
                text_feed.set_text(new_name)
                self.common_functions.tap_using_ui_item(
                    resource_id='com.cnh.pf.android.data.management:id/btFirst', item_text='Save')
                print(f'[{self.test_case_name}] > Clicked on save.')
            else:
                raise Exception(f'[{self.test_case_name}] > Failed to edit copy of Swath name.')
        success = self.wait_to_appear(resource_id='com.cnh.pf.android.data.management:id/tree_list_item_text',
                                      item_text=new_name)
        if success:
            print(f'[{self.test_case_name}] > Edited copy name from {old_name} to {new_name} successfully.')
        else:
            raise Exception(f'[{self.test_case_name}] > Failed to load the edited name in Data Card.')

    def deselect_all_select_one_croptypefilter(self, crop: str = None):
        """
        Deselect and select one item from crop type filter
        Args:
        Returns:
            status : todo

        """
        print(f'[{self.test_case_name}] > Deselecting All Crops.')
        status = self.wait_to_appear(resource_id='com.cnh.pf.android.data.management:id/crop_type_deselect_all_button',
                                     item_text='Deselect All')
        if status:
            self.common_functions.tap_using_ui_item(
                resource_id='com.cnh.pf.android.data.management:id/crop_type_deselect_all_button',
                item_text='Deselect All')
            self.wait_to_appear(resource_id='com.cnh.pf.android.data.management:id/btFirst', item_text='OK')
            print(f'[{self.test_case_name}] > Confirming with [OK].')
            self.common_functions.tap_using_ui_item(resource_id='com.cnh.pf.android.data.management:id/btFirst',
                                                    item_text='OK')
            self.wait_to_appear(resource_id='com.cnh.pf.android.data.management:id/crop_type_filter_checkbox',
                                item_text=crop)
            print(f'[{self.test_case_name}] > Checking required crop [{crop}].')
            self.common_functions.tap_using_ui_item(
                resource_id='com.cnh.pf.android.data.management:id/crop_type_filter_checkbox',
                item_text=crop)
            time.sleep(0.5)
            print(f'[{self.test_case_name}] > Selected requested crop [{crop}].')

    def select_all_croptypefilter(self):
        """
        Select all item from crop type filter
        Args:
        Returns:
            status : todo

        """
        print(f'[{self.test_case_name}] > Selecting All Crops.')
        status = self.wait_to_appear(resource_id='com.cnh.pf.android.data.management:id/crop_type_select_all_button',
                                     item_text='Select All')
        if status:
            self.common_functions.tap_using_ui_item(
                resource_id='com.cnh.pf.android.data.management:id/crop_type_select_all_button', item_text='Select All')
            time.sleep(2)
            print(f'[{self.test_case_name}] > Selected all crops.')

    def expand_verify_dm_tree_items(self, tree_items: List):
        """
        Expand verify items of DM Tree
        Args:
            tree_items: Item to verify from DM tree

        Returns:
            status : Status of verification

        """
        print(f'[{self.test_case_name}] > Expanding and Collecting Tree items')
        self.wait_to_appear(resource_id='com.cnh.pf.android.data.management:id/tree_view_list')
        only_expand = False
        if len(tree_items) == 0:
            tree_items = ['#']
            only_expand = True
        found_items = []
        remaining_items = tree_items
        last_item_duplicated = ''
        element_found = Display.active_display_uiautomator(resourceId='com.cnh.pf.android.data.management:id/treeview_list_item_frame_layout')
        if element_found.count > 3:
            raise Exception('Tree Already expanded')
        while True:
            break_condition = []
            element_found = Display.active_display_uiautomator(resourceId='com.cnh.pf.android.data.management:id/treeview_list_item_frame_layout')
            element_count = element_found.count
            for index in range(element_count):
                tree_view = Display.active_display_uiautomator(resourceId='com.cnh.pf.android.data.management:id/tree_view_list')
                element = tree_view.child(className='android.widget.LinearLayout', index=index)
                text = element.child(
                    resourceId='com.cnh.pf.android.data.management:id/tree_list_item_text').info['text']
                check_items_count = element_count - index
                if text not in found_items or text not in found_items[
                                                          -check_items_count:] and last_item_duplicated != text:
                    drop_down = element.child(
                        resourceId='com.cnh.pf.android.data.management:id/treeview_list_item_toggle')
                    if drop_down.exists:
                        if drop_down.click():
                            found_items.append(text)
                            last_item_duplicated = text
                            if text in remaining_items:
                                remaining_items.remove(text)
                                print(f'[{self.test_case_name}] > Collected : {text} Item found ')
                            else:
                                print(f'[{self.test_case_name}] > Collected : {text}')
                            Display.active_display_uiautomator.swipe(660, 680, 660, 600)
                            break
                    else:
                        found_items.append(text)
                        last_item_duplicated = text
                        if text in remaining_items:
                            remaining_items.remove(text)
                            print(f'[{self.test_case_name}] > Collected : {text} Item found')
                        else:
                            print(f'[{self.test_case_name}] > Collected : {text}')
                        Display.active_display_uiautomator.swipe(660, 680, 660, 600)
                        break
                else:
                    last_item_duplicated = text
                    break_condition.append(True)
            if len(break_condition) >= element_count or len(remaining_items) == 0:
                break

        print(f'[{self.test_case_name}] > Successfully expanded all tree items')
        print(f'[{self.test_case_name}] > Verifying Tree items')
        not_found = [item for item in tree_items if item.strip() not in found_items]
        if len(not_found) == 0 or only_expand:
            print(f'[{self.test_case_name}] > Successfully verify all tree items')
            return True
        raise Exception(f'DM Tree verification failed , Not Found : {not_found}')

    def expand_specific_dm_tree_item(self, tree_item_hierarchy: str, tab: str = 'Data Management'):
        """
        Expand DM Tree using specific path of DM tree ( Used for delete update items
        Args:
            tab: expand item in which tab (data management, export)
            tree_item_hierarchy:
        """
        print(f'[{self.test_case_name}] > Expanding and Collecting Tree items')
        self.wait_to_appear(resource_id='com.cnh.pf.android.data.management:id/tree_view_list')
        items_sp = tree_item_hierarchy.split('>>')
        tree_view = Display.active_display_uiautomator(resourceId='com.cnh.pf.android.data.management:id/tree_view_list')
        element_found = Display.active_display_uiautomator(resourceId='com.cnh.pf.android.data.management:id/treeview_list_item_frame_layout')
        initial_count = 0
        conflict_items_present = [True]
        if tab == 'Data Management':
            conflict_items_present = [item in DMConstants.ALWAYS_COLLAPSED_DM_ITEMS for item in items_sp]
            initial_count = 3
        elif tab == 'Export':
            conflict_items_present = [item in DMConstants.ALWAYS_COLLAPSED_DM_ITEMS for item in items_sp]
            initial_count = 4

        if any(conflict_items_present) and element_found.count > initial_count:
            print(f'[{self.test_case_name}] > Item Conflict found .. Collapsing GFFT')
            item = 'Grower/Farm/Field/Task'
            tree_view.child_by_text(item, allow_scroll_search=True)
            item_found = Display.active_display_uiautomator(text=item)
            expand_icon = item_found.left(
                resourceId='com.cnh.pf.android.data.management:id/treeview_list_item_toggle')
            if expand_icon is not None and expand_icon.exists:
                screenshot = self.click_screenshot_display(is_test_case_screenshot=True,
                                                           screenshot_name='expand_icon')
                reference = os.path.abspath(DMConstants.REFERENCE_IMAGES + '/plus.png')
                ui_info = expand_icon.info
                left = ui_info['bounds']['left']
                top = ui_info['bounds']['top']
                width = ui_info['bounds']['right'] - ui_info['bounds']['left']
                height = ui_info['bounds']['bottom'] - ui_info['bounds']['top']
                box = (left, top, width, height)
                result = self.image_comparison(image=screenshot, reference=reference, image_crop=box)
                if not result:
                    expand_icon.click()
                    self.expand_dm_tree_items = []
                    print(f'[{self.test_case_name}] > Collapsed GFFT')

        duplicate_counts = {}
        for item in items_sp:
            try:
                print(f'[{self.test_case_name}] > Searching Item : [{item}]')
                tree_view.child_by_text(item, allow_scroll_search=True)

                if item not in duplicate_counts:
                    duplicate_counts[item] = 0
                else:
                    duplicate_counts[item] += 1

                if not any(conflict_items_present) and item in self.expand_dm_tree_items and items_sp.count(item) <= 1:
                    print(f'[{self.test_case_name}] > Already expand : [{item}]')
                    continue
                else:
                    instance = duplicate_counts[item]
                    item_found = Display.active_display_uiautomator(text=item, instance=instance)
                    top_bound = item_found.info['bounds']['top']
                    if top_bound > 500:
                        os.system('adb shell input swipe 700 600 700 500')
                    time.sleep(1)
                    expand_icon = item_found.left(
                        resourceId='com.cnh.pf.android.data.management:id/treeview_list_item_toggle')
                    if (expand_icon is not None and expand_icon.exists) and items_sp[-1] != item:
                        print(f'[{self.test_case_name}] > Found Item : [{item}]')
                        print(f'[{self.test_case_name}] > Checking for expand button')
                        screenshot = self.click_screenshot_display(is_test_case_screenshot=True,
                                                                   screenshot_name='expand_icon')
                        reference = os.path.abspath(DMConstants.REFERENCE_IMAGES + '/plus.png')
                        ui_info = expand_icon.info
                        left = ui_info['bounds']['left']
                        top = ui_info['bounds']['top']
                        width = ui_info['bounds']['right'] - ui_info['bounds']['left']
                        height = ui_info['bounds']['bottom'] - ui_info['bounds']['top']
                        box = (left, top, width, height)
                        result = self.image_comparison(image=screenshot, reference=reference, image_crop=box)
                        if result:
                            expand_icon.click()
                            print(f'[{self.test_case_name}] > Expand : [{item}]')
                            if item not in DMConstants.ALWAYS_COLLAPSED_DM_ITEMS:
                                self.expand_dm_tree_items.append(item)

                        else:
                            print(f'[{self.test_case_name}] > Already Expanded : [{item}]')
                        continue

            except Exception as Err:
                raise Exception(f'Failed to expand item : [{item}]')
        return True

    def expand_verify_specific_dm_tree_items(self, tree_items: List):
        """

        Args:
            tree_items:
        """
        print(f'[{self.test_case_name}] > Expanding and Collecting Tree items')
        self.wait_to_appear(resource_id='com.cnh.pf.android.data.management:id/tree_view_list')
        failed_items = []
        for item in tree_items:
            try:
                item_text = item.split('>>')[-1]
                self.expand_specific_dm_tree_item(tree_item_hierarchy=item)
                item_widget = Display.active_display_uiautomator(text=item_text)
                if not item_widget.exists:
                    failed_items.append({item: 'Item not found'})
            except Exception as Err:
                failed_items.append({item: f'Error : {str(Err)}'})

        if len(failed_items) > 0:
            raise Exception(f'Failed to validate below field : {failed_items}')

    def edit_dm_gfft_items(self, items: Dict):
        """
        Edit item in DM tree
        Args:
            items: Information of item to edit ( check example )

        Returns:
            bool : Status of operation
        Examples:
            T_1= { 'hierarchy of element' : 'new_value'}
        """
        success = []
        failure = []
        self.expand_dm_tree_items = []
        for old_value_parent, new_value in items.items():
            old_value = old_value_parent.split(">>")[-1]
            print(f'[{self.test_case_name}] > Editing value for : {old_value}')
            self.expand_specific_dm_tree_item(tree_item_hierarchy=old_value_parent)
            try:
                dm_item = Display.active_display_uiautomator(text=old_value)
                if dm_item.exists:
                    self.common_functions.tap_using_ui_item(item_text=old_value)
                    time.sleep(1)
                    dm_item.sibling(resourceId="com.cnh.pf.android.data.management:id/mng_edit_button").click()
                    time.sleep(1.5)
                    self.common_functions.tap_using_ui_item(item_text=old_value)
                    os.system("adb shell input keyevent KEYCODE_DEL")
                    time.sleep(.5)
                    Display.active_display_uiautomator().set_text(new_value)
                    time.sleep(.5)
                    self.common_functions.tap_using_ui_item(item_text="Save")
                    success.append(True)
                    self.common_functions.tap_using_ui_item(item_text=new_value)
                    print(f'[{self.test_case_name}] > Edited {old_value} to {new_value}')
            except Exception as Err:
                print(f'[{self.test_case_name}] > Failed to Edit :{old_value}')
                success.append(False)
                failure.append(old_value + ':' + new_value)
        if all(success):
            return True
        raise Exception(f'Edit items of Home screen GFTT failed , Items : {failure}')

    def delete_dm_gftt_items(self, items: List):
        """
        Delete one or more item from DM tree
        Args:
            items: List of item to delete

        Returns:
            bool : Status of operation

        """
        success = []
        failure = []
        self.expand_dm_tree_items = []
        if isinstance(items, str):
            items = [items]
        for delete_value_parent in items:
            delete_value = delete_value_parent.split(">>")[-1]
            print(f'[{self.test_case_name}] > Editing value for : {delete_value}')
            self.expand_specific_dm_tree_item(tree_item_hierarchy=delete_value_parent)
            try:
                dm_item = Display.active_display_uiautomator(text=delete_value)
                if dm_item.exists:
                    dm_item.click()
                    time.sleep(1)
                    status = self.common_functions.tap_using_ui_item(
                        resource_id='com.cnh.pf.android.data.management:id/dm_delete_button')
                    if status:
                        time.sleep(1)
                        self.common_functions.tap_using_ui_item(item_text='Delete')
                        delete_status = self.wait_to_appear(
                            resource_id='com.cnh.pf.android.data.management:id/header_text',
                            item_text='Select item(s) to edit, copy, or delete', timeout=300)
                        ack_status = self.ack_deleted_pop_up()
                        if delete_status or ack_status:
                            success.append(True)
                        else:
                            success.append(False)
                            failure.append(f'Item : {delete_value}')
            except Exception as Err:
                success.append(False)
                failure.append(f'Item : {delete_value}')
        if all(success):
            return True
        raise Exception(f'DM Tree item Deletion failed , Items :{failure}')

    def total_items_dm_tree(self, expected_count: int, select_tree_item=None):
        """
        Count of DM tree items
        Args:
            expected_count: expected count of DM tree items
            select_tree_item: item select to count child

        Returns:
            bool : Status of operation
        """
        test_case = TestCaseHelper('a')
        verdict = False
        print(f'[{self.test_case_name}] > Verifying DM tree Selected Items')
        status = False
        select_all = Display.active_display_uiautomator(resourceId='com.cnh.pf.android.data.management:id/select_all_btn')
        select_all.click()
        if select_tree_item is None:
            status = test_case.select_data_tree()
            status = True
        else:
            select_all.click()
            status = True
        if status:
            time.sleep(2)
            header_widget = Display.active_display_uiautomator(resourceId='com.cnh.pf.android.data.management:id/header_text')
            actual = self.ui_automator_object_text(header_widget)
            expected = f'{expected_count} Items Selected'
            if actual == expected:
                verdict = True
        else:
            raise Exception(f'Items Selection failed in DM Tree')
        select_all.click()
        if verdict:
            return True
        raise Exception(f'Expected : {expected}, Actual : {actual} ')

    def total_items_export_tree(self, expected_count=None):
        """
        Count of DM tree items
        Args:
            expected_count: expected count of Export tree items

        Returns:
            bool : Status of operation
        """
        verdict = False
        print(f'[{self.test_case_name}] > Verifying Export tree Selected Items')
        select_all = Display.active_display_uiautomator(resourceId='com.cnh.pf.android.data.management:id/select_all_btn')
        status = select_all.click()
        if status:
            time.sleep(2)
            header_widget = Display.active_display_uiautomator(resourceId='com.cnh.pf.android.data.management:id/export_selected_btn')
            actual = self.ui_automator_object_text(header_widget, width_adjust=-4, top_adjust=-2)
            # expected = f'Export Selected ({expected_count})'
            # if actual == expected:
            #     verdict = True
            print(f'Export Item Count is:[{actual}]')
        else:
            raise Exception(f'Items Selection failed in Export Tree')
        select_all.click()
        # if verdict:
        #     return True
        # raise Exception(f'Error observed for count')

    # ---------------------------- Verify and create Operation screen items ----------------------------
    def select_operations_gfft_tree(self, gfft: Dict):
        """

        Args:
            gfft:
        """
        Display.active_display_uiautomator(resourceId='com.cnh.pf.phoenixapp:id/home_scroll_view').child_by_text('Grower',
                                                                                     allow_scroll_search=True)
        for title, value in gfft.items():
            print(f'[{self.test_case_name}] > Selecting [{title}] with [{value}]')
            resource_id = DMConstants.OPERATIONS_GFFT_RESOURCES_LIST.get(title, 'None')
            if resource_id is not None:
                Display.active_display_uiautomator(resourceId=resource_id).child(resourceId="com.cnh.pf.phoenixapp:id/ivArrow").click()
                try:
                    time.sleep(5)
                    Display.active_display_uiautomator(resourceId="com.cnh.pf.phoenixapp:id/picklistPopupList").child_by_text(value,
                                                                                                  allow_scroll_search=True)
                except JsonRPCError as Err:
                    self.common_functions.tap_adb(290, 578)
                    raise Exception(f'Failed to select GFFT item [{title}] with value [{value}]')
                status = self.common_functions.tap_using_ui_item(item_text=value)
                time.sleep(15)
                if status:
                    print(f'[{self.test_case_name}] > Selected [{title}] with [{value}]')
                else:
                    self.common_functions.tap_adb(290, 578)
                    raise Exception('Failed to select GFFT and Crop type')

    def configure_operation_screen_product_assignment(self, product_assignment: Dict):
        """

        Args:
            product_assignment:
        """
        print(f'[{self.test_case_name}] > Configuring product assignments')
        Display.active_display_uiautomator(scrollable=True).scroll.to(resourceId='com.cnh.pf.phoenixapp:id/controller_selector')
        top_bound = Display.active_display_uiautomator(resourceId='com.cnh.pf.phoenixapp:id/controller_selector').info['bounds']['top']
        if top_bound > 500:
            os.system('adb shell input swipe 700 600 700 450')

        controller = product_assignment.get('Controller')
        product = product_assignment.get('Product')
        prescription = product_assignment.get('Prescription')
        if controller is None:
            raise Exception('One of the required field is missing')

        print(f'[{self.test_case_name}] > Selecting controller : [{controller}]')
        controller_radio_button = Display.active_display_uiautomator(text=controller, className='android.widget.RadioButton')
        if controller_radio_button.exists:
            controller_radio_button.click()
            print(f'[{self.test_case_name}] > Selected controller : [{controller}]')
        else:
            raise Exception(f'Controller [{controller}] not found in assignment window')

        if product is not None:
            print(f'[{self.test_case_name}] > Selecting Product : [{product}]')
            Display.active_display_uiautomator(scrollable=True).scroll.to(resourceId='com.cnh.pf.phoenixapp:id/product_rate_1_inputfield')
            Display.active_display_uiautomator(resourceId='com.cnh.pf.phoenixapp:id/product_picklist').child(
                resourceId='com.cnh.pf.phoenixapp:id/ivArrow').click()
            Display.active_display_uiautomator(resourceId='com.cnh.pf.phoenixapp:id/picklistPopupList').child_by_text(product,
                                                                                          allow_scroll_search=True)
            status = self.common_functions.tap_using_ui_item(item_text=product)
            if not status:
                raise Exception(f'Product [{product}] not found in assignment window')
            print(f'[{self.test_case_name}] > Selected product : [{product}]')

        if prescription is not None:
            print(f'[{self.test_case_name}] > Selecting prescription : [{prescription}]')
            if product is None:
                Display.active_display_uiautomator(scrollable=True).scroll.toEnd()
                os.system("adb shell input swipe 350 350 350 550")
            Display.active_display_uiautomator(resourceId='com.cnh.pf.phoenixapp:id/prescription_picklist').child(
                resourceId='com.cnh.pf.phoenixapp:id/ivArrow').click()
            rx_prescription = f'Rx_{prescription}'
            try:
                Display.active_display_uiautomator(resourceId='com.cnh.pf.phoenixapp:id/picklistPopupList').child_by_text(rx_prescription,
                                                                                              allow_scroll_search=True)
                status = self.common_functions.tap_using_ui_item(item_text=rx_prescription)
            except (JsonRPCError, Exception) as Err:
                print(f'[{self.test_case_name}] > Trying prescription name for old build [{prescription}]')
                Display.active_display_uiautomator(resourceId='com.cnh.pf.phoenixapp:id/picklistPopupList').child_by_text(prescription,
                                                                                              allow_scroll_search=True)
                status = self.common_functions.tap_using_ui_item(item_text=prescription)
            if not status:
                raise Exception(f'Prescription [{prescription}] not found in assignment window')
            print(f'[{self.test_case_name}] > Selected prescription : [{prescription}]')
            return True

    def verify_operation_screen_tree_items(self, tree_items: Union[List[Dict], dict]):
        """
        Verify Home Screen item
        Args:
            tree_items: Tree item details to verify ( Check Example)

        Returns:
            bool : Status of operation
        Examples:
            1. dict
                T1= {"Grower": "NoGrower","Farm": "NoFarm", "Field": "NoField","TaskList": ['TASK1','TASK2']}
            2. list
                T= [T1]
        """
        print(f'[{self.test_case_name}] > Verify Home screen items')
        if isinstance(tree_items, dict):
            tree_items = [tree_items]
        not_found = []
        for item in tree_items:
            drop_down_clicked = False
            for field, resource_id in DMConstants.GDS_RESOURCE_ID.items():
                os.system('adb shell input swipe 700 400 700 600')  # Swipe up
                ui_item_checkbox_parent = Display.active_display_uiautomator(resourceId=resource_id)
                if ui_item_checkbox_parent.exists:
                    ui_item_checkbox = ui_item_checkbox_parent.child(resourceId="com.cnh.pf.phoenixapp:id/ivArrow")
                    if ui_item_checkbox.exists:
                        ui_item_checkbox.click()
                        drop_down_clicked = True
                        time.sleep(2)

                if drop_down_clicked:
                    verify_text = item[field]
                    if field != 'TaskList':
                        try:
                            Display.active_display_uiautomator(className="android.widget.ListView",
                                   resourceId="com.cnh.pf.phoenixapp:id/picklistPopupList").child_by_text(verify_text,
                                                                                                          allow_scroll_search=True,
                                                                                                          resourceId="com.cnh.pf.phoenixapp:id/picklistItem",
                                                                                                          className="android.widget.TextView").click()
                            print(f'[{self.test_case_name}] > Verified field {field} = {verify_text}, Status : True')
                        except JsonRPCError as er:
                            not_found.append({'item': item, 'Exception': f'Failed to identify : {verify_text}'})
                            self.common_functions.tap_adb(673, 222)
                            print(f'[{self.test_case_name}] > Verified field {field} = {verify_text}, Status : False')
                    else:
                        not_found_task = []
                        for task in verify_text:
                            try:
                                task_ui_item = Display.active_display_uiautomator(className="android.widget.ListView",
                                                      resourceId="com.cnh.pf.phoenixapp:id/picklistPopupList").child_by_text(
                                    task,
                                    allow_scroll_search=True,
                                    resourceId="com.cnh.pf.phoenixapp:id/picklistItem",
                                    className="android.widget.TextView")
                                if not task_ui_item.exists:
                                    not_found_task.append(task)
                                    print(
                                        f'[{self.test_case_name}] > Verified field Tasks = {task}, Status : False')
                                else:
                                    print(f'[{self.test_case_name}] > Verified field Tasks = {task}, Status : True')
                            except JsonRPCError:
                                not_found_task.append(task)
                                print(f'[{self.test_case_name}] > Verified field Tasks = {task}, Status : False')
                        if len(not_found_task) > 0:
                            not_found.append(
                                {'item': item, 'Exception': f'Failed to identify : {",".join(not_found_task)}'})
                        self.common_functions.tap_adb(673, 222)
                else:
                    raise Exception(f'Dropdown not clicked for : {field}')

        if len(not_found) == 0:
            return True
        else:
            not_found = json.dumps(not_found, indent=2)
            raise Exception(f'Failed to verify items : {not_found}')

    def verify_operation_screen_deleted_tree_item(self, set_items: dict, check_value: dict):
        """
        Verify home screen item with deleted item
        Args:
            set_items: item to selected for home screen
            check_value: checking for deleted item

        Returns:
            bool : Status of operation

        """
        print(f'[{self.test_case_name}] > Verify item is deleted from operation screen')
        for field in DMConstants.OPERATION_SCREEN_ORDER:
            resource_id = DMConstants.GDS_RESOURCE_ID.get(field)
            set_value = set_items.get(field)
            drop_down_clicked = False
            if resource_id is not None and set_value is not None:
                print(f'[{self.test_case_name}] > Setting item [{field}] with value [{set_value}]')
                ui_item_checkbox_parent = Display.active_display_uiautomator(resourceId=resource_id)
                if ui_item_checkbox_parent.exists:
                    ui_item_checkbox = ui_item_checkbox_parent.child(resourceId="com.cnh.pf.phoenixapp:id/ivArrow")
                    if ui_item_checkbox.exists:
                        ui_item_checkbox.click()
                        drop_down_clicked = True
                        time.sleep(2)

                if drop_down_clicked:
                    not_found = True
                    value_row = None
                    try:
                        value_row = Display.active_display_uiautomator(className="android.widget.ListView",
                                           resourceId="com.cnh.pf.phoenixapp:id/picklistPopupList").child_by_text(
                            set_value,
                            allow_scroll_search=True,
                            resourceId="com.cnh.pf.phoenixapp:id/picklistItem",
                            className="android.widget.TextView")
                        if value_row.exists:
                            not_found = False
                    except:
                        pass

                    if not not_found and check_value != set_value:
                        print(f'[{self.test_case_name}] > Item set [{field}] with value [{set_value}]')
                        value_row.click()
                    elif check_value == set_value:
                        print(f'[{self.test_case_name}] > Item Deleted : [{field} : {set_value}]')
                        self.common_functions.tap_adb(300, 695)
                        return True
                    else:
                        self.click_screenshot_display(is_test_case_screenshot=True,
                                                      screenshot_name=f'Deleted_item_{set_value}')
                        self.common_functions.tap_adb(300, 695)
                        raise Exception(f'Failed to delete item [{field} : {set_value}]')

    def create_operation_screen_gftt_items(self, items: Dict):
        """
        Creating home screen items
        Args:
            items: Details of items ( Example )

        Returns:
            bool : Status of operation
        Examples:
            T_1 = {"Grower": "Grower1","Farm": "Farm1","Field": "Field1","Task": "Task1"}
        """
        success = []
        failure = []
        for title, value in items.items():
            print(f'[{self.test_case_name}] > Creating item : {title} with value : {value}')
            resource_id = DMConstants.HOME_SCREEN_GFFT_RESOURCES_LIST.get(title, 'None')
            if resource_id is not None:
                Display.active_display_uiautomator(resourceId=resource_id).child(resourceId="com.cnh.pf.phoenixapp:id/ivArrow").click()
                time.sleep(1)
                status = self.common_functions.tap_using_ui_item(item_text='Add New')
                if status:
                    Display.active_display_uiautomator().set_text(value)
                    time.sleep(1)
                    self.common_functions.tap_adb(1130, 690)
                    self.common_functions.tap_using_ui_item(item_text='Apply')
                    success.append(True)
                    time.sleep(0.5)
                    print(f'[{self.test_case_name}] > Successfully Created item with value : {value}')
                    continue
                else:
                    failure.append(title + ':' + value)
                    success.append(False)
                    print(f'[{self.test_case_name}] > Failed to Create item with value : {value}')

        if all(success):
            return True
        raise Exception(f'Creation of Home screen GFTT failed , Items : {failure}')

    def verify_operation_screen_selected_options(self, items: Dict):
        """
        Check for item selected in Home Screen
        Args:
            items: Item details to check ( Example )

        Returns:
            bool : Status of verification

        Examples:
            T_1 = {'Grower': 'NoGrower','Farm': 'NoFarm','Field': 'NoField','Task': 'CART HAULING 2020 NoField'}
        """
        success = []
        failure = []

        for title, value in items.items():
            print(f'[{self.test_case_name}] > Validating Item : {title} with value : {value}')
            try:
                resource_id = DMConstants.HOME_SCREEN_GFFT_RESOURCES_LIST.get(title, 'None')
                if resource_id is not None:
                    if self.wait_to_appear(resource_id=resource_id):
                        selected_item = Display.active_display_uiautomator(resourceId=resource_id).child(
                            resourceId="com.cnh.pf.phoenixapp:id/tvHeaderText")
                        if selected_item.exists:
                            selected_text = selected_item.info['text']
                            if selected_text == value:
                                success.append(True)
                                print(f'[{self.test_case_name}] > Successfully validated Item : {title} > {value}')
                            else:
                                success.append(False)
                                failure.append({'Tree Items': title, 'Expected': value, 'Actual': selected_text})
                                print(f'[{self.test_case_name}] > Failed to  validated Item : {title} > {value}')
                            continue
            except Exception as E:
                failure.append(f'Exception : For title {title} and error : {str(E)}')

        if len(failure) == 0:
            return True
        failure = json.dumps(failure, indent=2)
        raise Exception(f'Validation of Home Screen Selected items Failed , Items : {failure}')

    def verify_operation_screen_drive_product_information(self, product_name, product_info={}, is_deleted=False):
        """

        Args:
            is_deleted:
            product_name:
            product_info:
        """
        print(f'[{self.test_case_name}] > Verifying product in drive')
        Display.active_display_uiautomator(scrollable=True).scroll.to(resourceId='com.cnh.pf.phoenixapp:id/rate_1_inputfield')
        Display.active_display_uiautomator(resourceId='com.cnh.pf.phoenixapp:id/product_picklist').child(
            resourceId='com.cnh.pf.phoenixapp:id/ivArrow').click()
        status = False
        try:
            Display.active_display_uiautomator(resourceId='com.cnh.pf.phoenixapp:id/picklistPopupList').child_by_text(product_name,
                                                                                          allow_scroll_search=True)
            status = self.common_functions.tap_using_ui_item(item_text=product_name)
            print(f'[{self.test_case_name}] > Product Selected [{product_name}]')
        except:
            pass

        if not status:
            print(f'[{self.test_case_name}] > Product not found [{product_name}]')
            self.common_functions.tap_adb(1240, 115)
            if is_deleted:
                return True
            else:
                raise Exception(f'Product [{product_name}] not found in assignment window')

        status = []
        failed = {}
        for title, value in product_info.items():
            resource_id = DMConstants.OPERATION_SCREEN_PRODUCT_DRIVE_RESOURCES.get(title)
            if resource_id is not None:
                print(f'[{self.test_case_name}] > Verifying field : [{title}], expected : [{value}]')
                Display.active_display_uiautomator(scrollable=True).scroll.to(resourceId=resource_id)
                widget = Display.active_display_uiautomator(resourceId=resource_id).child(className='android.widget.EditText')
                if widget.exists:
                    actual = widget.info['text']
                    print(f'[{self.test_case_name}] > Actual : [{value}]')
                    if actual == value:
                        status.append(True)
                    else:
                        status.append(False)
                        failed[title] = {'Expected': value, 'Actual': actual}

        if not all(status):
            raise Exception(f'Failed to validated fields , {failed}')

    def verify_operation_screen_custom_row_product(self, product_name, is_deleted=False):
        """

        Args:
            is_deleted:
            product_name:
        """
        # pass
        print(f'[{self.test_case_name}] > Verifying product in custom row')
        Display.active_display_uiautomator(scrollable=True).scroll.to(resourceId='com.cnh.pf.phoenixapp:id/variety_picklist')
        Display.active_display_uiautomator(resourceId='com.cnh.pf.phoenixapp:id/variety_picklist').child(
            resourceId='com.cnh.pf.phoenixapp:id/ivArrow').click()
        status = False
        try:
            Display.active_display_uiautomator(resourceId='com.cnh.pf.phoenixapp:id/picklistPopupList').child_by_text(product_name,
                                                                                          allow_scroll_search=True)
            status = self.common_functions.tap_using_ui_item(item_text=product_name)
            print(f'[{self.test_case_name}] > Product Selected [{product_name}]')
        except:
            pass

        if not status:
            print(f'[{self.test_case_name}] > Product not found [{product_name}]')
            self.common_functions.tap_adb(1240, 115)
            if is_deleted:
                return True
            else:
                raise Exception(f'Product [{product_name}] not found in assignment window')

    # ---------------------------- XML Comparison ----------------------------

    def xml_matching(self, is_complex: bool = False, node_unique_attrs: str = None):
        """
        Matching XML elements
        Args:
            node_unique_attrs:
            is_complex: Complexity of xml ( multiple modifications or similar tags with common attributes)

        Returns:
            bool : Status of matching

        """
        if node_unique_attrs is None:
            node_unique_attrs = []
        import_xml = os.path.abspath(self.import_directory + f'/{self.test_case_name}/TASKDATA.XML')
        export_xml = os.path.abspath(self.export_directory + f'/{self.test_case_name}/TASKDATA.XML')

        if not (os.path.isfile(import_xml) and os.path.isfile(export_xml)):
            raise Exception("Import/Export XML TASKDATA file not found")

        result, difference = XMLOperations.xml_match_data_management(import_xml=import_xml, export_xml=export_xml,
                                                                     is_complex=is_complex,
                                                                     node_unique_attrs=node_unique_attrs)
        if result:
            print(f'[{self.test_case_name}] > Both XML are identical')
        else:
            diff_pretty = json.dumps(difference, indent=4)
            exception = f'Difference : {diff_pretty}\n\n\n Import XML : {import_xml}\nExport XML : {export_xml}'
            raise Exception(f'XML are not identical \n {exception}')

    def verify_export_xml_attributes(self, check_items: List[Dict[str, Union[str, Dict[str, str]]]], is_deleted=False,
                                     export_path=None):
        """
        Check item of export xml with expected values
        Args:
            is_deleted:
            check_items: The information of items to verify

        Returns:
            bool : verification status
        Examples:
            >>> test_case = TestCaseHelper('test')
            >>> A = {'TagIdentifier': '/TSK:B=TILLAGE 2021 NoField/TIM/DLV:0', 'ValidateAttributes': {'B': '0'}}
            >>> C = {'TagIdentifier': '/TSK:B=TILLAGE 2021 NoField/TIM', 'ValidateAttributes': {'B': '@otherThan[0]'}}
            >>> E = {'TagIdentifier': '/TSK:B=TILLAGE 2021 NoField/TIM/DLV:4', 'ValidateAttributes': {'B': '0'}}
            >>> F = {'TagIdentifier': '/TSK:B=TILLAGE 2021 NoField/TIM', 'ValidateAttributes': {'B': '@contains[PDT]'}}
            >>> test_case.verify_export_xml_attributes([A,C,E,F])

        """
        if export_path == None:
            export_xml = os.path.abspath(self.export_directory + f'/{self.test_case_name}/TASKDATA.XML')
        else:
            export_xml = os.path.abspath(export_path + '/TASKDATA.XML')
        print(export_path)

        if not os.path.isfile(export_xml):
            raise Exception("Export XML TASKDATA file not found")
        check_pretty = json.dumps(check_items, indent=2)
        print(f'[{self.test_case_name}] > Verifying Items : \n {check_pretty}')
        final_result, failures = XMLOperations.verify_export_xml_attribute(export_xml, check_items, is_deleted)
        if not final_result:
            failures_pretty = json.dumps(failures, indent=4)
            raise Exception(f'Failed to validated below attributes \n{failures_pretty}')
        print(f'[{self.test_case_name}] > Verify all items for Export XML')
        return True

    def get_element_value_of_any_attribute(self, check_items: List[Dict[str, str]], export_path=None):
        """
        get values of  any element of uniq attr of export xml with expected values
        Args:
            check_items: The information of the items
            attr_element: element whose value required

        Returns:
            ele_value : attr_element value
        Examples:
            >>> test_case = TestCaseHelper('test')
            >>> A = {'TagIdentifier': '/TSK:B=TILLAGE 2021 NoField/TIM/DLV:0', 'Element':'B'}
            >>> test_case.get_element_value_of_any_attribute([A])

        """
        if export_path == None:
            export_xml = os.path.abspath(self.export_directory + f'/{self.test_case_name}/TASKDATA.XML')
        else:
            export_xml = os.path.abspath(export_path + '/TASKDATA.XML')

        print(export_path)

        if not os.path.isfile(export_xml):
            raise Exception("Export XML TASKDATA file not found")
        # check_pretty = json.dumps(check_items, indent=2)
        # print(f'[{self.test_case_name}] > Verifying Items : \n {check_pretty}')
        final_result, ele_value = XMLOperations.get_element_value_of_attribute(export_xml, check_items)
        if not final_result:
            print(f'Failed to get the value of element: {ele_value}')
        else:
            print(f'Successful to get the value of element: {ele_value}')
        return ele_value

    def verify_export_xml_item_count(self, check_items: List[Dict[str, Union[str, Dict[str, str]]]], export_path=None):
        """
        Check item of export xml with expected values
        Args:
            check_items: The information of items to verify

        Returns:
            bool : verification status
        Examples:
            >>> test_case = TestCaseHelper('test')
            >>> A = {'Parent': '/PDT','Condition': 'P094_ProductColor=1:920000','Count': 2}
            >>> test_case.verify_export_xml_attributes([A])
        """
        if export_path == None:
            export_xml = os.path.abspath(self.export_directory + f'/{self.test_case_name}/TASKDATA.XML')
        else:
            export_xml = os.path.abspath(export_path + '/TASKDATA.XML')
        print(export_path)
        if not os.path.isfile(export_xml):
            raise Exception("Export XML TASKDATA file not found")
        check_pretty = json.dumps(check_items, indent=2)
        print(f'[{self.test_case_name}] > Verifying Items : \n {check_pretty}')
        final_result, failures = XMLOperations.verify_export_xml_attribute_count(export_xml, check_items)
        if not final_result:
            failures_pretty = json.dumps(failures, indent=4)
            raise Exception(f'Failed to validated below attributes \n{failures_pretty}')
        print(f'[{self.test_case_name}] > Verify all items for Export XML')
        return True

    def xml_matching_with_attribute_deletion(self, items: List, is_complex: bool = False,
                                             node_unique_attrs: str = None):
        """
        XML matching with deleted attribute in export xml
        Args:
            items: items that are deleted from xml
            is_complex: Complexity of xml ( multiple modifications or similar tags with common attributes)
            node_unique_attrs : unique attribute to identify node
        Returns:
            bool : status of matching

        Examples:
            Exact Element Hierarchy , Use [] for indexing elements and > for Attribute Name
            >>> test_helper = TestCaseHelper('test_xml_delete')
            >>> ATTR_DELETE = ["/ISO11783_TaskData/PFD/GGP/GPN[1]>G"]
            >>> test_helper.xml_matching_with_attribute_deletion(items=ATTR_DELETE)
        """
        if node_unique_attrs is None:
            node_unique_attrs = []
        import_xml = os.path.abspath(self.import_directory + f'/{self.test_case_name}/TASKDATA.XML')
        export_xml = os.path.abspath(self.export_directory + f'/{self.test_case_name}/TASKDATA.XML')

        if not (os.path.isfile(import_xml) and os.path.isfile(export_xml)):
            raise Exception("Import/Export XML TASKDATA file not found")

        modification = {'attr_deleted': items}
        items_pretty = json.dumps(items, indent=4)
        print(f'[{self.test_case_name}] > Comparing with Attribute Delete :\n{items_pretty}')
        final_result, final_diff, new_import_xml, new_export_xml = XMLOperations.compare_xml(import_xml=import_xml,
                                                                                             export_xml=export_xml,
                                                                                             is_complex=is_complex,
                                                                                             modification=modification,
                                                                                             node_unique_attrs=node_unique_attrs)
        if final_result:
            print(f'[{self.test_case_name}] > Both XML are identical')
            return True
        diff_pretty = json.dumps(final_diff, indent=4)
        raise Exception(f'XML does not match after update : \n{diff_pretty}')

    def xml_matching_with_attribute_update(self, items: List, is_complex: bool = False, node_unique_attrs: str = None):
        """
        XML matching with updated attribute in export xml
        Args:
            items: items that are updated in xml
            is_complex: Complexity of xml ( multiple modifications or similar tags with common attributes)
            node_unique_attrs : unique attribute to identify node
        Returns:
            bool : Status of xml matching

        Examples:
            Exact Element Hierarchy , Use [] for indexing elements and > for Attribute Name and another > for Value
            >>> test_helper = TestCaseHelper('test_xml_update')
            >>> ATTR_UPDATE = ["/ISO11783_TaskData/PFD/GGP/GPN/LSG[1]>A>5"]
            >>> test_helper.xml_matching_with_attribute_update(items=ATTR_UPDATE)

        """
        if node_unique_attrs is None:
            node_unique_attrs = []
        import_xml = os.path.abspath(self.import_directory + f'/{self.test_case_name}/TASKDATA.XML')
        export_xml = os.path.abspath(self.export_directory + f'/{self.test_case_name}/TASKDATA.XML')

        if not (os.path.isfile(import_xml) and os.path.isfile(export_xml)):
            raise Exception("Import/Export XML TASKDATA file not found")

        modification = {'attr_updated': items}
        items_pretty = json.dumps(items, indent=4)
        print(f'[{self.test_case_name}] > Comparing with Attribute Update :\n{items_pretty}')
        final_result, final_diff, new_import_xml, new_export_xml = XMLOperations.compare_xml(import_xml=import_xml,
                                                                                             export_xml=export_xml,
                                                                                             is_complex=is_complex,
                                                                                             modification=modification,
                                                                                             node_unique_attrs=node_unique_attrs)
        if final_result:
            print(f'[{self.test_case_name}] > Both XML are identical')
            return True
        diff_pretty = json.dumps(final_diff, indent=4)
        raise Exception(f'XML does not match after update : \n{diff_pretty}')

    def xml_matching_with_multiple_actions(self, items: Dict, is_complex: bool = False, node_unique_attrs: str = None):
        """
        XML matching with multiple actions
        Args:
            items: Item actions and node,atrribute details
            is_complex: Complexity of xml ( multiple modifications or similar tags with common attributes)
            node_unique_attrs : unique attribute to identify node
        Returns:
            bool : status of matching

        Examples:
            Exact Element Hierarchy , Use [] for indexing elements and > for Attribute Name
            available options :
            1) tag_deleted : '/ISO11783_TaskData/PFD/PNT'
            2) tag_inserted :
            3) attr_deleted : '/ISO11783_TaskData/PFD/PLN/LSG[1]>B'
            4) attr_inserted : '/ISO11783_TaskData/PFD/PLN/LSG[1]>A>8'
            5) attr_updated : '/ISO11783_TaskData/PFD/PLN/LSG/PNT[1]>A>1'
            >>> test_helper = TestCaseHelper('test_xml_muitlple_actions')
            >>> ACTIONS = {'attr_deleted':['/ISO11783_TaskData/PFD/PLN/LSG[1]>B'],
            >>>             'attr_updated':['/ISO11783_TaskData/PFD/PLN/LSG/PNT[1]>A>1']}
            >>> test_helper.xml_matching_with_attribute_deletion(items=ACTIONS)
        """
        if node_unique_attrs is None:
            node_unique_attrs = []
        import_xml = os.path.abspath(self.import_directory + f'/{self.test_case_name}/TASKDATA.XML')
        export_xml = os.path.abspath(self.export_directory + f'/{self.test_case_name}/TASKDATA.XML')

        if not (os.path.isfile(import_xml) and os.path.isfile(export_xml)):
            raise Exception("Import/Export XML TASKDATA file not found")

        items_pretty = json.dumps(items, indent=4)
        print(f'[{self.test_case_name}] > Comparing with Below actions :\n{items_pretty}')
        final_result, final_diff, new_import_xml, new_export_xml = XMLOperations.compare_xml(import_xml=import_xml,
                                                                                             export_xml=export_xml,
                                                                                             is_complex=is_complex,
                                                                                             modification=items,
                                                                                             node_unique_attrs=node_unique_attrs)
        if final_result:
            print(f'[{self.test_case_name}] > Both XML are identical')
            return True
        diff_pretty = json.dumps(final_diff, indent=4)
        raise Exception(f'XML does not match after comparing : \n{diff_pretty}')

    # ---------------------------- JSON Comparison ----------------------------

    def json_file_matching(self, hash_match: bool = False):
        import json
        import os
        import hashlib
        global tractor_brand_1, tractor_brand_2, tractor_name_1, tractor_name_2, tractor_id_1, tractor_id_2
        global extract, settings, username_1, userid_1, username_2, userid_2, DAY_NIGHT_SETTINGS, VOLUME_SETTINGS, \
            sysId_1, sysId_2, tractor_id, tractor_name, tractor_brand
        res_1 = []
        vol_1 = []
        res_2 = []
        vol_2 = []
        Green = "\033[92m{}\033[00m"
        Red = "\033[91m{}\033[00m"
        # ------------------ User/Vehicle JSON file import in program -------------------------------- #
        import_user_json = os.path.abspath(self.import_directory + f'/{self.test_case_name}/USER.JSN')
        import_vehicle_json = os.path.abspath(self.import_directory + f'/{self.test_case_name}/VEHICLE.JSN')
        export_user_json = os.path.abspath(self.export_directory + f'/{self.test_case_name}/USER.JSN')
        export_vehicle_json = os.path.abspath(self.export_directory + f'/{self.test_case_name}/VEHICLE.JSN')
        # ------------------ User/Vehicle JSON file loading in memory -------------------------------- #
        import_user_file = open(import_user_json)
        import_user_data = json.load(import_user_file)  # import user json file

        import_vehicle_file = open(import_vehicle_json)
        import_vehicle_data = json.load(import_vehicle_file)  # import vehicle json file

        export_user_file = open(export_user_json)  # export user file
        export_user_data = json.load(export_user_file)

        export_vehicle_file = open(export_vehicle_json)  # export vehicle file
        export_vehicle_data = json.load(export_vehicle_file)

        # ---------------- Hash Matching of import/export USER.JSON/VEHICLE.JSON files ------------------ #
        if hash_match:
            hash_1 = hashlib.md5()
            import_user = open(import_user_json, 'rb')
            buf_1 = import_user.read()
            hash_1.update(buf_1)
            hash_2 = hashlib.md5()
            export_user = open(export_user_json, 'rb')
            buf_2 = export_user.read()
            hash_2.update(buf_2)
            if str(hash_1.hexdigest()) == str(hash_2.hexdigest()):
                print(Green.format(f'[{self.test_case_name}] > Imported USER.JSN matched with Exported USER.JSN file.'))
            else:
                print(Red.format(
                    f'[{self.test_case_name}] > Imported USER.JSN does not match with Exported USER.JSN file.'))

            v_hash_1 = hashlib.md5()
            import_vehicle = open(import_vehicle_json, 'rb')
            v_buf_1 = import_vehicle.read()
            v_hash_1.update(v_buf_1)
            v_hash_2 = hashlib.md5()
            export_vehicle = open(import_vehicle_json, 'rb')
            v_buf_2 = export_vehicle.read()
            v_hash_2.update(v_buf_2)
            if str(v_hash_1.hexdigest()) == str(v_hash_2.hexdigest()):
                print(Green.format(
                    f'[{self.test_case_name}] > Imported VEHICLE.JSN matched with Exported VEHICLE.JSN file.'))
            else:
                print(Red.format(
                    f'[{self.test_case_name}] > Imported VEHICLE.JSN does not match with Exported VEHICLE.JSN file.'))
        else:
            print()
            pass
            return True
        # ----------------- USERS.JSON Data Extraction --------------- #
        print("-------- Monitoring Variable Sanity --------")
        for i in import_user_data["users"]:
            for key, values in i.items():
                if key == 'data':
                    extract = values
        for key, values in extract.items():
            if key == 'SYSTEM_SETTINGS':
                settings = values
            if key == 'userName':
                username_1 = values
            if key == 'userId':
                userid_1 = values
        for key, values in settings.items():
            if key == 'DAY_NIGHT_SETTINGS':
                DAY_NIGHT_SETTINGS = values
            if key == 'VOLUME_SETTINGS':
                VOLUME_SETTINGS = values
            if key == 'sysId':
                sysId_1 = values
        for key in DAY_NIGHT_SETTINGS.keys():
            res_1.append(DAY_NIGHT_SETTINGS[key])
        for key in VOLUME_SETTINGS.keys():
            vol_1.append(VOLUME_SETTINGS[key])
        import_user_file.close()

        for i in export_user_data["users"]:
            for key, values in i.items():
                if key == 'data':
                    extract = values
        for key, values in extract.items():
            if key == 'SYSTEM_SETTINGS':
                settings = values
            if key == 'userName':
                username_2 = values
            if key == 'userId':
                userid_2 = values
        for key, values in settings.items():
            if key == 'DAY_NIGHT_SETTINGS':
                DAY_NIGHT_SETTINGS = values
            if key == 'VOLUME_SETTINGS':
                VOLUME_SETTINGS = values
            if key == 'sysId':
                sysId_2 = values
        for key in DAY_NIGHT_SETTINGS.keys():
            res_2.append(DAY_NIGHT_SETTINGS[key])
        for key in VOLUME_SETTINGS.keys():
            vol_2.append(VOLUME_SETTINGS[key])
        export_user_file.close()
        print(f"> Username Match: ", username_1 == username_2, '\n'
                                                               "UserID Match  : ", userid_1 == userid_2, '\n'
                                                                                                         "DAY_NIGHT_SETTINGS Match: ",
              res_1 == res_2, '\n'
                              "VOLUME_SETTINGS Match   : ", vol_1 == vol_2, '\n'
                                                                            "SYSTEM_ID Match         : ",
              sysId_1 == sysId_2)
        # ----------------- VEHICLE.JSON Data Extraction --------------- #
        for VIN in import_vehicle_data["TRACTOR_CONTROL_CONFIG"]:
            for key, values in VIN.items():
                if key == 'brand':
                    tractor_brand_1 = values
                if key == 'designator':
                    tractor_name_1 = values
                if key == 'id':
                    tractor_id_1 = values
        import_vehicle_file.close()
        for VIN in export_vehicle_data["TRACTOR_CONTROL_CONFIG"]:
            for key, values in VIN.items():
                if key == 'brand':
                    tractor_brand_2 = values
                if key == 'designator':
                    tractor_name_2 = values
                if key == 'id':
                    tractor_id_2 = values
        export_vehicle_file.close()
        print(f"> Tractor Brand Match: ", tractor_brand_1 == tractor_brand_2, '\n'
                                                                              "Tractor Name Match : ",
              tractor_name_1 == tractor_name_2, '\n'
                                                "Tractor ID Match   : ", tractor_id_1 == tractor_id_2)
        print("------------------------------------")
        # ------------- Extracted data outputs -------- #
        print("Imported USER.JSN & VEHICLE.JSN files")
        print("UserName : ", username_1)
        print("UserID : ", userid_1)
        print("System ID: ", sysId_1)
        print('\n')
        print("DAY_NIGHT_SETTINGS --------------" '\n'
              "Day: ", res_1[0], '\n'
                                 "DaySecondary: ", res_1[1], '\n'
                                                             "Night: ", res_1[2], '\n'
                                                                                  "NightSecondary: ", res_1[3], '\n'
                                                                                                                "\n ")
        print("VOLUME_SETTINGS ------------------" '\n'
              "Volume Primary: ", vol_1[0], '\n'
                                            "Volume Secondary: ", vol_1[1], '\n')

        print("TRACTOR_CONTROL_CONFIG ---------------" '\n'
              "Tractor Brand: ", tractor_brand_1, '\n'
                                                  "Tractor Name: ", tractor_name_1, '\n'
                                                                                    "Tractor ID: ", tractor_id_1, '\n')
        print('\n')
        print("Exported USER.JSN & VEHICLE.JSN files")
        print("UserName : ", username_2)
        print("UserID : ", userid_2)
        print("System ID: ", sysId_2)
        print('\n')
        print("DAY_NIGHT_SETTINGS --------------" '\n'
              "Day: ", res_2[0], '\n'
                                 "DaySecondary: ", res_2[1], '\n'
                                                             "Night: ", res_2[2], '\n'
                                                                                  "NightSecondary: ", res_2[3], '\n'
                                                                                                                "\n ")
        print("VOLUME_SETTINGS ------------------" '\n'
              "Volume Primary: ", vol_2[0], '\n'
                                            "Volume Secondary: ", vol_2[1], '\n')

        print("TRACTOR_CONTROL_CONFIG ---------------" '\n'
              "Tractor Brand: ", tractor_brand_2, '\n'
                                                  "Tractor Name: ", tractor_name_2, '\n'
                                                                                    "Tractor ID: ", tractor_id_2, '\n')
        # ---------------------------------------- JSON Matching End ----------------------------------------- #

    # ---------------------------- tesseract verifications ----------------------------

    def ui_automator_object_text(self, ui_object, left_adjust: int = 0, top_adjust: int = 0, width_adjust: int = 0,
                                 height_adjust: int = 0):
        """
        OCR text extract from ui automator widget
        Args:
            ui_object: UI widget from ui automator
            left_adjust: adjust left co-ordinate
            top_adjust: adjust top co-ordinate
            width_adjust: adjust width co-ordinate
            height_adjust: adjust height co-ordinate

        Returns:

        """
        print(f'[{self.test_case_name}] > Extracting text from UI object')
        is_tesseract_path_found = False

        for path in TestSuitConfig.TESSERACT_CMD:
            if os.path.isfile(path):
                pytesseract.tesseract_cmd = path
                is_tesseract_path_found = True
                break

        if not is_tesseract_path_found:
            raise Exception(f'Tesseract cmd not found at below paths : {TestSuitConfig.TESSERACT_CMD}')

        ui_info = ui_object.info
        left = ui_info['bounds']['left'] + left_adjust
        top = ui_info['bounds']['top'] + top_adjust
        width = ui_info['bounds']['right'] - ui_info['bounds']['left'] + width_adjust
        height = ui_info['bounds']['bottom'] - ui_info['bounds']['top'] + height_adjust

        screenshot_path = self.click_screenshot_display()
        screenshot = Image.open(screenshot_path)
        box = (left, top, left + width, top + height)
        area = screenshot.crop(box)
        cropped_path = os.path.abspath(DMConstants.TEMP_SCREENSHOT + f'/ui_object_verify.png')
        area.save(cropped_path)

        print(f'[{self.test_case_name}] > Getting data from tesseract cmd')
        text = pytesseract.image_to_string(cropped_path, config='--psm 11', lang='eng').strip()
        print(f'[{self.test_case_name}] > Text extracted : {text}')
        return text

    def ui_automator_object_tap(self, ui_object, left_adjust: int = 0, top_adjust: int = 0):
        """
        OCR text extract from ui automator widget
        Args:
            ui_object: UI widget from ui automator
            left_adjust: adjust left co-ordinate
            top_adjust: adjust top co-ordinate

        Returns:

        """
        print(f'[{self.test_case_name}] > Tap using ui object')

        ui_info = ui_object.info
        left = ui_info['bounds']['left'] + left_adjust
        top = ui_info['bounds']['top'] + top_adjust

        status = self.common_functions.tap_adb(top, left)
        return status

    # ---------------------------- Product and Product Mix ----------------------------

    def expand_product_dialogue(self):
        """
        Expand product tab in Product Library
        Returns:
            bool : Status of operation
        """
        print(f'[{self.test_case_name}] > Opening Product Library')
        status = True
        if not Display.active_display_uiautomator(text='Add Product +').exists:
            status = Display.active_display_uiautomator(text=DMConstants.PRODUCT_LIBRARY_PRODUCTS_HEADER,
                            resourceId="com.cnh.pf.android.data.management:id/tvHeader",
                            className="android.widget.TextView").click()
            time.sleep(1)
        if status:
            return True
        raise Exception('Create Product dialogue box failed to open')

    def expand_product_mix_dialogue(self):
        """
        Expand product mix tab in Product Library
        Returns:
            bool : Status of operation
        """
        print(f'[{self.test_case_name}] > Opening Product Mix Library')
        status = True
        if not Display.active_display_uiautomator(text='Add Product Mix +').exists:
            status = Display.active_display_uiautomator(text=DMConstants.PRODUCT_LIBRARY_PRODUCT_MIXES_HEADER,
                            resourceId="com.cnh.pf.android.data.management:id/tvHeader",
                            className="android.widget.TextView").click()
            time.sleep(1)
        if status:
            return True
        raise Exception('Create Product mix dialogue box failed to open')

    def create_copy_datamanagement(self):
        """
        Create product mix tab in Product Library
        Returns:
            bool : Status of operation
        """
        pass

    def check_create_product_is_disable(self):
        """

        Returns:

        """
        self.expand_product_dialogue()
        print(f'[{self.test_case_name}] > Checking for create product button is disable')
        create_button = Display.active_display_uiautomator(resourceId='com.cnh.pf.android.data.management:id/add_product_button')
        if create_button.exists:
            enable = create_button.info['enabled']
            if not enable:
                print(f'[{self.test_case_name}] > Create product button is disable')
                return True
        raise Exception('Create product button is enable')

    def open_create_product_dialogue(self):
        """
        Open create product pop up
        Returns:
            bool : Status of operation
        """
        print(f'[{self.test_case_name}] > Open create product dialogue')
        status = self.common_functions.tap_using_ui_item(item_text='Add Product +')
        time.sleep(2)
        if status:
            return True
        raise Exception('Open create product dialogue failed')

    def product_add_save_button_verify(self, enable_status: bool, button_text: str = 'Add'):
        """
        Verify product box button ADD or SAVE product is enable or not
        Args:
            enable_status: expected status of button is enable or not
            button_text: text of button

        Returns:
            bool : Status of operation
        """
        print(f'[{self.test_case_name}] > verifying button : {button_text} is enable : {enable_status}')
        button = Display.active_display_uiautomator(text=button_text)
        if button.exists and button.info['enabled'] == enable_status:
            print(f'[{self.test_case_name}] > button : {button_text} is enable : {enable_status}')
            return True
        raise Exception(f'Button {button_text} is failed to verify with enable : {enable_status}')

    def verify_product_and_mix_tab(self):
        """
        Verify product and product mix tab in product library
        Returns:
            bool : Status of operation
        """
        print(f'[{self.test_case_name}] > Verify Product library Tabs')
        for tab_name in DMConstants.PRODUCT_LIBRARY_TABS:
            verify_widget = Display.active_display_uiautomator(resourceId='com.cnh.pf.android.data.management:id/tvHeader', text=tab_name)
            if verify_widget.exists:
                print(f'[{self.test_case_name}] > Product tab verified : {tab_name}')
            else:
                raise Exception(f'Failed to verify Product library tab : {tab_name}')

    def verify_product_mix_item(self):
        """
        Verify product and product mix tab in product library
        Returns:
            bool : Status of operation
        """
        name = "mix1"
        form = 'Granular/Other'
        print(f'[{self.test_case_name}] > Verifying created items Product Mix')
        wait = self.wait_to_appear(resource_id='com.cnh.pf.android.data.management:id/product_mix_panel')
        if wait:
            stage = self.wait_to_appear(resource_id='com.cnh.pf.android.data.management:id/tvSubHeader',
                                        item_text='Total: 1 product mix')
            if stage:
                print(f'[{self.test_case_name}] > 1 product mix found.')
            self.expand_product_mix_dialogue()
        expand = self.wait_to_appear(resource_id='com.cnh.pf.android.data.management:id/product_item')
        if expand:
            product_name = Display.active_display_uiautomator(resourceId='com.cnh.pf.android.data.management:id/product_mix_name_text', text=name)
            product_form = Display.active_display_uiautomator(resourceId='com.cnh.pf.android.data.management:id/product_mix_form_text', text=form)
            if product_name.exists:
                print(f'[{self.test_case_name}] > Product name verified : {name}')
            else:
                raise Exception(f'Failed to verify Product name : {name}')
            if product_form.exists:
                print(f'[{self.test_case_name}] > Product form verified : {form}')
            else:
                raise Exception(f'Failed to verify Product form : {form}')
        else:
            raise Exception(f'Failed to expand Product Mix tab.')

    def set_product_name(self, product_name: str, is_operation_screen=False):
        """
        Set product name in create product dialogue
        Args:
            is_operation_screen:
            product_name: Name of product

        Returns:
            bool : The status of operation

        """
        resource_name = DMConstants.CREATE_PRODUCT_RESOURCES['ProductName']
        if is_operation_screen:
            resource_name = ModelConstants.CREATE_PRODUCT_OPERATION_RESOURCES['Product Name']

        scroll_layout = Display.active_display_uiautomator(className="android.widget.ScrollView", index="0")
        scroll_layout.scroll.to(text='Product Name')
        product_name_widget = Display.active_display_uiautomator(resourceId=resource_name).child(
            className='android.widget.EditText')
        if product_name_widget.exists:
            product_name_widget.click()
            time.sleep(1)
            product_name_widget.set_text(product_name)
            self.common_functions.tap_adb(1130, 690)
            time.sleep(1)
            print(f'[{self.test_case_name}] > Set Product Name : {product_name}')
            return True
        raise Exception('Setting product name Failed')

    def set_product_form(self, form: str, is_operation_screen=False):
        """
        Set form of product in create product dialogue
        Args:
            is_operation_screen:
            form: the form of product

        Returns:
            bool : Status of operation

        """
        scroll_layout = Display.active_display_uiautomator(className="android.widget.ScrollView", index="0")
        scroll_layout.scroll.to(text='Product Name')
        form_resource = DMConstants.CREATE_PRODUCT_RESOURCES['Form']
        form_tv_header = "com.cnh.pf.android.data.management:id/tvHeaderText"
        if is_operation_screen:
            form_resource = ModelConstants.CREATE_PRODUCT_OPERATION_RESOURCES['Form']
            form_tv_header = "com.cnh.pf.phoenixapp:id/tvHeaderText"

        Display.active_display_uiautomator(resourceId=form_resource).child(resourceId=form_tv_header).click()
        status = self.common_functions.tap_using_ui_item(item_text=form)
        time.sleep(1)
        print(f'[{self.test_case_name}] > Set Product Form : {form}')
        return status

    def increment_product_application_rate_1(self, rate_inc: int = 1, is_operation_screen=False):
        """
        Increment product application rate 1 in create product dialogue
        Args:
            is_operation_screen:
            rate_inc: increment rate by int

        Returns:
            bool : Status of operation

        """
        resource_name = DMConstants.CREATE_PRODUCT_RESOURCES['Application Rate 1']
        if is_operation_screen:
            resource_name = ModelConstants.CREATE_PRODUCT_OPERATION_RESOURCES['Application Rate 1']

        scroll_layout = Display.active_display_uiautomator(className="android.widget.ScrollView", index="0")
        scroll_layout.scroll.to(resourceId=resource_name)
        rate_setter = Display.active_display_uiautomator(resourceId=resource_name).child(
            className="android.widget.RelativeLayout", index="1")
        x = rate_setter.info['bounds']['right'] - 5
        y = rate_setter.info['bounds']['bottom'] - 5
        for _ in range(rate_inc):
            self.common_functions.tap_adb(x, y)
            time.sleep(0.3)
        print(f'[{self.test_case_name}] > Increment Application Rate 1 by  : {rate_inc}')
        return True

    def increment_product_application_rate_2(self, rate_inc: int = 1):
        """
        Increment product application rate 2 in create product dialogue
        Args:
            rate_inc: increment rate by int

        Returns:
            bool : Status of operation

        """
        resource_name = DMConstants.CREATE_PRODUCT_RESOURCES['Application Rate 2']
        scroll_layout = Display.active_display_uiautomator(className="android.widget.ScrollView", index="0")
        scroll_layout.scroll.to(resourceId=resource_name)
        rate_setter = Display.active_display_uiautomator(resourceId=resource_name).child(
            className="android.widget.RelativeLayout", index="1")
        x = rate_setter.info['bounds']['right'] - 5
        y = rate_setter.info['bounds']['bottom'] - 5
        for _ in range(rate_inc):
            self.common_functions.tap_adb(x, y)
            time.sleep(0.3)
        print(f'[{self.test_case_name}] > Increment Application Rate 2 by  : {rate_inc}')
        return True

    def set_product_usage_crop_type(self, usage_crop_type: str, is_operation_screen=False):
        """
        Set Product usage or crop type in create product dialogue
        Args:
            is_operation_screen:
            usage_crop_type: usage/crop type to be selected

        Returns:
            bool : Status of operation

        """
        resource_name = DMConstants.CREATE_PRODUCT_RESOURCES['Usage']
        crop_widget = "com.cnh.pf.android.data.management:id/rlInnerHeader"
        pick_list_resource = 'com.cnh.pf.android.data.management:id/picklistPopupList'
        pick_list_item_resource = 'com.cnh.pf.android.data.management:id/picklistItem'
        if is_operation_screen:
            resource_name = ModelConstants.CREATE_PRODUCT_OPERATION_RESOURCES['Usage']
            pick_list_resource = 'com.cnh.pf.phoenixapp:id/picklistPopupList'
            pick_list_item_resource = 'com.cnh.pf.phoenixapp:id/picklistItem'
            crop_widget = "com.cnh.pf.phoenixapp:id/rlInnerHeader"

        scroll_layout = Display.active_display_uiautomator(className="android.widget.ScrollView", index="0")
        scroll_layout.scroll.to(resourceId=resource_name)

        Display.active_display_uiautomator(resourceId=resource_name).child(resourceId=crop_widget).click()
        time.sleep(1)
        Display.active_display_uiautomator(resourceId=pick_list_resource).child_by_text(
            usage_crop_type, allow_scroll_search=True, resourceId=pick_list_item_resource).click()
        print(f'[{self.test_case_name}] > Set Product usage_crop_type/crop type : {usage_crop_type}')
        return True

    def validate_application_rates(self, field_name: str, value: str, pos: list):
        """
        Validate application rates only
        Args:
            field_name: name of field to verify
            value: value to be verify

        Returns:
            bool : status of verification

        """
        print(f'[{self.test_case_name}] > Validate Application rate : {field_name} = [{value}]')
        resource_name = DMConstants.CREATE_PRODUCT_RESOURCES[field_name]
        if field_name == 'Delta Application Rate':
            Display.active_display_uiautomator.swipe(774, 594, 774, 490)
        scrollable_layout = Display.active_display_uiautomator(className="android.widget.ScrollView", index="0")
        scrollable_layout.scroll.to(text=field_name)

        rate_widget = Display.active_display_uiautomator(resourceId=resource_name).child(className="android.widget.RelativeLayout", index="1")
        # rate_value = self.ui_automator_object_text(rate_widget, left_adjust=90, top_adjust=-210, width_adjust=-150,
        #                                            height_adjust=-5)
        rate_value = self.ui_automator_object_text(rate_widget, left_adjust=pos[0], top_adjust=pos[1],
                                                   width_adjust=pos[2],
                                                   height_adjust=pos[3])

        if rate_value == value:
            print(f'[{self.test_case_name}] > Validate Application rate : {rate_value}')
            return True
        else:
            raise Exception(f'Validate {field_name} , Expected : {value}, Actual : {rate_value}')

    def create_products(self, products: Union[List[dict], dict]):
        """
        Creating one or more products
        Args:
            products: required field details to create product

        Returns:
            bool : Status of creation of product

        """
        print(f'[{self.test_case_name}] > Creating product in Product Library')
        if isinstance(products, dict):
            products = [products]
        self.expand_product_dialogue()
        status_product = []
        failed = []
        for product in products:
            product_name, form, usage, rate = product.values()
            print(f'[{self.test_case_name}] > Creating product : {product_name}')
            try:
                Display.active_display_uiautomator(text='Add Product +').click()
                time.sleep(2)
                print(f'[{self.test_case_name}] > Setting product name : {product_name}')
                self.set_product_name(product_name)
                print(f'[{self.test_case_name}] > Setting product Form : {form}')
                self.set_product_form(form)
                print(f'[{self.test_case_name}] > Setting product Rate : incremented by {rate}')
                self.increment_product_application_rate_1(rate)
                print(f'[{self.test_case_name}] > Setting product Usage/CropType : {usage}')
                self.set_product_usage_crop_type(usage)
                save_button = Display.active_display_uiautomator(text="Add")
                if save_button.info['enabled']:
                    print(f'[{self.test_case_name}] > Saving Updated details')
                    save_button.click()
                    status_product.append(True)
                else:
                    self.common_functions.tap_using_ui_item(item_text='Cancel')
                    status_product.append(False)
            except Exception as E:
                self.common_functions.tap_using_ui_item(item_text='Cancel')
                product['Exception'] = str(E)
                failed.append(product)
                status_product.append(False)

        if all(status_product):
            return True
        raise Exception(f'Failed to create product : {failed}')

    def search_product(self, search_key: str):
        """
        Set product search text
        Args:
            search_key: the text to search

        Returns:
            bool : Status of opeartion
        """
        print(f'[{self.test_case_name}] > Search Product with Text : [{search_key}]')
        if isinstance(search_key, str):
            self.expand_product_dialogue()
            search_box = Display.active_display_uiautomator(resourceId='com.cnh.pf.android.data.management:id/product_search').child(
                className='android.widget.EditText')
            search_box.clear_text()
            search_box.set_text(search_key)
            self.common_functions.tap_adb(1130, 690)
            return True
        raise Exception('Search key provided is not in correct format')

    def search_product_mix(self, search_key: str):
        """
        Set product search text
        Args:
            search_key: the text to search

        Returns:
            bool : Status of opeartion
        """
        print(f'[{self.test_case_name}] > Search Product mix with Text : [{search_key}]')
        if isinstance(search_key, str):
            self.expand_product_mix_dialogue()
            search_box = Display.active_display_uiautomator(resourceId='com.cnh.pf.android.data.management:id/product_mix_search').child(
                className='android.widget.EditText')
            search_box.clear_text()
            search_box.set_text(search_key)
            self.common_functions.tap_adb(1130, 690)
            return True
        raise Exception('Search key provided is not in correct format')

    def product_exist(self, product_name: str = None, search_product: bool = True):
        """
        Check if product exist in library
        Args:
            product_name: name of product
            search_product: search before verifying product

        Returns:
            tuple : (product exist status, product widget )

        """
        print(f'[{self.test_case_name}] > Validating Product information')
        self.expand_product_dialogue()
        if search_product:
            print(f'[{self.test_case_name}] > Checking for product with search text {product_name} in Product Library')
            status = self.search_product(product_name)
        product_widget_view = Display.active_display_uiautomator(resourceId="com.cnh.pf.android.data.management:id/nested_product_scrollview")
        if product_widget_view.exists:
            products = Display.active_display_uiautomator(resourceId='com.cnh.pf.android.data.management:id/product_item')
            for instance in range(products.count):
                product_item = product_widget_view.child(
                    resourceId='com.cnh.pf.android.data.management:id/product_item', instance=instance)
                product_widget = product_item.child(resourceId='com.cnh.pf.android.data.management:id/name_text')
                if product_widget.exists and product_widget.info['text'] == product_name:
                    print(f'[{self.test_case_name}] > Product Found : {product_name}')
                    return True, instance
        print(f'[{self.test_case_name}] > Product Not Found : {product_name}')
        return False, None

    def product_mix_exist(self, product_mix: str, search_product_mix: bool = True):
        """
        Check if product mix exist in product library
        Args:
            search_product_mix:
            product_mix: name of product mix

        Returns:
            bool : (product mix exist , product mix widget)
        """
        print(f'[{self.test_case_name}] > Checking for product mix : {product_mix} in Product Library')
        self.expand_product_mix_dialogue()
        if search_product_mix:
            print(f'[{self.test_case_name}] > Checking for product with search text {product_mix} in Product Library')
            status = self.search_product_mix(product_mix)
        product_mix_widget_view = Display.active_display_uiautomator(
            resourceId="com.cnh.pf.android.data.management:id/nested_product_mix_scrollview")
        if product_mix_widget_view.exists:
            products = Display.active_display_uiautomator(resourceId='com.cnh.pf.android.data.management:id/product_item')
            for instance in range(products.count):
                product_item = product_mix_widget_view.child(
                    resourceId='com.cnh.pf.android.data.management:id/product_item', instance=instance)
                product_widget = product_item.child(
                    resourceId='com.cnh.pf.android.data.management:id/product_mix_name_text')
                if product_widget.exists and product_widget.info['text'] == product_mix:
                    print(f'[{self.test_case_name}] > Product Found : {product_mix}')
                    return True, instance
        print(f'[{self.test_case_name}] > Product Not Found : {product_mix}')
        return False, None

        print(f'[{self.test_case_name}] > Checking for product mix : {product_mix} in Product Library')
        status = True
        if not Display.active_display_uiautomator(text='Add Product Mix +').exists:
            status = Display.active_display_uiautomator(text=DMConstants.PRODUCT_LIBRARY_PRODUCT_MIXES_HEADER,
                            resourceId="com.cnh.pf.android.data.management:id/tvHeader",
                            className="android.widget.TextView").click()
        if status:
            widget = Display.active_display_uiautomator(resourceId='com.cnh.pf.android.data.management:id/product_mix_panel')
            if widget.exists:
                widget.click()
                time.sleep(2)
                search_box = Display.active_display_uiautomator(resourceId='com.cnh.pf.android.data.management:id/product_mix_search').child(
                    className='android.widget.EditText')
                search_box.clear_text()
                search_box.set_text(product_mix)
                self.common_functions.tap_adb(1130, 690)
                time.sleep(3)
                product_mix_widget = Display.active_display_uiautomator(
                    resourceId="com.cnh.pf.android.data.management:id/nested_product_mix_scrollview").child_by_text(
                    product_mix,
                    allow_scroll_search=True,
                    resourceId="com.cnh.pf.android.data.management:id/product_mix_name_text",
                    className="android.widget.TextView")
                if product_mix_widget.exists:
                    print(f'[{self.test_case_name}] > Product Mix Found : {product_mix}')
                    return True, product_mix_widget
            print(f'[{self.test_case_name}] > Product Mix not Found : {product_mix}')
            return False, None

    def validate_product_information(self, product_name: str, validate_fields: Dict, search_product: bool = True):
        """
        validate product information in library
        Args:
            product_name: name of product to verify
            validate_fields: field information to verify
            search_product: search before verifying

        Returns:
            bool : Status of verification

        """
        product_exist_status, product_widget_instance = self.product_exist(product_name, search_product)
        product_widget_view = Display.active_display_uiautomator(resourceId="com.cnh.pf.android.data.management:id/nested_product_scrollview")
        product_widget = product_widget_view.child(resourceId='com.cnh.pf.android.data.management:id/product_item',
                                                   instance=product_widget_instance)
        product_widget_info = product_widget_view.child(
            resourceId='com.cnh.pf.android.data.management:id/product_item_child_details',
            instance=product_widget_instance)
        if product_exist_status:
            product_widget.click()
            time.sleep(1)
            result = []
            print(f'[{self.test_case_name}] > Validating Product : {product_name} information')
            for field, value in validate_fields.items():
                print(f'[{self.test_case_name}] > validating Field ["{field}"] with expected value ["{value}"]')
                if field == 'Product Name':
                    continue
                resource_id = DMConstants.VALIDATION_PRODUCT.get(field + '_main', None)
                drop_down_verify = True  # which screen to verify
                if resource_id is None:
                    resource_id = DMConstants.VALIDATION_PRODUCT.get(field + '_edit', None)
                    drop_down_verify = False
                if resource_id is not None and resource_id != '':
                    field_text = 'NA'
                    try:
                        if drop_down_verify:  # drop down verify
                            cancel_widget = Display.active_display_uiautomator(text='Cancel')
                            if cancel_widget.exists:
                                cancel_widget.click()
                            time.sleep(2)
                            if field == 'Form':
                                field_item = product_widget.child(resourceId=resource_id)
                            else:
                                field_item = product_widget_info.child(resourceId=resource_id)
                            if field_item.exists:
                                field_text = field_item.info['text']

                                if 'Units' in field:
                                    field_text = ' '.join(field_text.split()[1:]).strip()

                                if field in ['Package Size', 'Density', 'Step Size', 'Plant Density',
                                             'Seed Density'] or 'Rate' in field:
                                    if len(value.split(' ')) == 1:
                                        field_text = ''.join(field_text.split()[0]).strip()
                                        value = value.split(' ')[0]

                                result.append(
                                    {'Field': field, 'Expected': value, 'Actual': field_text, 'Exception': ''})
                        else:
                            cancel_widget = Display.active_display_uiautomator(text='Cancel')  # edit box verify
                            if not cancel_widget.exists:
                                Display.active_display_uiautomator(resourceId="com.cnh.pf.android.data.management:id/edit_button").click()
                                time.sleep(3)
                            scrollable_layout = Display.active_display_uiautomator(className="android.widget.ScrollView", index="0")
                            scrollable_layout.scroll.to(resourceId=resource_id)
                            ui_item = Display.active_display_uiautomator(resourceId=resource_id)
                            if field in ['EPA Number', 'Manufacturer', 'Buffer Distance', 'Max Wind Speed']:
                                field_text = ui_item.child(className="android.widget.EditText").info['text']
                            elif field in ['Restricted Use', 'Posting Required']:
                                scrollable_layout.scroll.to(text='Buffer Distance')
                                radio_group = ui_item.child(className="android.widget.RadioGroup")
                                is_enable = ui_item.child(index=0, className="android.widget.RadioButton").info[
                                    'checked'] if value else \
                                    radio_group.child(index=1, className="android.widget.RadioButton").info['checked']
                                field_text = 'Yes' if is_enable else 'No'
                            else:
                                field_text = \
                                    ui_item.child(resourceId="com.cnh.pf.android.data.management:id/rlInnerHeader",
                                                  index="0").child(
                                        resourceId="com.cnh.pf.android.data.management:id/tvHeaderText",
                                        className="android.widget.TextView").info['text']
                            result.append({'Field': field, 'Expected': value, 'Actual': field_text, 'Exception': ''})
                    except Exception as E:
                        result.append({'Field': field, 'Expected': value, 'Actual': field_text, 'Exception': str(E)})
                else:
                    print(f'[{self.test_case_name}] > Resource id for {field} not configured in Constants')

            cancel_widget = Display.active_display_uiautomator(text='Cancel')
            if cancel_widget.exists:
                cancel_widget.click()

            verdict = [value for value in result if value['Expected'] != value['Actual']]
            if len(verdict) == 0:
                print(f'[{self.test_case_name}] > All fields validated successfully')
                return True
            else:
                raise Exception(f'Product Values Mismatched : \n\t\t{str(verdict)}')
        else:
            raise Exception(f'[Product Not found] : {product_name} not exists in Library')

    # def validate_product_mix_information_2(self, product_mix_name: str, validate_fields: Dict,
    #                                        search_product_mix: bool = True):
    #     """
    #     validate product information in library
    #     Args:
    #         product_name: name of product to verify
    #         validate_fields: field information to verify
    #         search_product: search before verifying
    #
    #     Returns:
    #         bool : Status of verification
    #
    #     """
    #     product_mix_exist_status, product_widget_instance = self.product_mix_exist(product_mix_name, search_product_mix)
    #     product_mix_widget_view = Display.active_display_uiautomator(
    #         resourceId="com.cnh.pf.android.data.management:id/nested_product_mix_scrollview")
    #     product_mix_widget = product_mix_widget_view.child(
    #         resourceId='com.cnh.pf.android.data.management:id/product_item',
    #         instance=product_widget_instance)
    #
    #     if product_mix_exist_status:
    #         product_mix_widget.click()
    #         time.sleep(1)
    #         result = []
    #         print(f'[{self.test_case_name}] > Validating Product mix : {product_mix_name} information')
    #         is_mix_product_clicked = False
    #         is_application_rate_clicked = False
    #         is_advance_clicked = False
    #
    #         for field, value in validate_fields.items():
    #             perform_expand = False
    #             resource_item = None
    #
    #             print(f'[{self.test_case_name}] > validating Field ["{field}"] with expected value ["{value}"]')
    #             if field == 'Product Mix Name':
    #                 continue
    #             resource_id = ModelConstants.CREATE_PRODUCT_MIX.get(field, None)
    #
    #             if resource_id is not None:
    #                 if field in ModelConstants.MIX_PRODUCTS_ITEMS and not is_mix_product_clicked:
    #                     perform_expand = True
    #                     resource_item = ModelConstants.PRODUCT_MIX_EXPAND_RESOURCES['Mix Products']
    #                     is_mix_product_clicked = True
    #                 if field in ModelConstants.APPLICATION_RATES_ITEMS and not is_application_rate_clicked:
    #                     perform_expand = True
    #                     resource_item = ModelConstants.PRODUCT_MIX_EXPAND_RESOURCES['Application Rates']
    #                     is_application_rate_clicked = True
    #                 if field in ModelConstants.ADVANCE and not is_advance_clicked:
    #                     perform_expand = True
    #                     resource_item = ModelConstants.PRODUCT_MIX_EXPAND_RESOURCES['Advance']
    #                     is_advance_clicked = True
    #
    #                 if perform_expand:
    #                     scroll_layout = Display.active_display_uiautomator(className="android.widget.ScrollView", index="0")
    #                     scroll_layout.scroll.to(resourceId=resource_item)
    #                     expand = Display.active_display_uiautomator(resourceId=resource_item).child(
    #                         resourceId='com.cnh.pf.android.data.management:id/id_expand_collapse')
    #                     if expand.exists:
    #                         expand.click()
    #                         os.system('adb shell input swipe 775 600 775 300')
    #                         time.sleep(1)
    #
    #                 ui_item = Display.active_display_uiautomator(resourceId=resource_id)
    #                 scrollable_layout = Display.active_display_uiautomator(className="android.widget.ScrollView", index="0")
    #                 scrollable_layout.scroll.to(resourceId=resource_id)
    #
    #                 if field in ['EPA Number', 'Manufacturer', 'Buffer Distance', 'Max Wind Speed']:
    #                     field_text = ui_item.child(className="android.widget.EditText").info['text']
    #                 elif field in ['Restricted Use', 'Posting Required']:
    #                     scrollable_layout.scroll.to(text='Buffer Distance')
    #                     radio_group = ui_item.child(className="android.widget.RadioGroup")
    #                     is_enable = ui_item.child(index=0, className="android.widget.RadioButton").info[
    #                         'checked'] if value else \
    #                         radio_group.child(index=1, className="android.widget.RadioButton").info['checked']
    #                     field_text = 'Yes' if is_enable else 'No'
    #                 else:
    #                     field_text = \
    #                         ui_item.child(resourceId="com.cnh.pf.android.data.management:id/rlInnerHeader",
    #                                       index="0").child(
    #                             resourceId="com.cnh.pf.android.data.management:id/tvHeaderText",
    #                             className="android.widget.TextView").info['text']
    #
    #     #     cancel_widget = Display.active_display_uiautomator(text='Cancel')
    #     #     if cancel_widget.exists:
    #     #         cancel_widget.click()
    #     #
    #     #     verdict = [value for value in result if value['Expected'] != value['Actual']]
    #     #     if len(verdict) == 0:
    #     #         print(f'[{self.test_case_name}] > All fields validated successfully')
    #     #         return True
    #     #     else:
    #     #         raise Exception(f'Product Values Mismatched : \n\t\t{str(verdict)}')
    #     # else:
    #     #     raise Exception(f'[Product Not found] : {product_mix_name} not exists in Library')

    def get_recipe_details(self):
        """
        Get product mix details
        Returns:
            dict : dict of product mix details
        """
        print(f'[{self.test_case_name}] > Getting Product Mix Recipes')
        recipe_list = {}
        recipe_resource = DMConstants.VALIDATION_PRODUCT_MIX.get('Recipe', 'None')
        recipes = Display.active_display_uiautomator(resourceId=recipe_resource)
        if recipes.exists:
            count = Display.active_display_uiautomator(resourceId=DMConstants.VALIDATION_PRODUCT_MIX['Recipe_Product']).count
            for inst in range(count):
                product = recipes.child_by_instance(resourceId=DMConstants.VALIDATION_PRODUCT_MIX['Recipe_Product'],
                                                    inst=inst).info['text']
                app_rate1_full = \
                    recipes.child_by_instance(resourceId=DMConstants.VALIDATION_PRODUCT_MIX['Recipe_AppRate1'],
                                              inst=inst).info['text']
                app_rate2_full = \
                    recipes.child_by_instance(resourceId=DMConstants.VALIDATION_PRODUCT_MIX['Recipe_AppRate2'],
                                              inst=inst).info['text']

                rate1, rate1_unit = app_rate1_full.split()
                rate2, rate2_unit = app_rate2_full.split()

                recipe_list[product] = {'Product': product, 'AppRate1': rate1.strip(), 'AppRate2': rate2.strip(),
                                        'AppRate1_Unit': rate1_unit.strip(), 'AppRate2_Unit': rate2_unit.strip()}
            print(f'[{self.test_case_name}] > Total Recipes Found : {len(recipe_list)}')
            return recipe_list

    def validate_product_mix_information(self, product_mix: str, validate_fields: Dict):
        """
        Validate product mix information in library
        Args:
            product_mix: the name of product mix
            validate_fields: field details to validate

        Returns:
            bool : Status of validation

        """
        product_mix_exist_status, instance = self.product_mix_exist(product_mix)
        product_mix_widget_view = Display.active_display_uiautomator(
            resourceId="com.cnh.pf.android.data.management:id/nested_product_mix_scrollview")
        product_mix_item = product_mix_widget_view.child(
            resourceId='com.cnh.pf.android.data.management:id/product_item', instance=instance)
        if product_mix_exist_status:
            product_mix_item.click()
            time.sleep(3)
            result = []
            for field, value in validate_fields.items():
                print(f'[{self.test_case_name}] > validating Field : {field} with expected value ["{value}"]')
                if field == 'Form':
                    field_text = 'NA'
                    try:
                        resource_id = DMConstants.VALIDATION_PRODUCT_MIX.get(field, None)
                        field_item = Display.active_display_uiautomator(resourceId=resource_id)
                        if field_item.exists:
                            field_text = field_item.info['text']
                            result.append({'Field': field, 'Expected': value, 'Actual': field_text, 'Exception': ''})
                    except Exception as E:
                        result.append({'Field': field, 'Expected': value, 'Actual': field_text, 'Exception': str(E)})
                elif 'Recipe' == field:
                    recipe_data = self.get_recipe_details()
                    for recipe in value:
                        product = recipe.get('Product', None)
                        if product is not None and recipe_data is not None:
                            actual = recipe_data.get(product, None)
                            if actual is not None:
                                for rec_key, rec_value in recipe.items():
                                    result.append({'Field': product + '_' + rec_key, 'Expected': rec_value,
                                                   'Actual': actual.get(rec_key, 'NA'),
                                                   'Exception': ''})
                            else:
                                result.append(
                                    {'Field': 'Product', 'Expected': product, 'Actual': str(list(recipe_data.keys())),
                                     'Exception': 'Recipe not found'})
                        else:
                            result.append({'Field': 'Product', 'Expected': product, 'Actual': 'NA',
                                           'Exception': 'Recipe not found'})

            verdict = [value for value in result if value['Expected'] != value['Actual']]
            if len(verdict) == 0:
                return True
            else:
                raise Exception(f'Product Values Mismatched : \n\t\t{str(verdict)}')
        else:
            raise Exception(f'[Product Not found] : {product_mix} not exists in Library')

    def edit_product_info(self, product_name: str, product_info: Dict):
        """
        Edit product information from product library
        Args:
            product_name: name of product to edit
            product_info: information of field to update

        Returns:
            bool : Status of edit product operation
        """
        print(f'[{self.test_case_name}] > Creating product in Product Library')
        self.expand_product_dialogue()
        try:
            product_exist_status, product_widget_instance = self.product_exist(product_name)
            product_widget_view = Display.active_display_uiautomator(resourceId="com.cnh.pf.android.data.management:id/nested_product_scrollview")
            product_widget = product_widget_view.child(resourceId='com.cnh.pf.android.data.management:id/product_item',
                                                       instance=product_widget_instance)
            if product_exist_status:
                product_widget.click()
                time.sleep(1)
                print(f'[{self.test_case_name}] > Editing Product : {product_name} information')
                Display.active_display_uiautomator(resourceId="com.cnh.pf.android.data.management:id/edit_button").click()
                for title, value in product_info.items():
                    if title == 'Name':
                        print(f'[{self.test_case_name}] > Editing product Name to New Name : {value}')
                        self.set_product_name(value)
                    elif title == 'Form':
                        print(f'[{self.test_case_name}] > Editing product Form to New Form : {value}')
                        self.set_product_form(value)
                    elif title == 'Usage_CropType':
                        print(f'[{self.test_case_name}] > Editing Usage/Crop to Usage/Crop type : {value}')
                        self.set_product_usage_crop_type(value)
                save_button = Display.active_display_uiautomator(text="Save")
                if save_button.info['enabled']:
                    print(f'[{self.test_case_name}] > Saving Updated details')
                    save_button.click()
                    return True
                else:
                    self.common_functions.tap_using_ui_item(item_text='Cancel')
                    raise Exception("Editing product failed : Save button is disable")
        except Exception as E:
            self.common_functions.tap_using_ui_item(item_text='Cancel')
            raise Exception('Failed to edit Product Information')

    def verify_product_form_list(self, form_type: List):
        """
        Verify all the product forms list
        Returns:
            bool : Status of operation
        """
        print(f'[{self.test_case_name}] > Expanding Product Library Section')
        self.expand_product_dialogue()
        verify_status = []
        print(f'[{self.test_case_name}] > Opening add Product dialogue box')
        self.open_create_product_dialogue()
        time.sleep(1.5)
        Display.active_display_uiautomator(resourceId='com.cnh.pf.android.data.management:id/tvHeaderText', text='Select').click()
        time.sleep(1)
        for form in form_type:
            status_form = False
            try:
                form_widget = Display.active_display_uiautomator(text=form, resourceId="com.cnh.pf.android.data.management:id/picklistItem")
                if form_widget.exists:
                    status_form = True
                verify_status.append({'Form': form, 'Status': status_form, 'Exception': ''})
            except Exception as E:
                verify_status.append({'Form': form, 'Status': False, 'Exception': str(E)})
            print(f'[{self.test_case_name}] > Verified Product Form : {form}, Status : {status_form}')
        Display.active_display_uiautomator(resourceId='com.cnh.pf.android.data.management:id/picklistItem').click()
        time.sleep(1)
        self.common_functions.tap_using_ui_item(item_text='Cancel')
        verdict = [item for item in verify_status if not item['Status']]
        if len(verdict) == 0:
            return True
        else:
            raise Exception(f'Failed to validate product forms : {str(verdict)}')

    def create_product_field_verified(self, product_data: Dict, check_required: str):
        """
        Check required field to create product in library
        Args:
            product_data: product information
            check_required: name of required field

        Returns:
            bool : Status of operation

        """
        product_name = product_data.get('ProductName', None)
        form = product_data.get('Form', None)
        rate_inc = product_data.get('Application Rate 1', None)
        usage = product_data.get('Usage_CropType', None)
        self.expand_product_dialogue()
        print(f'[{self.test_case_name}] > Open Create Product Dialogue')
        self.open_create_product_dialogue()
        time.sleep(2)
        form_selected = False
        try:
            if check_required != 'ProductName' and product_name is not None:
                print(f'[{self.test_case_name}] > Setting product name : {product_name}')
                self.set_product_name(product_name)
            if check_required != 'Form' and form is not None:
                print(f'[{self.test_case_name}] > Setting product Form : {form}')
                self.set_product_form(form)
                form_selected = True
            if check_required != 'Application Rate 1' and rate_inc is not None:
                print(f'[{self.test_case_name}] > Setting product Rate : increment by {rate_inc}')
                if isinstance(rate_inc, str):
                    rate_inc = int(rate_inc)
                self.increment_product_application_rate_1(rate_inc)
            if form_selected and check_required != 'Usage_CropType' and usage is not None:
                print(f'[{self.test_case_name}] > Setting product Usage/CropType : {usage}')
                self.set_product_usage_crop_type(usage)

            print(f'[{self.test_case_name}] > Checking Required Filed : {check_required}')
            add_button = Display.active_display_uiautomator(text='Add')
            if not add_button.info['enabled']:
                if check_required == 'ProductName':
                    scroll_layout = Display.active_display_uiautomator(className="android.widget.ScrollView", index="0")
                    scroll_layout.scroll.to(text=DMConstants.ADD_PRODUCT_NAME_TITLE)
                    self.set_product_name(product_name)
                elif check_required == 'Form':
                    self.set_product_form(form)
                    self.set_product_usage_crop_type(usage)
                elif check_required == 'Application Rate 1':
                    if isinstance(rate_inc, str):
                        rate_inc = int(rate_inc)
                    self.increment_product_application_rate_1(rate_inc)
                elif check_required != 'Usage_CropType':
                    self.set_product_usage_crop_type(usage)
                else:
                    raise Exception('Check_Required name is invalid')
                if add_button.info['enabled']:
                    self.common_functions.tap_using_ui_item(item_text='Cancel')
                    return True
                else:
                    self.common_functions.tap_using_ui_item(item_text='Cancel')
                    raise Exception('Required Product Attributes are missing')
        except Exception as E:
            self.common_functions.tap_using_ui_item(item_text='Cancel')
            raise Exception(f'Checking required attribute value failed : {str(E)}')

    def verify_presence_usage_crop(self, product_forms: List, check_field_text: str):
        """
        Check if usage/crop type option is display for forms
        Args:
            product_forms: name of product form
            check_field_text: text to identify (Usage/ Crop Type)

        Returns:
            bool : Status of operation
        """
        print(f'[{self.test_case_name}] > verifying presence of Usage or Crop type')
        self.expand_product_dialogue()
        result = []
        failed = []
        self.open_create_product_dialogue()
        time.sleep(2)
        try:
            self.set_product_name(DMConstants.PRODUCT_NAME_1)
            self.increment_product_application_rate_1()
            for form in product_forms:
                print(f'[{self.test_case_name}] > verifying for form : {form}')
                try:
                    scrollable_layout = Display.active_display_uiautomator(className="android.widget.ScrollView", index="0")
                    scrollable_layout.scroll.to(text=DMConstants.ADD_PRODUCT_FORM_TITLE)
                    self.set_product_form(form)
                    time.sleep(0.3)
                    scrollable_layout.scroll.to(
                        resourceId="com.cnh.pf.android.data.management:id/product_usage_pick_list")
                    if Display.active_display_uiautomator(text=check_field_text).exists:
                        print(f'[{self.test_case_name}] > Form : {form} , Text: {check_field_text}, Status : True')
                        result.append(True)

                    else:
                        print(
                            f'[{self.test_case_name}] > Form : {form} , Text : {check_field_text}, Status = False')
                        failed.append({'Form': form, 'Status': False})
                        result.append(False)
                except Exception as E:
                    print(f'[{self.test_case_name}] > Form : {form} , Text : {check_field_text}, Status = False')
                    failed.append({'Form': form, 'Status': False, 'Exception': str(E)})
                    result.append(False)
        except Exception as E:
            self.common_functions.tap_using_ui_item(item_text='Cancel')
        if all(result):
            self.common_functions.tap_using_ui_item(item_text='Cancel')
            return True
        raise Exception(f'Failed for below forms : {failed}')

    def copy_product(self, existing_product: str, new_product_name: str):
        """
        Copy product from product library
        Args:
            existing_product: exiting product to copy
            new_product_name: name of new product

        Returns:
            bool : Status of operation
        """
        print(f'[{self.test_case_name}] > Copy product : {existing_product} with new name : {new_product_name}')
        product_exist_status, product_widget_instance = self.product_exist(existing_product)
        product_widget_view = Display.active_display_uiautomator(resourceId="com.cnh.pf.android.data.management:id/nested_product_scrollview")
        product_widget = product_widget_view.child(resourceId='com.cnh.pf.android.data.management:id/product_item',
                                                   instance=product_widget_instance)
        if product_exist_status:
            product_widget.click()
            status = self.common_functions.tap_using_ui_item(
                resource_id="com.cnh.pf.android.data.management:id/copy_button")
            if status:
                status = self.common_functions.tap_using_ui_item(item_text="Copy Product")
                if status:
                    self.set_product_name(new_product_name)
                    status = self.common_functions.tap_using_ui_item(item_text='Save')
                    if status:
                        return True
                    raise Exception('New product copy failed to save')
            raise Exception('Copy product failed')
        else:
            raise Exception('Product not exist')

    def copy_product_mix(self, existing_product: str, new_product_name: str):
        """
        Copy product mix from product library
        Args:
            existing_product: exiting product to copy
            new_product_name: name of new product

        Returns:
            bool : Status of operation
        """
        print(f'[{self.test_case_name}] > Copy product mix : {existing_product} with new name : {new_product_name}')
        self.common_functions.tap_adb(1067, 309)
        product_exist_status = self.wait_to_appear(
            resource_id="com.cnh.pf.android.data.management:id/product_mix_name_text", item_text=existing_product)
        if product_exist_status:
            self.common_functions.tap_adb(1077, 509)
            self.wait_to_appear(resource_id="com.cnh.pf.android.data.management:id/copy_button")
            status = self.common_functions.tap_using_ui_item(
                resource_id="com.cnh.pf.android.data.management:id/copy_button")
            if status:
                self.wait_to_appear(item_text="Product Mix Name")
                product_name_widget = Display.active_display_uiautomator(className='android.widget.EditText')
                if product_name_widget.exists:
                    product_name_widget.click()
                    # self.common_functions.tap_adb(444, 239)
                    time.sleep(1)
                    product_name_widget.set_text(new_product_name)
                    self.common_functions.tap_adb(1130, 690)
                    time.sleep(1)
                    print(f'[{self.test_case_name}] > Set Product Mix Name : {new_product_name}')
                    self.common_functions.tap_using_ui_item(item_text='Add')
                    time.sleep(1)
                    self.common_functions.tap_adb(1067, 309)
                    return True
                else:
                    raise Exception('Copy product mix failed')
        else:
            raise Exception('Product Mix not exist')

    def delete_product(self, product_name: str):
        """
        Delete product from library
        Args:
            product_name: name of product to delete

        Returns:
            bool : Status of operation

        """
        print(f'[{self.test_case_name}] > Deleting product : {product_name} ')
        product_exist_status, product_widget_instance = self.product_exist(product_name)
        product_widget_view = Display.active_display_uiautomator(resourceId="com.cnh.pf.android.data.management:id/nested_product_scrollview")
        product_widget = product_widget_view.child(resourceId='com.cnh.pf.android.data.management:id/product_item',
                                                   instance=product_widget_instance)
        if product_exist_status:
            product_widget.click()
            status = self.common_functions.tap_using_ui_item(
                resource_id="com.cnh.pf.android.data.management:id/delete_button")
            if status:
                status = self.wait_to_appear(item_text="Confirm Delete")
                if status:
                    status = self.common_functions.tap_using_ui_item(item_text='Delete')
                    if status:
                        return True
                    raise Exception(f'Product : {product_name} failed to confirm delete box')
            raise Exception('Failed to click on delete button')
        else:
            raise Exception('Product not exist')

    def delete_product_mix(self, product_mix_name: str):
        """
        Delete product from library
        Args:
            product_mix_name: name of product to delete

        Returns:
            bool : Status of operation

        """
        print(f'[{self.test_case_name}] > Deleting product mix: {product_mix_name} ')
        product_mix_exist_status, product_mix_widget_instance = self.product_mix_exist(product_mix_name)
        product_mix_widget_view = Display.active_display_uiautomator(
            resourceId="com.cnh.pf.android.data.management:id/nested_product_mix_scrollview")
        product_mix_widget = product_mix_widget_view.child(
            resourceId='com.cnh.pf.android.data.management:id/product_item',
            instance=product_mix_widget_instance)
        if product_mix_exist_status:
            if not Display.active_display_uiautomator(resourceId="com.cnh.pf.android.data.management:id/delete_button").exists:
                product_mix_widget.click()
            status = self.common_functions.tap_using_ui_item(
                resource_id="com.cnh.pf.android.data.management:id/delete_button")
            if status:
                status = self.wait_to_appear(item_text="Confirm Delete")
                if status:
                    status = self.common_functions.tap_using_ui_item(item_text='Delete')
                    if status:
                        return True
                    raise Exception(f'Product : {product_mix_name} failed to confirm delete box')
            raise Exception('Failed to click on delete button')
        else:
            raise Exception('Product not exist')

    def verify_add_product_layout(self, item_texts: List):
        """
        Verify layout of create product dialogue
        Args:
            item_texts: text list to verify

        Returns:

        """
        print(f'[{self.test_case_name}] > Verify Add product layout')
        final_result = []
        for verify_text in item_texts:
            try:
                text_widget = Display.active_display_uiautomator(resourceId="com.cnh.pf.android.data.management:id/flContent",
                                     className='android.widget.FrameLayout').child_by_text(verify_text,
                                                                                           allow_scroll_search=True,
                                                                                           className="android.widget.TextView")
                status = False
                if text_widget.exists:
                    status = True
                final_result.append({'Field': verify_text, 'Status': True})
                print(f'[{self.test_case_name}] > Verified Field : {verify_text}, Status : {status}')
            except Exception as E:
                print(f'[{self.test_case_name}] > Verified Field : {verify_text}, Status : False')
                final_result.append({'Field': verify_text, 'Status': False, 'Exception': str(E)})

        failed = [result for result in final_result if not result['Status']]
        if len(failed) == 0:
            return True
        raise Exception(f'Failed to verify product layout items : \n {failed}')

    def validate_product_form_in_add_product(self, form: str):
        """
        Verify selected value in add product box
        Args:
            form: expected form

        Returns:
            bool : Status of operation

        """
        print(f'[{self.test_case_name}] > Validating product form : {form}')
        try:
            Display.active_display_uiautomator(className="android.widget.FrameLayout",
                   resourceId="com.cnh.pf.android.data.management:id/flContent").child_by_text(
                "Form", allow_scroll_search=True, className="android.widget.TextView")
            time.sleep(.5)

            actual_form = Display.active_display_uiautomator(resourceId="com.cnh.pf.android.data.management:id/product_form_picklist").child(
                resourceId="com.cnh.pf.android.data.management:id/tvHeaderText").info['text']
            if actual_form == form:
                print(f"[{self.test_case_name}] > Validated successfully product form : {form}")
                return True
            raise Exception(f'Product Form valudating failed , Expected : {form}, Actual : {actual_form}')
        except Exception as E:
            raise Exception(f'Product Form valudating failed , Expected : {form}, Actual : {str(E)}')

    def validate_usage_crop_type_in_add_product(self, usage_crop: str, is_usage=True):
        """
        validate usage / crop type of selected in add product dialogue box
        Args:
            usage_crop: expected value
            is_usage: is usage or crop type

        Returns:
            bool : Status of operation
        """
        print(f'[{self.test_case_name}] > Validating product Usage : {usage_crop}')
        try:
            if is_usage:
                text_to_find = 'Usage'
            else:
                text_to_find = 'Crop Type'

            scrollable_layout = Display.active_display_uiautomator(className="android.widget.ScrollView", index="0")
            scrollable_layout.scroll.to(text=text_to_find)

            actual_usage = Display.active_display_uiautomator(resourceId="com.cnh.pf.android.data.management:id/product_usage_pick_list").child(
                resourceId="com.cnh.pf.android.data.management:id/tvHeaderText").info['text']
            if actual_usage == usage_crop:
                print(f"[{self.test_case_name}] > Validated successfully product form : {usage_crop}")
                return True
            raise Exception(f'Product Form validation failed , Expected : {usage_crop}, Actual : {actual_usage}')
        except Exception as E:
            raise Exception(f'Product Form validation failed , Expected : {usage_crop}, Actual : {str(E)}')

    def validate_field_in_add_product(self, field_name: str, value: str):
        """
        Validate field selected values in add product dialogue box
        Args:
            field_name: name of fields
            value: expected value

        Returns:
            bool : Status of operation

        """
        print(f'[{self.test_case_name}] > Validating product Field : {field_name}')
        try:
            actual_value = None
            resource_id = DMConstants.VALIDATION_PRODUCT.get(field_name + '_edit', None)
            if resource_id is not None:
                scrollable_layout = Display.active_display_uiautomator(className="android.widget.ScrollView", index="0")
                scrollable_layout.scroll.to(text=field_name)

                if field_name in ['EPA Number', 'Manufacturer', 'Buffer Distance', 'Max Wind Speed']:
                    actual_value = Display.active_display_uiautomator(resourceId=resource_id).child(className='android.widget.EditText').info[
                        'text']
                elif field_name in ['Restricted Use', 'Posting Required']:
                    radio_group = Display.active_display_uiautomator(resourceId=resource_id).child(className="android.widget.RadioGroup")
                    if radio_group.child(index=0, className="android.widget.RadioButton").info['checked']:
                        actual_value = True
                    else:
                        actual_value = False
            if actual_value == value:
                print(f'[{self.test_case_name}] > Validate Field {field_name} with text : ["{value}"]')
                return True
            raise Exception(f'Validation failed for {field_name} , Expected : ["{value}"], Actual : ["{actual_value}"]')
        except Exception as E:
            raise Exception(f'Validation failed for {field_name} , Expected : ["{value}"],  Actual : {str(E)}')

    def verify_add_product_dialogue(self):
        """

        Returns:

        """
        print(f'[{self.test_case_name}] > Validating add product dialogue screen')
        status = self.wait_to_appear(item_text='Cancel')
        if status:
            self.click_screenshot_display(is_test_case_screenshot=True, screenshot_name='add_product_dialogue')
            self.common_functions.tap_using_ui_item(item_text='Cancel')
            print(f'[{self.test_case_name}] > Product dialogue is open')
        else:
            raise Exception('Product dialogue is closed')
        return True

    # ----------------------------- System Settings change  ----------------------------------------

    def set_global_unit(self, unit_name: str):
        """
        Setting global unit in display setting
        Args:
            unit_name: name of unit to select

        Returns:
            bool : Status of operation
        """
        try:
            self.click_settings()
            system_setting = Display.active_display_uiautomator(text='System')
            time.sleep(2)
            if system_setting.exists:
                system_setting.click()
                time.sleep(2)
                unit_metric = None
                for i in range(2):
                    try:
                        print(f'[{self.test_case_name}] > Searching for Unit Section in settings')
                        unit_metric = Display.active_display_uiautomator(className="android.view.View",
                                             resourceId="com.cnh.android.systemsettings:id/tab_activity_tabs") \
                            .child_by_text(
                            "Units & Metrics",
                            allow_scroll_search=True,
                            className="android.widget.TextView"
                        )
                        break
                    except:
                        continue
                if unit_metric is not None and unit_metric.exists:
                    print(f'[{self.test_case_name}] > Selecting Global unit : {unit_name}')
                    unit_metric.click()
                    time.sleep(2)
                    unit_id = DMConstants.SYSTEM_GLOBAL_UNITS_RESOURCES.get(unit_name, None)
                    if unit_id is not None:
                        unit_selection = Display.active_display_uiautomator(resourceId=unit_id)
                        time.sleep(1)
                        if unit_selection.exists:
                            unit_selection.click()
                            Display.active_display_uiautomator(resourceId='com.cnh.android.systemsettings:id/tab_activity_close').click()
                            print(f'[{self.test_case_name}] > Selected Global unit : {unit_name}')
                            return True
            raise Exception('Unit selection failed :', unit_name)
        except Exception as E:
            raise Exception('Unit not found :', unit_name, str(E))

    # ----------------------------- Database Verification --------------------------------------------

    def verify_prescription_rates(self, prescription_rates: Dict):
        """

        Args:
            prescription_rates:
        """
        prescription_table = 'prescription'
        prescription_zone_table = 'prescription_zone'

        print(f'[{self.test_case_name}] > Verifying prescription rates ')
        db_connector = DBConnector()
        print(f'[{self.test_case_name}] > Connecting to database ')
        db_connector.get_connection()
        print(f'[{self.test_case_name}] > Successfully Connected : [{db_connector.db_connection.dsn}]')
        status = []
        actual_data = None
        try:
            for prescription_name, rates in prescription_rates.items():
                print(f'[{self.test_case_name}] > Validating rates for prescription [{prescription_name}] ')
                temp = {prescription_name: []}
                rate_query = f'''select rate from {prescription_zone_table} 
                                           where prescription_id in (select id from {prescription_table} 
                                            where name='{prescription_name}')'''
                data, columns = db_connector.run_select_query(rate_query)
                actual_data = [round(d[0], 6) for d in data]
                add_failure = False
                for rate in rates:
                    if round(rate, 6) not in actual_data:
                        temp[prescription_name].append(rate)
                        add_failure = True
                if add_failure:
                    status.append(temp)
        except Exception as Err:
            raise Exception(str(Err))
        finally:
            db_connector.close_connection()

        if len(status) > 0:
            not_found = json.dumps(status, indent=1)
            actual = json.dumps(actual_data, indent=1)
            raise Exception(f'Failed to validate below fields : \n Expected : {not_found} \n Actual : {actual}')
        else:
            print(f'[{self.test_case_name}] > All rates validate successfully ')

    # ----------------------------- MAPS verification -----------------------------------------------
    def verify_map_screen(self, verification_data: List, reference_image: Union[str, List], threshold: float = 0.97):
        """

        Args:
            verification_data:
            reference_image:
            threshold:
        """
        global error
        print(f'[{self.test_case_name}] > Verifying map screen  ')
        time.sleep(1)
        for config in verification_data:
            if Display.active_display_uiautomator(text='Cancel').exists:
                self.common_functions.tap_using_ui_item(item_text='Cancel')
            for config_name, config_data in config.items():
                if config_name == 'Layer':
                    print(f'[{self.test_case_name}] > Verifying map screen configurations  [{config_name}]')
                    self.configure_layer(config_data)
                    print(f'[{self.test_case_name}] > Completed map screen configurations  [{config_name}]')

                elif config_name == 'Swath':
                    print(f'[{self.test_case_name}] > Verifying map screen configurations  [{config_name}]')
                    try:
                        self.configure_swath(config_data)
                        print(f'[{self.test_case_name}] > Completed map screen configurations  [{config_name}]')
                    except:
                        self.click_screenshot_display(is_test_case_screenshot=True, screenshot_name='Swath_verify')
                        buttonstatus = self.wait_to_appear(item_text='Cancel')
                        if buttonstatus:
                            self.common_functions.tap_using_ui_item(item_text='Cancel')
                            self.common_functions.tap_using_ui_item(item_text='Cancel')
                        else:
                            self.common_functions.tap_using_ui_item(item_text='Close')
                            self.common_functions.tap_using_ui_item(item_text='Close')
                        raise Exception('Failed to verify swath')

                elif config_name == 'Boundary':
                    print(f'[{self.test_case_name}] > Verifying map screen configurations  [{config_name}]')
                    try:
                        self.configure_boundary(config_data)
                        print(f'[{self.test_case_name}] > Completed map screen configurations  [{config_name}]')
                    except:
                        self.click_screenshot_display(is_test_case_screenshot=True, screenshot_name='Boundary_verify')
                        buttonstatus = self.wait_to_appear(item_text='Cancel')
                        if buttonstatus:
                            self.common_functions.tap_using_ui_item(item_text='Cancel')
                            self.common_functions.tap_using_ui_item(item_text='Cancel')
                        else:
                            self.common_functions.tap_using_ui_item(item_text='Close')
                            self.common_functions.tap_using_ui_item(item_text='Close')
                        raise Exception('Failed to verify boundary')
        if isinstance(reference_image, str):
            reference_image = [reference_image]
        status_matching = []
        error = 'Exception Handling'
        for image in reference_image:
            try:
                self.verify_reference_image(reference_image_name=image,
                                            crop=DMConstants.MAP_SCREEN_CROP_CO_ORDINATES,
                                            threshold=threshold)
                status_matching.append(True)
            except Exception as Err:
                status_matching.append(False)
                error = str(Err)

        if not any(status_matching):
            self.click_screenshot_display(is_test_case_screenshot=True, screenshot_name='Map_failed')
            buttonstatus = self.wait_to_appear(item_text='Cancel')
            if buttonstatus:
                self.common_functions.tap_using_ui_item(item_text='Cancel')
                self.common_functions.tap_using_ui_item(item_text='Cancel')
            else:
                self.common_functions.tap_using_ui_item(item_text='Close')
                self.common_functions.tap_using_ui_item(item_text='Close')
            raise Exception(error)
        print(f'[{self.test_case_name}] > Completed map screen verification')

    def click_menu_map_screen(self, menu: str):
        """

        Args:
            menu:

        Returns:

        """
        menu_widget = DMConstants.MAPS_SCREEN_RESOURCE_LIST.get(menu, None)
        if menu_widget is not None:
            print(f'[{self.test_case_name}] > Clicking Map screen Menu : [{menu}] ')
            if self.wait_to_appear(resource_id=menu_widget, timeout=120):
                if self.common_functions.tap_using_ui_item(resource_id=menu_widget):
                    print(f'[{self.test_case_name}] > Successfully clicked Map screen Menu : [{menu}] ')
                    return True
        print(f'Failed to change map screen menu : [{menu}]')
        return False

    def verify_reference_image(self, reference_image_name: str, crop: List = None, threshold: float = 0.90,
                               is_failure=False):
        """

        Args:
            is_failure:
            crop:
            reference_image_name:
            threshold:

        Returns:

        """
        time.sleep(2)
        target_image_path = self.click_screenshot_display()
        reference_image_path = os.path.abspath(
            self.ref_image_directory + f'/{self.test_case_name}/{reference_image_name}')

        if crop is not None:
            img = Image.open(target_image_path)
            area = (crop[0], crop[1], crop[0] + crop[2], crop[1] + crop[3])
            cropped_img = img.crop(area)
            cropped_image_path = os.path.abspath(DMConstants.TEMP_SCREENSHOT + '/crop.png')
            cropped_img.save(cropped_image_path)
            target_image_path = cropped_image_path

        image = cv2.imread(target_image_path)
        template = cv2.imread(reference_image_path)
        print(f'[{self.test_case_name}] > Comparing screenshot with reference image ')
        if image.shape[0] >= template.shape[0] and image.shape[1] >= template.shape[1] and image.shape[2] >= \
                template.shape[2]:
            result1 = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
            match = cv2.minMaxLoc(result1)[1]
            if match >= threshold:
                print(
                    f'[{self.test_case_name}] > Image Compare Status [PASS], Match [{match * 100}], Threshold [{threshold}] ')
                return True
            else:
                print(
                    f'[{self.test_case_name}] > Image Compare Status [FAIL], Match [{match * 100}], Threshold [{threshold}] ')
                if is_failure:
                    return True
                raise Exception(f'Reference image failed to match, Match : {match * 100}')
        raise Exception('Reference image size is small than Cropped image')

    def verify_reference_image_ui_widget(self, ui_object, reference_image_name: str, threshold: float = 0.97,
                                         is_failure=False, left_adjust=0, top_adjust=0, width_adjust=0,
                                         height_adjust=0):
        """

        Args:
            is_failure:
            ui_object:
            reference_image_name:
            threshold:

        Returns:

        """
        ui_info = ui_object.info
        left = ui_info['bounds']['left'] + left_adjust
        top = ui_info['bounds']['top'] + top_adjust
        width = ui_info['bounds']['right'] - ui_info['bounds']['left'] + width_adjust
        height = ui_info['bounds']['bottom'] - ui_info['bounds']['top'] + height_adjust
        box = [left, top, width, height]
        result = self.verify_reference_image(reference_image_name, box, threshold, is_failure)
        if result:
            return True
        else:
            return False

    def configure_layer(self, layer_configuration: Dict):
        """

        Args:
            layer_configuration:

        Returns:

        """
        self.change_run_screen(3)
        self.click_menu_map_screen(menu='ZCenter')
        self.click_menu_map_screen(menu='Layers')
        for title, layer in layer_configuration.items():
            if title == 'View':
                print(f'[{self.test_case_name}] > Configuring View options')
                for layer_name, layer_data in layer.items():
                    print(f'[{self.test_case_name}] > Searching layer : [{layer_name}] ')
                    time.sleep(5)
                    Display.active_display_uiautomator(resourceId='com.cnh.pf.map:id/la_panel_display_scrollview').child_by_text(layer_name,
                                                                                                     allow_scroll_search=True)
                    print(f'[{self.test_case_name}] > Found layer : [{layer_name}] ')
                    print(f'[{self.test_case_name}] > Configuring layer : [{layer_name}] ')
                    layer_item = Display.active_display_uiautomator(text=layer_name,
                                        resourceId='com.cnh.pf.map:id/la_display_layer_item_text')
                    x_arrow = layer_item.info['bounds']['right'] + 15
                    y_arrow = layer_item.info['bounds']['top'] + 25
                    left_arrow = layer_item.info['bounds']['left']
                    status = self.common_functions.tap_adb(x_arrow, y_arrow)
                    time.sleep(0.5)
                    if status:
                        print(f'[{self.test_case_name}] > Selected layer for configuration : [{layer_name}] ')
                        self.configure_selected_layer(layer_data)
                        apply_status = Display.active_display_uiautomator(text='Apply')
                        if apply_status.info['enabled']:
                            self.common_functions.tap_using_ui_item(item_text='Apply')
                        else:
                            print(f'[{self.test_case_name}] > Prescription already selected')
                            buttonstatus = self.wait_to_appear(item_text='Cancel')
                            if buttonstatus:
                                self.common_functions.tap_using_ui_item(item_text='Cancel')
                                self.common_functions.tap_using_ui_item(item_text='Cancel')
                            else:
                                self.common_functions.tap_using_ui_item(item_text='Close')
                                self.common_functions.tap_using_ui_item(item_text='Close')
                        time.sleep(0.5)
                        status = self.common_functions.tap_adb(left_arrow, y_arrow)
                        if status:
                            time.sleep(3)
                            print(f'[{self.test_case_name}] > Selected layer on map : [{layer_name}] ')
                            time.sleep(3)
                            buttonstatus = self.wait_to_appear(item_text='Cancel')
                            if buttonstatus:
                                self.common_functions.tap_using_ui_item(item_text='Cancel')
                            else:
                                self.common_functions.tap_using_ui_item(item_text='Close')
                            return True
                        else:
                            raise Exception(f'Failed to Select layer in task : [{layer_name}]')

                    else:
                        raise Exception(f'Failed to select layer : [{layer_name}]')

            if title == 'Legends':
                pass

    def configure_selected_layer(self, layer_data: Dict):
        """

        Args:
            layer_data:

        Returns:

        """
        for option, option_data in layer_data.items():
            if option == 'Color Scheme':
                pass
            if option == 'Ranges':
                pass
            if option == 'Background':
                if Display.active_display_uiautomator(resourceId='com.cnh.pf.map:id/la_manage_edit_background').click():
                    time.sleep(0.5)
                    switcher = Display.active_display_uiautomator(resourceId='com.cnh.pf.map:id/la_background_chooser_switch')
                    switcher_text = self.ui_automator_object_text(switcher, left_adjust=5, top_adjust=5,
                                                                  width_adjust=-80,
                                                                  height_adjust=-10)
                    if switcher_text == 'OFF':
                        if not switcher.click():
                            raise Exception(f'Failed to turn on Background option')
                    time.sleep(0.5)
                    for panel, item in option_data.items():
                        if Display.active_display_uiautomator(text=panel).click():
                            rx_prescription = f'Rx_{item}'
                            time.sleep(0.5)
                            status = self.common_functions.tap_using_ui_item(item_text=item)
                            if not status:
                                status = self.common_functions.tap_using_ui_item(item_text=rx_prescription)

                            if status:
                                if self.common_functions.tap_using_ui_item(item_text='Apply'):
                                    time.sleep(0.5)
                                    return True
                                else:
                                    self.click_screenshot_display(is_test_case_screenshot=True,
                                                                  screenshot_name='layer_background_apply')
                                    self.common_functions.tap_using_ui_item(item_text='Cancel')
                                    raise Exception(f'Failed to apply background')
                            else:
                                raise Exception('Prescription does not exists')
                        else:
                            raise Exception(f'Failed to click panel : [{panel}]')

                else:
                    raise Exception(f'Failed to select Background option edit box')

    def configure_swath(self, swath_configuration: Dict):
        """

        Args:
            swath_configuration:

        Returns:

        """
        self.change_run_screen(3)
        self.click_menu_map_screen(menu='ZCenter')
        self.click_menu_map_screen(menu='Swath')
        for title, swath in swath_configuration.items():
            if title == 'Manage':
                print(f'[{self.test_case_name}] > Configuring Manage options')
                self.common_functions.tap_using_ui_item(resource_id='com.cnh.pf.map:id/sw_button_select',
                                                        item_text='Manage')
                for swath_name, swath_data in swath.items():
                    print(f'[{self.test_case_name}] > Configuring swath : [{swath_name}] ')
                    Display.active_display_uiautomator(resourceId='com.cnh.pf.map:id/sw_list').child_by_text(swath_name, allow_scroll_search=True)
                    if swath_data is not None:
                        pass

                    os.environ["jsonrpc_timeout"] = '200'
                    if Display.active_display_uiautomator(text=swath_name).left(
                            resourceId='com.cnh.pf.map:id/list_item_check').click():
                        os.environ["jsonrpc_timeout"] = '90'
                        time.sleep(3)
                        print(f'[{self.test_case_name}] > Selected swath on map : [{swath_name}] ')
                        if Display.active_display_uiautomator(text='Apply').click():
                            print(f'[{self.test_case_name}] > Apply Swath [{swath_name}]')
                        return True
                    else:
                        raise Exception(f'Failed to Select swath : [{swath_name}]')

            if title == 'New':
                print(f'[{self.test_case_name}] > Configuring New swath')
                self.common_functions.tap_using_ui_item(resource_id='com.cnh.pf.map:id/sw_button_new',
                                                        item_text='New')

                swath_type = swath.get('Swath Type')
                if swath_type is not None:
                    print(f'[{self.test_case_name}] > Configuring Swath [{swath_type}]')
                    scroll_layout = Display.active_display_uiautomator(className="android.widget.ScrollView", index="1")
                    scroll_layout.scroll.to(text=swath_type)
                    status = Display.active_display_uiautomator(text=swath_type).click()
                    if status:
                        if Display.active_display_uiautomator(text='Apply').click():
                            print(f'[{self.test_case_name}] > Configured Swath [{swath_type}]')
                            return True

    def configure_boundary(self, boundary_configuration: Dict):
        """

        Args:
            boundary_configuration:

        Returns:

        """
        self.change_run_screen(3)
        self.click_menu_map_screen(menu='ZCenter')
        self.click_menu_map_screen(menu='Boundaries')
        for title, boundary in boundary_configuration.items():
            if title == 'Manage':
                print(f'[{self.test_case_name}] > Configuring Manage options')
                self.common_functions.tap_using_ui_item(resource_id='com.cnh.pf.map:id/bo_button_select',
                                                        item_text='Manage')
                for boundary_name, boundary_data in boundary.items():
                    print(f'[{self.test_case_name}] > Configuring boundary : [{boundary_name}] ')
                    Display.active_display_uiautomator(resourceId='com.cnh.pf.map:id/bo_list_scrollview').child_by_text(boundary_name,
                                                                                            allow_scroll_search=True)
                    if boundary_data is not None:
                        pass
                    os.environ["jsonrpc_timeout"] = '200'
                    check_box = Display.active_display_uiautomator(text=boundary_name).left(resourceId='com.cnh.pf.map:id/list_item_check')
                    if check_box.info['selected']:
                        print(f'[{self.test_case_name}] > Boundary already selected : [{boundary_name}] ')
                    else:
                        if Display.active_display_uiautomator(text=boundary_name).left(resourceId='com.cnh.pf.map:id/list_item_check').click():
                            os.environ["jsonrpc_timeout"] = '90'
                            time.sleep(3)
                            print(f'[{self.test_case_name}] > Selected Boundary on map : [{boundary_name}] ')
                            return True
                        else:
                            raise Exception(f'Failed to select boundary : [{boundary_name}]')

            if title == 'New':
                pass

    def configure_widget(self, widget_configuration: Dict):
        """

        Args:
            widget_configuration:

        Returns:

        """
        self.change_run_screen(3)
        self.click_menu_map_screen(menu='ZCenter')
        self.click_menu_map_screen(menu='Widgets')
        for title, config_data in widget_configuration.items():
            if title == 'AFS AccuTurn':
                is_enable = Display.active_display_uiautomator(resourceId='com.cnh.pf.map:id/mapudw_aeort_parent').exists
                time.sleep(10)
                self.common_functions.tap_adb(1255, 255)
                print("Tapped on gear")
                # Display.active_display_uiautomator(resourceId='com.cnh.pf.map:id/wi_aoert_button_gear').click()
                status = self.wait_to_appear(item_text='GNSS & Guidance | AFS AccuTurn')
                if status:
                    time.sleep(3)
                    self.click_image_icons(reference_image_name='ON', is_common=True)
                    # self.common_functions.long_press(400,265)
                    # aeort_widget = Display.active_display_uiautomator(resourceId='com.cnh.pf.phoenixapp:id/aeort_on_off_button')
                    # aeort_widget.click()
                    # aeort_on_off = self.ui_automator_object_text(aeort_widget)
                    # if aeort_on_off == 'OFF':
                    #     print(f'[{self.test_case_name}] > Turning on Aeort')
                    #     CommonFunctions.tap_ui_auto(400, 265)
                    print(f'[{self.test_case_name}] > Aeort is turned on')

                    config_status = {}

                    auto_turn_trigger = config_data.get('Auto Turn Trigger')
                    if auto_turn_trigger is not None:
                        print(f'[{self.test_case_name}] > Configuring auto turn trigger')
                        scroll_resource = 'com.cnh.pf.phoenixapp:id/turn_trigger_pick_list_header'
                        auto_turn_trigger_resource = 'com.cnh.pf.phoenixapp:id/turn_trigger_pick_list'
                        scroll_layout = Display.active_display_uiautomator(className="android.widget.ScrollView", index="0")
                        scroll_layout.scroll.to(resourceId=scroll_resource)
                        top_bound = Display.active_display_uiautomator(resourceId=scroll_resource).info['bounds']['top']
                        if top_bound > 500:
                            os.system('adb shell input swipe 700 600 700 500')
                        if top_bound < 200:
                            os.system('adb shell input swipe 700 500 700 600')

                        status = Display.active_display_uiautomator(resourceId=auto_turn_trigger_resource).click()
                        if status:
                            Display.active_display_uiautomator(resourceId='com.cnh.pf.phoenixapp:id/picklistPopupList').child_by_text(
                                auto_turn_trigger, allow_scroll_search=True)
                            status = Display.active_display_uiautomator(text=auto_turn_trigger).click()
                            if status:
                                print(
                                    f'[{self.test_case_name}] > Successfully set auto turn trigger to [{auto_turn_trigger}]')
                                config_status['Auto Turn Trigger'] = True
                            else:
                                print(
                                    f'[{self.test_case_name}] > Failed to set auto turn trigger to [{auto_turn_trigger}]')
                                config_status['Auto Turn Trigger'] = False
                                self.common_functions.tap_adb(1030, 125)

                    if not all(config_status.values()):
                        raise Exception('Failed to configure below fields')

                    self.common_functions.tap_using_ui_item(resource_id='com.cnh.pf.phoenixapp:id/tab_activity_close')

                if not is_enable:
                    self.common_functions.tap_using_ui_item(resource_id='com.cnh.pf.map:id/wi_aoert_check')
                    print(f'[{self.test_case_name}] > Already selected Aoert on map screen widget')

                if self.common_functions.tap_using_ui_item(resource_id='com.cnh.pf.map:id/wi_manage_button_apply'):
                    print(f'[{self.test_case_name}] > Successfully configured widgets')
                    return True
                raise Exception('Failed to apply Aeort')

    def swath_exists(self, swath_name: str):
        """
        Swath exists
        Args:
            swath_name: swath exist or not

        Returns:

        """
        self.change_run_screen(3)
        self.click_menu_map_screen(menu='Swath')
        print(f'[{self.test_case_name}] > Selecting Swath window')
        self.common_functions.tap_using_ui_item(item_text='Manage')
        swath_widget = Display.active_display_uiautomator(resourceId='com.cnh.pf.map:id/sw_list').child_by_text(swath_name,
                                                                                    allow_scroll_search=True)
        if swath_widget.exists:
            return True
        raise Exception(f'unable to find swath [{swath_name}]')

    def edit_swath(self, old_name: str, new_name: str):
        """
        Edit name of existing swath
        Args:
            old_name:
            new_name:
        """
        self.change_run_screen(3)
        self.click_menu_map_screen(menu='Swath')
        print(f'[{self.test_case_name}] > Selecting Swath window')
        self.common_functions.tap_using_ui_item(item_text='Manage')
        swath_widget = Display.active_display_uiautomator(resourceId='com.cnh.pf.map:id/sw_list').child_by_text(old_name,
                                                                                    allow_scroll_search=True)
        if swath_widget.exists:
            if Display.active_display_uiautomator(text=old_name).right(
                    resourceId='com.cnh.pf.map:id/list_item_button').click():
                time.sleep(3)
                print(f'[{self.test_case_name}] > Editing Swath name : [{old_name}] to [{new_name}] ')
                edit_widget = Display.active_display_uiautomator(resourceId="com.cnh.pf.map:id/sw_manage_edit_name")
                if edit_widget.exists:
                    edit_widget.click()
                    Display.active_display_uiautomator.press(0x0000001d, 0x00001000)
                    Display.active_display_uiautomator.press("delete")
                    edit_widget.set_text(new_name)
                    self.common_functions.tap_adb(1130, 690)
                    self.common_functions.tap_using_ui_item(item_text='Apply')
                    self.common_functions.tap_using_ui_item(item_text='Cancel')
                    return True
        raise Exception(f'unable to find or edit swath [{old_name}]')

    def copy_swath(self, copy_swath_name: str, new_swath_name=None):
        """
        Edit name of existing swath
        Args:
            copy_swath_name:
            new_swath_name:
        """
        self.change_run_screen(3)
        self.click_menu_map_screen(menu='Swath')
        print(f'[{self.test_case_name}] > Selecting Swath window')
        self.common_functions.tap_using_ui_item(item_text='Manage')
        swath_widget = Display.active_display_uiautomator(resourceId='com.cnh.pf.map:id/sw_list').child_by_text(copy_swath_name,
                                                                                    allow_scroll_search=True)
        if swath_widget.exists:
            if Display.active_display_uiautomator(text=copy_swath_name).right(
                    resourceId='com.cnh.pf.map:id/list_item_button').click():
                time.sleep(3)
                print(f'[{self.test_case_name}] > Copy Swath : [{copy_swath_name}] ')
                copy_swath_widget = Display.active_display_uiautomator(resourceId='com.cnh.pf.map:id/sw_manage_button_copy')
                copy_swath_widget.click()
                if new_swath_name is not None:
                    edit_widget = Display.active_display_uiautomator(resourceId="com.cnh.pf.map:id/sw_manage_edit_name")
                    edit_widget.click()
                    Display.active_display_uiautomator.press(0x0000001d, 0x00001000)
                    Display.active_display_uiautomator.press("delete")
                    edit_widget.set_text(new_swath_name)
                    self.common_functions.tap_adb(1130, 690)
                    self.common_functions.tap_using_ui_item(item_text='Apply')
                self.common_functions.tap_using_ui_item(item_text='Cancel')
                self.common_functions.tap_using_ui_item(item_text='Cancel')
                self.common_functions.tap_using_ui_item(item_text='Cancel')
                return True
        raise Exception(f'unable to find or copy swath [{copy_swath_name}]')

    def delete_swath(self, swath_name: str):
        """
        Edit name of existing swath
        Args:
            swath_name:
        """
        self.change_run_screen(3)
        self.click_menu_map_screen(menu='Swath')
        print(f'[{self.test_case_name}] > Selecting Swath window')
        self.common_functions.tap_using_ui_item(item_text='Manage')
        swath_widget = Display.active_display_uiautomator(resourceId='com.cnh.pf.map:id/sw_list').child_by_text(swath_name,
                                                                                    allow_scroll_search=True)

        if swath_widget.exists:
            if Display.active_display_uiautomator(text=swath_name).right(
                    resourceId='com.cnh.pf.map:id/list_item_button').click():
                time.sleep(3)
                print(f'[{self.test_case_name}] > Delete Swath : [{swath_name}] ')
                copy_swath_widget = Display.active_display_uiautomator(resourceId='com.cnh.pf.map:id/sw_manage_button_delete')
                copy_swath_widget.click()
                self.common_functions.tap_using_ui_item(item_text='Yes')
                self.common_functions.tap_using_ui_item(item_text='Cancel')
                self.common_functions.tap_using_ui_item(item_text='Cancel')
                return True
        raise Exception(f'unable to find or delete swath [{swath_name}]')

    def edit_boundary(self, old_name: str, new_name: str):
        """
        Edit name of existing swath
        Args:
            old_name:
            new_name:
        """
        self.change_run_screen(3)
        self.click_menu_map_screen(menu='Boundaries')
        print(f'[{self.test_case_name}] > Selecting Boundary window')
        self.common_functions.tap_using_ui_item(item_text='Manage')
        boundary_widget = Display.active_display_uiautomator(resourceId='com.cnh.pf.map:id/bo_list_scrollview').child_by_text(old_name,
                                                                                                  allow_scroll_search=True)
        if boundary_widget.exists:
            if Display.active_display_uiautomator(text=old_name).right(
                    resourceId='com.cnh.pf.map:id/list_item_button').click():
                time.sleep(3)
                print(f'[{self.test_case_name}] > Editing Swath name : [{old_name}] to [{new_name}] ')
                edit_widget = Display.active_display_uiautomator(resourceId="com.cnh.pf.map:id/bo_manage_edit_name")
                if edit_widget.exists:
                    edit_widget.click()
                    Display.active_display_uiautomator.press(0x0000001d, 0x00001000)
                    Display.active_display_uiautomator.press("delete")
                    edit_widget.set_text(new_name)
                    self.common_functions.tap_adb(1130, 690)
                    self.common_functions.tap_using_ui_item(item_text='Apply')
                    self.common_functions.tap_using_ui_item(item_text='Cancel')
                    return True
        raise Exception(f'unable to find or edit Boundary [{old_name}]')

    def set_boundary_impassable_properties(self, boundary_name: str, impassable: bool):
        """

        Args:
            boundary_name:
            impassable:  passable if True
        """
        self.change_run_screen(3)
        self.click_menu_map_screen(menu='Boundaries')
        print(f'[{self.test_case_name}] > Selecting Boundary window')
        self.common_functions.tap_using_ui_item(item_text='Manage')
        boundary_widget = Display.active_display_uiautomator(resourceId='com.cnh.pf.map:id/bo_list_scrollview').child_by_text(boundary_name,
                                                                                                  allow_scroll_search=True)
        passable_resource_id = 'com.cnh.pf.map:id/bo_manage_button_passable'
        impassable_resource_id = 'com.cnh.pf.map:id/bo_manage_button_impassable'
        if boundary_widget.exists:
            if Display.active_display_uiautomator(text=boundary_name).right(
                    resourceId='com.cnh.pf.map:id/list_item_button').click():
                time.sleep(3)
                print(f'[{self.test_case_name}] > Setting Passable as [{impassable}] ')
                if impassable:
                    Display.active_display_uiautomator(resourceId=impassable_resource_id).click()
                else:
                    Display.active_display_uiautomator(resourceId=passable_resource_id).click()
                self.common_functions.tap_using_ui_item(item_text='Apply')
                self.common_functions.tap_using_ui_item(item_text='Cancel')
                self.common_functions.tap_using_ui_item(item_text='Cancel')
                return True
        raise Exception(f'unable to find or change setting for Boundary [{boundary_name}]')

    def set_boundary_type(self, boundary_name: str, boundary_type: str):
        """

        Args:
            boundary_name:
            boundary_type: Type of boundary
        """
        self.change_run_screen(3)
        self.click_menu_map_screen(menu='Boundaries')
        print(f'[{self.test_case_name}] > Selecting Boundary window')
        self.common_functions.tap_using_ui_item(item_text='Manage')
        boundary_widget = Display.active_display_uiautomator(resourceId='com.cnh.pf.map:id/bo_list_scrollview').child_by_text(boundary_name,
                                                                                                  allow_scroll_search=True)
        inner_resource_id = 'com.cnh.pf.map:id/bo_manage_button_inner'
        outer_resource_id = 'com.cnh.pf.map:id/bo_manage_button_outer'
        if boundary_widget.exists:
            if Display.active_display_uiautomator(text=boundary_name).right(
                    resourceId='com.cnh.pf.map:id/list_item_button').click():
                time.sleep(3)
                print(f'[{self.test_case_name}] > Setting Boundary type as [{boundary_type}] ')
                if boundary_type == 'Outer':
                    Display.active_display_uiautomator(resourceId=outer_resource_id).click()
                else:
                    Display.active_display_uiautomator(resourceId=inner_resource_id).click()
                self.common_functions.tap_using_ui_item(item_text='Apply')
                self.common_functions.tap_using_ui_item(item_text='Cancel')
                self.common_functions.tap_using_ui_item(item_text='Cancel')
                return True
        raise Exception(f'unable to find or change setting for Boundary [{boundary_name}]')

    def boundary_exists(self, boundary_name: str):
        """
        Swath exists
        Args:
            boundary_name: swath exist or not

        Returns:

        """
        self.change_run_screen(3)
        self.click_menu_map_screen(menu='Boundaries')
        print(f'[{self.test_case_name}] > Selecting Boundaries window')
        self.common_functions.tap_using_ui_item(item_text='Manage')
        print(f'[{self.test_case_name}] > Searching for Boundary [{boundary_name}]')
        try:
            boundary_widget = Display.active_display_uiautomator(resourceId='com.cnh.pf.map:id/bo_list_scrollview').child_by_text(boundary_name,
                                                                                                      allow_scroll_search=True)
            if boundary_widget.exists:
                print(f'[{self.test_case_name}] > Boundary [{boundary_name}], Found : True')
                return True
            print(f'[{self.test_case_name}] > Searching for Boundary [{boundary_name}], Found : False')
            return False
        except Exception:
            print(f'[{self.test_case_name}] > Searching for Boundary [{boundary_name}], Found : False')
            return False
        finally:
            self.common_functions.tap_using_ui_item(item_text='Cancel')
            self.common_functions.tap_using_ui_item(item_text='Cancel')

    def landmark_exists(self, landmark_name: str):
        """
        Swath exists
        Args:
            landmark_name:

        Returns:

        """
        self.change_run_screen(3)
        self.click_menu_map_screen(menu='Landmarks')
        print(f'[{self.test_case_name}] > Selecting Landmark window')
        self.common_functions.tap_using_ui_item(item_text='Manage')
        print(f'[{self.test_case_name}] > Searching for Landmark [{landmark_name}]')
        try:
            landmark_widget = Display.active_display_uiautomator(resourceId='com.cnh.pf.map:id/ob_list').child_by_text(landmark_name,
                                                                                           allow_scroll_search=True)
            if landmark_widget.exists:
                print(f'[{self.test_case_name}] > Landmark [{landmark_name}], Found : True')
                return True
            print(f'[{self.test_case_name}] > Searching for Landmark [{landmark_name}], Found : False')
            return False
        except Exception:
            print(f'[{self.test_case_name}] > Searching for Landmark [{landmark_name}], Found : False')
            return False
        finally:
            self.common_functions.tap_using_ui_item(item_text='Cancel')
            self.common_functions.tap_using_ui_item(item_text='Cancel')

    def prescription_exists(self, layer_name, prescription_name: str):
        """

        Args:
            layer_name:
            prescription_name:

        Returns:

        """
        self.change_run_screen(3)
        self.click_menu_map_screen(menu='Layers')
        Display.active_display_uiautomator(resourceId='com.cnh.pf.map:id/la_panel_display_scrollview').child_by_text(layer_name,
                                                                                         allow_scroll_search=True)
        status = Display.active_display_uiautomator(text=layer_name).right(
            resourceId='com.cnh.pf.map:id/la_display_layer_item_arrow').click()
        time.sleep(0.5)
        if status:
            print(f'[{self.test_case_name}] > Selected layer for configuration : [{layer_name}] ')
            if Display.active_display_uiautomator(resourceId='com.cnh.pf.map:id/la_manage_edit_background').click():
                time.sleep(0.5)
                switcher = Display.active_display_uiautomator(resourceId='com.cnh.pf.map:id/la_background_chooser_switch')
                switcher_text = self.ui_automator_object_text(switcher, left_adjust=5, top_adjust=5,
                                                              width_adjust=-80,
                                                              height_adjust=-10)
                if switcher_text == 'OFF':
                    if not switcher.click():
                        raise Exception(f'Failed to turn on Background option')
                time.sleep(0.5)
                Display.active_display_uiautomator(text='Rx').click()
                prescription = Display.active_display_uiautomator(text=prescription_name)
                self.common_functions.tap_using_ui_item(item_text='Cancel')
                self.common_functions.tap_using_ui_item(item_text='Cancel')
                self.common_functions.tap_using_ui_item(item_text='Cancel')
                if prescription.exists:
                    return True
                else:
                    return False
            else:
                raise Exception(f'Failed to select Background option edit box')

    # ----------------------------- File/DB download functions -----------------------------------------------

    def download_data(self, folder_name, details, remove_previous_folder=False):
        """

        Args:
            remove_previous_folder:
            folder_name:
            details:
        """
        print(f'[{self.test_case_name}] > Collect files from PCM and Database')
        folder_path = os.path.abspath(self.data_container_dir + f'/{folder_name}')
        os.makedirs(folder_path, exist_ok=True)
        db_connector = DBConnector()
        ssh_connector = SSHConnector()

        db_tables = details.get('DB_Tables')
        if db_tables is not None:
            print(f'[{self.test_case_name}] > Collecting tables ')
            for table_name in db_tables:
                print(f'[{self.test_case_name}] > Collecting [{table_name}]')
                query = f''' select * from {table_name}'''
                try:
                    data, columns = db_connector.run_select_query(query)
                except:
                    data = []
                    columns = []

                with open(folder_path + f'/{table_name}.json', 'w+') as file_object:
                    file_data = {'Columns': columns,
                                 'Data': data}
                    file_object.write(json.dumps(file_data, indent=2, sort_keys=True))

        folders = details.get('Folders')
        files = details.get('Files')

        if folders is not None or files is not None:
            try:
                ssh_connector.pcm_open_connection()
                if folders is not None:
                    print(f'[{self.test_case_name}] > Collecting folders ')
                    for name, path in folders.items():
                        print(f'[{self.test_case_name}] > Collecting [{name}] ')
                        from_location = path
                        to_location = os.path.abspath(folder_path + f'/{name}')
                        if os.path.isdir(to_location):
                            os.remove(to_location)
                            print(f'[{self.test_case_name}] > Removing Previous folder {name} ')
                        os.makedirs(to_location, exist_ok=True)
                        ssh_connector.download_folder(from_location, to_location)

                if files is not None:
                    print(f'[{self.test_case_name}] > Collecting files ')
                    for name, path in files.items():
                        print(f'[{self.test_case_name}] > Collecting [{name}] ')
                        to_location = os.path.abspath(folder_path + f'/{name}')
                        ssh_connector.download_file(path, to_location)

            finally:
                ssh_connector.pcm_close_connection()

    def get_database_columns_value(self, table_name, columns_name, condition=None, is_multiple=False):
        """

        Args:
            is_multiple:
            table_name:
            columns_name:
            condition:

        Returns:

        """
        if isinstance(columns_name, str):
            columns_name = [columns_name]
        print(f'[{self.test_case_name}] > Connecting to Database')
        db_connector = DBConnector()
        columns_str = ','.join(columns_name)
        query = f''' select {columns_str} from {table_name}'''
        if condition is not None:
            query = f''' select {columns_str} from {table_name} where {condition}'''
        try:
            data_dict = {}
            print(f'[{self.test_case_name}] > Fetching Data ..')
            data, columns = db_connector.run_select_query(query)
            if is_multiple:
                counter = 0
                for d in data:
                    data_dict[counter] = {column: value for column, value in
                                          zip(columns, d)}
                    counter += 1
            else:
                if len(data) > 0:
                    data_dict = {column: value for column, value in
                                 zip(columns, data[0])}

            print(f'[{self.test_case_name}] > Fetching Successfully completed ..')
            return data_dict
        except:
            raise Exception(f'Failed to get data from Table : [{table_name}]')
        finally:
            db_connector.close_connection()

    def get_sqlite_database_columns_value(self, data_container, task_folder, table_name, columns_name, condition=None,
                                          is_multiple=False):
        """

        Args:
            task_folder:
            data_container:
            is_multiple:
            table_name:
            columns_name:
            condition:

        Returns:

        """
        if isinstance(columns_name, str):
            columns_name = [columns_name]
        print(f'[{self.test_case_name}] > Connecting to Database')
        database_file_location = os.path.abspath(
            DMConstants.DATA_CONTAINERS + f'/{self.test_case_name}/{data_container}/{task_folder}')
        db_files = [os.path.abspath(database_file_location + f'/{file}') for file in os.listdir(database_file_location)
                    if file.endswith('.db')]
        db_file = None
        if len(db_files) > 0:
            db_file = db_files[0]
        else:
            raise Exception(f'Database file not found at {database_file_location}')

        db_connector = SQLiteConnector(db_file)
        columns_str = ','.join(columns_name)
        query = f''' select {columns_str} from {table_name}'''
        if condition is not None:
            query = f''' select {columns_str} from {table_name} where {condition}'''
        try:
            data_dict = {}
            print(f'[{self.test_case_name}] > Fetching Data ..')
            data, columns = db_connector.run_select_query(query)
            if is_multiple:
                counter = 0
                for d in data:
                    data_dict[counter] = {column: value for column, value in
                                          zip(columns, d)}
                    counter += 1
            else:
                data_dict = {column: value for column, value in
                             zip(columns, data[0])}
            print(f'[{self.test_case_name}] > Fetching Successfully completed ..')
            return data_dict
        except:
            raise Exception(f'Failed to get data from Table : [{table_name}]')
        finally:
            db_connector.close_connection()

    def verify_hash_directories(self, directory_1, directory_2, match_individual=False, hash_algorithm='md5'):
        """

        Args:
            directory_1:
            directory_2:
            hash_algorithm:
            match_individual:
        Returns:

        """
        print(f'[{self.test_case_name}] > Hashing directory with hash algorithm {hash_algorithm}')
        md5_hash_object = FileHash(hash_algorithm)
        if match_individual:
            failed_match = {}
            for file_1 in os.listdir(directory_1):
                file_path_1 = os.path.abspath(directory_1 + f'/{file_1}')
                file_path_2 = os.path.abspath(directory_2 + f'/{file_1}')
                if os.path.isfile(file_path_1) and os.path.isfile(file_path_2):
                    hash_1 = md5_hash_object.hash_file(file_path_1)
                    hash_2 = md5_hash_object.hash_file(file_path_2)
                    if hash_1 != hash_2:
                        failed_match[file_1] = {'dir_1': hash_1, 'dir_2': hash_2}

            if len(failed_match) > 0:
                return False, failed_match
            return True, {}

        else:
            directory_1_hash = md5_hash_object.hash_dir(directory_1)
            directory_2_hash = md5_hash_object.hash_dir(directory_2)

            if directory_1_hash == directory_2_hash:
                print(f'[{self.test_case_name}] > Both directory has matching content')
                return True, {}
            print(f'[{self.test_case_name}] > Directory Content mismatched')
            return False, {}

    # -------------------------- Logging PCM ----------------------------------------------------------

    def monitor_log_pfdatasynced(self, data, stop_thread):
        """
        monitor log pfdatasynced log
        Returns:

        """
        stages = {
            'Export': r'Perform Operations ISOXML',
            'Export Completed': 'WORKING pfNewExportAvailable',
            'Chunk Found': 'status:CHUNK_FILE_AVAILABLE',
            'Hydration success': 'status:HYDRATION_SUCCESSFUL,',
            '100% Hydration Success': '- HYDRATION_SUCCESSFUL: TASKDATA'
        }
        file_zip_name = None
        ssh_manager = SSHConnector()
        ssh_manager.pcm_open_connection()
        _, out, _ = ssh_manager.ssh_client.exec_command(
            'ls -t /var/volatile/tmp/mount/farming/data/log/cnhi/pfdata* | head -n 1 ')
        latest_file = out.readline().strip()

        _, read_lines, _ = ssh_manager.ssh_client.exec_command(f'tail -f {latest_file}')
        counter = 0
        completed = False
        for line in iter(read_lines):
            counter += 1
            if counter < 10:
                continue
            if stop_thread():
                break
            for k, val in stages.items():
                if val in line:
                    print(f'[PFdatasynced] > ', k, ' Log : ', line.strip())
                    if k == '100% Hydration Success':
                        completed = True
                        zip_sp = line.split('HYDRATION_SUCCESSFUL:')[-1].strip().split('.')
                        file_zip_name = '.'.join(zip_sp[:3])
                        tdac = zip_sp[3]
                        data.put(file_zip_name + '::' + tdac)
                        break
            if completed:
                print(f'[PFdatasynced - COMPLETE] > Stopping monitor thread ..')
                break
        ssh_manager.pcm_close_connection()
        print(f'[SSH Connection] > Closed....')

    def auto_export_event_scheduler(self):
        self.count = 0
        print(f'[Event_Receiver] > Wait complete...Initializing data capture sequence....')
        t = time.localtime()
        current_time = time.strftime("%H:%M:%S", t)
        current_date = str(date.today())
        log_time = current_time
        stages = {
            'Chunk Found': 'status:CHUNK_FILE_AVAILABLE',
            'Hydration success': 'status:HYDRATION_SUCCESSFUL,',
            '100% Hydration Success': '- HYDRATION_SUCCESSFUL: TASKDATA'
        }
        ssh_manager = SSHConnector()
        ssh_manager.pcm_open_connection()
        _, out, _ = ssh_manager.ssh_client.exec_command(
            'ls -t /var/volatile/tmp/mount/farming/data/log/cnhi/pfdata* | head -n 1 ')
        latest_file = out.readline().strip()

        _, read_lines, _ = ssh_manager.ssh_client.exec_command(f'tail -f {latest_file}')
        counter = 0
        completed = False
        print(f'[Event_Receiver] > Processing data.Please wait.....')
        for line in iter(read_lines):
            counter += 1
            if counter < 10:
                continue
            for k, val in stages.items():
                if val in line:
                    print(f'[PFdatasynced] > ', k, ' Log : ', line.strip())
                    if k == 'Hydration success':
                        self.count = self.count + 1
                        completed = True
                        zip_sp = line.split('HYDRATION_SUCCESSFUL:')[-1].strip().split('.')
                        file_zip_name = '.'.join(zip_sp[:3])
                        tdac = zip_sp[3]
                        received_data = (file_zip_name + '::' + tdac)
                        data_logger = os.path.abspath(DMConstants.EXPORT + f'/AGDNA/AUTO_Export_monitor_log.txt')
                        with open(data_logger, 'a') as f:
                            f.write(current_date)
                            f.write('\t')
                            f.write(k)
                            f.write('\n')
                            f.write(log_time)
                            f.write('\t')
                            f.write(received_data)
                            f.write('\n\n')
                            print(f'[Event_Receiver] > Saved data in logger...')
                        with open(data_logger, 'r') as f:
                            content = f.readlines()
                            cnt = 0
                            for data_line in content:
                                if 'Hydration success count: ' in data_line:
                                    data_line = 'Hydration success count: {}\n'.format(self.count)
                                    content[cnt] = data_line
                                    break
                                cnt = cnt + 1
                            with open(data_logger, 'w') as f:
                                f.writelines(content)
                            return self.count
                        break
            if completed:
                print(f'[Event_Receiver] > Completed! Wait for the next sequence...')
                time.sleep(2)
                break

        ssh_manager.pcm_close_connection()

    def run_monitor_export(self, token: int = None, minutes: int = None):
        self.runner_count = 0
        for self.runner_count in range(1, token):
            print(f'[Event_Receiver] > Event scheduler started... ')
            time.sleep(1)
            data_logger = os.path.abspath(DMConstants.EXPORT + f'/AGDNA/AUTO_Export_monitor_log.txt')
            toplayer = "#################################################### AUTO EXPORT MONITOR LOG ####################################################"
            with open(data_logger, 'a') as f:
                f.truncate(0)
                print(f'[Event_Receiver] > Clearing old logs... ')
                f.write(toplayer)
                f.write('\n')
                f.write('Hydration success count: 0')
                f.write('\n\n')
            t = time.localtime()
            current_time = time.strftime("%H:%M:%S", t)
            gmt_time = timezone('GMT')
            schedule.every(minutes).minutes.do(self.auto_export_event_scheduler)
            while True:
                schedule.run_pending()
                time.sleep(1)
                print(
                    f'[Event_Receiver] > START TIME: [{current_time}] | GMT TIME: [{datetime.now(gmt_time)}] | WAIT TIME: [{minutes}] minute(s).')

    def extract_zip_to_folder(self, zip_file, extract_folder):
        """
        Extract zip file to folder
        Args:
            zip_file:
            extract_folder:
        """
        print(f'[{self.test_case_name}] > Extract zip file to folder')
        if os.path.isdir(extract_folder):
            shutil.rmtree(extract_folder)
        os.makedirs(extract_folder, exist_ok=True)
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(extract_folder)
        print(f'[{self.test_case_name}] > Extracted files from zip file')

    # ------------------------- Selenium -------------------------------------------------------

    def download_and_send_taskdata_ag_dna_portal(self, file_name, send_tdac=None,
                                                 company='Data Management Company (ACC000002191)'):
        """
        Download file from AGDNA portal
        Args:
            company:
            send_tdac:
            file_name: name of taskdata file

        Returns:
            tuple : (downloaded file path , send file name)

        """
        if not os.path.isdir(DMConstants.AG_DNA):
            os.makedirs(DMConstants.AG_DNA, exist_ok=True)

        if os.path.isfile(DMConstants.AG_DNA + f'/{file_name}'):
            os.remove(DMConstants.AG_DNA + f'/{file_name}')

        # # For Chrome ----------------------------------------------------------------
        # chromedriver_exe = os.path.abspath(DMConstants.UTILITIES + '/chromedriver.exe')
        # chrome_options = webdriver.ChromeOptions()
        # prefs = {"download.default_directory": DMConstants.AG_DNA}
        # chrome_options.add_experimental_option("prefs", prefs)
        # chrome = webdriver.Chrome(executable_path=chromedriver_exe, options=chrome_options)
        # # For Edge -------------------------------------------------------------------
        options = webdriver.EdgeOptions()
        options.use_chromium = True
        options.add_experimental_option("prefs", {"download.default_directory": DMConstants.AG_DNA})
        msedgedriver_exe = os.path.abspath(DMConstants.UTILITIES + f'/msedgedriver.exe')
        chrome = webdriver.Edge(executable_path=msedgedriver_exe, options=options)

        try:
            chrome.get(TestSuitConfig.AG_DNA_WEBSITE_URL)
            print(f'[{self.test_case_name}] > Login into AGDNA Portal')
            username_element = chrome.find_element("id", DMConstants.SE_USERNAME)
            username_element.send_keys(base64.b64decode(TestSuitConfig.AG_DNA_USERNAME).decode())

            password_element = chrome.find_element("id", DMConstants.SE_PASSWORD)
            password_element.send_keys(base64.b64decode(TestSuitConfig.AG_DNA_PASSWORD).decode())

            login_element = chrome.find_element("id", DMConstants.SE_LOGIN)
            login_element.click()
            chrome.maximize_window()
            print(f'[{self.test_case_name}] > Waiting for portal to load ...')
            wait = WebDriverWait(chrome, 300)
            # ---------- Disabled as popup is not observed --------------- #
            # pop_wait = WebDriverWait(chrome, 150)
            # popup = pop_wait.until(EC.element_to_be_clickable((By.XPATH, '/html/body/div[3]/div/div/div[1]/button')))
            # if popup:
            #     print(f'[{test_case_name}] > Pop-Up found... handling it..')
            #     chrome.find_element("xpath", "/html/body/div[3]/div/div/div[1]/button").click()
            #     time.sleep(2)
            # else:
            #     pass
            # ---------- ================================= --------------- #
            wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="mnuMapNav"]/div/div/div[4]/a[2]')))
            chrome.find_element("xpath", '//*[@id="mnuMapNav"]/div/div/div[4]/a[2]').click()
            print(f'[{self.test_case_name}] > Expect to download file : {file_name}')
            wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '#tabSetupFiles')]")))
            chrome.find_element("xpath", "//a[contains(@href, '#tabSetupFiles')]").click()
            wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(),'Data Files')]")))
            time.sleep(10)
            chrome.find_element("xpath", "//a[contains(text(),'Data Files')]").click()
            time.sleep(5)
            chrome.find_element("xpath", '//*[@id="rcdFilesTable_filter"]/label/input').click()
            time.sleep(2)
            chrome.find_element("xpath", '//*[@id="rcdFilesTable_filter"]/label/input').send_keys(
                file_name + Keys.RETURN)
            time.sleep(3)
            print(f'[{self.test_case_name}] > Attempting to find and download the requested file..')

            def every_downloads_chrome(driver):
                if not driver.current_url.startswith("chrome://downloads"):
                    driver.get("chrome://downloads/")
                return driver.execute_script("""
                    var items = document.querySelector('downloads-manager')
                        .shadowRoot.getElementById('downloadsList').items;
                    if (items.every(e => e.state === "COMPLETE"))
                        return items.map(e => e.fileUrl || e.file_url);
                    """)

            try:
                # if send_tdac is not None and company is not None:  # Function locked as it is not valid anymore
                #     print(f'[{self.test_case_name}] > Sending file to display ...')
                # send_file_name = self.send_taskdata_to_display(chrome, send_tdac, company)

                chrome.find_element("class name", 'btn-download').click()
                print(f'[{self.test_case_name}] > Downloading started ...')
                # -------- Function modified ----------- #
                # time.sleep(5)
                # WebDriverWait(chrome, 240, 1).until(every_downloads_chrome)  # javascript error
                # -------------------------------------- #
                target = "Unconfirmed"
                files = DMConstants.AG_DNA
                wait = True
                while wait:
                    for fname in os.listdir(files):
                        if target in fname:
                            print(f'[{self.test_case_name}] > Waiting for download to finish......')
                            wait = True
                        else:
                            wait = False
                print(f'[{self.test_case_name}] > Download finished')
            except:
                raise Exception(f'Expected file not found in portal: {file_name}')

            # return os.path.abspath(DMConstants.AG_DNA + f'/{file_name}'), send_file_name
            return os.path.abspath(DMConstants.AG_DNA + f'/{file_name}')

        except Exception as Err:
            raise Exception(f'Failed to download TASKDATA, Error : {str(Err)}')

        finally:
            chrome.close()
            chrome.quit()

    def send_taskdata_to_display(self, chrome, send_tdac, company):
        """

        Args:
            send_tdac:
            company:

        Returns:

        """
        chrome.find_element_by_class_name('send').click()
        time.sleep(4)
        Select(chrome.find_element_by_class_name('org')).select_by_visible_text(company)
        print(f'[{self.test_case_name}] > Searching TDAC : [{send_tdac}]...')
        chrome.find_elements_by_xpath("//div[@class='btn-group bootstrap-multiselect']")[2].click()
        chrome.find_elements_by_class_name('multiselect-search')[1].send_keys(send_tdac)
        [element for element in chrome.find_elements_by_xpath(f"//label[@class='checkbox']") if
         send_tdac in element.text][0].click()
        print(f'[{self.test_case_name}] > Selected TDAC : [{send_tdac}]...')
        [element for element in chrome.find_elements_by_class_name('open') if send_tdac in element.text][
            0].click()
        chrome.find_element_by_class_name('modal-ok').click()
        time.sleep(7)
        chrome.find_element_by_class_name('modal-ok').click()
        time.sleep(3)
        print(f'[{self.test_case_name}] > Sending File...')
        WebDriverWait(chrome, 60).until(EC.alert_is_present(), 'Timeout sending file')
        chrome.switch_to.alert.accept()
        time.sleep(3)

        while True:
            first_element = chrome.find_element_by_id('processStatusList').find_element_by_tag_name('tr')
            progress_msg = first_element.find_element_by_xpath("//td[@class=' progressMessage']").text

            if 'Finished - File was sent successful' in progress_msg:
                file_name_txt = first_element.find_element_by_xpath(
                    "//td[contains(text(),'Machine Confirmation')]").text
                file_name = file_name_txt.split('(')[1].split('to')[0].strip()
                chrome.find_element_by_id('dlgProcessStatus').find_element_by_class_name('close').click()
                print(f'[{self.test_case_name}] > Sending completed successfully ...')
                return file_name
            else:
                time.sleep(10)
                chrome.find_element_by_class_name('btnRefresh').click()

        # chrome.find_element_by_id('dlgProcessStatus').find_element_by_class_name('close').click()
        # print(f'[{self.test_case_name}] > Sending completed successfully ...')

    def SDP_Portal_autoexport_data_check(self, TDAC_num):
        """
        1. This functions opens SDP and navigates to UPLINK where export files are uploaded.
        2. Once in UPLINK, this functions collect the date and validates with the exported TASKDATA file
           uploaded in portal by the auto-export function in PCM.
        """
        global timestamp, value, key, result_status
        # # For Chrome only --------------------------------------------------------------
        options = Options()
        options.add_argument('--no-sandbox')
        config = configparser.ConfigParser()
        config_dir = Helper.script_dir + "\\"
        config.read(config_dir + 'config.ini')
        chromedriver_exe = os.path.abspath(DMConstants.UTILITIES + f'/chromedriver.exe')
        chrome_options = webdriver.ChromeOptions()
        driver = webdriver.Chrome(executable_path=chromedriver_exe, options=chrome_options)
        # # For Edge only -------------------------------------------------------------------
        # msedgedriver_exe = os.path.abspath(DMConstants.UTILITIES + f'/msedgedriver.exe')
        # driver = webdriver.Edge(msedgedriver_exe)
        # # Common
        driver.get(TestSuitConfig.SDP_Portal)
        auto_export_files = {}
        manual_export_files = {}
        auto_timestamp = {}
        manual_timestamp = {}
        global file, time_stamp
        data_logger = os.path.abspath(DMConstants.EXPORT + f'/AGDNA/SDP_Export_monitor_log.txt')
        time.sleep(5)
        try:
            print("Your SELENIUM version: %s" % (selenium.__version__))
            print(f'[SDP Log Validator] > Maximizing Chrome Window')
            driver.maximize_window()  # if you want to see the web-automation
            # driver.minimize_window()    # if you do not want to see the web-automation
            time.sleep(1)
            driver.find_element("xpath", TestSuitConfig.understand_button).click()
            print(f'[SDP Log Validator] > Clicked on I Understand Button')
            time.sleep(1)
            driver.find_element("xpath", TestSuitConfig.sdp_login_button).click()
            print(f'[SDP Log Validator] > Clicked on Use CNH Login button')
            time.sleep(3)
            driver.find_element("xpath", TestSuitConfig.sdp_user_name).send_keys(TestSuitConfig.SDP_Username)
            print(f'[SDP Log Validator] > Entered User name')
            driver.find_element("xpath", TestSuitConfig.sdp_password).send_keys(TestSuitConfig.SDP_Password)
            print(f'[SDP Log Validator] > Entered Password')
            driver.find_element("xpath", TestSuitConfig.sdp_login_app).click()
            print(f'[SDP Log Validator] > Clicked on Login')
            time.sleep(6)
            if driver.find_element("xpath", TestSuitConfig.veh_info_lhmenu_item):
                print(f'[SDP Log Validator] > Login to SDP successful')
            driver.implicitly_wait(5)
            driver.find_element("xpath", TestSuitConfig.veh_info_lhmenu_item).click()
            print(f'[SDP Log Validator] > Clicked on <Vehicle Information> menu item ')
            time.sleep(2)
            if driver.find_element("xpath", TestSuitConfig.search_by_dropdown):
                print(f'[SDP Log Validator] > Vehicle Information page has loaded')
            else:
                print(f'[SDP Log Validator] > Vehicle Information page did not load')
            driver.find_element("xpath", TestSuitConfig.search_by_dropdown).click()
            print(f'[SDP Log Validator] > Clicked on Search By dropdown')
            time.sleep(2)
            driver.find_element("xpath", TestSuitConfig.search_by_tdac).click()
            print(f'[SDP Log Validator] > Selected search by TDC from the dropdown list')
            time.sleep(2)
            driver.find_element("xpath", TestSuitConfig.tdac_entry_box).click()
            time.sleep(3)
            driver.find_element("xpath", TestSuitConfig.tdac_entry_box).send_keys(TestSuitConfig.TDAC_num)
            print(f'[SDP Log Validator] > Entered TDAC')
            driver.find_element("xpath", TestSuitConfig.search_button).click()
            print(f'[SDP Log Validator] > Clicked on <Search> Button')
            time.sleep(2)
            driver.find_element("xpath", TestSuitConfig.tdac_num).click()
            print(f'[SDP Log Validator] > Clicked on TDAC Number')
            time.sleep(10)
            driver.find_element("xpath", TestSuitConfig.view_icon).click()
            print(f'[SDP Log Validator] > Clicked on View button')
            time.sleep(2)
            wait = WebDriverWait(driver, 100)
            # wait.until(EC.element_to_be_clickable((By.XPATH, loc.uplink)))
            driver.find_element("xpath", TestSuitConfig.uplink).click()
            print(f'[SDP Log Validator] > Selected <Up Link> menu item')
            time.sleep(10)
            # wait.until(EC.presence_of_element_located((By.XPATH, loc.table)))
            # Obtain the number of rows in body
            rows = driver.execute_script("return document.getElementsByTagName('tr').length")
            # Obtain the number of columns in table
            cols = driver.execute_script("return document.getElementsByTagName('th').length")
            # Print all rows and columns present in SDP Dynamic Data Table
            print(f'[SDP Log Validator] > Number of rows found:', rows)  # Dynamic
            print(f'[SDP Log Validator] > Number of columns found:', cols)  # Static
            for r in range(1, 10):
                file_name = driver.find_element("xpath",
                                                f'//*[@id="asset-card"]/div[2]/div/div/table/tbody/tr[{r}]/td').text
                file_name_dict = json.loads(file_name)
                # Auto export files shall have 39 character name "TASKDATA-81758911044-20211026220529.zip"
                if len(file_name_dict['filename']) == 39:
                    auto_export_files[file_name_dict['filename']] = file_name
                    if len(file_name_dict['timestamp']) == 24:
                        auto_timestamp[file_name_dict['timestamp']] = file_name
                # Manual export files shall have 27 character name "TASKDATA.20211026220529.ZIP"
                elif len(file_name_dict['filename']) == 27:
                    manual_export_files[file_name_dict['filename']] = file_name
                    if len(file_name_dict['timestamp']) == 24:
                        manual_timestamp[file_name_dict['timestamp']] = file_name
                else:
                    Helper.prRed(f'[SDP Log Validator] > No data found in SDP portal')
                    continue
            # Log first 10 Auto/Manual export files and their timestamps seen in the SDP for the given TDAC
            try:
                global timestamp
                Helper.prBlue(f'[SDP Log Validator] > Manual export files in SDP:')
                for key, value in list(manual_export_files.items())[:1]:
                    file = key
                    for key, value in list(manual_timestamp.items())[:1]:
                        time_stamp = key
                        date_time = time_stamp.split('T')
                        Date = date_time[0]
                        Time = date_time[1].strip('Z')
                        timestamp = str("DATE: " + Date + " <> " + "TIME: " + Time[:8])
                with open(data_logger, 'a') as f:
                    f.write('\n')
                    f.write('Manual: ')
                    f.write(file)
                    f.write('\t')
                    f.write(timestamp)
                print('[Manual] :', file, ':: Time: ', timestamp)
            except:
                Helper.prRed(f'[SDP Log Validator] > No recent manual export files found.')
            Helper.prBlue(f'[SDP Log Validator] > Auto export files in SDP:')
            for key, value in list(auto_export_files.items())[:10]:
                file = key
                for key, value in list(auto_timestamp.items())[:10]:
                    time_stamp = key
                    date_time = time_stamp.split('T')
                    Date = date_time[0]
                    Time = date_time[1].strip('Z')
                    timestamp = str("DATE: " + Date + " <> " + "TIME: " + Time[:8])
                print('[Auto] :', file, ':: Time: ', timestamp)
                with open(data_logger, 'a') as f:
                    f.write('\n')
                    f.write('Auto: ')
                    f.write(file)
                    f.write('\t')
                    f.write(timestamp)
            driver.close()
            result_status = True
            return True, result_status
        except Exception as skip:
            print('SKIPPED: Possible reasons ->\n', '[A] Login Credintials expired.Please check.\n', f'[B] {str(skip)}')
            result_status = False
            return result_status

    def run_sdp_monitor(self, TDAC_num: str = None):
        try:
            data_logger = os.path.abspath(DMConstants.EXPORT + f'/AGDNA/SDP_Export_monitor_log.txt')
            top_layer = "#################################################### SDP EXPORT MONITOR LOG ####################################################"
            with open(data_logger, 'a') as f:
                f.truncate(0)
                print(f'[SDP Log Validator] > Erasing previous SDP data-logs... ')
                time.sleep(2)
                print(f'[SDP Log Validator] > Starting SDP automation monitor... ')
                f.write(top_layer)
                f.write('\n')
                f.write('Data Logged for Display.active_display_uiautomator[TDAC] Number:')
                f.write('\t')
                f.write(TDAC_num)
                f.write('\n')
            self.SDP_Portal_autoexport_data_check(TDAC_num)
        except:
            pass
        # ---------------------------- Create Implement ----------------------------

    def click_on_implement(self):
        """
        Click on implement
        Returns:
            bool : Clicked or not
        """
        print(f'[{self.test_case_name}] > Clicking on Implement')
        status = self.common_functions.tap_using_ui_item(resource_id="com.cnh.android.cardmanager:id/card_title",
                                                         item_text="Implement")
        if status:
            if self.wait_to_appear(resource_id='com.cnh.pf.phoenixapp:id/tab_activity_back_btn',
                                   item_text='Menu'):
                print(f'[{self.test_case_name}] > Clicked on Implement')
                return True
            else:
                print(f'[{self.test_case_name}] > Failed to click on Implement')
        raise Exception('Failed to click Implement')

    def click_on_applicator(self):
        """
        Click on implement
        Returns:
            bool : Clicked or not
        """
        print(f'[{self.test_case_name}] > Clicking on Applicator')
        status = self.common_functions.tap_using_ui_item(resource_id="com.cnh.android.cardmanager:id/card_title",
                                                         item_text="Applicator")
        if status:
            if self.wait_to_appear(resource_id='com.cnh.pf.phoenixapp:id/tab_activity_back_btn',
                                   item_text='Menu'):
                print(f'[{self.test_case_name}] > Clicked on Applicator')
                return True
            else:
                print(f'[{self.test_case_name}] > Failed to click on Applicator')
        raise Exception('Failed to click Applicator')

    def create_implement_settings(self, settings_items: Dict):
        """
        Creating home screen items
        Args:
            items: Details of items ( Example )

        Returns:
            none
        Examples:
            T_1 = {"Implement Name":"Planting Implement test"}
        """

        #  #****Settings setup***
        self.common_functions.tap_adb(1200, 200)  # Click on Settings
        for title, value in settings_items.items():
            print(f'[{self.test_case_name}] > Selecting item : {title} with value : {value}')
            self.common_functions.tap_using_ui_item(resource_id="com.cnh.pf.phoenixapp:id/ivArrow")  # Drop down list
            status = self.common_functions.tap_using_ui_item(resource_id="com.cnh.pf.phoenixapp:id/picklistItem",
                                                             item_text=value)  # Select Seed for controller type

            if status:
                print(f'[{self.test_case_name}] > Selected [{title}] with [{value}]')  # If implement already exists
                pop_screen = self.wait_to_appear(resource_id='com.cnh.android.tractor:id/btFirst', item_text='Continue')
                if pop_screen:
                    self.common_functions.tap_using_ui_item(resource_id='com.cnh.android.tractor:id/btFirst',
                                                            item_text='Continue')
                    print(f'[{self.test_case_name}] > Pop-up found and handled with [Continue].')
                    time.sleep(0.5)
                else:
                    pass
                return True

            else:
                print(f'[{self.test_case_name}] > Creating a new {value} implement')
                Display.active_display_uiautomator(resourceId="com.cnh.pf.phoenixapp:id/picklistAddNewButton").click()
                time.sleep(0.5)
                pop_screen = self.wait_to_appear(resource_id='com.cnh.android.tractor:id/btFirst', item_text='Continue')
                if pop_screen:
                    self.common_functions.tap_using_ui_item(resource_id='com.cnh.android.tractor:id/btFirst',
                                                            item_text='Continue')
                    print(f'[{self.test_case_name}] > Pop-up found and handled with [Continue].')
                    time.sleep(0.5)
                else:
                    pass

                for title, value in settings_items.items():
                    resource_id = DMConstants.IMPLEMENT_SETTINGS_GFFT_RESOURCES_LIST.get(title, 'None')  # ID address

                    if title == "Implement Name":
                        Display.active_display_uiautomator(resourceId=resource_id).set_text(value)  # Fill out implement data
                        self.common_functions.tap_adb(1130, 700)  # Click Done
                        time.sleep(0.5)
                    else:
                        self.common_functions.tap_using_ui_item(resource_id=resource_id)  # Drop down list
                        scrollable_layout = Display.active_display_uiautomator(className="android.widget.RelativeLayout", index="0")
                        scrollable_layout.scroll.to(text=value)  # scroll down to the desired value location
                        status = self.common_functions.tap_using_ui_item(
                            resource_id="com.cnh.pf.phoenixapp:id/picklistItem",
                            item_text=value)  # Select Seed for controller type

                        if not status:
                            Display.active_display_uiautomator(resourceId="com.cnh.pf.phoenixapp:id/picklistAddNewButton").click()
                            time.sleep(0.5)
                            Display.active_display_uiautomator(resourceId="com.cnh.pf.phoenixapp:id/inputField").set_text(
                                value)  # Fill out implement data
                            self.common_functions.tap_adb(1130, 700)  # Click Done
                            self.common_functions.tap_using_ui_item(resource_id="com.cnh.pf.phoenixapp:id/btFirst",
                                                                    item_text="Apply")
                            time.sleep(0.5)
            self.common_functions.tap_using_ui_item(resource_id="com.cnh.pf.phoenixapp:id/btFirst",
                                                    item_text="Save")
            time.sleep(15)
            return False

    def create_applicator_settings(self, settings_items: Dict):
        """
        Creating home screen items
        Args:
            items: Details of items ( Example )

        Returns:
            none
        Examples:
            T_1 = {"Implement Name":"Planting Implement test"}
        """

        #  #****Settings setup***
        self.common_functions.tap_adb(1200, 200)  # Click on Settings
        for title, value in settings_items.items():
            print(f'[{self.test_case_name}] > Selecting item : {title} with value : {value}')
            self.common_functions.tap_using_ui_item(resource_id="com.cnh.pf.phoenixapp:id/ivArrow")  # Drop down list
            status = self.common_functions.tap_using_ui_item(resource_id="com.cnh.pf.phoenixapp:id/picklistItem",
                                                             item_text=value)  # Select Seed for controller type

            if status:
                print(f'[{self.test_case_name}] > Selected [{title}] with [{value}]')  # If implement already exists
                pop_screen = self.wait_to_appear(resource_id='com.cnh.android.tractor:id/btFirst', item_text='Continue')
                if pop_screen:
                    self.common_functions.tap_using_ui_item(resource_id='com.cnh.android.tractor:id/btFirst',
                                                            item_text='Continue')
                    print(f'[{self.test_case_name}] > Pop-up found and handled with [Continue].')
                    time.sleep(0.5)
                else:
                    pass
                return True

            else:
                print(f'[{self.test_case_name}] > Creating a new {value} applicator')
                Display.active_display_uiautomator(resourceId="com.cnh.pf.phoenixapp:id/picklistAddNewButton").click()
                time.sleep(0.5)
                pop_screen = self.wait_to_appear(resource_id='com.cnh.android.tractor:id/btFirst', item_text='Continue')
                if pop_screen:
                    self.common_functions.tap_using_ui_item(resource_id='com.cnh.android.tractor:id/btFirst',
                                                            item_text='Continue')
                    print(f'[{self.test_case_name}] > Pop-up found and handled with [Continue].')
                    time.sleep(0.5)
                else:
                    pass

                for title, value in settings_items.items():
                    resource_id = DMConstants.APPLICATOR_SETTINGS_GFFT_RESOURCES_LIST.get(title, 'None')  # ID address

                    if title == "Applicator Name":
                        Display.active_display_uiautomator(resourceId=resource_id).set_text(value)  # Fill out implement data
                        self.common_functions.tap_adb(1130, 700)  # Click Done
                        time.sleep(0.5)
                    else:
                        self.common_functions.tap_using_ui_item(resource_id=resource_id)  # Drop down list
                        scrollable_layout = Display.active_display_uiautomator(className="android.widget.RelativeLayout", index="0")
                        scrollable_layout.scroll.to(text=value)  # scroll down to the desired value location
                        status = self.common_functions.tap_using_ui_item(
                            resource_id="com.cnh.pf.phoenixapp:id/picklistItem",
                            item_text=value)  # Select Seed for controller type

                        if not status:
                            Display.active_display_uiautomator(resourceId="com.cnh.pf.phoenixapp:id/picklistAddNewButton").click()
                            time.sleep(0.5)
                            Display.active_display_uiautomator(resourceId="com.cnh.pf.phoenixapp:id/inputField").set_text(
                                value)  # Fill out implement data
                            self.common_functions.tap_adb(1130, 700)  # Click Done
                            self.common_functions.tap_using_ui_item(resource_id="com.cnh.pf.phoenixapp:id/btFirst",
                                                                    item_text="Apply")
                            time.sleep(0.5)
            self.common_functions.tap_using_ui_item(resource_id="com.cnh.pf.phoenixapp:id/btFirst",
                                                    item_text="Save")
            time.sleep(15)
            return False

    def create_implement_measurements(self, measurements_items: Dict):
        # def create_implement(self):
        """
        Creating home screen items
        Args:
            items: Details of items ( Example )

        Returns:
            none
        Examples:
            T_1 = {"Bar Distance":"300"}
        """
        # Display.active_display_uiautomator.swipe(660, 680, 660, 800)    # Swipe up
        # Display.active_display_uiautomator.swipe(660, 680, 660, 640)    # Swipe down
        Display.active_display_uiautomator.swipe(660, 680, 660, 500)  # Swipe down testing
        #  #****Measurements setup***
        self.common_functions.tap_adb(1200, 300)  # Click on Measurements
        for title, value in measurements_items.items():
            print(f'[{self.test_case_name}] > Selecting item : {title} with value : {value}')
            resource_id = DMConstants.IMPLEMENT_MEASUREMENTS_GFFT_RESOURCES_LIST.get(title, 'None')  # ID address
            self.common_functions.tap_using_ui_item(resource_id=resource_id)  # select field
            Display.active_display_uiautomator(resourceId=resource_id).set_text(value)  # Fill out implement data
            self.common_functions.tap_adb(1100, 600)  # Click Done
        time.sleep(15)

    def get_implements_list(self):
        """In Data Management tab, get Implement names in a list by reading Data Tree."""
        list_view = device(resourceId="com.cnh.pf.android.data.management:id/tree_view_list")
        # get Implements LinearLayout index number, assuming default value = 1(if "Crop and Product Library" is not present)
        imp_index_num = 1
        list_view_count = list_view.info['childCount']
        if list_view_count == 2:
            imp_index_num = 1
        elif list_view_count == 3:
            imp_index_num = 2
        exist = self.wait_to_appear(item_text="Implements")
        if exist:
            print("Expanding Implements in data tree")
            item_frame_layout = list_view.child(className="android.widget.LinearLayout",
                                                index=str(imp_index_num)).child(
                resourceId="com.cnh.pf.android.data.management:id/treeview_list_item_frame_layout")
            imp_expand_btn = item_frame_layout.child(
                resourceId="com.cnh.pf.android.data.management:id/treeview_list_item_toggle")
            imp_expand_btn.click()
            time.sleep(2)

            # get total count of Implements
            self.common_functions.tap_using_ui_item(item_text="Implements")
            time.sleep(2)
            imp_count = device(resourceId="com.cnh.pf.android.data.management:id/header_text").info['text']
            imp_count = int(imp_count.split()[0])
            print("Number of Implements found: " + str(imp_count))
            device(text="Implements").click()
            time.sleep(2)

            # get Implement names list
            imp_name_list = []
            while len(imp_name_list) < imp_count:
                counter = 0
                list_view_count = list_view.info['childCount']
                while counter < list_view_count:
                    list_view_item = list_view.child(className="android.widget.LinearLayout", index=str(counter))
                    imp_name = \
                        list_view_item.child(
                            resourceId="com.cnh.pf.android.data.management:id/tree_list_item_text").info[
                            'text']
                    if imp_name not in imp_name_list and imp_name not in ["Implements", "Grower/Farm/Field/Task",
                                                                          "Crop and Product Library"]:
                        imp_name_list.append(imp_name)
                        # print(imp_name)
                    counter += 1
                    if len(imp_name_list) == imp_count:
                        break
                    elif counter == 7:
                        os.system("adb shell input swipe 660 690 660 380")
            # Collapsing Implements
            imp_expand_btn.click()
            print("Implement names list: " + str(imp_name_list))
            return imp_name_list
        else:
            print("There is no Implements present in DM tab")

    def delete_selected_implement(self, implement_list):
        """Delete All the Implements except passed Implement list.
        :param implement_list: Specify the list of Implement names which shouldn't be deleted"""

        self.click_menu_tab('Data Management')
        list_view = device(resourceId="com.cnh.pf.android.data.management:id/tree_view_list")

        imp_index_num = 1
        list_view_count = list_view.info['childCount']
        if list_view_count == 2:
            imp_index_num = 1
        elif list_view_count == 3:
            imp_index_num = 2
        exist = self.wait_to_appear(item_text="Implements")
        if exist:
            all_imp_list = self.get_implements_list()
            # Select all items in list implements similar to original
            if len(all_imp_list) == len(implement_list):
                self.common_functions.tap_using_ui_item(resource_id="com.cnh.pf.android.data.management:id/tree_list_item_text",
                                                        item_text="Implements")
                time.sleep(1)
                self.common_functions.tap_using_ui_item(resource_id="com.cnh.pf.android.data.management:id/dm_delete_button")
                time.sleep(2)
                self.common_functions.tap_using_ui_item(resource_id="com.cnh.pf.android.data.management:id/btFirst", item_text="Delete")
            else:
                # Select specified implements
                visible = self.wait_to_appear(item_text=implement_list[1])
                if not visible:
                    print(f"[{self.test_case_name}] > Expanding Implements in data tree")
                    item_frame_layout = list_view.child(className="android.widget.LinearLayout",
                                                        index=str(imp_index_num)).child(
                        resourceId="com.cnh.pf.android.data.management:id/treeview_list_item_frame_layout")
                    imp_expand_btn = item_frame_layout.child(
                        resourceId="com.cnh.pf.android.data.management:id/treeview_list_item_toggle")
                    imp_expand_btn.click()
                    time.sleep(2)
                else:
                    pass
                for i in range(0, len(implement_list)):
                    # Check whether 'implement_list' names are present in Implement data tree
                    if implement_list[i] in all_imp_list:
                        print(f"[{self.test_case_name}] > Selecting: " + implement_list[i])
                        device(className="android.widget.ListView",
                               resourceId="com.cnh.pf.android.data.management:id/tree_view_list"). \
                            child_by_text(implement_list[i], allow_scroll_search=True,
                                          resourceId="com.cnh.pf.android.data.management:id/tree_list_item_text",
                                          className="android.widget.TextView").click()
                self.common_functions.tap_using_ui_item(
                    resource_id="com.cnh.pf.android.data.management:id/dm_delete_button")
                time.sleep(2)
                self.common_functions.tap_using_ui_item(resource_id="com.cnh.pf.android.data.management:id/btFirst",
                                                        item_text="Delete")
                time.sleep(2)

            print(f'[{self.test_case_name}] > Waiting to detect change implement warning..!')
            time.sleep(3)
            change_implement_status = self.wait_to_appear(resource_id="com.cnh.android.tractor:id/btFirst",
                                                          item_text="Continue", timeout=10)
            if change_implement_status:
                self.common_functions.tap_using_ui_item(resource_id="com.cnh.android.tractor:id/btFirst",
                                                        item_text="Continue")
            else:
                pass
            self.ack_deleted_pop_up()
            self.handle_pop_ups()
        else:
            print(f"[{self.test_case_name}] > FAILED: Implements data tree item is not available")

    def check_implement_deleted(self):
        """Check if the Implement option is deleted in DM tab. If its deleted return True, else return False."""

        visible = self.wait_to_appear(item_text="Implements")
        if visible:
            print(f"[{self.test_case_name}] > Implement tab is still present in DM tab.")
            return False
        else:
            print(f"[{self.test_case_name}] > Implement tab is deleted.")
            return True

    def create_applicator_measurements(self, measurements_items: Dict):
        """
        Creating applicator measurement items
        """
        measurements_items = [i for i in measurements_items.values()]
        Center_Offset = measurements_items[0]
        Boom_Distance = measurements_items[1]
        Applicator_Width = measurements_items[2]
        Display.active_display_uiautomator.swipe(660, 680, 660, 500)  # Swipe down testing
        #  #****Measurements setup***
        self.common_functions.tap_adb(1200, 300)  # Click on Measurements
        print(f'[{self.test_case_name}] > Selecting item : Center Offset with set value: {Center_Offset} ')
        self.wait_to_appear(resource_id="com.cnh.pf.phoenixapp:id/center_offset_header_tv", item_text="Center Offset")
        self.common_functions.tap_adb(410, 250)
        self.wait_to_appear(resource_id="com.cnh.pf.phoenixapp:id/center_offset_position_header_tv", item_text="Offset Value")
        self.common_functions.tap_adb(570, 375)
        Helper.input_number_or_text(Center_Offset)
        self.common_functions.tap_using_ui_item(item_text="Save")
        self.wait_to_appear(item_text="Applicator Width")
        print(f'[{self.test_case_name}] > Selecting item : Applicator Width with set value: {Applicator_Width}')
        self.common_functions.tap_adb(640, 555)
        Helper.input_number_or_text(Applicator_Width)
        print(f'[{self.test_case_name}] > Applicator measurement setting is done.')

    def create_implement_appControl(self, appControl_items, controller_name=None):
        """
        Creating home screen items
        Args:
            items: Details of items ( Example )

        Returns:
            none
        Examples:
            T_1 = {"Seed"}
        """

        #  #****Settings setup***
        #  #****Application Control setup***
        self.common_functions.tap_adb(1200, 400)  # Click on Application Control
        if isinstance(appControl_items, str):
            appControl_items = [appControl_items]
        if controller_name == None:
            for i, controller in enumerate(appControl_items):
                self.common_functions.tap_using_ui_item(resource_id="com.cnh.pf.phoenixapp:id/btn_add_controller",
                                                        item_text="Add Controller")  # Add controller
                self.common_functions.tap_using_ui_item(
                    resource_id="com.cnh.pf.phoenixapp:id/ivArrow")  # Drop down list
                Display.active_display_uiautomator(resourceId="com.cnh.pf.phoenixapp:id/picklistItem", text=controller).click()

                # self.common_functions.tap_using_ui_item(resource_id="com.cnh.pf.phoenixapp:id/picklistItem",
                #                                         item_text=controller)  # Select Seed for controller type

                self.common_functions.tap_using_ui_item(resource_id="com.cnh.pf.phoenixapp:id/btFirst",
                                                        item_text="Save")  # Save
        elif not controller_name == None:
            for i, controller in enumerate(appControl_items):
                self.common_functions.tap_using_ui_item(resource_id="com.cnh.pf.phoenixapp:id/btn_add_controller",
                                                        item_text="Add Controller")  # Add controller
                self.common_functions.tap_using_ui_item(
                    resource_id="com.cnh.pf.phoenixapp:id/ivArrow")  # Drop down list
                Display.active_display_uiautomator(resourceId="com.cnh.pf.phoenixapp:id/picklistItem", text=controller).click()

                # self.common_functions.tap_using_ui_item(resource_id="com.cnh.pf.phoenixapp:id/picklistItem",
                #                                         item_text=controller)  # Select Seed for controller type
                Display.active_display_uiautomator(resourceId="com.cnh.pf.phoenixapp:id/control_name_text").child(
                    className="android.widget.EditText", index=1).click()
                Helper.input_number_or_text(controller_name[i])

                self.common_functions.tap_using_ui_item(resource_id="com.cnh.pf.phoenixapp:id/btFirst",
                                                        item_text="Save")  # Save
        else:
            print("Something went wrong please check !!!")
        time.sleep(15)

    def kpi_excel_log_structure(self):

        import csv

        temp_csv = os.path.abspath(DMConstants.IMPORT + f'/BM/temp.csv')
        standard_header = ['Unique ID', 'tester', 'Test Case name', 'Test Date', 'Test Description', 'Discovery Time',
                           'Import Time', 'Export Time', 'Window Launch Time', 'Save Time', 'Launch Time']
        with open(temp_csv, 'w', encoding='UTF8') as f:
            writer = csv.writer(f)
            writer.writerow(standard_header)

    def BM_excel_gen_report(self, is_kpi_timer=False, is_timer_required=False, is_export_time=False,
                            is_P_window_launch=False, is_logging: bool = False, is_capture_timer: bool = False,
                            is_M_window_launch=False, is_tree_appear_time=False, is_prescription_import=False,
                            is_multiswath_import=False, is_boundary_import=False, Unique_id: str = None,
                            T_info: str = None, is_delete_timer=False):

        """
            Selection of kpi testcase
            Args:
                is_logging:
                is_kpi_timer:
                is_delete_timer:
                is_timer_required:
                is_export_time:
                is_P_window_launch:
                is_M_window_launch:
                is_tree_appear_time:
                is_prescription_import:
                is_multiswath_import:
                is_boundary_import:
                Unique_id: Creates a unique ID for the test cases to identify data from list.
                :param
        """
        # ------------ Module imports -------------- #
        import csv
        from DMAutomatedTest.DMTestCases.TestCases_DMBM import Test_info
        # ------------ Structures -------------- #
        tested_on = datetime.now().strftime('%d-%m-%y %H-%M-%S')
        tester = 'Dev_CNH_Offshore_team'
        cyan = "\033[96m {}\033[00m"
        red = "\033[91m{}\033[00m"
        temp_csv = os.path.abspath(DMConstants.IMPORT + f'/BM/temp.csv')
        name = self.test_case_name
        # -------------functions ------------- #
        print(f'[BM Testing Report] > Preparing log file ...')
        try:
            if is_logging:
                if is_capture_timer:
                    print(f'[BM Testing Report] > Fetching data...')
                    data = [Unique_id, tester, name, tested_on, T_info, discovery_time, actual_import_time_taken,
                            Export_Time, '', '', '', delete_time]
                    with open(temp_csv, 'a', encoding='UTF8') as f:
                        writer = csv.writer(f)
                        writer.writerow(data)
                    print(cyan.format(f'[BM Testing Report] > Time(s) updated in excel report'))
                    return True
                if is_tree_appear_time:
                    print(f'[BM Testing Report] > Fetching data...')
                    if Unique_id == 'L001':  # DataCard Launch Time without Key-cycle
                        data = [Unique_id, tester, name, tested_on, T_info, '', '',
                                '', '', '', data_launch_time, '', datacard_view]
                        with open(temp_csv, 'a', encoding='UTF8') as f:
                            writer = csv.writer(f)
                            writer.writerow(data)
                    else:  # DataCard Launch Time with Key-cycle
                        data = [Unique_id, tester, name, tested_on, T_info, '', '',
                                '', '', '', data_launch_time, '', datacard_view]
                        with open(temp_csv, 'a', encoding='UTF8') as f:
                            writer = csv.writer(f)
                            writer.writerow(data)
                    print(cyan.format(f'[BM Testing Report] > DataCard Launch Time updated in excel report'))
                    return True
                if is_P_window_launch:
                    from DMAutomatedTest.DMHelper.DataModel.Product.DisplayModel import P_window_launch_time, \
                        M_save_timer, M_window_launch_time, P_save_timer

                    p_launch = P_window_launch_time
                    p_save = P_save_timer
                    print(f'[BM Testing Report] > Fetching data...')
                    data = [Unique_id, tester, name, tested_on, T_info, '', '', '',
                            p_launch, p_save, '']
                    with open(temp_csv, 'a', encoding='UTF8') as f:
                        writer = csv.writer(f)
                        writer.writerow(data)
                    print(cyan.format(f'[BM Testing Report] > Product Creation/Save Time updated in excel report'))
                    return True
                if is_M_window_launch:
                    from DMAutomatedTest.DMHelper.DataModel.Product.DisplayModel import P_window_launch_time, \
                        M_save_timer, M_window_launch_time, P_save_timer

                    m_launch = M_window_launch_time
                    m_save = M_save_timer
                    print(f'[BM Testing Report] > Fetching data...')
                    data = [Unique_id, tester, name, tested_on, T_info, '', '', '',
                            m_launch, m_save, '']
                    with open(temp_csv, 'a', encoding='UTF8') as f:
                        writer = csv.writer(f)
                        writer.writerow(data)
                    print(cyan.format(f'[BM Testing Report] > Product Mix/Save Time updated in excel report'))
                    return True
                if is_prescription_import:
                    print(f'[BM Testing Report] > Fetching data...')
                    data = [Unique_id, tester, name, tested_on, T_info, '', Prescription_import_time]

                    with open(temp_csv, 'a', encoding='UTF8') as f:
                        writer = csv.writer(f)
                        writer.writerow(data)
                    print(cyan.format(f'[BM Testing Report] > Prescription import time updated in excel report'))
                    return True
                if is_multiswath_import:
                    print(f'[BM Testing Report] > Fetching data...')
                    data = [Unique_id, tester, name, tested_on, T_info, '', Multiswath_import_timer]

                    with open(temp_csv, 'a', encoding='UTF8') as f:
                        writer = csv.writer(f)
                        writer.writerow(data)
                    print(cyan.format(f'[BM Testing Report] > Multiswath import time updated in excel report'))
                    return True
                if is_boundary_import:
                    print(f'[BM Testing Report] > Fetching data...')
                    data = [Unique_id, tester, name, tested_on, T_info, '', Boundary_import_timer]

                    with open(temp_csv, 'a', encoding='UTF8') as f:
                        writer = csv.writer(f)
                        writer.writerow(data)
                    print(
                        cyan.format(f'[BM Testing Report] > Boundary import time updated in excel report'))
                    return True
                return True
            else:
                print(f'[BM Testing Report] > No data to write in excel report...')
                pass

        except Exception as E:
            print(red.format(f'[BM Testing Report] > Failed to write data. [Reason] : ') + str(E))

        finally:
            # ---------- Processing ---------- #
            b = "\033[94m{}\033[00m"
            print(b.format('******[WAIT]******'))
            time.sleep(0.5)

    def breathe_time(self, is_cycle: bool = False):
        from DMAutomatedTest.DMTestSuite import Key_Cycle
        if is_cycle:
            print('[Power Cycle] : Commencing power sequence. Key_Cycling.......')
            Key_Cycle.reboot()
            print('[Display Down] : Wait for 2 mins to load display fully..')
            time.sleep(120)
            print('[Display Up] : Display loaded.')
            time.sleep(2)
            print('[POP-UP] : Handling pop-ups')
            self.handle_pop_ups()
            time.sleep(0.5)
            Key_Cycle.system_volume_down()

    # ------------------------- Vehicle configuration -------------------------------------------------------

    def vehicle_configuration(self, vehicle_name: str = None):
        """
                Click on tractor menu -> Set gear to Park -> Change vehicle config -> Set gear to forward
                Returns:
                    vehicle_name: Quadtrac 540 CVT Case IH Precisi
                    Screenshot: Captures the modified config screen and saves in local
        """
        try:
            self.click_settings()
            print(f'[{self.test_case_name}] > Clicking on Tractor Menu')
            status = self.common_functions.tap_using_ui_item(resource_id="com.cnh.android.cardmanager:id/card_title",
                                                             item_text="Tractor")
            if status:
                if self.wait_to_appear(resource_id='com.cnh.android.tractor:id/namelabel',
                                       item_text='Vehicle Name'):
                    print(f'[{self.test_case_name}] > Clicked on Tractor')
                else:
                    print(f'[{self.test_case_name}] > Failed to click on Tractor menu')
            time.sleep(2)
            com_connect = COMIsobusInterface()
            print(f'[{self.test_case_name}] > Comm Interface: OK')
            com_connect.set_gear(3)
            print(f'[{self.test_case_name}] > Vehicle gear set to Park Position')
            self.common_functions.tap_using_ui_item(resource_id="com.cnh.android.tractor:id/ivArrow")
            check = self.wait_to_appear(resource_id="com.cnh.android.tractor:id/picklistItem",
                                        item_text=vehicle_name)
            if check:
                self.common_functions.tap_using_ui_item(resource_id="com.cnh.android.tractor:id/picklistItem",
                                                        item_text=vehicle_name)
                print(f'[{self.test_case_name}] > Vehicle Config found in Picklist')
            else:
                self.common_functions.tap_using_ui_item(resource_id="com.cnh.android.tractor:id/picklistAddNewButton",
                                                        item_text='Add New')
                self.wait_to_appear(resource_id="com.cnh.android.tractor:id/flContent")
                text_feed = Display.active_display_uiautomator(resourceId="com.cnh.android.tractor:id/flContent").child(
                    className='android.widget.EditText')
                text_feed.click()
                text_feed.clear_text()
                text_feed.set_text(vehicle_name)
                self.common_functions.tap_using_ui_item(resource_id="com.cnh.android.tractor:id/btFirst",
                                                        item_text='Apply')
                print(f'[{self.test_case_name}] > Vehicle Config is created in Picklist')
            print(f'[{self.test_case_name}] > Vehicle Config selected:', vehicle_name)
            self.click_screenshot_display()
            time.sleep(1)
            print(
                f'[{self.test_case_name}] > Vehicle config screenshot saved in : [DMAutomatedTest\DMTestData\TempScreenshots] folder')
            com_connect.set_gear(1)
            print(f'[{self.test_case_name}] > Vehicle gear set to Forward Position')
            self.common_functions.tap_using_ui_item(resource_id="com.cnh.android.tractor:id/tab_activity_close")
            print(f'[{self.test_case_name}] > Vehicle configured status: PASS')
        except:
            raise Exception('Failed to configure Tractor')

    def verify_vehicle_config(self, vehicle_name: str = None, set_vehicle=False):
        """
        Click on tractor menu -> Set gear to Park -> Verify vehicle config -> Set gear to forward
        Returns:
            vehicle_name: Quadtrac 540 CVT Case IH Precisi
            Screenshot: Captures the modified config screen and saves in local
        """
        self.click_settings()
        print(f'[{self.test_case_name}] > Clicking on Tractor Menu')
        status = self.common_functions.tap_using_ui_item(resource_id="com.cnh.android.cardmanager:id/card_title",
                                                         item_text="Tractor")
        if status:
            if self.wait_to_appear(resource_id='com.cnh.android.tractor:id/namelabel',
                                   item_text='Vehicle Name'):
                print(f'[{self.test_case_name}] > Clicked on Tractor')
            else:
                print(f'[{self.test_case_name}] > Failed to click on Tractor menu')
        print(f'[{self.test_case_name}] > Comm Interface: OK')
        time.sleep(2)
        com_connect = COMIsobusInterface()
        com_connect.set_gear(3)
        print(f'[{self.test_case_name}] > Vehicle gear set to Park Position')
        self.common_functions.tap_using_ui_item(resource_id="com.cnh.android.tractor:id/ivArrow")
        check = self.wait_to_appear(resource_id="com.cnh.android.tractor:id/picklistItem",
                                    item_text=vehicle_name)
        if check:
            print(f'[{self.test_case_name}] > Vehicle Config [{vehicle_name}] found in Picklist')
            if set_vehicle:
                self.common_functions.tap_using_ui_item(resource_id="com.cnh.android.tractor:id/picklistItem",
                                                        item_text=vehicle_name)
                print(f'[{self.test_case_name}] > Vehicle set to [{vehicle_name}]')
            else:
                pass
            com_connect.set_gear(1)
            print(f'[{self.test_case_name}] > Vehicle gear set to Forward Position')
            self.click_screenshot_display()
            self.common_functions.tap_using_ui_item(resource_id="com.cnh.android.tractor:id/tab_activity_close")
            print(f'[{self.test_case_name}] > Vehicle configuration validity statue: ', True)
            self.click_screenshot_display()
            com_connect.set_gear(1)
            self.common_functions.tap_using_ui_item(resource_id="com.cnh.android.tractor:id/tab_activity_close")
            return True
        else:
            print(f'[{self.test_case_name}] > Vehicle configuration validity status: ', False)
            self.click_screenshot_display()
            com_connect.set_gear(1)
            self.common_functions.tap_using_ui_item(resource_id="com.cnh.android.tractor:id/tab_activity_close")
        raise Exception('Failed to verify Tractor configuration')

    def take_screenshot_and_save_in_gallery(self):
        """
        Screenshot: Captures the modified config screen and saves in Display.active_display_uiautomator gallery
        """
        screen_capture = f'adb shell input touchscreen swipe 740 30 740 30 8000'
        print(f'[{self.test_case_name}] > Taking screenshot')
        os.system(screen_capture)
        time.sleep(2)
        print(f'[{self.test_case_name}] > Clicking on view screenshot..')
        status = self.common_functions.tap_using_ui_item(resource_id="com.cnh.android.systemsettings:id/btFirst",
                                                         item_text="View Screenshot")
        time.sleep(2)
        if status:
            if self.wait_to_appear(resource_id="com.cnh.android.systemsettings:id/btFirst",
                                   item_text='View Screenshot'):
                print(f'[{self.test_case_name}] > Screenshot saved in gallery.')
        self.common_functions.tap_using_ui_item(resource_id="com.cnh.android.systemsettings:id/id_button_close")
        print(f'[{self.test_case_name}] > Clicking on close gallery...')
        time.sleep(2)

    def check_system_brightness(self, set_level: int = None):
        """
        Screen Brightness: to check the display screen brightness.
        :return:
        """
        import subprocess as sp
        brightness_cmd = f'adb shell settings get system screen_brightness'
        print(f'[{self.test_case_name}] > Requesting system brightness level...')
        os.system(brightness_cmd)
        output = sp.getoutput(brightness_cmd)
        current_level = int(output)
        print(f'[{self.test_case_name}] > Current system brightness level:', current_level)
        set_brightness = set_level
        if current_level > set_brightness:
            print(f'[{self.test_case_name}] > Brightness is higher than mid level...')
        else:
            print(f'[{self.test_case_name}] > Brightness is lower than mid level...')

    def check_system_volume(self, set_level: int = None):
        """
        System Volume: to check the display volume level.
        :return:
        """
        import subprocess as sp
        volume_cmd = f'adb shell settings get system volume_music'
        print(f'[{self.test_case_name}] > Requesting system volume level...')
        os.system(volume_cmd)
        output = sp.getoutput(volume_cmd)
        current_level = int(output)
        print(f'[{self.test_case_name}] > Current system volume level:', current_level)
        set_vol = set_level
        if current_level > set_vol:
            print(f'[{self.test_case_name}] > Volume is higher than mid level...')
        else:
            print(f'[{self.test_case_name}] > Volume is lower than mid level...')

    ########################################################## SANITY NEW FUNCTIONS ########################################

    def check_implement_settings(self, settings_items: Dict):
        """

        Args:
            items: Details of items ( Example )

        Returns:
            none
        Examples:
            T_1 = {"Implement Name":"Anything"}
        """
        self.common_functions.tap_adb(1200, 200)  # Click on  Implement Settings
        check = self.wait_to_appear(resource_id='com.cnh.pf.phoenixapp:id/ivArrow')

        if check:
            print(
                f'[{self.test_case_name}] > Selecting item : [Implement Name] with value : {settings_items["Implement Name"]}')
            self.common_functions.tap_using_ui_item(resource_id="com.cnh.pf.phoenixapp:id/ivArrow")  # Drop down list
            status = self.common_functions.tap_using_ui_item(resource_id="com.cnh.pf.phoenixapp:id/picklistItem",
                                                             item_text=settings_items[
                                                                 "Implement Name"])  # Select Seed for controller type
            if status:
                print(
                    f'[{self.test_case_name}] > Found [Implement Name] with [{settings_items["Implement Name"]}]')  # If implement already exists
                time.sleep(3)
            pop_screen = self.wait_to_appear(resource_id='com.cnh.android.tractor:id/btFirst', item_text='Continue')
            if pop_screen:
                self.common_functions.tap_using_ui_item(resource_id='com.cnh.android.tractor:id/btFirst',
                                                        item_text='Continue')
                print(f'[{self.test_case_name}] > Pop-up found and handled with [Continue].')
                time.sleep(0.5)
            else:
                pass

            print(f'[{self.test_case_name}] > Checking preselect items.')
            operator = self.wait_to_appear(item_text=settings_items["Implement Operation"])
            if operator:
                print(
                    f'[{self.test_case_name}] > Implement Operation : {settings_items["Implement Operation"]} [FOUND]')
            else:
                raise Exception("Required Implement Operation not found in list")

            type = self.wait_to_appear(item_text=settings_items["Implement Type"])
            if type:
                print(
                    f'[{self.test_case_name}] > Implement Type : {settings_items["Implement Type"]} [FOUND]')
            else:
                raise Exception("Required Implement Type not found in list")

            make = self.wait_to_appear(item_text=settings_items["Implement Make"])
            if make:
                print(
                    f'[{self.test_case_name}] > Implement Make : {settings_items["Implement Make"]} [FOUND]')
            else:
                raise Exception("Required Implement Make not found in list")

            model = self.wait_to_appear(item_text=settings_items["Implement Model"])
            if model:
                print(
                    f'[{self.test_case_name}] > Implement Model : {settings_items["Implement Model"]} [FOUND]')
            else:
                raise Exception("Required Implement Model not found in list")

        else:
            raise Exception("Required Implement Name not found in list")

    def check_implement_appControl(self, appControl_items, value_items, tab):

        """
        Checking home screen items
        Args:
            items: Details of items ( Example )

        Returns:
            none
        Examples:
            T_1 = {"Seed"}
        """

        self.common_functions.tap_adb(1200, 400)  # Click on Application Control
        confirm = self.wait_to_appear(resource_id='com.cnh.pf.phoenixapp:id/btn_add_controller')
        if confirm:
            print(f'[{self.test_case_name}] > Verifying AppControl settings.')
            for index, (item, item_A) in enumerate(zip(value_items, appControl_items)):

                self.common_functions.tap_using_ui_item(item_text=item_A)
                print(f'[{self.test_case_name}] > Clicking on Radio Button {item_A}')
                VT = self.wait_to_appear(resource_id=tab[1], item_text=tab[2])
                if VT:
                    print(f'[{self.test_case_name}] > {tab[0]} with status {tab[2]} found.')
                    self.common_functions.tap_using_ui_item(resource_id=tab[1], item_text=tab[2])
                    print(f'[{self.test_case_name}] > Selected {tab[0]} tab.')
                    for i in range(0, 3):
                        os.system('adb shell input touchscreen swipe 900 570 1230 470')
                        print(f'[{self.test_case_name}] > Scrolling screen to find Info.')
                else:
                    raise Exception(f'{tab[0]} tab not found.')

                one = self.wait_to_appear(item_text=item[1])
                if one:
                    print(f'[{self.test_case_name}] > ELEMENT : {item[1]} [FOUND].')
                else:
                    print(f'[{self.test_case_name}] > {item[1]} not found.')

                two = self.wait_to_appear(item_text=item[2])
                if two:
                    print(f'[{self.test_case_name}] > ELEMENT : {item[2]} [FOUND].')
                else:
                    print(f'[{self.test_case_name}] > {item[2]} not found.')

                three = self.wait_to_appear(item_text=item[3])
                if three:
                    print(f'[{self.test_case_name}] > ELEMENT : {item[3]} [FOUND].')
                else:
                    print(f'[{self.test_case_name}] > {item[3]} not found.')

                four = self.wait_to_appear(item_text=item[4])
                if four:
                    print(f'[{self.test_case_name}] > ELEMENT : {item[4]} [FOUND].')
                else:
                    print(f'[{self.test_case_name}] > {item[4]} not found.')

                five = self.wait_to_appear(item_text=item[5])
                if five:
                    print(f'[{self.test_case_name}] > ELEMENT : {item[5]} [FOUND].')
                else:
                    print(f'[{self.test_case_name}] > {item[5]} not found.')

                for i in range(0, 3):
                    os.system('adb shell input touchscreen swipe 900 470 900 570')
                    print(f'[{self.test_case_name}] > Scrolling screen back to initial position.')
                time.sleep(2)

            print(f'[{self.test_case_name}] > AppControl Tab items verified..')
        else:
            raise Exception("AppControl Card is not responding.")

    def check_implement_measurements(self, measurements_items: Dict, settings_data: bool = False,
                                     settings_value: str = None):
        # def create_implement(self):
        """
        Checking home screen items
        Args:
            items: Details of items ( Example )

        Returns:
            none
        Examples:
            T_1 = {"Bar Distance":"200"}
        """
        #  #****Measurements setup***
        self.common_functions.tap_adb(1200, 300)  # Click on Measurements
        wait = self.wait_to_appear(item_text='Bar Distance')
        if wait:
            for title, value in measurements_items.items():
                print(f'[{self.test_case_name}] > Verifying item : {title} with value : {value}')
                confirm = self.wait_to_appear(item_text=value)
                if confirm:
                    print(f'[{self.test_case_name}] > FOUND : {title} with value : {value}')
                else:
                    print(f'[{self.test_case_name}] > Attempting scroll-down.')
                    os.system('adb shell input touchscreen swipe 900 570 1230 400')
                    if value:
                        print(f'[{self.test_case_name}] > FOUND : {title} with value : {value}')
                    else:
                        print(f'[{self.test_case_name}] > NOT FOUND : {title} with value : {value}')
                        raise Exception
                time.sleep(0.5)
            print(f'[{self.test_case_name}] > Measurement Tab verified.')
        else:
            raise Exception("Failed to open Implement | Measurements.")
        if settings_data:
            print(f'[{self.test_case_name}] > Verifying additional settings menu')
            for i in range(0, 2):
                os.system('adb shell input touchscreen swipe 900 470 900 570')
            find = self.wait_to_appear(resource_id='com.cnh.pf.phoenixapp:id/advanced_hitch_settings_ib')
            if find:
                self.common_functions.tap_using_ui_item(
                    resource_id='com.cnh.pf.phoenixapp:id/advanced_hitch_settings_ib')
                self.wait_to_appear(item_text='Advanced Hitch Settings')
                option = self.wait_to_appear(
                    resource_id='com.cnh.pf.phoenixapp:id/implement_hitch_pivot_offset_input_header_text',
                    item_text='Implement Hitch Pivot Offset')
                if option:
                    value_available = self.wait_to_appear(item_text=settings_value)
                    if value_available:
                        print(
                            f'[{self.test_case_name}] > FOUND : Implement Hitch Pivot Offset with value {settings_value}')
                        self.common_functions.tap_using_ui_item(resource_id='com.cnh.pf.phoenixapp:id/btFirst',
                                                                item_text='Save')
                        print(f'[{self.test_case_name}] > SAVED : Pop-Up closed with option [Save]')
                        time.sleep(1)
                    else:
                        print(
                            f'[{self.test_case_name}] > NOT FOUND : Implement Hitch Pivot Offset with value : {settings_value}')
                        raise Exception
                else:
                    print(f'[{self.test_case_name}] > Settings tab is different than expected.')
                    raise Exception
            else:
                print(f'[{self.test_case_name}] > Settings icon is either not present or unresponsive.')
                raise Exception
        else:
            print(f'[{self.test_case_name}] > Additional settings tab verification status : FALSE.')
            pass

    def check_blank_implement_appControl(self):

        """
        Checking home screen items
        Args:
            items: Details of items ( Example )

        Returns:
            none
        Examples:
            T_1 = {"Seed"}
        """
        self.common_functions.tap_adb(1200, 400)  # Click on Application Control
        confirm = self.wait_to_appear(resource_id='com.cnh.pf.phoenixapp:id/btn_add_controller')
        if confirm:
            print(f'[{self.test_case_name}] > Verifying AppControl settings.')
            look = self.wait_to_appear(resource_id='com.cnh.pf.phoenixapp:id/controller_body_edit')
            if look:
                print(f'[{self.test_case_name}] > AppControl settings is not empty.')
                raise Exception
            else:
                print(f'[{self.test_case_name}] > AppControl settings is empty.')
        else:
            print(f'[{self.test_case_name}] > Add Controller in AppControl settings not found.')
            raise Exception

    # ------------------------------------------ CREATE MAX COPY ------------------------------------------ #

    def create_max_swath_copies(self, max_limit: int = 0):
        """
            Creating swath copies for stress test: max = 999
        """
        from itertools import repeat
        global new_data
        start_time = time.time()
        TSK = os.path.abspath(DMConstants.IMPORT + f'/STRESS/test_TC_DM_Stress_006/TASKDATA.XML')
        n = 2
        try:
            # Start of JSON file
            start = f"""<?xml version="1.0" encoding="UTF-8"?>
            <ISO11783_TaskData VersionMajor="4" VersionMinor="2" ManagementSoftwareManufacturer="CNH Industrial N.V." ManagementSoftwareVersion="03.30.38.0" TaskControllerManufacturer="CNH Industrial N.V." TaskControllerVersion="2021.3.2" DataTransferOrigin="2" P094_XML_VERSION="1" P094_ADDITIONAL="2021.03.02 41.4.1 03.30.38.0">
            	<CTR A="CTR-1" B="-----"/>
            	<CTR A="CTR-2" B="*Grower1"/>
            	<FRM A="FRM-1" B="-----" I="CTR-1"/>
            	<FRM A="FRM-2" B="Farm1" I="CTR-2"/>
            	<PFD A="PFD-1" C="-----" D="0" E="CTR-1" F="FRM-1">
            		<GGP A="GGP-1" B="StraightSwath" P094_GuidanceGroupType="0" P094_MapTransformationType="0">
            			<GPN A="GPN-1" B="StraightSwath" C="1" E="1" F="1">
            				<LSG A="5">
            					<PNT A="6" C="41.8497573460" D="-93.8239066780"/>
            					<PNT A="7" C="41.8497421650" D="-93.8220301660"/>
            				</LSG>
            			</GPN>
            		</GGP>"""
            with open(TSK, 'w+') as fp:
                fp.write(start)
                fp.write('\n')
            # Repeated Data
            for unused in repeat(None, (max_limit - 1)):
                json_var = f"""        <GGP A="GGP-{n}" B="StraightSwath ({n})" P094_GuidanceGroupType="0" P094_MapTransformationType="0">
                        <GPN A="GPN-{n}" B="StraightSwath ({n})" C="1" E="1" F="1">
                            <LSG A="5">
                                <PNT A="6" C="41.8497573460" D="-93.8239066780"/>
                                <PNT A="7" C="41.8497421650" D="-93.8220301660"/>
                            </LSG>
                        </GPN>
                    </GGP>"""
                new_data = json_var
                n = n + 1
                with open(TSK, 'a') as fp:
                    fp.write(new_data)
                    fp.write('\n')
            # End of Json File
            end = f"""    </PFD>
            	<PFD A="PFD-2" C="Field1" D="298983" E="CTR-2" F="FRM-2">
            		<GGP A="GGP-{n}" B="StraightSwath" P094_GuidanceGroupType="0" P094_MapTransformationType="0">
            			<GPN A="GPN-{n}" B="StraightSwath" C="1" E="1" F="1">
            				<LSG A="5">
            					<PNT A="6" C="41.8497573460" D="-93.8239066780"/>
            					<PNT A="7" C="41.8497421650" D="-93.8220301660"/>
            				</LSG>
            			</GPN>
            		</GGP>
            	</PFD>
            </ISO11783_TaskData>"""
            with open(TSK, 'a') as fp:
                fp.write(end)
            end_time = time.time()
            print(f'[{self.test_case_name}] >',
                  "\033[94m{}\033[00m".format(f'Completed File creation in {end_time - start_time} sec(s): '), True)
        except:
            raise Exception

    # ------------------------------------------- SIMULATOR CONTROLLER ------------------------------------- #

    def launch_simulator(self, path, app_title):
        try:
            self.application = Application(backend="uia").start(path)
            self.application_header = self.application[app_title]
            self.application_header.set_focus()
            print(f'[SIM_CONTROLLER] > Simulator [{self.application_header}] launched')
        except Exception as err:
            print(f'[SIM_CONTROLLER] > Exception occurred : {err}')

    def turn_simulator_ON(self, power_button):
        Green = "\033[92m{}\033[00m"
        try:
            self.application_header.window(best_match=power_button, control_type="Button").click()
            print(f'[SIM_CONTROLLER] > Simulator power is turned ', Green.format('ON'))
        except Exception as err:
            print(f'[SIM_CONTROLLER] > Exception occurred : {err}')

    def turn_simulator_OFF(self, app_title):
        Red = "\033[91m{}\033[00m"
        try:
            self.application_header.window(best_match="Close", control_type="Button").click()
            print(f'[SIM_CONTROLLER] > Simulator power is turned', Red.format('OFF'))
        except Exception as err:
            print(f'[SIM_CONTROLLER] > Exception occurred : {err}')

    # ----------------------------------------------RUN SCREEN------------------------------------------- #

    def toggle_button(self, status, off_coordinates: list, on_coordinates: list):
        """
        className: test cases name
        Status: expected status
        Off_coordinates: Toggle button off button coordinates
        On_coordinates: Toggle button on button coordinates
        """
        try:
            # [90,311, 58,25], [154,311,57,23] OFF / ON
            current_status = []
            Helper.snapshot(self.test_case_name)
            cstatus = Helper.crop_image_extract_text(self.test_case_name, off_coordinates[0], off_coordinates[1],
                                                     off_coordinates[2],
                                                     off_coordinates[3], inv=True)
            current_status.append(cstatus)
            cstatus = Helper.crop_image_extract_text(self.test_case_name, on_coordinates[0], on_coordinates[1],
                                                     on_coordinates[2],
                                                     on_coordinates[3], inv=True)
            current_status.append(cstatus)
            print('current_status:', current_status)
            for a in current_status:
                if 'OFF' in a and status == "ON":
                    print("Button current state : OFF")
                    Helper.long_tap(x=on_coordinates[0] + 20, y=on_coordinates[1] + 20, t=10000)
                    print("Button turned into ON state")
                elif 'ON' in a and status == "OFF":
                    print("Button current state : Auto")
                    Helper.long_tap(x=off_coordinates[0] + 20, y=off_coordinates[1] + 20, t=10000)
                    print("Button turned into OFF state")
            # validation
            current_status.clear()
            Helper.snapshot(self.test_case_name)
            print(current_status)
            cstatus = Helper.crop_image_extract_text(self.test_case_name, off_coordinates[0], off_coordinates[1],
                                                     off_coordinates[2],
                                                     off_coordinates[3], inv=True)
            current_status.append(cstatus)
            cstatus = Helper.crop_image_extract_text(self.test_case_name, on_coordinates[0], on_coordinates[1],
                                                     on_coordinates[2],
                                                     on_coordinates[3], inv=True)
            current_status.append(cstatus)
            for a in current_status:
                if 'ON' in a and status == "ON":
                    Helper.prGreen("Button turned ON successfully")

                elif 'OFF' in a and status == "OFF":
                    Helper.prGreen("Button turned OFF successfully")
        except Exception as e:
            print("Boundary_toggle_switch encountered an " + str(e))
            Helper.prRed("Boundary_toggle_switch encountered an " + str(e))

    def switch_user_profile(self, switch_user):
        print(f'[{self.test_case_name}] > Clicking on User Profile')
        self.common_functions.tap_adb(806, 44)
        self.wait_to_appear(resource_id="com.cnh.android.user:id/id_title", item_text="User Profile")
        print(f'[{self.test_case_name}] > Clicked on User Profile screen')
        currentUser = Display.active_display_uiautomator(resourceId="com.cnh.android.user:id/id_user_name").__getattr__('text')
        print(f'[{self.test_case_name}] > Currently logged user is: ' + currentUser)

        # if currently logged user is not 'Owner', then switch user to 'Owner'
        if currentUser != switch_user:
            status = self.wait_to_appear(resource_id="com.cnh.android.user:id/id_button_switch_user",
                                         item_text="Switch User")
            if status:
                self.common_functions.tap_using_ui_item(resource_id="com.cnh.android.user:id/id_button_switch_user",
                                                        item_text="Switch User")
                time.sleep(2)
                print(f'[{self.test_case_name}] > Clicked on Select User screen')

                # Click on 'Owner' to set it as current user
                user = self.wait_to_appear(resource_id="com.cnh.android.user:id/id_user_name",
                                           item_text=switch_user)
                if user:
                    switchUserRole = \
                        Display.active_display_uiautomator(resourceId="com.cnh.android.user:id/id_user_name", text=switch_user).sibling(
                            resourceId="com.cnh.android.user:id/id_user_role").__getattr__('text')
                    self.common_functions.tap_using_ui_item(resource_id="com.cnh.android.user:id/id_user_name",
                                                            item_text=switch_user)
                    print(f'[{self.test_case_name}] > Current User Profile set to ' + switch_user)
                    time.sleep(10)
                    status = self.wait_to_appear(resource_id="com.cnh.android.user:id/btFirst")

                    if status:
                        print(f"[{self.test_case_name}] > Clicking on Login popup")
                        self.common_functions.tap_using_ui_item(resource_id="com.cnh.android.user:id/btFirst",
                                                                item_text="Login")
                    else:
                        print(f"[{self.test_case_name}] > Login popup doesn't exist")
                else:
                    result_description = "FAILED: " + switch_user + " is not available to set as current user"
                    raise Exception(result_description)
            else:
                result_description = "FAILED: Switch User button is not available to click"
                raise Exception(result_description)

            if switchUserRole == "Basic":
                # wait until the screen is enabled after setting the user profile
                counter = 0
                image_name = "limitedPermissionsDialogCompare"
                ref = "limitedPermissionsDialog.png"
                while counter <= 20:
                    Helper.snapshot(image_name)
                    Helper.image_crop(image_name, image_name, 483, 240, 590, 257)
                    image_result = Helper.image_comparison(ref, image_name + ".png", 0.8, False, 5)
                    if image_result is True:
                        print("Limited Permissions dialog is appeared")
                        # Click on OK button
                        Helper.tap(988, 530)
                        return
                    else:
                        counter += 1
        else:
            print("Current logged user profile is already " + switch_user)

        self.wait_for_runScreenToOpen()
        time.sleep(2)

    def wait_for_runScreenToOpen(self):
        # wait until Run Screen loading is completed
        counter = 0
        time.sleep(1)
        while counter <= 10:
            self.common_functions.tap_adb(312, 768)
            time.sleep(2)
            rs1_eng_speed = self.wait_to_appear(item_text="Engine Speed")
            if rs1_eng_speed:
                print("Run Screen is Open")
                time.sleep(2)
                return
            else:
                print("Run Screen is still loading...")
                counter += 1
                time.sleep(1)
        raise Exception("FAILED: Waited Long Time To open Run Screen, But it is taking long time")

    def delete_users_from_usermanagement(self):
        print(f'[{self.test_case_name}] > Clicking on User Profile')
        self.common_functions.tap_adb(806, 44)
        time.sleep(2)
        print(f'[{self.test_case_name}] > Clicked on User Profile screen')
        time.sleep(3)
        currentUser = Display.active_display_uiautomator(resourceId="com.cnh.android.user:id/id_user_name").__getattr__('text')
        print("Currently logged user is: " + currentUser)

        # Switch to Owner user profile if its not
        if currentUser != "Owner":
            self.switch_user_profile("Owner")
            time.sleep(5)
        print(f'[{self.test_case_name}] > Clicking on User Profile')
        self.common_functions.tap_adb(806, 44)
        time.sleep(2)
        # Click on User Management
        print(f"[{self.test_case_name}] > Clicking on User Management")
        self.common_functions.tap_adb(1112, 679)
        time.sleep(2)
        print(f'[{self.test_case_name}] > Clicked on User Management screen')

        userList = Display.active_display_uiautomator(resourceId="com.cnh.android.user:id/id_user_list")
        userCount = userList.info['childCount']
        userNameList = []
        while userCount > 2:
            # To get the list of User-Names
            for i in range(0, userCount):
                user_name = userList.child(
                    className="android.widget.RelativeLayout", index=i).child(
                    resourceId="com.cnh.android.user:id/id_user_name").__getattr__('text')
                userNameList.append(user_name)
            print(f'[{self.test_case_name}] > List of Users displayed: ' + str(userNameList))
            # To delete the Non-default Users (Default users are Guest User, Owner)
            for i in range(2, userCount):
                if not userNameList[i] in ('Guest User', 'Owner'):
                    # Click on Delete icon of the user if the user exists
                    time.sleep(10)
                    if userList.child_by_text(userNameList[i]).exists:
                        userList.child_by_text(
                            userNameList[i], resourceId="com.cnh.android.user:id/id_user_name").sibling(
                            resourceId="com.cnh.android.user:id/id_user_options").child(
                            className="android.widget.FrameLayout").child(
                            resourceId="com.cnh.android.user:id/id_user_delete").click()
                        time.sleep(1)

                        print(f'[{self.test_case_name}] > Clicked on Delete icon of user: ' + userNameList[i])
                        # Click on 'Delete User' button in Delete User window
                        del_user = self.wait_to_appear(resource_id="com.cnh.android.user:id/btFirst",
                                                       item_text="Delete User")
                        if del_user:
                            self.common_functions.tap_using_ui_item(resource_id="com.cnh.android.user:id/btFirst",
                                                                    item_text="Delete User")
                            time.sleep(1)

                            print(f'[{self.test_case_name}] > {userNameList[i]} is deleted')
                        else:
                            result_description = "FAILED: Delete User button is not available"
                            raise Exception(result_description)
                    else:
                        result_description = "FAILED: " + userNameList[i] + " is not available"
                        raise Exception(result_description)
            # to update the userCount after deleting two users
            userCount = userList.info['childCount']
            userNameList = []
        if userCount == 2:
            print(f'[{self.test_case_name}] > Only default users are present')
        print(f'[{self.test_case_name}] > Closing user profile\n')
        from Screen.UserProfile import UserProfile
        UP = UserProfile()
        UP.close()

    def data_import_and_validate_default_runScreen_layouts(self, userProfile_list):

        # Expand the data tree and Validate with existing list if Data tree is available
        profiles = self.wait_to_appear(
            resource_id="com.cnh.pf.android.data.management:id/tree_list_item_simple",
            item_text="User Profiles and Run-Screen Layouts")
        if profiles:
            print("Expand and Validate User Profile")
            validateDataList = self.expand_and_validate_userProfile_vehicleConfig_exportTab(userProfile_list)

            if validateDataList is True:

                print("Expanded and Validated Export Data Tree")

                # Click on DM tab once export is completed
                self.click_menu_tab('Data Management')

                # switch_userProfile = import_data_conflict_testcase.switch_user_profile()
                self.switch_user_profile("Admin User")

                # Go to run screen edit mode to check runscreen layout
                print("Long press on Run1 to open Edit Run Screen mode")
                self.common_functions.long_press(290, 775)
                time.sleep(5)
                self.common_functions.tap_adb(715, 485)
                time.sleep(10)
                udw_testcase.click_layout_button()
                time.sleep(15)
                layout = self.wait_to_appear(resource_id="com.cnh.android.screenmanager:id/layout_name",
                                             item_text="Generic")
                if layout:
                    print("Selecting Generic layout from Layout Management")
                    self.common_functions.tap_using_ui_item(resource_id="com.cnh.android.screenmanager:id/layout_name",
                                                            item_text="Generic")
                    status = self.wait_to_appear(
                        resource_id="com.cnh.android.screenmanager:id/popover_layouts_close")
                    if status:
                        udw_testcase.close_layout_managment()
                else:
                    raise Exception("Imported Admin layout does not exist")

                print("Closing Edit Run Screen mode")
                udw_testcase.close_layout_edit_mode()
                popup = self.wait_to_appear(resource_id="com.cnh.android.screenmanager:id/btFirst",
                                            item_text="OK")
                if popup:
                    self.common_functions.tap_using_ui_item(resource_id="com.cnh.android.screenmanager:id/btFirst",
                                                            item_text="OK")
                else:
                    pass

                # wait until Admin custom layout appears
                self.wait_for_runScreenToOpen()

                print("Verifying Default Run Screen Layouts\n")
                runscreen1 = udw_testcase.checkDefaultUDWsRunScreen1_on_CH26_casemodel_testcase()
                runscreen1.run()

                print("Result of Run Screen1 is: " + runscreen1.result_description + "\n")
                runscreen1_result = runscreen1.result

                runscreen2 = udw_testcase.checkDefaultUDWsRunScreen2_on_CH26_casemodel_testcase()
                runscreen2.run()

                print("Result of Run Screen2 is: " + runscreen2.result_description + "\n")
                runscreen2_result = runscreen2.result

                runscreen3 = udw_testcase.checkDefaultUDWsRunScreen3_testcase()
                runscreen3.run()

                print("Result of Run Screen3 is: " + runscreen3.result_description + "\n")
                runscreen3_result = runscreen3.result
                if runscreen3_result is False:
                    self.click_screenshot_display()

                runscreen4 = udw_testcase.checkDefaultUDWsRunScreen4_on_CH26_casemodel_testcase()
                runscreen4.run()

                print("Result of Run Screen4 is: " + runscreen4.result_description + "\n")
                runscreen4_result = runscreen4.result

                runscreen5 = udw_testcase.checkDefaultUDWsRunScreen5_on_CH26_casemodel_testcase()
                runscreen5.run()

                print("Result of Run Screen5 is: " + runscreen5.result_description + "\n")
                runscreen5_result = runscreen5.result

                result = [runscreen1_result, runscreen2_result, runscreen3_result,
                          runscreen4_result,
                          runscreen5_result]
                runscreen_names = ["Run_Screen1", "Run_Screen2", "Run_Screen3", "Run_Screen4",
                                   "Run_Screen5"]

                if all(result):
                    print(f"[{self.test_case_name}] > All validation PASSED")
                    self.common_functions.tap_adb(312, 768)
                    time.sleep(2)
                    self.wait_to_appear(item_text="Engine Speed")

                else:
                    for index, value in enumerate(result):
                        if value is False:
                            print("FAILED: " + runscreen_names[index])
                        self.common_functions.tap_adb(312, 768)
                        time.sleep(2)
                        self.wait_to_appear(item_text="Engine Speed")

            else:

                result_description = "FAILED: Mismatch in Export Data Tree item"
                raise KeyError(result_description)
        else:
            result_description = "FAILED: User Profile Data tree is not available to expand and validate"
            raise Exception(result_description)

    def expand_and_validate_userProfile_vehicleConfig_exportTab(self,
                                                                dataTreeList=None):
        # Click On expand (+) button of dataTreeList (User Profile/Vehicle Config)
        from AutomatedTestCases.testcase import current_results_path
        from AutomatedTestCases.testcase import run_count
        run_number = run_count
        tree_counter = 0
        listView = Display.active_display_uiautomator(resourceId="com.cnh.pf.android.data.management:id/tree_view_list")
        listViewChildCount = listView.info['childCount']
        if dataTreeList[0] == "User Profiles and Run-Screen Layouts":
            tree_counter = int(listViewChildCount) - 2
        elif dataTreeList[0] == "Vehicle Configurations":
            tree_counter = int(listViewChildCount) - 1

        try:
            if dataTreeList is None:
                raise Exception("FAILED: [validateDataTree]: Please Provide Items To Validate In Data Tree")
            else:
                failCounter = 0
                for item in dataTreeList:
                    flag = True
                    while flag:
                        listViewItem = listView.child(className="android.widget.LinearLayout", index=tree_counter)
                        if listViewItem.exists:
                            time.sleep(1)
                            itemLayout = listViewItem.child(resourceId="com.cnh.pf.android.data.management:id"
                                                                       "/treeview_list_item_frame_layout")
                            expand_button = itemLayout.child(
                                resourceId="com.cnh.pf.android.data.management:id/treeview_list_item_toggle")
                            frameLayout = itemLayout.child(
                                resourceId="com.cnh.pf.android.data.management:id/treeview_list_item_frame")
                            item_name = frameLayout.child(
                                resourceId="com.cnh.pf.android.data.management:id/tree_list_item_simple").__getattr__(
                                'text')
                            if expand_button.exists:
                                expand_button.click()
                            if item_name == item:
                                print("Validated item: " + item)
                            else:
                                image_name = item.replace(" ", "_")
                                print("FAILED: Validating " + item)
                                print("Expected item: " + item + ", " + "Actual item: " + item_name)
                                self.click_screenshot_display()
                                failCounter += 1
                            break
                        else:
                            os.system("adb shell input swipe 660 690 660 400")
                            time.sleep(1)
                            itemLayout = listViewItem.child(resourceId="com.cnh.pf.android.data.management:id"
                                                                       "/treeview_list_item_frame_layout")
                            expand_button = itemLayout.child(
                                resourceId="com.cnh.pf.android.data.management:id/treeview_list_item_toggle")
                            frameLayout = itemLayout.child(
                                resourceId="com.cnh.pf.android.data.management:id/treeview_list_item_frame")
                            item_name = frameLayout.child(
                                resourceId="com.cnh.pf.android.data.management:id/tree_list_item_simple").__getattr__(
                                'text')
                            if expand_button.exists:
                                expand_button.click()
                            if item_name == item:
                                print("Validated item: " + item)
                            else:
                                print("FAILED: Validating " + item)
                                print("Expected item: " + item + ", " + "Actual item: " + item_name)
                                self.click_screenshot_display()
                                failCounter += 1
                            break
                    tree_counter = tree_counter + 1
                if failCounter != 0:
                    return False
                elif failCounter == 0:
                    return True
        except JsonRPCError as JsonErr:
            self.click_screenshot_display()
            print("FAILED: UIObject could not be found -JsonRPC Error. " + str(JsonErr))

