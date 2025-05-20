import unittest
from unittest.mock import patch, MagicMock
import sqlite3
import os
from pathlib import Path

# Assuming utils.user_data is in the python path
from utils.user_data import UserDataManager, PreferencesManager

# Define a temporary path for file-based DB testing
TEMP_DB_DIR = "temp_test_db_dir"
TEMP_DB_FILE = Path(TEMP_DB_DIR) / "test_user_data.db"

class TestUserDataManager(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(TEMP_DB_DIR):
            os.makedirs(TEMP_DB_DIR)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(TEMP_DB_FILE):
            os.remove(TEMP_DB_FILE)
        if os.path.exists(TEMP_DB_DIR):
            try:
                os.rmdir(TEMP_DB_DIR) # Only if empty
            except OSError:
                pass # Not empty, other tests might be using it or failed to clean up

    def setUp(self):
        # Most tests will use in-memory DB for speed and isolation
        self.db_path_memory = ":memory:"
        self.manager = UserDataManager(self.db_path_memory)

        # For file creation test
        if os.path.exists(TEMP_DB_FILE):
            os.remove(TEMP_DB_FILE)
        self.db_path_file = TEMP_DB_FILE

    def tearDown(self):
        self.manager.close_connection()
        if os.path.exists(TEMP_DB_FILE):
            try:
                # Ensure connection is closed if a test used the file directly
                if hasattr(self, 'file_manager') and self.file_manager:
                    self.file_manager.close_connection()
                os.remove(TEMP_DB_FILE)
            except OSError:
                pass # File might be locked if connection not closed by manager

    def test_01_initialization_creates_file_if_not_exists(self):
        """Test that UserDataManager creates the DB file if it doesn't exist."""
        self.assertFalse(os.path.exists(self.db_path_file))
        self.file_manager = UserDataManager(self.db_path_file)
        self.assertTrue(os.path.exists(self.db_path_file))
        self.file_manager.close_connection()

    def test_02_initialization_creates_user_position_table(self):
        """Test that UserDataManager creates the user_position table with correct schema."""
        # Use the in-memory DB manager created in setUp
        cursor = self.manager.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_position';")
        self.assertIsNotNone(cursor.fetchone(), "Table 'user_position' was not created.")

        cursor.execute("PRAGMA table_info(user_position);")
        columns = {row['name']: row['type'] for row in cursor.fetchall()}
        
        self.assertIn('id', columns)
        self.assertEqual(columns['id'], 'INTEGER') # PRIMARY KEY implies NOT NULL
        self.assertIn('ayah_number', columns)
        self.assertEqual(columns['ayah_number'], 'INTEGER')
        self.assertIn('criteria_number', columns)
        self.assertEqual(columns['criteria_number'], 'INTEGER')
        self.assertIn('position', columns)
        self.assertEqual(columns['position'], 'INTEGER')

    def test_03_save_position_inserts_new_row(self):
        """Test saving a new position when the table is empty (inserts with id=1)."""
        self.manager.save_position(ayah_number=10, criteria_number=1, position=50)
        
        pos = self.manager.get_last_position()
        self.assertIsNotNone(pos)
        self.assertEqual(pos.get('id'), 1)
        self.assertEqual(pos.get('ayah_number'), 10)
        self.assertEqual(pos.get('criteria_number'), 1)
        self.assertEqual(pos.get('position'), 50)

    def test_04_save_position_updates_existing_row(self):
        """Test updating an existing position (updates row with id=1)."""
        self.manager.save_position(ayah_number=15, criteria_number=2, position=75) # Initial save
        self.manager.save_position(ayah_number=20, criteria_number=3, position=100) # Update
        
        pos = self.manager.get_last_position()
        self.assertIsNotNone(pos)
        self.assertEqual(pos.get('id'), 1)
        self.assertEqual(pos.get('ayah_number'), 20)
        self.assertEqual(pos.get('criteria_number'), 3)
        self.assertEqual(pos.get('position'), 100)

        # Verify there's still only one row with id=1
        cursor = self.manager.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM user_position")
        self.assertEqual(cursor.fetchone()[0], 1)


    def test_05_get_last_position_retrieves_saved_position(self):
        """Test retrieving the last saved position."""
        self.manager.save_position(ayah_number=25, criteria_number=4, position=125)
        pos = self.manager.get_last_position()
        
        self.assertIsNotNone(pos)
        self.assertEqual(pos.get('ayah_number'), 25)
        self.assertEqual(pos.get('criteria_number'), 4)
        self.assertEqual(pos.get('position'), 125)

    def test_06_get_last_position_empty_table(self):
        """Test get_last_position when no position has been saved."""
        pos = self.manager.get_last_position()
        self.assertEqual(pos, {}, "Should return an empty dict if no position saved.")

    def test_07_convert_to_dict_with_row(self):
        """Test convert_to_dict with a sample sqlite3.Row object."""
        # Manually insert a row and fetch it as a sqlite3.Row
        self.manager.cursor.execute("INSERT INTO user_position (id, ayah_number, criteria_number, position) VALUES (?, ?, ?, ?)",
                               (1, 5, 1, 10))
        self.manager.conn.commit()
        
        row = self.manager.cursor.execute("SELECT * FROM user_position WHERE id = 1").fetchone()
        self.assertIsInstance(row, sqlite3.Row)
        
        dict_row = UserDataManager.convert_to_dict(row)
        self.assertEqual(dict_row, {'id': 1, 'ayah_number': 5, 'criteria_number': 1, 'position': 10})

    def test_08_convert_to_dict_with_none(self):
        """Test convert_to_dict with None as input."""
        self.assertEqual(UserDataManager.convert_to_dict(None), {})

    def test_09_connection_handling_connect(self):
        """Test that connect establishes a connection."""
        # manager in setUp already calls connect.
        self.assertIsNotNone(self.manager.conn)
        self.assertIsNotNone(self.manager.cursor)
        # Try a simple query
        self.manager.cursor.execute("SELECT 1")
        self.assertIsNotNone(self.manager.cursor.fetchone())

    def test_10_connection_handling_close_connection(self):
        """Test that close_connection closes the connection."""
        self.manager.close_connection()
        # Try an operation that should fail on a closed connection
        with self.assertRaises(sqlite3.ProgrammingError, msg="Query on closed connection should fail."):
            self.manager.conn.execute("SELECT 1") # Accessing conn directly as cursor might be None

    @patch('utils.user_data.UserDataManager.close_connection')
    def test_11_destructor_calls_close_connection(self, mock_close_connection):
        """Test that the destructor __del__ attempts to close the connection."""
        temp_manager = UserDataManager(self.db_path_memory)
        # Ensure the manager is set up
        self.assertIsNotNone(temp_manager.conn)
        
        # Delete the manager instance
        del temp_manager
        
        # Assert that close_connection was called
        # This can be flaky due to Python's garbage collection timing.
        # A more robust way is to check if the mock was called at least once if multiple managers were created and deleted.
        # For a single instance, it should be called once.
        mock_close_connection.assert_called_once()
        
        # Re-create self.manager as it might have been affected if __del__ was called on it too early
        self.manager = UserDataManager(self.db_path_memory)


class TestPreferencesManager(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(TEMP_DB_DIR):
            os.makedirs(TEMP_DB_DIR)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(TEMP_DB_FILE): # Check if the specific file exists
            os.remove(TEMP_DB_FILE)
        if os.path.exists(TEMP_DB_DIR):
            try:
                os.rmdir(TEMP_DB_DIR)
            except OSError:
                pass

    def setUp(self):
        self.db_path_memory = ":memory:"
        self.manager = PreferencesManager(self.db_path_memory)

        # For file creation test
        if os.path.exists(TEMP_DB_FILE):
            os.remove(TEMP_DB_FILE)
        self.db_path_file = TEMP_DB_FILE

    def tearDown(self):
        self.manager.close()
        if os.path.exists(TEMP_DB_FILE):
            try:
                if hasattr(self, 'file_manager') and self.file_manager:
                    self.file_manager.close()
                os.remove(TEMP_DB_FILE)
            except OSError:
                pass

    def test_01_initialization_creates_file_if_not_exists(self):
        """Test that PreferencesManager creates the DB file if it doesn't exist."""
        self.assertFalse(os.path.exists(self.db_path_file))
        self.file_manager = PreferencesManager(self.db_path_file)
        self.assertTrue(os.path.exists(self.db_path_file))
        self.file_manager.close()


    def test_02_initialization_creates_preferences_table(self):
        """Test that PreferencesManager creates the preferences table with correct schema."""
        cursor = self.manager.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='preferences';")
        self.assertIsNotNone(cursor.fetchone(), "Table 'preferences' was not created.")

        cursor.execute("PRAGMA table_info(preferences);")
        columns = {row['name']: row['type'] for row in cursor.fetchall()}

        self.assertIn('key', columns)
        self.assertEqual(columns['key'], 'TEXT') # PRIMARY KEY implies NOT NULL
        self.assertIn('value', columns)
        self.assertEqual(columns['value'], 'TEXT')


    def test_03_set_preference_insert_new(self):
        """Test inserting a new preference."""
        self.manager.set_preference("theme", "dark")
        val = self.manager.get("theme")
        self.assertEqual(val, "dark")

    def test_04_set_preference_update_existing(self):
        """Test updating an existing preference (UPSERT behavior)."""
        self.manager.set_preference("fontSize", "12")
        self.manager.set_preference("fontSize", "14") # Update
        
        val = self.manager.get("fontSize")
        self.assertEqual(val, "14")

    def test_05_get_preference_existing(self):
        """Test retrieving an existing preference."""
        self.manager.set_preference("language", "en")
        self.assertEqual(self.manager.get("language"), "en")

    def test_06_get_preference_non_existent_no_default(self):
        """Test retrieving a non-existent preference without a default (should return None)."""
        self.assertIsNone(self.manager.get("non_existent_key"))

    def test_07_get_preference_non_existent_with_default(self):
        """Test retrieving a non-existent preference with a default value."""
        self.assertEqual(self.manager.get("non_existent_key", "default_val"), "default_val")

    def test_08_get_int(self):
        """Test get_int for valid integer strings and default value."""
        self.manager.set_preference("count", "100")
        self.assertEqual(self.manager.get_int("count"), 100)
        self.assertEqual(self.manager.get_int("non_existent_int", 42), 42)
        # Current implementation returns -1 if default_value is None and key not found
        self.assertEqual(self.manager.get_int("non_existent_int_no_default"), -1) 
        # Test with a non-integer string (should ideally raise ValueError or handle gracefully)
        self.manager.set_preference("invalid_int", "abc")
        with self.assertRaises(ValueError):
             self.manager.get_int("invalid_int")


    def test_09_get_float(self):
        """Test get_float for valid float strings and default value."""
        self.manager.set_preference("rate", "0.75")
        self.assertEqual(self.manager.get_float("rate"), 0.75)
        self.assertEqual(self.manager.get_float("non_existent_float", 3.14), 3.14)
        # Current implementation returns -1.0 if default_value is None and key not found
        self.assertEqual(self.manager.get_float("non_existent_float_no_default"), -1.0)
        self.manager.set_preference("invalid_float", "xyz")
        with self.assertRaises(ValueError):
            self.manager.get_float("invalid_float")

    def test_10_get_bool(self):
        """Test get_bool for 'True', 'False', and default value."""
        self.manager.set_preference("is_enabled", "True")
        self.manager.set_preference("is_disabled", "False") # Any string not "True" is False
        self.manager.set_preference("is_something_else", "Maybe")

        self.assertTrue(self.manager.get_bool("is_enabled"))
        self.assertFalse(self.manager.get_bool("is_disabled"))
        self.assertFalse(self.manager.get_bool("is_something_else")) # "Maybe" != "True"

        self.assertTrue(self.manager.get_bool("non_existent_bool_true_default", True))
        self.assertFalse(self.manager.get_bool("non_existent_bool_false_default", False))
        # Default for get_bool if key not found and default_value is None is False (None != "True")
        self.assertFalse(self.manager.get_bool("non_existent_bool_no_default"))


    def test_11_connection_handling_close(self):
        """Test that the close method closes the connection."""
        # manager in setUp already calls connect.
        self.assertIsNotNone(self.manager.conn)
        self.manager.close()
        
        # Try an operation that should fail on a closed connection
        with self.assertRaises(sqlite3.ProgrammingError, msg="Query on closed connection should fail."):
            self.manager.conn.execute("SELECT 1")


if __name__ == '__main__':
    unittest.main()
