import os
from pathlib import Path
from PyQt6.QtWidgets import QSystemTrayIcon
import sys # Added import for sys

# Determine APP_ROOT based on whether the script is frozen or not
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # PyInstaller specific temp directory
    APP_ROOT = Path(sys._MEIPASS).resolve()
elif getattr(sys, 'frozen', False):
    # General case for frozen executables (like cx_Freeze)
    APP_ROOT = Path(sys.executable).parent.resolve()
else:
    # Running as a script, assuming const.py is in utils/
    # and the project root is one level above utils/
    APP_ROOT = Path(__file__).resolve().parent.parent

home_dir = Path.home()
if sys.platform == "win32":
    # Windows (AppData/Roaming)
    albayan_folder = home_dir / "AppData" / "Roaming" / "tecwindow" / "albayan"
elif sys.platform == "darwin":
    # macOS (Library/Application Support)
    albayan_folder = home_dir / "Library" / "Application Support" / "tecwindow" / "albayan"
else:
    # Linux and other Unix-like systems (.local/share)
    albayan_folder = home_dir / ".local" / "share" / "tecwindow" / "albayan"

albayan_folder.mkdir(parents=True, exist_ok=True)
user_db_path = albayan_folder / "user_data.db"
data_folder = APP_ROOT / "database"

#athkar
athkar_db_path = albayan_folder / "athkar.db"
default_athkar_path = albayan_folder / "audio" / "athkar"
default_athkar_path.mkdir(parents=True, exist_ok=True)
test_athkar_path = APP_ROOT / "Audio" / "athkar"

# albayan folder in temp
# temp_folder = os.path.join(os.getenv("TEMP"), "albayan") # Consider replacing os.getenv("TEMP") with tempfile.gettempdir() for better cross-platform temp dir
temp_folder = Path(os.getenv("TEMP", "/tmp")) / "albayan" # Using /tmp as a fallback for non-Windows
temp_folder.mkdir(parents=True, exist_ok=True)

# Get the path to the Documents directory
albayan_documents_dir = Path.home() / "Documents" / "Albayan"
albayan_documents_dir.mkdir(parents=True, exist_ok=True)

# program information
program_name = "البيان"
program_english_name = "Albayan"
program_version = "3.0.0"
program_icon = APP_ROOT / "Albayan.ico"
website = "https://tecwindow.net/"


class Globals:
    """Class for managing global shared objects."""
    TRAY_ICON = None
    effects_manager = None
