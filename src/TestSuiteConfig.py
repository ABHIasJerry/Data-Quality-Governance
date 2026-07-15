# QAHelper -> TestSuiteConfif.py

PCM_LOGS_CAPTURE = False
DISPLAY_LOGS_ANR = True

PCM_IP_ADDRESS = configure.get('Test info', 'sel_ip')
PCM_PORT_ADDRESS = 22
PCM_POSTGRES_PORT_ADDRESS = 2222
PCM_USERNAME = 'root'
PCM_PASSWORD = ''          
DB_NAME = DB_USERNAME = DB_PASSWORD = 'root'


SF_Username = configure.get('SDP info', 'sdp_username')
SF_Password = configure.get('SDP info', 'sdp_password')
