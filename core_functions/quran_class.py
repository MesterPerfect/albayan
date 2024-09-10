"""
This file is part of the Qurani project, created by Nacer Baaziz.
Copyright (c) 2023 Nacer Baaziz
Qurani is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
Qurani is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.
You should have received a copy of the GNU General Public License
along with Qurani. If not, see https://www.gnu.org/licenses/.
You are free to modify this file, but please keep this header.
For more information, visit: https://github.com/baaziznasser/qurani
"""

#code start here


import sqlite3
from core_functions.ayah_data import AyahData


class QuranConst:
    """
    Defines constants and methods to access them for Quran categorization. It
    contains predefined values for maximum pages, surah numbers, juz, hizb, and
    hizb quarters. Two class methods allow retrieval of these maximum values and
    corresponding category labels by their numerical index.

    Attributes:
        max_page (int): 604, representing the maximum number of pages in the Quranic
            text.
        max_surah_number (int|None): 114, representing the maximum number of suras
            (chapters) in the Quran. It specifies the upper limit for various
            categorizations such as page numbers, juz, and hizb divisions.
        max_juz (int): 30, which represents the maximum number of Juz (parts) in
            the Quran.
        max_hizb (int): 60, which represents the maximum number of "hizbs" or
            sections that can be divided into a chapter (surah) of the Quran.
        max_hizb_quarter (int): 240. It appears to represent the maximum number
            of quarters (or parts) within a Hizb, a division used for organizing
            the Quran's chapters or verses in some Islamic traditions.
        _max (Tuple[int,int,int,int,int]): Initialized with the values (604, 114,
            240, 60, 30). It stores a list of maximum values for different Quran
            categorizations.
        _category_labels (Tuple[str,]): 5 elements long. It contains string
            representations for different categories of Quranic divisions: page,
            surah, quarter, hizb, and juz. Each element corresponds to a category
            number in the same order.

    """
    max_page = 604
    max_surah_number = 114
    max_juz = 30
    max_hizb = 60
    max_hizb_quarter = 240
    _max = (max_page, max_surah_number, max_hizb_quarter, max_hizb, max_juz)
    _category_labels = ("صفحة", "سورة", "ربع", "حزب", "جزء")

    @classmethod
    def get_max(cls, category_number: int) -> int:
        """
        Retrieves the maximum value associated with a given category number from
        the `_max` attribute, which is assumed to be a collection of category
        numbers and their corresponding maximum values.

        Args:
            category_number (int): Required to uniquely identify a value within
                the `_max` attribute, an instance variable storing maximum values
                for different categories.

        Returns:
            int: Stored as a class attribute _max at the specified index
            category_number, allowing for accessing maximum values for specific categories.

        """
        assert isinstance(category_number, int), "category_number must be integer"
        return cls._max[category_number]

    @classmethod
    def get_category_label(cls, category_number: int) -> str:
        """
        Retrieves and returns the label associated with a specified category number
        from the _category_labels dictionary, asserting that the input category_number
        must be an integer.

        Args:
            category_number (int): Required, denoted by its position before the
                function name. It represents a category number that must be an integer.

        Returns:
            str: A string corresponding to the category label associated with the
            given category number. This label is retrieved from the class-level
            attribute `_category_labels`.

        """
        assert isinstance(category_number, int), "category_number must be integer"
        return cls._category_labels[category_number]


class quran_mgr:
    """
    Manages Quran data by providing methods to load, retrieve and navigate through
    various sections (Surahs, Hizbs, Juzzes, Quarters, Pages) based on user input.
    It also allows for text formatting and highlighting specific ayahs.

    Attributes:
        show_ayah_number (bool): Initialized to True by default. It controls whether
            or not to display the Ayah number at the end of each verse in the text
            output.
        aya_to_line (bool): Used to determine how Ayahs are displayed. If it is
            True, each Ayah will be on a new line; otherwise, they will be displayed
            in a single line.
        current_pos (int|None): Used to store a current position or number for
            various types of queries like surah, page, hizb, etc. It can also be
            set by calling methods like next(), back() or goto().
        max_pos (int|None): Used to store maximum position value for different
            types of Quran data (surah, hizb, juzz, quarter, page) depending on
            its type.
        type (int|0): Used to track the current mode or section of the Quran being
            accessed, with possible values representing different types such as
            Surah (1), Hizb (3), Juzz (4) etc.
        data_list (list[tuple[Any]]|list[Any]): Initialized as an empty list []
            in the __init__ method. It stores data fetched from the database, which
            are used to generate text.
        conn (sqlite3Connection|NoneType): Used to store a connection object that
            connects to a SQLite database file specified by the `db_path` parameter
            passed to the `load_quran` method.
        cursor (sqlite3Cursor|None): Used to execute SQL queries on a SQLite
            database connection. It allows the retrieval of data from the database
            by executing SELECT statements and fetching results.
        text (str): Used to store the formatted quranic text fetched from the
            database, which includes ayah numbers if `show_ayah_number` is True
            and line breaks if `aya_to_line` is True.
        ayah_data (AyahData|None): Used to store information about the positions
            of ayahs within a retrieved quran text. It appears to be populated by
            the `get_text` method.

    """
    def __init__(self):
        """
        Initializes various instance variables to default settings, preparing an
        object for Quran-related operations, such as displaying Ayah numbers,
        managing database connections and cursors, storing text data, and tracking
        current position within a specific Quran chapter or range.

        """
        self.show_ayah_number = True
        self.aya_to_line = False
        self.current_pos = 1
        self.max_pos = 604
        self.type = 0
        self.data_list = []
        self.conn = None
        self.cursor = None
        self.text = ""
        self.ayah_data = None

    def load_quran(self, db_path):
        """
        Establishes a connection to a SQLite database located at the specified
        path and returns a cursor object that can be used for executing SQL queries
        on the database.

        Args:
            db_path (str): Used to specify the file path to a SQLite database that
                contains Quran data. It is required for connecting to an existing
                SQLite database.

        """
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()

    def get_surah(self, surah_number):
        """
        Retrieves data from a database table named 'quran' for a given surah number.
        It ensures that the current position is set to the maximum allowed value
        if it exceeds the limit and fetches relevant rows before returning further
        processed data in text format.

        Args:
            surah_number (int): 1-based index of a surah (chapter) in the Quran,
                where valid values range from 1 to 114. It determines which chapter's
                data to retrieve from the database.

        Returns:
            List[Tuple[str,str,str,str,str,str,str,str,str,str,str]]: A list
            containing data about a Quranic surah, consisting of various attributes
            such as text and translation. The actual returned value depends on the
            result of `self.get_text()`.

        """
        self.current_pos = surah_number
        self.max_pos = 114
        self.type = 1
        self.current_pos = self.max_pos if self.current_pos > self.max_pos else self.current_pos

        self.cursor.execute(f"SELECT * FROM quran WHERE sura_number = {surah_number}")
        rows = self.cursor.fetchall()
        self.data_list = [(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], None, None) for row in rows]
        return self.get_text()

    def get_hizb(self, hizb_number):
        """
        Fetches data from a database for a specified Hizb number, then populates
        a list with the retrieved rows and returns text based on this list after
        executing a subsequent method called get_text().

        Args:
            hizb_number (int): Used to specify the hizb number for which data is
                to be retrieved from the database table named "quran". It appears
                to represent a specific division or section of the Quran.

        Returns:
            list: The result of calling another function `self.get_text()` likely
            containing Quran text data corresponding to the specified hizb number,
            formatted into a list structure.

        """
        self.current_pos = hizb_number
        self.max_pos = 60
        self.type = 3
        self.current_pos = self.max_pos if self.current_pos > self.max_pos else self.current_pos

        self.cursor.execute(f"SELECT * FROM quran WHERE hizb = {hizb_number}")
        rows = self.cursor.fetchall()
        self.data_list = [(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], None, None) for row in rows]
        return self.get_text()

    def get_juzz(self, juzz_number):
        """
        Retrieves data from a database table "quran" for a specified Juz number,
        limits the current position to 30 if it exceeds, and fetches text data
        associated with the retrieved rows.

        Args:
            juzz_number (int): 1-indexed, meaning it corresponds to one of the 30
                sections (juzz) of the Quran, with values ranging from 1 to 30.

        Returns:
            List[Dict[str,str]]: List containing dictionaries representing data
            from a SQL query, with each dictionary corresponding to a row in the
            database and each key being a column name.

        """
        self.current_pos = juzz_number
        self.max_pos = 30
        self.type = 4
        self.current_pos = self.max_pos if self.current_pos > self.max_pos else self.current_pos
        self.cursor.execute(f"SELECT * FROM quran WHERE juz = {juzz_number}")
        rows = self.cursor.fetchall()
        self.data_list = [(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], None, None) for row in rows]
        return self.get_text()

    def get_quarter(self, quarter_number):
        """
        Retrieves data from a database based on a specified quarter number, limits
        current position to maximum allowed value if exceeded, and returns formatted
        text. It updates instance variables with query results for future use.

        Args:
            quarter_number (int | float): 1-indexed, representing the number of
                the quarter to retrieve from the Quran database, where each quarter
                contains 60 pages (hizb) in total.

        Returns:
            List[List[object]]: 2D list containing data retrieved from database
            table 'quran' where hizbQuarter matches the input quarter_number. Each
            inner list represents a row with 13 columns of data.

        """
        self.current_pos = quarter_number
        self.max_pos = 240
        self.type = 2
        self.current_pos = self.max_pos if self.current_pos > self.max_pos else self.current_pos

        self.cursor.execute(f"SELECT * FROM quran WHERE hizbQuarter = {quarter_number}")
        rows = self.cursor.fetchall()
        self.data_list = [(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], None, None) for row in rows]
        return self.get_text()

    def get_page(self, page_number):
        """
        Retrieves data from the 'quran' table where the page number matches the
        input, stores it in self.data_list, and returns the translated text of the
        retrieved data. The current position is tracked and clamped to the maximum
        value if necessary.

        Args:
            page_number (int): Used as an argument to select data from the 'quran'
                table based on its page number. It may not be validated or restricted,
                but rather capped at a maximum value of 604.

        Returns:
            str|None: The result of calling the method `self.get_text()`, a list
            of tuples representing the data from the database query, each containing
            eleven elements.

        """
        self.current_pos = page_number
        self.max_pos = 604
        self.type = 0
        self.current_pos = self.max_pos if self.current_pos > self.max_pos else self.current_pos

        self.cursor.execute(f"SELECT * FROM quran WHERE page = {page_number}")
        rows = self.cursor.fetchall()
        self.data_list = [(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], None, None) for row in rows]
        return self.get_text()

    def get_range(self, from_surah = False, from_ayah = False, to_surah = False, to_ayah = False):
        """
        Retrieves data from the Quran database within a specified range, based on
        surah (chapter) and ayah (verse) numbers. It constructs SQL queries to
        fetch data, processes results, and populates a list with extracted information.

        Args:
            from_surah (bool | int): 0 by default when not provided. It specifies
                whether to start the range from a specific surah number, where
                False means starting from the beginning of the Quran and any
                positive integer value represents the surah number.
            from_ayah (bool | int): 2-valued, with a default value of False. When
                True, it specifies an Ayah number as the starting point for
                retrieving Quran data; when False or omitted, it defaults to Ayah
                1.
            to_surah (bool | int): Used to specify the last surah number for which
                data should be retrieved. If it's False, all available surahs are
                assumed; if an integer is provided, only that surah is considered.
            to_ayah (bool | int): Set to False by default. It determines whether
                an ending Ayah number should be included in the query or not, with
                True including it and False excluding it.

        Returns:
            str|None: A string representation of the data contained within a
            database table 'quran' based on the specified range of Surah and Ayah
            numbers.

        """
        self.current_pos = -1
        self.max_pos = -1
        self.type = 5

        #check from_surah real number
        if from_surah >= 1:
            self.cursor.execute(f"select number from quran WHERE sura_number = {from_surah}")
            result = self.cursor.fetchall()
            if from_ayah < 1:
                from_ayah = 1
            elif from_ayah > len(result):
                from_ayah = len(result	)
            else:
                from_ayah = int(result[0][0])+(int(from_ayah)-1)

        #check to_surah real number
        if to_surah >= 1:
            self.cursor.execute(f"select number from quran WHERE sura_number = {to_surah}")
            result = self.cursor.fetchall()
            if to_ayah < 1:
                to_ayah = len(result)
            elif to_ayah > len(result):
                to_ayah = len(result	)
            else:
                to_ayah = int(result[0][0])+(int(to_ayah)-1)

        if to_ayah:
            from_ayah = 1 if from_ayah is False else from_ayah
            query = f"SELECT * FROM quran WHERE number BETWEEN {from_ayah} AND {to_ayah}"
        elif from_ayah and to_ayah is False:
            query = f"SELECT * FROM quran WHERE  number >= {from_ayah}"
        else:
            query = f"SELECT * FROM quran WHERE number > 1'"
        self.cursor.execute(query)
        rows = self.cursor.fetchall()
        self.data_list = [(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], None, None) for row in rows]
        return self.get_text()


    def next(self):
        """
        Returns the next page or part of the Quran based on its current position
        and type, incrementing the position after retrieval.

        Returns:
            str|None: A page, surah, quarter, hizb or juzz depending on the type
            of data being iterated over. It returns None if the current position
            is beyond the maximum position.

        """
        if self.current_pos >= self.max_pos:
            return ""
        self.current_pos += 1
        if self.type == 0:
            return self.get_page(self.current_pos)
        elif self.type == 1:
            return self.get_surah(self.current_pos)
        elif self.type == 2:
            return self.get_quarter(self.current_pos)
        elif self.type == 3:
            return self.get_hizb(self.current_pos)
        else:
            return self.get_juzz(self.current_pos)


    def back(self):
        """
        Navigates to the previous item in a list of Quran content, depending on
        its type (page, surah, quarter, hizb, or juzz). It decrements the current
        position and returns the corresponding content based on the selected type.

        Returns:
            str|int: The result of calling a specific method based on the object's
            attribute `type`. The returned value depends on the current position
            and the type of object being accessed.

        """
        if self.current_pos <= 1:
            return ""
        self.current_pos -= 1

        if self.type == 0:
            return self.get_page(self.current_pos)
        elif self.type == 1:
            return self.get_surah(self.current_pos)
        elif self.type == 2:
            return self.get_quarter(self.current_pos)
        elif self.type == 3:
            return self.get_hizb(self.current_pos)
        else:
            return self.get_juzz(self.current_pos)


    def goto(self, goto):
        """
        Navigates to a specified position within Quranic content, based on its
        type (chapter, surah, quarter, hizb, or juzz), and returns relevant data
        for that position. It also validates the position against the maximum
        allowed value.

        Args:
            goto (int | None): Required, its value represents an index or position
                that can be used to navigate within a collection of data. The type
                and validity of this value determine the outcome of the function
                call.

        Returns:
            str|None: A page, surah, quarter, hizb or juzz based on the current
            position and type. The return value will be empty string when goto
            exceeds maximum allowed position.

        """
        if goto > self.max_pos:
            return ""
        self.current_pos = goto

        if self.type == 0:
            return self.get_page(self.current_pos)
        elif self.type == 1:
            return self.get_surah(self.current_pos)
        elif self.type == 2:
            return self.get_quarter(self.current_pos)
        elif self.type == 3:
            return self.get_hizb(self.current_pos)
        else:
            return self.get_juzz(self.current_pos)

    def get_by_ayah_number(self, ayah_number) -> str:

        """
        Retrieves data from the database based on an ayah number, then extracts
        and returns relevant information such as text associated with that ayah
        along with full text.

        Args:
            ayah_number (int): An integer representing the number of the Ayah
                (verse) for which Quran data is to be retrieved from the database.

        Returns:
            str: A dictionary containing two items:
            
            - "ayah_text" : The text of the ayah (verse) corresponding to the given
            number.
            - "full_text": The full Quran text, obtained by calling the `get_text()`
            method.

        """
        col_name = None
        match self.type:
            case 0:
                col_name = "page"
            case 1:
                col_name = "sura_number"
            case 2:
                col_name = "hizbQuarter"
            case 3:
                col_name = "hizb"
            case 4:
                col_name = "juz"

        assert col_name is not None, "Must set a valid type."
        query = f"""
        SELECT * FROM quran WHERE {col_name} = (
        SELECT DISTINCT {col_name} FROM quran WHERE number = ? LIMIT 1
    )
"""
        self.cursor.execute(query, (ayah_number,))

        rows = self.cursor.fetchall()
        self.data_list = [(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], None, None) for row in rows]
        self.cursor.execute(f"SELECT DISTINCT {col_name}, text FROM quran WHERE number = ?", (ayah_number,))
        ayah_result = self.cursor.fetchone()
        self.current_pos = ayah_result[0]
        self.max_pos = QuranConst.get_max(self.type)
        return {
            "ayah_text": ayah_result[1],
            "full_text": self.get_text()
        }
    
    def get_ayah_info(self, position: int) -> list:
        """
        Retrieves information about an ayah (verse) from the Quran database based
        on its position. The function queries the database for data related to the
        sura number, ayah number, sura name, and its position in the sura given
        the ayah's position.

        Args:
            position (int): Likely an index or a unique identifier representing
                the position of an Ayah (verse) in the Quran's database. It is
                used to retrieve information about a specific verse at that position.

        Returns:
            list: 4 elements long. The elements are expected to contain information
            about an Ayah's position in a Quranic Surah, specifically the Sura
            number, Ayah number, Sura name, and the Ayah's position within its Sura.

        """
        ayah_number = self.ayah_data.get(position)
        self.cursor.execute("SELECT sura_number, number, sura_name, numberInSurah FROM quran WHERE number = ?", (ayah_number,))
        return self.cursor.fetchone()

    def get_text(self):

        """
        Processes and formats Quran data from self.data_list, which is expected
        to be a list of AyahData objects. It generates formatted text with optional
        features such as ayah numbers and line breaks between verses.

        Returns:
            str: The compiled text of multiple Ayahs from the data list, formatted
            according to various configuration settings.

        """
        if not self.data_list:
            return ""

        text = ""
        current_position = 0
        ayah_data = AyahData()

        for ayah_index, ayah in enumerate(self.data_list):
            ayah_text = ayah[0]
            ayah_number = ayah[4]
            if int(ayah_number) == 1:
                start_point_text = f"{ayah[2]} {ayah[3]}\n|\n"
                ayah_text = start_point_text + ayah_text
                if  ayah[3] != 1:
                    ayah_text = ayah_text.replace("بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ ", f"بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ\n")

            if self.show_ayah_number:
                ayah_text += f" ({ayah_number})"

            if self.aya_to_line:
                ayah_text = f"{ayah_text}\n"
            else:
                ayah_text += " "

            text += ayah_text

            # Calculate the positions
            first_position = current_position
            current_position += len(ayah_text)
            last_position = current_position - 1
            ayah_data.insert(ayah[1], first_position, last_position)

        text = text.strip("\n")
        self.text = text
        self.ayah_data = ayah_data

        return text
