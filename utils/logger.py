import logging
import traceback
import ctypes # Removed import os
import sys
from pathlib import Path # Added Path import
from utils.settings import SettingsManager
from utils.const import albayan_folder


class Logger:
    last_logging_status = None

    @classmethod
    def initialize_logger(cls):
        current_logging_status = "True"
        if current_logging_status != cls.last_logging_status:
            if current_logging_status == "True":
                mode = "a"
            else:
                mode = "w"
            # Ensure albayan_folder is a Path object, which it should be from const.py
            log_file_path = albayan_folder / "albayan.log"
            logging.basicConfig(filename=log_file_path, # Used Path object
                                level=logging.INFO,
                                filemode=mode,
                                format="(%(asctime)s) | %(name)s | %(levelname)s => '%(message)s'")
        cls.last_logging_status = current_logging_status

    @classmethod
    def info(cls, message:str) -> None:
        cls.initialize_logger()
        if SettingsManager.current_settings["general"].get("is_logging_enabled"):
            logging.info(message)

    @classmethod
    def error(cls, message:str) -> None:
        cls.initialize_logger()
        logging.error(message, exc_info=True)

    @classmethod
    def show_error_message(cls, message:str) -> None:
        ctypes.windll.user32.MessageBoxW(None, message, "Error", 0x10)

    @classmethod
    def my_excepthook(cls, exctype, value, tb):
        tb_list = traceback.extract_tb(tb)
        error_message = "Exception Type: {} | ".format(exctype.__name__)

        for tb_item in tb_list: # Renamed tb to tb_item to avoid conflict with traceback module
            file_name = Path(tb_item.filename).name # Used Path(tb.filename).name
            line_number = tb_item.lineno
            code = tb_item.line

            error_message += "File: {} | Line: {} | Code: {} | ".format(file_name, line_number, code)

        error_message += "Error Value: {}".format(value)

        cls.error(error_message)
        print(error_message)
        cls.show_error_message("حدث خطأ، إذا استمرت المشكلة، يرجى تفعيل السجل وتكرار الإجراء الذي تسبب بالخطأ ومشاركة رمز الخطأ والسجل مع المطورين.")
