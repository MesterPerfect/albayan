import unittest
import os
import configparser
import shutil
from utils.settings import SettingsManager
from utils.const import albayan_folder # Used by SettingsManager, so we might need to handle it

# Define a temporary path for testing
TEMP_CONFIG_DIR = "temp_test_config_dir"
TEMP_CONFIG_PATH = os.path.join(TEMP_CONFIG_DIR, "test_config.ini")

class TestSettingsManager(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Create a temporary directory for the config file
        if os.path.exists(TEMP_CONFIG_DIR):
            shutil.rmtree(TEMP_CONFIG_DIR)
        os.makedirs(TEMP_CONFIG_DIR)

        # Store original values
        cls.original_path = SettingsManager.path
        cls.original_albayan_folder_exists = os.path.exists(albayan_folder)
        if not cls.original_albayan_folder_exists:
            os.makedirs(albayan_folder, exist_ok=True)


    @classmethod
    def tearDownClass(cls):
        # Restore original values
        SettingsManager.path = cls.original_path
        if hasattr(SettingsManager, "_current_settings"):
            del SettingsManager._current_settings
        SettingsManager.config = configparser.ConfigParser() # Reset parser

        # Clean up the temporary directory
        if os.path.exists(TEMP_CONFIG_DIR):
            shutil.rmtree(TEMP_CONFIG_DIR)

        if not cls.original_albayan_folder_exists and os.path.exists(albayan_folder):
            # Attempt to remove albayan_folder only if it was created by setup
            # This is a bit risky if other processes depend on it, but for isolated testing...
            try:
                if not os.listdir(albayan_folder): # Only remove if empty
                    os.rmdir(albayan_folder)
                elif albayan_folder == SettingsManager.path.rsplit(os.sep,1)[0] and "config.ini" in os.listdir(albayan_folder):
                     # if the only file is config.ini, remove it and the folder
                     if len(os.listdir(albayan_folder)) == 1 and os.path.exists(os.path.join(albayan_folder, "config.ini")):
                        os.remove(os.path.join(albayan_folder, "config.ini"))
                        os.rmdir(albayan_folder)

            except OSError as e:
                print(f"Warning: Could not clean up albayan_folder: {e}")


    def setUp(self):
        # Override the path to use the temporary one for each test
        SettingsManager.path = TEMP_CONFIG_PATH
        # Reset config parser for each test
        SettingsManager.config = configparser.ConfigParser()
        # Clear any cached settings
        if hasattr(SettingsManager, "_current_settings"):
            del SettingsManager._current_settings
        # Ensure the temporary config file does not exist at the start of a test
        if os.path.exists(TEMP_CONFIG_PATH):
            os.remove(TEMP_CONFIG_PATH)

    def tearDown(self):
        # Clean up the temporary config file after each test
        if os.path.exists(TEMP_CONFIG_PATH):
            os.remove(TEMP_CONFIG_PATH)
        # Clear any cached settings again
        if hasattr(SettingsManager, "_current_settings"):
            del SettingsManager._current_settings
        SettingsManager.config = configparser.ConfigParser()


    def test_read_default_settings_when_no_file_exists(self):
        """Test that read_settings returns default_settings if no config file exists."""
        if os.path.exists(TEMP_CONFIG_PATH):
            os.remove(TEMP_CONFIG_PATH) # Ensure no file
        
        settings = SettingsManager.read_settings()
        self.assertEqual(settings, SettingsManager.default_settings)
        # Check that the default settings were written to the new file
        self.assertTrue(os.path.exists(TEMP_CONFIG_PATH))
        
        # Verify content of the newly created file
        parser = configparser.ConfigParser()
        parser.read(TEMP_CONFIG_PATH)
        for section, options in SettingsManager.default_settings.items():
            for option, default_value in options.items():
                if isinstance(default_value, bool):
                    read_val = parser.getboolean(section, option)
                elif isinstance(default_value, int):
                    read_val = parser.getint(section, option)
                elif isinstance(default_value, float):
                    read_val = parser.getfloat(section, option)
                else:
                    read_val = parser.get(section, option)
                self.assertEqual(read_val, default_value, f"Default setting for {section}/{option} not written correctly.")


    def test_current_settings_property_loads_defaults(self):
        """Test that current_settings property loads defaults if no file exists."""
        if os.path.exists(TEMP_CONFIG_PATH):
            os.remove(TEMP_CONFIG_PATH)

        settings = SettingsManager.current_settings
        self.assertEqual(settings, SettingsManager.default_settings)
        self.assertTrue(os.path.exists(TEMP_CONFIG_PATH)) # File should be created

    def test_write_and_read_settings(self):
        """Test writing and then reading settings."""
        test_settings = {
            "general": {
                "language": "English",  # String
                "auto_start_enabled": True,  # Boolean
            },
            "audio": {
                "volume_level": 50,  # Integer
            },
            "new_section": { # Completely new section
                "new_setting_str": "test_value",
                "new_setting_int": 123,
                "new_setting_bool": False,
            }
        }
        # SettingsManager only writes sections/keys defined in default_settings
        # So, we need to merge with defaults for this test to reflect how write_settings works
        
        # Simulate writing new settings (it only updates existing keys from default)
        # A more robust test would be to check if write_settings can add new keys/sections
        # But current implementation of write_settings only updates based on what it reads or defaults
        
        # For this test, let's update some default values and write them
        custom_settings_to_write = SettingsManager.default_settings.copy()
        custom_settings_to_write["general"]["language"] = "English"
        custom_settings_to_write["general"]["auto_start_enabled"] = True
        custom_settings_to_write["audio"]["volume_level"] = 50

        SettingsManager.write_settings(custom_settings_to_write)
        
        # Clear cache and read again
        if hasattr(SettingsManager, "_current_settings"):
            del SettingsManager._current_settings
        
        read_back_settings = SettingsManager.read_settings()

        self.assertEqual(read_back_settings["general"]["language"], "English")
        self.assertEqual(read_back_settings["general"]["auto_start_enabled"], True)
        self.assertEqual(read_back_settings["audio"]["volume_level"], 50)
        # Check a default value that wasn't changed
        self.assertEqual(read_back_settings["audio"]["sound_effect_enabled"], SettingsManager.default_settings["audio"]["sound_effect_enabled"])

    def test_reset_settings(self):
        """Test resetting settings to default."""
        custom_settings = SettingsManager.default_settings.copy()
        custom_settings["general"]["language"] = "French"
        custom_settings["listening"]["reciter"] = 10
        
        SettingsManager.write_settings(custom_settings)
        
        # Verify it's not default first
        current = SettingsManager.read_settings()
        self.assertEqual(current["general"]["language"], "French")
        self.assertEqual(current["listening"]["reciter"], 10)

        SettingsManager.reset_settings()
        
        # Clear cache before reading
        if hasattr(SettingsManager, "_current_settings"):
            del SettingsManager._current_settings

        reset_settings = SettingsManager.read_settings()
        self.assertEqual(reset_settings, SettingsManager.default_settings)

        # Also check current_settings property
        if hasattr(SettingsManager, "_current_settings"):
            del SettingsManager._current_settings # force re-read
        self.assertEqual(SettingsManager.current_settings, SettingsManager.default_settings)


    def test_handling_missing_setting_in_file(self):
        """Test fallback to default if a setting is missing in the file."""
        # Create a config file with a missing setting
        parser = configparser.ConfigParser()
        # Use a subset of default settings, deliberately omitting one
        partial_settings = {
            "general": {"language": "TestLang"}, # Missing "run_in_background_enabled"
            "audio": SettingsManager.default_settings["audio"].copy()
        }
        del partial_settings["audio"]["volume_level"] # Deliberately remove a key

        parser.read_dict(partial_settings)
        with open(TEMP_CONFIG_PATH, "w", encoding='utf-8') as f:
            parser.write(f)

        # Read settings. SettingsManager should fill in the missing one with default and save it.
        settings = SettingsManager.read_settings()

        # Check that the missing setting is now there with its default value
        self.assertEqual(settings["general"]["language"], "TestLang") # The one we wrote
        self.assertEqual(settings["general"]["run_in_background_enabled"], 
                         SettingsManager.default_settings["general"]["run_in_background_enabled"])
        self.assertEqual(settings["audio"]["volume_level"], 
                         SettingsManager.default_settings["audio"]["volume_level"])


        # Verify that the file was updated with the missing default value
        updated_parser = configparser.ConfigParser()
        updated_parser.read(TEMP_CONFIG_PATH)
        self.assertEqual(updated_parser.getboolean("general", "run_in_background_enabled"),
                         SettingsManager.default_settings["general"]["run_in_background_enabled"])
        self.assertEqual(updated_parser.getint("audio", "volume_level"),
                         SettingsManager.default_settings["audio"]["volume_level"])


    def test_handling_missing_section_in_file(self):
        """Test fallback to default if a whole section is missing."""
        # Create a config file with a missing section
        parser = configparser.ConfigParser()
        # Deliberately omit the "listening" section
        partial_settings = {
            "general": SettingsManager.default_settings["general"].copy()
        }
        parser.read_dict(partial_settings)
        with open(TEMP_CONFIG_PATH, "w", encoding='utf-8') as f:
            parser.write(f)

        settings = SettingsManager.read_settings()

        # Check that the missing section is now present with all its default values
        self.assertIn("listening", settings)
        self.assertEqual(settings["listening"], SettingsManager.default_settings["listening"])

        # Verify file was updated
        updated_parser = configparser.ConfigParser()
        updated_parser.read(TEMP_CONFIG_PATH)
        for key, value in SettingsManager.default_settings["listening"].items():
            if isinstance(value, bool):
                self.assertEqual(updated_parser.getboolean("listening", key), value)
            elif isinstance(value, int):
                 self.assertEqual(updated_parser.getint("listening", key), value)
            else:
                self.assertEqual(updated_parser.get("listening", key), value)


    def test_current_settings_property_reflects_changes(self):
        """Test that current_settings property reflects changes after write/reset."""
        # Initial state (defaults)
        defaults = SettingsManager.default_settings
        self.assertEqual(SettingsManager.current_settings, defaults)

        # Change settings
        custom_settings = defaults.copy()
        custom_settings["general"]["language"] = "Esperanto"
        SettingsManager.write_settings(custom_settings)
        # current_settings should now reflect this without explicit re-read call by test
        self.assertEqual(SettingsManager.current_settings["general"]["language"], "Esperanto")

        # Reset settings
        SettingsManager.reset_settings()
        # current_settings should now reflect defaults
        self.assertEqual(SettingsManager.current_settings, defaults)
        self.assertEqual(SettingsManager.current_settings["general"]["language"], defaults["general"]["language"])

    def test_write_settings_persists_all_default_keys(self):
        """Ensure write_settings writes all keys from default_settings even if input dict is partial."""
        # This test is based on the observation that `write_settings` uses `cls.config.read_dict(new_settings)`
        # which means it *adds to or overwrites* the current `cls.config` object.
        # Then `cls.config.write(config_file)` writes the entire `cls.config` object.
        # So if `cls.config` was already populated (e.g. by a previous read or default setup),
        # it should persist.
        
        # 1. Start with a clean slate (no file, _current_settings cleared)
        if os.path.exists(TEMP_CONFIG_PATH):
            os.remove(TEMP_CONFIG_PATH)
        if hasattr(SettingsManager, "_current_settings"):
            del SettingsManager._current_settings
        SettingsManager.config = configparser.ConfigParser() # Reset parser

        # 2. Initialize settings (this will load defaults into cls.config and write them)
        SettingsManager.read_settings() 
        # At this point, TEMP_CONFIG_PATH contains default settings

        # 3. Write a partial setting update
        partial_update = {
            "general": {"language": "TestLang"}
        }
        SettingsManager.write_settings(partial_update)

        # 4. Read the file directly and check
        parser = configparser.ConfigParser()
        parser.read(TEMP_CONFIG_PATH)

        self.assertEqual(parser.get("general", "language"), "TestLang")
        # Check another key from "general" that was not in partial_update but is in defaults
        self.assertEqual(parser.getboolean("general", "auto_start_enabled"),
                         SettingsManager.default_settings["general"]["auto_start_enabled"])
        # Check a key from a different section ("audio")
        self.assertEqual(parser.getint("audio", "volume_level"),
                         SettingsManager.default_settings["audio"]["volume_level"])


if __name__ == '__main__':
    unittest.main()
