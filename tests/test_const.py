import unittest
from unittest.mock import patch, call
import os
import sys
from pathlib import Path

# Store the original os.environ and os.path.expanduser to restore them later
# This is important if other tests or modules rely on the actual environment
ORIGINAL_ENVIRON = os.environ.copy()
ORIGINAL_EXPANDUSER = os.path.expanduser

# Define mock return values for environment variables
MOCK_APPDATA = "/mock/appdata"
MOCK_TEMP = "/mock/temp"
MOCK_HOME = "/mock/home"

# Before importing utils.const, we need to set up mocks for os.getenv and os.path.expanduser
# because these are used at the module level in const.py
# We also need to mock os.makedirs before import.

# We'll apply these patches globally for this test file or use a context manager
# if utils.const is imported within test methods.
# It's generally safer to ensure utils.const is imported *after* mocks are set up if it has module-level side effects.

# Let's assume utils.const will be imported once when this test module is loaded.
# So, we need to patch before that happens. This is tricky.
# A common way is to ensure utils.const is imported *inside* the test methods,
# or within a setUp method, after patches are activated.

# To handle the module-level 'os.makedirs' calls in 'utils.const.py' upon its import,
# we need to patch 'os.makedirs' *before* 'utils.const' is first imported by the test runner.
# This can be done by patching it at the module level of the test file.

mock_makedirs = patch('os.makedirs', return_value=None)
# Start the patch manually, it will be active when utils.const is imported.
# We need to keep a reference to stop it later.
MOCKER_makedirs = mock_makedirs.start()

# Mock os.getenv and os.path.expanduser *before* utils.const is imported.
def mock_getenv_custom(variable_name, default=None):
    if variable_name == "AppData":
        return MOCK_APPDATA
    if variable_name == "TEMP":
        return MOCK_TEMP
    return ORIGINAL_ENVIRON.get(variable_name, default)

def mock_expanduser_custom(path):
    if path == "~":
        return MOCK_HOME
    return ORIGINAL_EXPANDUSER(path)

MOCKER_getenv = patch('os.getenv', side_effect=mock_getenv_custom).start()
MOCKER_expanduser = patch('os.path.expanduser', side_effect=mock_expanduser_custom).start()

# Now, import the module to be tested.
# The os.makedirs calls within utils.const will use our MOCKER_makedirs.
# The path constructions will use our mocked getenv/expanduser.
import utils.const

# Stop the module-level patches after utils.const has been imported and processed.
# These are stopped here so they don't interfere with other test modules if run in a suite.
# Individual tests can still use their own patches.
MOCKER_makedirs.stop()
MOCKER_getenv.stop()
MOCKER_expanduser.stop()


class TestConstants(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Reset os.environ and os.path.expanduser to their original state
        # This is important because the module-level patches might have been stopped,
        # but os.environ itself could have been modified if not handled carefully by mocks.
        # os.getenv and os.path.expanduser are restored by stopping their patchers.
        pass


    def setUp(self):
        # Re-apply mocks for os.getenv and os.path.expanduser for each test method
        # to ensure a clean state, as utils.const might be re-imported or re-evaluated
        # in some complex scenarios, or if other tests modify these.
        # Or, more simply, trust that the initial import of utils.const used the
        # module-level patches and its values are now fixed.

        # We will rely on the fact that utils.const is imported once when the test file is loaded,
        # and its values are set using the module-level patches active at that time.
        # So, no per-test patching of getenv/expanduser for *reading* consts should be needed.
        pass

    def tearDown(self):
        # Stop any patches started within individual tests, if any.
        patch.stopall() # Stops patches started with .start() in test methods

    def test_program_information_constants(self):
        self.assertEqual(utils.const.program_name, "البيان")
        self.assertEqual(utils.const.program_english_name, "Albayan")
        self.assertEqual(utils.const.program_version, "3.0.0")
        self.assertEqual(utils.const.program_icon, "Albayan.ico")
        self.assertEqual(utils.const.website, "https://tecwindow.net/")

    @patch('os.makedirs') # Patch os.makedirs again for this specific test if needed, or verify initial calls.
    def test_directory_creation_calls(self, new_mock_makedirs):
        # This test verifies the calls made during the initial import of utils.const.
        # We need to access the 'MOCKER_makedirs' that was active during import.
        # Or, if utils.const is re-imported or its setup code re-run,
        # new_mock_makedirs would catch those calls.

        # The module-level MOCKER_makedirs should have recorded the calls.
        # Let's re-import utils.const under a controlled patch environment for this test
        # to make it more robust and independent of initial import order.

        with patch('os.makedirs') as fresh_mock_makedirs, \
             patch('os.getenv', side_effect=mock_getenv_custom) as fresh_mock_getenv, \
             patch('os.path.expanduser', side_effect=mock_expanduser_custom) as fresh_mock_expanduser:

            # Reload utils.const to trigger its module-level code with these fresh mocks
            # sys.modules manipulation is one way, or importlib.reload
            if 'utils.const' in sys.modules:
                del sys.modules['utils.const']
            import utils.const as reloaded_const

            expected_albayan_folder = os.path.join(MOCK_APPDATA, "tecwindow", "albayan")
            expected_temp_folder = os.path.join(MOCK_TEMP, "albayan")
            expected_albayan_documents_dir = os.path.join(MOCK_HOME, "Documents", "Albayan")

            calls = [
                call(expected_albayan_folder, exist_ok=True),
                call(expected_temp_folder, exist_ok=True),
                call(expected_albayan_documents_dir, exist_ok=True),
            ]
            fresh_mock_makedirs.assert_has_calls(calls, any_order=True)
            self.assertEqual(fresh_mock_makedirs.call_count, len(calls))


    def test_path_constants_structure_and_type(self):
        # These paths are constructed using the mocked os.getenv and os.path.expanduser
        # that were active when utils.const was first imported.
        
        # tecwindow_folder = os.path.join(os.getenv("AppData"), "tecwindow")
        # albayan_folder = os.path.join(tecwindow_folder, "albayan")
        # user_db_path = os.path.join(albayan_folder, "user_data.db")
        # data_folder = Path("database")
        # athkar_db_path = Path(albayan_folder) / "athkar.db"
        # default_athkar_path = Path(albayan_folder) / "audio" / "athkar"
        # test_athkar_path = Path("audio/athkar")
        # temp_folder = os.path.join(os.getenv("TEMP"), "albayan")
        # albayan_documents_dir = os.path.join(os.path.expanduser("~"), "Documents", "Albayan")

        self.assertIsInstance(utils.const.tecwindow_folder, str)
        self.assertEqual(utils.const.tecwindow_folder, os.path.join(MOCK_APPDATA, "tecwindow"))

        self.assertIsInstance(utils.const.albayan_folder, str)
        self.assertEqual(utils.const.albayan_folder, os.path.join(MOCK_APPDATA, "tecwindow", "albayan"))
        self.assertTrue(utils.const.albayan_folder.startswith(utils.const.tecwindow_folder))

        self.assertIsInstance(utils.const.user_db_path, str)
        self.assertEqual(utils.const.user_db_path, os.path.join(MOCK_APPDATA, "tecwindow", "albayan", "user_data.db"))
        self.assertTrue(utils.const.user_db_path.startswith(utils.const.albayan_folder))

        self.assertIsInstance(utils.const.data_folder, Path)
        self.assertEqual(utils.const.data_folder, Path("database"))

        self.assertIsInstance(utils.const.athkar_db_path, Path)
        self.assertEqual(utils.const.athkar_db_path, Path(os.path.join(MOCK_APPDATA, "tecwindow", "albayan")) / "athkar.db")
        self.assertTrue(str(utils.const.athkar_db_path).startswith(utils.const.albayan_folder))

        self.assertIsInstance(utils.const.default_athkar_path, Path)
        self.assertEqual(utils.const.default_athkar_path, Path(os.path.join(MOCK_APPDATA, "tecwindow", "albayan")) / "audio" / "athkar")
        self.assertTrue(str(utils.const.default_athkar_path).startswith(utils.const.albayan_folder))

        self.assertIsInstance(utils.const.test_athkar_path, Path)
        self.assertEqual(utils.const.test_athkar_path, Path("audio/athkar"))

        self.assertIsInstance(utils.const.temp_folder, str)
        self.assertEqual(utils.const.temp_folder, os.path.join(MOCK_TEMP, "albayan"))

        self.assertIsInstance(utils.const.albayan_documents_dir, str)
        self.assertEqual(utils.const.albayan_documents_dir, os.path.join(MOCK_HOME, "Documents", "Albayan"))


    def test_globals_class_initial_state(self):
        self.assertIsNone(utils.const.Globals.TRAY_ICON)
        self.assertIsNone(utils.const.Globals.effects_manager)

    @classmethod
    def tearDownClass(cls):
        # Restore original os.environ and os.path.expanduser
        # This is crucial if other test modules are run in the same suite.
        # The patchers for getenv and expanduser should have restored the functions,
        # but if os.environ was directly modified, it needs manual restoration.
        # Our mock_getenv_custom avoids direct modification of os.environ.
        os.environ = ORIGINAL_ENVIRON
        os.path.expanduser = ORIGINAL_EXPANDUSER

        # Ensure sys.modules is cleaned up if we manipulated it for reloading
        if 'utils.const_reloaded_for_test' in sys.modules: # Example name
            del sys.modules['utils.const_reloaded_for_test']
        if 'utils.const' in sys.modules: # If it was deleted in a test
            # This might be problematic if other tests need it; typical test isolation
            # means each test file handles its own imports.
            pass


if __name__ == '__main__':
    unittest.main()
