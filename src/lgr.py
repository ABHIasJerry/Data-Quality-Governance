import os
import subprocess
import threading
from typing import Any

import paramiko

from DMAutomatedTest.DMHelper import TestSuitConfig


class PCM:
    def __init__(self, test_case_name: str, wifi_enable=False):
        self.remote_ip = '172.16.1.17'
        if wifi_enable:
            self.remote_ip = '192.168.249.65'
        self.remote_port = 22
        self.username = 'root'
        self.password = 'root'
        self.test_case_name = test_case_name

        self.ssh_client = paramiko.SSHClient()

    def __enter__(self):
        """
            Connect to PCM
        Raises:
            Exception : User define failed connection Exception
        """
        try:
            print(f'[{self.test_case_name}] > Connecting to PCM ... ')
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh_client.connect(self.remote_ip, self.remote_port, self.username, self.password, look_for_keys=False)
            if not self.is_connected():
                self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                self.ssh_client.connect(self.remote_ip, self.remote_port, self.username, self.password,
                                        look_for_keys=False)
                print(f'[{self.test_case_name}] > Successfully Connected ... ')
                return self
            print(f'[{self.test_case_name}] > Already Connected ... ')
            return self
        except Exception as E:
            print(f"[{self.test_case_name}] > Failed to connect to PCM ")
            raise E

    def is_connected(self) -> bool:
        """
            Check PCM is connected or not
        Returns:
            bool : PCM connection status
        """
        cmd = 'pwd'
        try:
            self.ssh_client.exec_command(cmd, timeout=30)
            return True
        except Exception:
            return False

    def get_logs(self, pcm_log_path: str, log_file_name: str = 'PCMLogs') -> bool:
        """
            Get logs from pcm
        Returns:
            bool : successfully captured or not
        Raises:
            Exception : User define failed to capture log
        """
        try:
            tar_file = '/home/apps/farming/data/log/pcmLogs.tar.gz'
            log_path = '/home/apps/farming/data/log/ cnhi'
            tar_ball_cmd = f'tar --ignore-failed-read -czvf {tar_file} -C {log_path}'
            std_in, std_out, std_err = self.ssh_client.exec_command(tar_ball_cmd, timeout=100)
            print("PCM Log Status :\n", std_out.readlines())
            print("PCM Log Error:\n", std_err.readlines())
            pcm_log_path = os.path.abspath(pcm_log_path + f'/{log_file_name}.tar.gz')
            file_exists_cmd = f'[ -f {tar_file} ] && echo "True" || echo "False"'
            std_in, std_out, std_err = self.ssh_client.exec_command(file_exists_cmd)
            if ''.join(std_out.readlines()).strip() == 'True':
                status = self.download_file(from_location='/home/apps/farming/data/log/pcmLogs.tar.gz',
                                            to_location=pcm_log_path)
                if status:
                    self.ssh_client.exec_command(
                        'rm -r /home/apps/farming/data/log/pcmLogs.tar.gz')
                    return True
        except Exception as E:
            print(str(E))
        return False

    def download_file(self, from_location: str, to_location: str) -> bool:
        """
            Download File using sftp
        Returns:
            bool : status of downloading
        Raises:
            Exception : User define failed to download file
        """
        try:
            ftp_client = self.ssh_client.open_sftp()
            ftp_client.get(from_location, to_location)
            ftp_client.close()
            return True
        except Exception as E:
            print(f"[{self.test_case_name}] > Failed to download file from display : " + str(E))
            return False

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        """
            Close ssh Connection
        """
        # if self.is_connected():
        if self.is_connected():
            self.ssh_client.close()
        return True


class Logger(threading.Thread):
    def __init__(self, test_case_name: str, log_time: str, display_logs_path: str, pcm_logs_path: str = None,
                 pcm_file_name: str = 'PCMLogs'):
        super().__init__()
        self.time_log = log_time

        self.display_logs_path = display_logs_path
        self.pcm_logs_path = os.path.abspath(pcm_logs_path) if pcm_logs_path is not None else None
        self.pcm_file_name = pcm_file_name
        self.test_case_name = test_case_name

        self.adb_log_cat_thread = None
        self.is_logcat_running = False

        self.cpu_top_thread = None
        self.is_cpu_top_running = False

        self.mem_thread = None
        self.is_mem_running = False
        self.create_log_folder()

    def create_log_folder(self) -> None:
        if not os.path.isdir(self.display_logs_path):
            os.makedirs(self.display_logs_path)

    def adb_logcat(self) -> None:
        adb_process = subprocess.Popen('adb shell logcat -v threadtime', stdout=subprocess.PIPE)
        logcat_filename = os.path.abspath(self.display_logs_path + f'/{self.time_log}_logcat.txt')
        with open(logcat_filename, mode='w+', encoding='utf8') as log_file:
            self.is_logcat_running = True
            for line in iter(adb_process.stdout.readline, b''):
                if not self.is_logcat_running:
                    break
                elif line != '' and line != '\r\r\n':
                    log_file.write(line.decode('utf8'))
        adb_process.kill()

    def cpu_data(self):
        cpu_process = subprocess.Popen('adb shell top -d 1', stdout=subprocess.PIPE)
        cpu_top_filename = os.path.abspath(self.display_logs_path + f'/{self.time_log}_cpu_top.txt')
        with open(cpu_top_filename, mode='w+', encoding='utf8') as cpu_top:
            self.is_cpu_top_running = True
            for line in iter(cpu_process.stdout.readline, b''):
                if not self.is_cpu_top_running:
                    break
                elif line != '' and line != '\r\r\n':
                    cpu_top.write(line.decode('utf8'))
        cpu_process.kill()

    def mem_data(self):
        mem_filename = os.path.abspath(self.display_logs_path + f'/{self.time_log}_mem.txt')
        with open(mem_filename, mode='w+', encoding='utf8') as mem:
            self.is_mem_running = True
            while True:
                if not self.is_mem_running:
                    break
                process = subprocess.Popen('adb shell grep Mem* /proc/meminfo', stdout=subprocess.PIPE)
                try:
                    stdout, stderr = process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    # print(threading.Thread.name, 'memory collector subprocess timeout')
                    pass
                if process.returncode == 0:
                    mem.write(stdout.decode('utf8').replace('\r\r\n', '\t'))
                    mem.write('\r\n')
                process.kill()

    def logs_collector(self):
        data_to_collect = {}
        if TestSuitConfig.DISPLAY_LOGS_TOMBSTONE:
            data_to_collect['tombstones'] = '/data/tombstones/'
        if TestSuitConfig.DISPLAY_LOGS_ANR:
            data_to_collect['ANR'] = '/data/anr/'
        if TestSuitConfig.UT_SERVICE_LOGS:
            data_to_collect['utservice'] = '/data/data/com.cnh.android.utservice/files/log/'

        for folder, loc in data_to_collect.items():
            print(f"[{self.test_case_name}] > Collecting Data : {folder}")
            is_location_exist = True if 'No such file or directory' not in subprocess.check_output(
                f'adb shell ls {loc}').decode('utf8') else False
            if is_location_exist:
                dest_pull = os.path.abspath(f'{self.display_logs_path}/{folder}')
                subprocess.call(f'adb pull {loc} "{dest_pull}"', stdout=subprocess.PIPE)
                subprocess.call(f'adb shell rm {loc}*', stdout=subprocess.PIPE)

        if TestSuitConfig.PCM_LOGS_CAPTURE:
            print(f'[{self.test_case_name}] > Capturing PCM Logs ..')
            try:
                with PCM(wifi_enable=TestSuitConfig.PCM_WIFI_ENABLE, test_case_name=self.test_case_name) as pcm_device:
                    status = pcm_device.get_logs(self.pcm_logs_path, self.pcm_file_name)
                    if status:
                        print(f'[{self.test_case_name}] > Successfully captured logs from PCM')
                    else:
                        print(f"[{self.test_case_name}] > Failed pcm log capture")
            except Exception as e:
                print(f"[{self.test_case_name}] >Failed pcm log captured : Traceback\n", str(e))

    def run(self):
        if TestSuitConfig.DISPLAY_LOGS_LOGCAT:
            self.adb_log_cat_thread = threading.Thread(target=self.adb_logcat)
            self.adb_log_cat_thread.start()
        if TestSuitConfig.DISPLAY_LOGS_CPU:
            self.cpu_top_thread = threading.Thread(target=self.cpu_data)
            self.cpu_top_thread.start()
        if TestSuitConfig.DISPLAY_LOGS_MEM:
            self.mem_thread = threading.Thread(target=self.mem_data)
            self.mem_thread.start()

    def stop(self):
        if TestSuitConfig.DISPLAY_LOGS_LOGCAT:
            self.is_logcat_running = False
            self.adb_log_cat_thread.join()
        if TestSuitConfig.DISPLAY_LOGS_CPU:
            self.is_cpu_top_running = False
            self.cpu_top_thread.join()
        if TestSuitConfig.DISPLAY_LOGS_MEM:
            self.is_mem_running = False
            self.mem_thread.join()
