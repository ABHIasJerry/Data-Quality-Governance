
class base_testcase(object):
    """Base testcase which defines the attributes for a testcase. All testcases should inherit from this base class.

    This class is intended to hold a simple test case which results in a pass fail. These test cases will then be used
    by the testsuit class in order to create an integration test. This class holds the information needed for the
    framework to correctly use the testcase and properly document the execution of the test case.

    testcases should be basic building blocks intended to be reused by multilple testsuits

    Attributes:
        test_name (str):            unique name of the testcase used for reporting results
        test_description (str):     description of the test, this is mainly for helping other people using the testcase
                                    and maybe removed if it does not add value
        result (boolean):           This is the result of the test case
        result_description (str):   This is a description of the result intended to document the reason for a failure
        elapsed_time (double):      Time taken to run test case, the intention is that this time can be used by the
                                    test runner to document the times taken for different steps of an integraiton test
        timeout (double):           This is an optional parameter, but if a test has a condition it waits for there
                                    should be a timeout that will cause the result to be false and the elapsed time to
                                     be -1

    Methods:
        run(args)
    """

    def __init__(self):
        """"Init of base class should be run after definitions in child testcase"""

        # result, result_description and elapsed_time should be implemented in the run function
        self.test_name = NotImplementedError
        self.test_description = NotImplementedError
        self.result = NotImplementedError
        self.result_description = NotImplementedError
        self.elapsed_time = NotImplementedError
        self.timeout = 999999
        self.project = None
        self.id = None
        self.fail_img_path = None

    def run(self, *args, **kwargs):
        """This function runs the test case and must set the result and result_description fields of the class"""
        raise NotImplementedError

    def take_failure_snapshot(self, image_name=""):
        """
        This will take a screenshot of the active display and use the resulting path as the value for the test case
        fail_img_path attribute. This attribute then can be used to attach the image to test reports.
        """
        # If no name was given, set the image name based on the test case name.
        if not image_name:
            image_name = f"{self.test_name}_fail.png"

        # Take snapshot of the display.
        try:
            self.fail_img_path = display_capture.snapshot(image_name)
        except display_capture.ADB.NoDeviceFoundError:
            ColorPrint.error("Not able to take failure snapshot due to no display connected.")

    def handle_failure(self, failure_description: str):
        """
        When a test case fail this method can be used to set the result, result description, and take a picture of the
        display.
        """
        self.result = False
        self.result_description = failure_description

        # If no existing failure image, add a snapshot of what is present on the display.
        if not self.fail_img_path:
            self.take_failure_snapshot()
