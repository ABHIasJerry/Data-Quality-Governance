import os
from packaging import version

PROJECT_PATH = os.path.abspath(os.path.dirname(__file__))

LOGS = os.path.abspath(PROJECT_PATH + '/Logs')
REPORTS = os.path.abspath(PROJECT_PATH + '/Reports')
DATA_FOLDER = os.path.abspath(PROJECT_PATH + '/HelperData')
GHMI_LOCATION = os.path.abspath(DATA_FOLDER + '/GHMI_build')
EXTRACTED_FILES = os.path.abspath(DATA_FOLDER + '/Extracted')
YAML_FILES = os.path.abspath(PROJECT_PATH + '/ScriptCheckers')
BACKUP_TABLES = os.path.abspath(DATA_FOLDER + '/TableBackup')

TABLES_DOWNLOAD = ['variety_polygon', 'variety_zone', 'variety_map_layer']

VERSIONS = {1: '1',

            }
