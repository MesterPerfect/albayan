import unittest
from unittest.mock import patch, MagicMock, PropertyMock
import os
import sys

# Attempt to import winreg, will be None if not on Windows
try:
    import winreg as reg
    WINREG_AVAILABLE = True
except ImportError:
    reg = MagicMock() # If winreg is not available, mock it entirely
    WINREG_AVAILABLE = False

# Import the class to be tested
from utils.Startup import StartupManager # Corrected import statement
from utils.logger import Logger # To mock Logger methods

# Define constants that would exist in 'winreg' if it were real
REG_SZ = 1 # From winreg documentation
KEY_SET_VALUE = 0x0002 # From winreg documentation
KEY_READ = 0x0001 # From winreg documentation, simplified
HKEY_CURRENT_USER = -2147483647 # Actual value for HKEY_CURRENT_USER

# If winreg was mocked, ensure these constants are attributes of the mock
if not WINREG_AVAILABLE:
    reg.REG_SZ = REG_SZ
    reg.KEY_SET_VALUE = KEY_SET_VALUE
    reg.KEY_READ = KEY_READ
    reg.HKEY_CURRENT_USER = HKEY_CURRENT_USER
    # Also mock WindowsError and FileNotFoundError if winreg is not available
    # These are usually built-in or part of os on Windows.
    # For testing, we can define them as simple Exception subclasses.
    if 'WindowsError' not in globals():
        class WindowsError(OSError): pass # OSError is a common base
    if 'FileNotFoundError' not in globals():
        class FileNotFoundError(IOError): pass # IOError is a common base
    reg.WindowsError = WindowsError
    reg.FileNotFoundError = FileNotFoundError


@unittest.skipUnless(WINREG_AVAILABLE or os.name == 'nt', "winreg tests are skipped on non-Windows unless winreg is mockable")
class TestStartupManager(unittest.TestCase):

    def setUp(self):
        # Mock dependencies for each test
        self.mock_logger_info = patch.object(Logger, 'info').start()
        self.mock_logger_error = patch.object(Logger, 'error').start()

        # Mock winreg functions
        self.mock_reg_open_key = patch('winreg.OpenKey', spec=True).start()
        self.mock_reg_set_value_ex = patch('winreg.SetValueEx', spec=True).start()
        self.mock_reg_delete_value = patch('winreg.DeleteValue', spec=True).start()
        self.mock_reg_query_value_ex = patch('winreg.QueryValueEx', spec=True).start()
        
        # Mock os.path.abspath
        self.mock_os_path_abspath = patch('os.path.abspath').start()
        
        # Mock sys.argv
        self.mock_sys_argv = patch('sys.argv', ['C:\\path\\to\\app.exe']).start() # Default to .exe

        # Common mock for the registry key handle
        self.mock_key_handle = MagicMock(spec=reg.HKEYType if WINREG_AVAILABLE else object)
        self.mock_reg_open_key.return_value.__enter__.return_value = self.mock_key_handle
        
        # Re-evaluate StartupManager.app_path based on mocked sys.argv and os.path.abspath for consistency
        # This is tricky because app_path is a class variable.
        # We can patch it directly or mock its components (sys.argv, os.path.abspath)
        # before StartupManager is used in the test.
        self.test_app_name = "TestApp"
        self.expected_abs_path = "C:\\abs\\path\\to\\app.exe"
        self.mock_os_path_abspath.return_value = self.expected_abs_path
        
        # Dynamically update StartupManager.app_path for tests
        # This requires careful handling if StartupManager is imported multiple times or its class variables are sticky
        StartupManager.app_path = f'"{self.expected_abs_path}" --minimized'


    def tearDown(self):
        patch.stopall()

    # --- Tests for add_to_startup ---
    def test_add_to_startup_exe_path_success(self):
        StartupManager.add_to_startup(self.test_app_name)

        self.mock_reg_open_key.assert_called_once_with(
            reg.HKEY_CURRENT_USER, StartupManager.STARTUP_KEY, 0, reg.KEY_SET_VALUE
        )
        self.mock_reg_set_value_ex.assert_called_once_with(
            self.mock_key_handle, self.test_app_name, 0, reg.REG_SZ, StartupManager.app_path
        )
        self.mock_logger_info.assert_called_once_with(f"{self.test_app_name} added to startup successfully.")
        self.mock_logger_error.assert_not_called()

    def test_add_to_startup_not_exe_path(self):
        with patch('sys.argv', ['C:\\path\\to\\script.py']):
             # Must also re-patch StartupManager.app_path or ensure it's re-evaluated
            StartupManager.app_path = f'"{os.path.abspath(sys.argv[0])}" --minimized' # Re-evaluate based on new sys.argv
            StartupManager.add_to_startup(self.test_app_name)

        self.mock_reg_open_key.assert_not_called()
        self.mock_reg_set_value_ex.assert_not_called()
        self.mock_logger_info.assert_not_called() # No action, no log
        self.mock_logger_error.assert_not_called()


    def test_add_to_startup_openkey_raises_windowerror(self):
        self.mock_reg_open_key.side_effect = WindowsError("OpenKey failed")
        StartupManager.add_to_startup(self.test_app_name)

        self.mock_reg_set_value_ex.assert_not_called()
        self.mock_logger_error.assert_called_once_with(f"Failed to add {self.test_app_name} to startup: OpenKey failed")
        self.mock_logger_info.assert_not_called()

    def test_add_to_startup_setvalue_raises_windowerror(self):
        self.mock_reg_set_value_ex.side_effect = WindowsError("SetValueEx failed")
        StartupManager.add_to_startup(self.test_app_name)

        self.mock_logger_error.assert_called_once_with(f"Failed to add {self.test_app_name} to startup: SetValueEx failed")
        self.mock_logger_info.assert_not_called()

    # --- Tests for remove_from_startup ---
    def test_remove_from_startup_success(self):
        StartupManager.remove_from_startup(self.test_app_name)

        self.mock_reg_open_key.assert_called_once_with(
            reg.HKEY_CURRENT_USER, StartupManager.STARTUP_KEY, 0, reg.KEY_SET_VALUE
        )
        self.mock_reg_delete_value.assert_called_once_with(self.mock_key_handle, self.test_app_name)
        self.mock_logger_info.assert_called_once_with(f"{self.test_app_name} removed from startup successfully.")
        self.mock_logger_error.assert_not_called()

    def test_remove_from_startup_deletevalue_raises_filenotfounderror(self):
        self.mock_reg_delete_value.side_effect = FileNotFoundError("Value not found")
        StartupManager.remove_from_startup(self.test_app_name)

        self.mock_logger_error.assert_called_once_with(f"{self.test_app_name} not found in startup.")
        self.mock_logger_info.assert_not_called()

    def test_remove_from_startup_openkey_raises_windowerror(self):
        self.mock_reg_open_key.side_effect = WindowsError("OpenKey failed")
        StartupManager.remove_from_startup(self.test_app_name)

        self.mock_reg_delete_value.assert_not_called()
        self.mock_logger_error.assert_called_once_with(f"Failed to remove {self.test_app_name} from startup: OpenKey failed")
        self.mock_logger_info.assert_not_called()

    def test_remove_from_startup_deletevalue_raises_windowerror(self):
        # Ensure it's not FileNotFoundError for this test
        self.mock_reg_delete_value.side_effect = WindowsError("DeleteValue failed")
        StartupManager.remove_from_startup(self.test_app_name)

        self.mock_logger_error.assert_called_once_with(f"Failed to remove {self.test_app_name} from startup: DeleteValue failed")
        self.mock_logger_info.assert_not_called()


    # --- Tests for is_in_startup ---
    def test_is_in_startup_true(self):
        # QueryValueEx success means it's in startup
        self.mock_reg_query_value_ex.return_value = (StartupManager.app_path, reg.REG_SZ)
        
        result = StartupManager.is_in_startup(self.test_app_name)

        self.assertTrue(result)
        self.mock_reg_open_key.assert_called_once_with(
            reg.HKEY_CURRENT_USER, StartupManager.STARTUP_KEY, 0, reg.KEY_READ
        )
        self.mock_reg_query_value_ex.assert_called_once_with(self.mock_key_handle, self.test_app_name)
        self.mock_logger_error.assert_not_called()


    def test_is_in_startup_false_filenotfound(self):
        self.mock_reg_query_value_ex.side_effect = FileNotFoundError("Value not found")
        
        result = StartupManager.is_in_startup(self.test_app_name)

        self.assertFalse(result)
        self.mock_logger_error.assert_not_called() # FileNotFoundError is expected for "not in startup"

    def test_is_in_startup_false_other_windowerror(self):
        self.mock_reg_query_value_ex.side_effect = WindowsError("QueryValueEx failed")
        
        result = StartupManager.is_in_startup(self.test_app_name)

        self.assertFalse(result)
        self.mock_logger_error.assert_called_once_with(f"Failed to check startup status: QueryValueEx failed")

    def test_is_in_startup_openkey_raises_windowerror(self):
        self.mock_reg_open_key.side_effect = WindowsError("OpenKey failed")

        result = StartupManager.is_in_startup(self.test_app_name)

        self.assertFalse(result)
        self.mock_reg_query_value_ex.assert_not_called()
        self.mock_logger_error.assert_called_once_with(f"Failed to check startup status: OpenKey failed")


if __name__ == '__main__':
    # This allows running the tests directly, respecting the skip decorator
    if WINREG_AVAILABLE or os.name == 'nt' or 'unittest.mock' in sys.modules: # Allow running if mock is available for patching
        unittest.main()
    else:
        print("Skipping StartupManager tests: winreg module not available and not on Windows.")
