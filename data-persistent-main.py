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

    def write(self, message):
        """
        Write logs ti multiple location
        Args:
            message: actual msg
        """
        self.terminal.write(message)
        self.log_file.write(message)
        self.log_file.flush()
        self.tkinter_logs.insert('end', message)
        self.tkinter_logs.see("end")

    def flush(self):
        """
        Flushing msg
        """
        pass


class AutomationMain:
    """
        Main class for data persistent
    """

    def __init__(self):
        self.root = None
        self.verify_from_to = None
        self.top = None
        self.old_schema = None
        self.new_schema = None

        self.download_button = None
        self.hardware_type = None
        self.btn_generate_report = None
        self.btn_run_scripts = None
        self.file_location = None
        self.flash_button = None
        self.check_fdr = None
        self.check_fsu = None

        self.uri = None
        self.logging_windows = []
        self.execution_time = datetime.now().strftime('%y-%m-%d-%H-%M-%S')
        self.execution_log_folder, self.report_folder, self.log_file_path = self.get_files_paths()
        self.data_helper = DataHelper(self.execution_time)
        self.logging_txt = None
        self.stdout_logger = None

    def get_files_paths(self):
        """
        Get files path for logging and reporting
        Returns:
            tuple : log folder path , report path and log file path
        """
        execution_log_folder = Constants.LOGS + f'/{self.execution_time}'
        report_folder = Constants.REPORTS + f'/{self.execution_time}'
        log_file_path = execution_log_folder + f'/stdout_execution.log'
        if not os.path.isdir(execution_log_folder):
            os.makedirs(execution_log_folder, exist_ok=True)
        if not os.path.isdir(report_folder):
            os.makedirs(report_folder, exist_ok=True)

        return execution_log_folder, report_folder, log_file_path

    def init_dashboard(self):
        """
            Init main dashboard
        """
        self.root = Tk()
        self.root.title("Data Persistent Testing Tool | Rev 1.0")
        self.root.minsize(width=1000, height=200)

        main_frame = Frame(self.root, width=500, height=200, bg='gray', bd=0, relief=SOLID)
        main_frame.pack(fill="both", expand=True)

        title_frame = Frame(main_frame, width=500, height=50, bg='whitesmoke', bd=2, relief=SOLID)
        title_frame.pack(fill="both", expand=True)

        title_label = Label(title_frame, text="Data Persistent Testing Tool", relief=FLAT, bg="whitesmoke",
                            fg="black", font='Helvetica 12 bold')
        title_label.grid(row=1, column=1, padx=400, pady=30, sticky='wens')

        operation_frame = Frame(main_frame, width=500, height=100, bg='whitesmoke', bd=2, relief=SOLID)
        operation_frame.pack(fill="both", expand=True)

        btn_prepare_database = Button(operation_frame, text="Prepare Database",
                                      command=lambda: self.run_thread('prepare_database'),
                                      bg="dark green", fg="white", width=20, height=2,
                                      font='Helvetica 10 bold')
        btn_flash_display = Button(operation_frame, text="Flash Display",
                                   command=lambda: self.run_thread('flashing_build'),
                                   bg="orange", fg="white", width=20, height=2,
                                   font='Helvetica 10 bold')
        btn_validate_database = Button(operation_frame, text="Validate databases",
                                       command=lambda: self.get_from_to_values(),
                                       bg="dark red", fg="white", width=20, height=2,
                                       font='Helvetica 10 bold')
        self.btn_generate_report = Button(operation_frame, text="Generate Report",
                                          command=lambda: self.run_thread('generate_report'),
                                          bg="SteelBlue2", fg="white", width=20, height=2,
                                          font='Helvetica 10 bold')

        btn_run_scripts = Button(operation_frame, text="Run TestsSuites",
                                 command=lambda: self.run_thread('run_test_suites'),
                                 bg="magenta2", fg="black", width=20, height=2,
                                 font='Helvetica 10 bold')

        btn_prepare_database.grid(row=1, column=1, padx=35, pady=30)
        btn_flash_display.grid(row=1, column=2, padx=35, pady=30)
        btn_validate_database.grid(row=1, column=3, padx=35, pady=30)
        self.btn_generate_report.grid(row=1, column=4, padx=35, pady=30)
        # btn_run_scripts.grid(row=1, column=5, padx=40, pady=20)
        self.btn_generate_report["state"] = "disable"

        logging_frame = Frame(self.root, width=1000, height=300, bg='gray', bd=1, relief=SUNKEN)
        logging_frame.pack(fill="both", expand=True)
        logging_frame.grid_propagate(False)
        logging_frame.grid_rowconfigure(0, weight=1)
        logging_frame.grid_columnconfigure(0, weight=1)
        self.logging_txt = Text(logging_frame, borderwidth=3, relief="sunken")
        self.logging_txt.config(font=("consolas", 9), undo=True, wrap='word')
        self.logging_txt.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        scroll_bar = Scrollbar(logging_frame, command=self.logging_txt.yview)
        scroll_bar.grid(row=0, column=1, sticky='nsew')
        self.logging_txt['yscrollcommand'] = scroll_bar.set
        self.stdout_logger = LoggerMain(self.logging_txt, self.log_file_path)
        sys.stdout = self.stdout_logger
        self.root.mainloop()

    def get_from_to_values(self):
        """
        get schema version values
        """
        self.top = Toplevel(self.root, bg='gray')
        self.top.minsize(width=300, height=100)

        old_schema = Label(self.top, text="Old build schema version : ", bg='gray', fg='whitesmoke')
        new_schema = Label(self.top, text="New build schema version : ", bg='gray', fg='whitesmoke')

        self.old_schema = StringVar()
        self.new_schema = StringVar()

        old_schema_option = OptionMenu(self.top, self.old_schema, *list(Constants.VERSIONS.values()))
        new_schema_option = OptionMenu(self.top, self.new_schema, *list(Constants.VERSIONS.values()))
        old_schema_option.config(bg="grey", fg="whitesmoke", width=15)
        new_schema_option.config(bg="grey", fg="whitesmoke", width=15)
        ok_button = Button(self.top, text='Verify Database',
                           command=lambda: self.run_thread('validate_database'),
                           bg='olive drab', fg='whitesmoke', width=15)
        cancel_button = Button(self.top, text='Cancel',
                               command=lambda: self.close_popup(),
                               bg='red4', fg='whitesmoke', width=10)

        old_schema.grid(row=2, column=0, padx=5, pady=5)
        new_schema.grid(row=3, column=0, padx=5, pady=5)
        old_schema_option.grid(row=2, column=1, padx=5, pady=5)
        new_schema_option.grid(row=3, column=1, padx=5, pady=5)
        ok_button.grid(row=5, column=0, padx=4, pady=10)
        cancel_button.grid(row=5, column=1, pady=10)
        self.root.wait_window(self.top)

    def close_popup(self):
        """
        Usage:
            close pmt pop-up
        Args:
            N/A
        Returns:
            N/A
        Raises:
            N/A
        """
        self.top.destroy()

    def run_thread(self, function_name, *data):
        """
            Run Thread for multiple scenario
        Args:
            function_name (str) : Which function to run
        """
        if function_name == 'prepare_database':
            thread = threading.Thread(target=self.prepare_database)
            thread.start()
        elif function_name == 'flashing_build':
            thread = threading.Thread(target=self.artifact_flash)
            thread.start()
        elif function_name == 'validate_database':
            thread = threading.Thread(target=self.validate_databases)
            thread.start()
        elif function_name == 'generate_report':
            thread = threading.Thread(target=self.generate_report)
            thread.start()
        elif function_name == 'search_build':
            bundle_version, choices_var, deployment_widget = data
            thread = threading.Thread(target=self.search_and_update,
                                      args=(bundle_version, choices_var, deployment_widget,))
            thread.start()
        elif function_name == 'download_build':
            bundle_version, var, var_hw = data
            thread = threading.Thread(target=self.download_build,
                                      args=(bundle_version, var, var_hw,))
            thread.start()
        elif function_name == 'display_flash':
            thread = threading.Thread(target=self.flashing_build,
                                      args=())
            thread.start()
        elif function_name == 'run_test_suites':
            thread = threading.Thread(target=self.run_test_suites(),
                                      args=())
            thread.start()
        else:
            print('not found')

    def prepare_database(self):
        """
        Preparing database for test execution
        """
        print(''.center(140, '*'))
        print(' Preparing Database '.center(139, ' '))
        print(''.center(140, '*'))
        print(f'[Automation Main] > Preparing database structure for test')
        print(f'[Automation Main] > Dropping existing database')
        self.data_helper.drop_database()
        print(f'[Automation Main] > Existing database dropped')
        print(f'[Automation Main] > Performing new database creation')
        self.data_helper.create_database_with_data('./HelperData/PostgresDB.sql')
        print(f'[Automation Main] > Database successfully created')
        print(f'[Automation Main] > Uploading task folder')
        task_folder_location = os.path.abspath(Constants.DATA_FOLDER + f'/task.zip')
        self.data_helper.upload_replace_pcm_task_folder(task_zip=task_folder_location)
        print(f'[Automation Main] > Task folder upload completed')
        print(f'[Automation Main] > Successfully prepared database for test')
        print(f'[Automation Main] > Downloading Tables for validations')
        self.data_helper.download_tables(Constants.TABLES_DOWNLOAD)
        print(f'[Automation Main] > Successfully download all tables')
        showinfo("Database preparation Status", "Successfully completed database preparation")

    def search_and_update(self, bundle_version, choices_var, deployment_widget):
        """

        Args:
            bundle_version:
            choices_var:
            deployment_widget:
        """
        self.flash_button['state'] = 'disable'
        bundle_version = bundle_version.get().strip()
        deployment_stages, self.uri = self.data_helper.search_artifact(build_number=bundle_version)
        if len(deployment_stages) > 0:
            choices_var.set('')
            deployment_widget['menu'].delete(0, 'end')
            for choice in deployment_stages:
                deployment_widget['menu'].add_command(label=choice, command=_setit(choices_var, choice))
            choices_var.set(deployment_stages[0])
            self.download_button['state'] = 'normal'
        else:
            showinfo('Build not found', f'{self.uri}')
            self.top.focus()

    def download_build(self, bundle_version, var, var_hw):
        """

        Args:
            bundle_version:
            var:
            var_hw:
        """
        hw_type = var_hw.get()
        self.file_location, exist = self.data_helper.download_build(bundle_version, var, hw_type, self.uri)
        if self.file_location is None and not exist:
            print(f'[Automation Main] > failed to download build')
            return
        elif exist:
            showinfo("Build Status", "Build Already Exist")
            self.top.focus()
        else:
            showinfo("Build Status", "Build Download successfully")
        self.flash_button['state'] = 'normal'

    def artifact_flash(self):
        """

        """
        self.top = Toplevel(self.root, bg='gray')
        self.top.minsize(width=300, height=100)

        bundle_version_label = Label(self.top, text="Bundle Version : ", bg='gray')
        bundle_version = Entry(self.top, bg='light yellow')
        refresh_button = Button(self.top, text='Search Build',
                                command=lambda: self.run_thread('search_build', bundle_version, var,
                                                                deployment_stage),
                                bg='yellow', fg='black', width=15)

        deployment_stage_label = Label(self.top, text="Deployment Stage : ", bg='gray')
        choices = ('Select Stage',)
        var = StringVar(self.top)
        var.set(choices[0])
        deployment_stage = OptionMenu(self.top, var, *choices)
        deployment_stage["menu"]["bg"] = "light yellow"
        deployment_stage["bg"] = "grey"
        deployment_stage["activebackground"] = "white"
        deployment_stage["borderwidth"] = 0
        deployment_stage["width"] = 15

        hardware_type_label = Label(self.top, text="Hardware Type  : ", bg='gray')
        choices_hw = ('R6', 'R5')
        var_hw = StringVar(self.top)
        var_hw.set(choices_hw[0])
        hardware_type = OptionMenu(self.top, var_hw, *choices_hw)
        hardware_type["menu"]["bg"] = "light yellow"
        hardware_type["bg"] = "grey"
        hardware_type["activebackground"] = "white"
        hardware_type["borderwidth"] = 0
        hardware_type["width"] = 15

        self.check_fdr = IntVar()
        self.check_fsu = IntVar()
        checkbox_fdr = Checkbutton(self.top, text="Factory Data Reset", variable=self.check_fdr, onvalue=True,
                                   offvalue=False,
                                   height=1, width=20, bg='grey')
        checkbox_fsu = Checkbutton(self.top, text="Factory System Reset", variable=self.check_fsu, onvalue=True,
                                   offvalue=False, height=1, width=20, bg='grey')

        self.download_button = Button(self.top, text='Download Build',
                                      command=lambda: self.run_thread('download_build', bundle_version, var, var_hw),
                                      bg='green', fg='whitesmoke', width=15)
        self.download_button['state'] = 'disable'
        self.flash_button = Button(self.top, text='Flash Build',
                                   command=lambda: self.run_thread('display_flash'),
                                   bg='green', fg='whitesmoke', width=15)
        self.flash_button['state'] = 'disable'
        cancel_button = Button(self.top, text='Cancel',
                               command=lambda: self.close_popup(),
                               bg='orange', fg='whitesmoke', width=15)

        bundle_version_label.grid(row=2, column=0, padx=5, pady=5)
        bundle_version.grid(row=2, column=1, padx=5, pady=5)
        refresh_button.grid(row=2, column=2, padx=5, pady=5)
        deployment_stage_label.grid(row=3, column=0, padx=5, pady=5)
        deployment_stage.grid(row=3, column=1, padx=5, pady=5)
        hardware_type_label.grid(row=4, column=0, padx=5, pady=5)
        hardware_type.grid(row=4, column=1, padx=5, pady=5)
        checkbox_fdr.grid(row=5, column=0, padx=2, pady=5)
        checkbox_fsu.grid(row=5, column=1, padx=2, pady=5)

        self.download_button.grid(row=7, column=0, padx=5, pady=5)
        self.flash_button.grid(row=7, column=1, padx=5, pady=5)
        cancel_button.grid(row=7, column=2, padx=5, pady=5)

        bundle_version.focus()

        self.root.wait_window(self.top)

    def flashing_build(self):
        """
        Flashing build on display
        """
        self.close_popup()
        print(''.center(140, '*'))
        print(' Flashing Build '.center(139, ' '))
        print(''.center(140, '*'))
        print(f'[Automation Main] > Preparing display for flashing')
        fdr = self.check_fdr.get()
        fsu = self.check_fsu.get()
        self.data_helper.flashing_build(self.file_location, fdr, fsu)
        print(f'[Automation Main] > Flashing completed')
        showinfo("Flashing Status", "Successfully completed display flashing")

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

    def run_test_suites(self):
        """
        Run test Suites
        """
        print(''.center(140, '*'))
        print(' Run test Suites '.center(139, ' '))
        print(''.center(140, '*'))
        script_list = ['AircartSmoke_testsuite']
        print(f'[Automation Main] > Running Scripts')
        test_project_path = os.path.abspath('/'.join(os.path.dirname(__file__).split('/')[:-2]))
        test_suites_path = os.path.abspath(test_project_path + '/AutomatedTestSuites')
        sys.path.append(test_project_path)

        for script in script_list:
            print(f'[Automation Main] > Running Script [{script}]')
            script_path = os.path.abspath(f'{test_suites_path}/{script}.py').replace('/', '\\')
            cmd = f'python "{script_path}"'
            process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, universal_newlines=True,
                                       shell=False)
            while process.poll() is None:
                time.sleep(5)
                if process.stdout.readline is not None:
                    for line in iter(process.stdout.readline, b''):
                        if line is not None and line != '':
                            sys.stdout = None
                            print(line)
                            # self.logging_txt.insert('end', line)
                            # self.logging_txt.see("end")

            print(f'[Automation Main] > Script Finished : [{script}]')


if __name__ == '__main__':
    app = AutomationMain()
    app.init_dashboard()
