import os
import time
import Helper

from AutomatedTestCases.testcase import base_testcase, logger
from Helpers import ColorPrint
from DMAutomatedTest.DMHelper import DMConstants


def testcase_runner(given_testcase: base_testcase, run_num: int, given_logger: logger,
                    log_when_true=True, *args, **kwargs):
    """
    testcase_runner

    Run testcases through this function

    :param given_testcase: testcase class e.g. guidanceEngagement_testcases.checkAGLiability_testcase()
    :param run_num: run number that you on for logging purpose. Set to NULL to disregard this
    :param given_logger: testcase.logger class to log testcase results. Set to NULL if not logging
    :param log_when_true: when this is true, always log to file. If false, only log when testcase fails
    :param args: Arguments that are to be passed into the run function of the given testcase
    :return: if the test is successful True or False
    """

    # Set given testcases properties in case they were not setup
    if not hasattr(given_testcase, 'test_name'):
        given_testcase.test_name = given_testcase.__class__.__name__

    if not hasattr(given_testcase, 'result'):
        given_testcase.result = False

    if not hasattr(given_testcase, 'result_description'):
        given_testcase.result_description = "Testcase DID NOT setup result_description while running!!! Please fix!"

    # Execute test
    given_testcase.logger = given_logger  # TODO: base_testcase does not have a logger attribute. Need to investigate
    ColorPrint.output("magenta", f"Starting execution of {given_testcase.test_name}")
    if args:
        ColorPrint.output("magenta", f"passing {args=}")
    if kwargs:
        ColorPrint.output("magenta", f"passing {kwargs=}")
    start_time = time.time()

    try:
        given_testcase.run(*args, **kwargs)
    except Exception as e:
        ColorPrint.output("red", f"Unhandled test case exception. Need to fix test case!!!: {e}")
        given_testcase.result = False
        given_testcase.result_description = str(e)
    finally:
        duration = int(time.time() - start_time)
        given_testcase.elapsed_time = duration

    ColorPrint.output("yellow", f"Completed {given_testcase.test_name} in {duration} seconds")

    # Set what language will be reported in the test report.
    language = 'English'
    language_options = {'eng': 'English', 'deu': 'German', 'nld': 'Dutch', 'tur': 'Turkish', 'dan': 'Danish',
                        'est': 'Estonian', 'spa': 'Spanish', 'spa+eng': 'MexicanSpanish', 'fra': 'French',
                        'hrv': 'Crotian', 'ita': 'Italian', 'lat': 'Latvian', 'lit': 'Lithuanian', 'hun': 'Hungarians',
                        'nor': 'Norwegian', 'pol': 'Polish', 'por': 'Portuguese', 'por+eng': 'BrasilianPortuguese',
                        'ron': 'Romanian', 'slk': 'Slovak', 'slv': 'Slovenian', 'fin': 'Finnish', 'swe': 'Swedish',
                        'ces': 'Czech', 'ell': 'Greek', 'srp': 'Serbian', 'bul': 'Bulgarian', 'rus': 'Russian',
                        'ara': 'Arabic', 'tha': 'Thailand', 'chi_sim': 'Chinese', 'jpn': 'Japanese', 'ukr': 'Ukrainian'}
    if kwargs:
        for key, value in kwargs.items():
            if key == 'lang':
                language = language_options[value]
                # language = value
                break

    # Handle logger recording
    if given_testcase.result:
        ColorPrint.output("green", f'{given_testcase.test_name} test passed')
        if log_when_true:
            given_testcase.logger.log(run_num, given_testcase, duration, language)
        return True

    else:
        ColorPrint.output(
            "red", f'{given_testcase.test_name} test failed with result: {given_testcase.result_description}'
        )
        given_testcase.logger.log(run_num, given_testcase, duration, language)

        # TODO: Figure out why TC_DM has this logic
        if given_testcase.test_name.startswith('test_TC_DM_'):
            current_run_log_directory = os.path.abspath(
                DMConstants.ARTIFACTS + f'/{given_testcase.logger.results_name}/{given_testcase.test_name}')
            Helper.set_os_dir(current_run_log_directory)
            Helper.snapshot("Error_screenshot")

        # TODO: Figure out if returning 2 is valid. This is due to the type returned not being consistent bool vs int
        if given_testcase.result_description == "Run Screen Changed: Probably a screen manager reboot":
            return 2

        return False
