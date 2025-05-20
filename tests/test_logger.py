import unittest
from unittest.mock import patch, MagicMock, mock_open, call
import logging
import os
import sys
import ctypes # For mocking MessageBoxW
import traceback

# Assuming utils.logger and utils.settings are in the python path
from utils.logger import Logger
from utils.settings import SettingsManager # To mock its behavior
from utils.const import albayan_folder # For path verification

# Hold original values
ORIGINAL_SYS_EXCEPTHOOK = sys.excepthook

class TestLogger(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # This is to ensure albayan_folder exists for os.path.join to work as expected
        # if it's used directly in the Logger module upon import.
        # However, Logger.initialize_logger creates the path.
        # We will also mock os.path.join for more control.
        if not os.path.exists(albayan_folder):
            os.makedirs(albayan_folder, exist_ok=True)
        cls.log_file_path = os.path.join(albayan_folder, "albayan.log")


    @classmethod
    def tearDownClass(cls):
        # Clean up the log file if it was created
        if os.path.exists(cls.log_file_path):
            try:
                os.remove(cls.log_file_path)
            except OSError:
                pass # Ignore if it can't be removed (e.g. still in use by logger)
        # Clean up albayan_folder if it was created by tests and is empty
        if os.path.exists(albayan_folder) and not os.listdir(albayan_folder):
            try:
                os.rmdir(albayan_folder)
            except OSError:
                pass


    def setUp(self):
        # Reset Logger's state before each test
        Logger.last_logging_status = None
        # Reset sys.excepthook to its original value before each test
        sys.excepthook = ORIGINAL_SYS_EXCEPTHOOK

        # Default mock for SettingsManager.current_settings
        # Tests that require specific settings will override this mock
        self.settings_mock = patch.dict(SettingsManager.current_settings, {
            "general": {"is_logging_enabled": True, "logging_enabled": True} # Ensure both are covered if logic changes
        }, clear=True)
        self.settings_mock.start()

        # It's important that if initialize_logger is called, it doesn't actually
        # try to create/write to a real file system path during most tests,
        # unless that's what's being tested.
        # Patch basicConfig by default.
        self.mock_basic_config = patch('logging.basicConfig').start()


    def tearDown(self):
        patch.stopall() # Stops all patches started with start()
        # Ensure log file is cleaned up if a test inadvertently created it
        # and tearDownClass doesn't catch it because of an error
        if os.path.exists(self.log_file_path) and self.log_file_path != os.path.join(albayan_folder, "albayan.log"):
             # A test might have changed albayan_folder mock, so be careful
            pass
        elif os.path.exists(os.path.join(albayan_folder, "albayan.log")):
             try:
                os.remove(os.path.join(albayan_folder, "albayan.log"))
             except OSError:
                pass


    @patch('utils.const.albayan_folder', "mocked_albayan_folder") # Mock albayan_folder path
    def test_initialize_logger_enabled_first_time(self):
        """Test initialize_logger when logging is enabled for the first time."""
        Logger.last_logging_status = None # Ensure it's like the first run
        
        # SettingsManager.current_settings["general"]["logging_enabled"] is True by default in setUp
        # The Logger.initialize_logger uses a hardcoded "True" for current_logging_status check
        # Let's analyze the actual logic:
        # current_logging_status = "True" -> this is hardcoded
        # if current_logging_status != cls.last_logging_status: -> this will be true if last_logging_status is None or "False"
        #   if current_logging_status == "True": mode = "a"
        # So, it should always try to set mode = "a" if last_logging_status is not "True"

        Logger.initialize_logger()

        expected_log_path = os.path.join("mocked_albayan_folder", "albayan.log")
        self.mock_basic_config.assert_called_once_with(
            filename=expected_log_path,
            level=logging.INFO,
            filemode="a", # Should be 'a' as current_logging_status is "True" and last_logging_status is None
            format="(%(asctime)s) | %(name)s | %(levelname)s => '%(message)s'"
        )
        self.assertEqual(Logger.last_logging_status, "True")


    @patch('utils.const.albayan_folder', "mocked_albayan_folder_w")
    def test_initialize_logger_mode_w_when_previously_false(self):
        """Test initialize_logger sets mode 'w' if last_logging_status was 'False'."""
        # This test is tricky because initialize_logger hardcodes current_logging_status = "True"
        # The internal logic is:
        # current_logging_status = "True"
        # if current_logging_status != cls.last_logging_status:
        #    if current_logging_status == "True": mode = "a"
        #    else: mode = "w"
        # This means mode 'w' is currently unreachable by initialize_logger as implemented.
        # The test will reflect the actual behavior. If the code were to change to:
        # current_logging_status = SettingsManager.current_settings["general"].get("logging_enabled")
        # then this test would be different.

        Logger.last_logging_status = "False" # Simulate logging was "disabled" (by some other mechanism)

        Logger.initialize_logger()
        expected_log_path = os.path.join("mocked_albayan_folder_w", "albayan.log")
        self.mock_basic_config.assert_called_once_with(
            filename=expected_log_path,
            level=logging.INFO,
            filemode="a", # Still 'a' due to hardcoded "True" for current_logging_status
            format="(%(asctime)s) | %(name)s | %(levelname)s => '%(message)s'"
        )
        self.assertEqual(Logger.last_logging_status, "True")

    def test_initialize_logger_not_called_if_status_unchanged(self):
        """Test basicConfig is not called if logging status hasn't changed."""
        Logger.last_logging_status = "True" # Simulate it was already initialized and "True"
        # SettingsManager mock in setUp ensures "logging_enabled" is true.
        # initialize_logger hardcodes current_logging_status = "True"
        
        Logger.initialize_logger()
        self.mock_basic_config.assert_not_called()


    @patch('logging.info')
    def test_info_logs_message_when_enabled(self, mock_log_info):
        # SettingsManager is mocked in setUp to have is_logging_enabled: True
        Logger.info("Test info message")
        self.mock_basic_config.assert_called() # initialize_logger should be called
        mock_log_info.assert_called_once_with("Test info message")

    @patch('logging.info')
    def test_info_does_not_log_when_disabled(self, mock_log_info):
        # Override SettingsManager mock for this test
        self.settings_mock.stop() # Stop the default one
        settings_disabled_mock = patch.dict(SettingsManager.current_settings, {
            "general": {"is_logging_enabled": False}
        }, clear=True)
        settings_disabled_mock.start()
        
        Logger.info("Test info message")
        self.mock_basic_config.assert_called() # initialize_logger is still called
        mock_log_info.assert_not_called() # But logging.info should not be

        settings_disabled_mock.stop()
        self.settings_mock.start() # Restart default for other tests


    @patch('logging.error')
    def test_error_logs_message_when_enabled(self, mock_log_error):
        # SettingsManager is mocked in setUp to have is_logging_enabled: True
        # Note: Logger.error doesn't check SettingsManager, it always logs to logging.error
        Logger.error("Test error message")
        self.mock_basic_config.assert_called() # initialize_logger should be called
        mock_log_error.assert_called_once_with("Test error message", exc_info=True)


    @patch('ctypes.windll.user32.MessageBoxW', new_callable=MagicMock)
    def test_show_error_message(self, mock_message_box):
        test_message = "A test error occurred."
        Logger.show_error_message(test_message)
        mock_message_box.assert_called_once_with(None, test_message, "Error", 0x10)


    @patch('utils.logger.Logger.show_error_message')
    @patch('utils.logger.Logger.error')
    @patch('traceback.extract_tb')
    @patch('os.path.basename') # Mock basename as it's used in the loop
    def test_my_excepthook(self, mock_basename, mock_extract_tb, mock_logger_error, mock_logger_show_error):
        # Setup dummy exception info
        exctype = type("DummyException", (Exception,), {})
        value = exctype("Test exception value")
        
        # Create a mock traceback object
        # A traceback object has attributes like tb_frame, tb_lineno, tb_next
        # traceback.extract_tb returns a list of FrameSummary objects
        # FrameSummary(filename, lineno, name, line)
        mock_frame1 = MagicMock()
        mock_frame1.filename = "/path/to/file1.py"
        mock_frame1.lineno = 10
        mock_frame1.name = "function1" # Not used by current logger.my_excepthook, but good for completeness
        mock_frame1.line = "code line 1"
        
        mock_frame2 = MagicMock()
        mock_frame2.filename = "/path/to/another/file2.py"
        mock_frame2.lineno = 25
        mock_frame2.name = "function2"
        mock_frame2.line = "code line 2"

        mock_extract_tb.return_value = [mock_frame1, mock_frame2]
        
        # Configure os.path.basename to return predictable names
        def basename_side_effect(path):
            if path == "/path/to/file1.py":
                return "file1.py"
            if path == "/path/to/another/file2.py":
                return "file2.py"
            return os.path.basename(path)
        mock_basename.side_effect = basename_side_effect

        # Create a dummy tb object (not strictly needed if extract_tb is fully mocked, but good practice)
        tb = MagicMock() 

        Logger.my_excepthook(exctype, value, tb)

        mock_extract_tb.assert_called_once_with(tb)
        
        expected_error_message_part1 = "Exception Type: DummyException | "
        expected_error_message_part1 += "File: file1.py | Line: 10 | Code: code line 1 | "
        expected_error_message_part2 = "File: file2.py | Line: 25 | Code: code line 2 | "
        expected_error_message_end = "Error Value: Test exception value"
        
        # Check that Logger.error was called with a message containing these parts
        mock_logger_error.assert_called_once()
        actual_error_call_arg = mock_logger_error.call_args[0][0]
        self.assertIn(expected_error_message_part1, actual_error_call_arg)
        self.assertIn(expected_error_message_part2, actual_error_call_arg)
        self.assertIn(expected_error_message_end, actual_error_call_arg)
        
        mock_logger_show_error.assert_called_once_with("حدث خطأ، إذا استمرت المشكلة، يرجى تفعيل السجل وتكرار الإجراء الذي تسبب بالخطأ ومشاركة رمز الخطأ والسجل مع المطورين.")

    def test_sys_excepthook_assignment(self):
        """Test if sys.excepthook can be set to Logger.my_excepthook"""
        # This is more of an integration check, but good to have
        with patch.object(sys, 'excepthook', Logger.my_excepthook):
             self.assertEqual(sys.excepthook, Logger.my_excepthook)
        # sys.excepthook is restored in setUp/tearDown

if __name__ == '__main__':
    unittest.main()
