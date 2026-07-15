# QAHelper/QAConstants.py

import os
from datetime import datetime

# ----------------------------------- Update Paths for TestSuites -------------------------------------------
PROJECT_PATH = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
TEST_DATA = os.path.abspath(PROJECT_PATH + '/DMTestData')
TEST_SCRIPTS = os.path.abspath(PROJECT_PATH + '/TestSuites')
ICONS = os.path.abspath(TEST_DATA + '/Icons')
IMPORT = os.path.abspath(TEST_DATA + '/Import')
EXPORT = os.path.abspath(TEST_DATA + '/Export')
REPORTS = os.path.abspath(TEST_DATA + '/Reports')
REFERENCE_IMAGES = os.path.abspath(TEST_DATA + '/ReferenceImage')
ARTIFACTS = os.path.abspath(TEST_DATA + '/Artifacts')
TEMP_SCREENSHOT = os.path.abspath(TEST_DATA + '/TempScreenshots')
TEST_CASE_RESULTS = os.path.abspath(TEST_DATA + '/TestCaseResults')
TEST_CASE_SCREENSHOT = os.path.abspath(TEST_DATA + '/TestCaseScreenshots')
EXECUTION_LOGS = os.path.abspath(TEST_DATA + '/ExecutionLogs')
DATA_CONTAINERS = os.path.abspath(TEST_DATA + '/DataContainers')
UTILITIES = os.path.abspath(TEST_DATA + '/Utilities')

IMPORT_DIR_META = {
    'Default': os.path.abspath(IMPORT + '/Default'),

}

# ------------------------------------------- Common Constants -------------------------------------------
DATETIME_TODAY = datetime.now().strftime('%d%m%y')
DATETIME_YEAR = datetime.now().strftime('%Y')

TABLE_RESOURCES = {
    'TableName': 'xxxx',
    'ColumnName': 'xxxx',
    'ROWID': 'xxxx',
    'VALUE': 'xxx'
}
