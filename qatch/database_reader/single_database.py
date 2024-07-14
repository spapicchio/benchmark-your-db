from __future__ import annotations

import contextlib
import logging
import os.path
import sqlite3

import pandas as pd


class SingleDatabase:
    """Provides a simplified interface for interacting with SQLite databases in Python.

    Note: If the database already exist, do not replace the tables

    Attributes:
        conn (sqlite3.Connection): A connection object representing the SQLite database.
        cursor (sqlite3.Cursor): A cursor object used to execute SQL commands and retrieve results.
        db_name (str): The name of the database.
        table_schemas (Dict[str, pd.DataFrame]): Table name as key, table schema as value.
            Table schema is a Pandas DataFrame with columns: cid, name, type, notnull, dflt_value, pk.
        table_names (str): The names of the tables in the database.
        db_path (str): Path to the folder which contains the SQLite file.
        db_path_sqlite (str): Path to the SQLite file.
    """

    def __init__(self, db_path: str, db_name: str,
                 tables: dict[str, pd.DataFrame] | None = None,
                 table2primary_key: dict[str, str] | None = None):
        # Get the valid directory for the database
        self.db_path = self._ensure_valid_directory(db_path, db_name)
        # Store the name of the database
        self.db_name = db_name
        # Create the final path for the SQLite database file
        self.db_path_sqlite = os.path.join(self.db_path, f'{db_name}.sqlite')
        # Get the existing table names in the database
        self.table_names = self._get_existing_table_names()
        # If there are no existing tables
        if not self.table_names:
            # If no tables dictionary is provided
            if not tables:
                raise ValueError(f"No tables provided and no database found at "
                                 f"{self.db_path_sqlite}")
            # Otherwise, set the tables in the database
            self.set_tables_in_db(tables, table2primary_key)
            # Get the table names from the provided dictionary
            self.table_names = list(tables.keys())
            # Logs that the tables are stored in the database
            logging.info(f"Tables stored in {self.db_path_sqlite}")

        # Store the dictionary mapping table names to their primary keys
        self.table2primary_key = table2primary_key
        # Get the schemas of the tables
        self.table_schemas = self._get_table_schemas()

    @contextlib.contextmanager
    def connect_cursor(self):
        with sqlite3.connect(self.db_path_sqlite) as conn:
            conn.text_factory = lambda b: b.decode(errors='ignore')
            yield conn.cursor()

    @staticmethod
    def _ensure_valid_directory(db_path: str, db_name: str) -> str:
        """Ensures the db_path/db_name exist, create if necessary"""
        if db_path in ('', '.', './'):
            db_path = os.getcwd()

        full_path = os.path.join(db_path, db_name)
        os.makedirs(full_path, exist_ok=True)
        return full_path

    def _get_table_schemas(self) -> dict[str, pd.DataFrame]:
        """Retrieve schemas for all the tables in the SQLite database"""
        with self.connect_cursor() as cursor:
            table_names = self._get_existing_table_names()
            return {tbl_name: pd.read_sql_query(f'PRAGMA table_info("{tbl_name}")', cursor.connection)
                    for tbl_name in self.table_names}

    def _get_existing_table_names(self) -> list[str]:
        """Retrieve the table name in the SQLite database"""
        with self.connect_cursor() as cursor:
            cursor.execute('SELECT name from sqlite_master where type= "table"')
            return [tbl[0] for tbl in cursor.fetchall()]

    def set_tables_in_db(self, tables: dict[str, pd.DataFrame] | None,
                         table2primary_key: dict[str, str] | None):
        """
        Sets the tables in the SQLite database represented by the given connection object.

        This method takes a dictionary of tables in which keys are table names and values are Pandas DataFrames
        representing the tables, and sets these tables in the SQLite database represented by the `conn` object.

        The optional `table2primary_key` argument can be used to set primary keys for some or all tables.
        If not provided, all tables are created without primary keys.
        If the table contains an attribute with the same name of a primary key, a foreign key relationship is created.

        Note:
            - If a table is named as 'table', the method will replace its name with 'my_table'.
            - Assume the PKs have all different names. two tables must have different PK names.

        Args:
            tables (Optional[Dict[str, pd.DataFrame]]): A dictionary of tables to set in the SQLite database.
                Keys are table names and values are corresponding Pandas DataFrames.

            table2primary_key (Optional[Dict[str, str]]): A dictionary mapping table names to primary keys.
                For example, if you want to set the primary key of table `A` to be `Key_1`, you should pass
                `table2primary_key={'A': 'Key_1'}`. Default is None.
        """
        with self.connect_cursor() as cursor:
            conn = cursor.connection
            for name, table in tables.items():
                if name == 'table':
                    name = 'my_table'
                if not table2primary_key:
                    table.to_sql(name, conn, if_exists='replace', index=False)
                else:
                    create_table_string = SingleDatabase._create_table_in_db(name, table, table2primary_key)
                    conn.cursor().execute(create_table_string)
                    table.to_sql(name, conn, if_exists='append', index=False)

    @staticmethod
    def _create_table_in_db(name, table, table2primary_key):
        """
        Returns a SQLite CREATE TABLE command as a string, constructed based on the given table name, DataFrame,
        and primary_key2table dict.

        This method first converts pandas DataFrame dtypes to SQLite data types.
        Then, a SQLite CREATE TABLE command is built step by step.
        The command includes creating simple columns, adding primary keys, and creating foreign key relationships.
        Finally, the CREATE TABLE command is returned as a string.

        Args:
             name (str): The name of the table to be created in SQLite database.
             table (pd.DataFrame): A pandas DataFrame holding the data and structure of the SQL table.
                                  The dtype of each column translated to SQLite data types.
             table2primary_key (dict): A dictionary where the keys are the names of columns of the table,
                                        and the values are the names of the tables they are primary keys to.

        Example:
            >>> import pandas as pd
            >>> from qatch.database_reader import SingleDatabase

            >>> name = 'sample_table'
            >>> table = pd.DataFrame({
            >>>    'id': [1, 2, 3],
            >>>    'name': ['Alice', 'Bob', 'Charlie'],
            >>>})
            >>>primary_key2table = {
            >>>    'sample_table_id': 'sample_table'
            >>>}
            >>>print(SingleDatabase._create_table_in_db(name,table,primary_key2table))
            >>># Outputs: CREATE TABLE `sample_table`( "id" INTEGER, "name" TEXT, PRIMARY KEY ("id") );
        """

        def convert_pandas_dtype_to_sqlite_type(type_):
            if 'int' in type_:
                return 'INTEGER'
            if 'float' in type_:
                return 'REAL'
            if 'object' in type_ or 'date' in type_:
                return 'TEXT'

        primary_key2table = {tbl_PK: tbl_name for tbl_name, tbl_PK in
                             table2primary_key.items()} if table2primary_key else None
        column2type = {k: convert_pandas_dtype_to_sqlite_type(str(table.dtypes[k]))
                       for k in table.dtypes.index}
        create_table = [f'CREATE TABLE `{name}`(']
        # add simple col
        # "Round" real,
        [create_table.append(f'"{col}" {column2type[col]},') for col in table.columns]
        # Add primary key and foreign key
        for col in table.columns:
            if col in primary_key2table:
                if name == primary_key2table[col]:
                    # PRIMARY KEY ("Round"),
                    create_table.append(f'PRIMARY KEY ("{col}"),')
                else:
                    # FOREIGN KEY (`Winning_Aircraft`) REFERENCES `aircraft`(`Aircraft_ID`),
                    create_table.append(f'FOREIGN KEY (`{col}`) REFERENCES `{primary_key2table[col]}`(`{col}`),')
        # remove last comma
        create_table[-1] = create_table[-1][:-1]
        # add closing statement
        create_table.append(');')
        return " ".join(create_table)

    def get_table_given(self, table_name: str) -> pd.DataFrame:
        """
        Retrieves a specified table from the database as a Pandas DataFrame.

        Args:
            table_name (str): The name of the table to retrieve from the database.

        Returns:
            pd.DataFrame: A Pandas DataFrame representing the specified table from the database.
        """
        with self.connect_cursor() as cursor:
            conn = cursor.connection
            return pd.read_sql_query(f"SELECT * FROM `{table_name}`", conn)

    def get_schema_given(self, table_name: str) -> pd.DataFrame:
        """
        Given the table name, returns the schema of the table.
        Table schema is a Pandas DataFrame with columns: cid, name, type, notnull, dflt_value, pk.

        Args:
            table_name (str): The name of the table to retrieve the schema from the database.

        Returns:
            pd.DataFrame: A Pandas DataFrame representing the schema of the specified table from the database.
        """
        return self.table_schemas[table_name]

    def run_query(self, query: str) -> list[list]:
        """
        Run a query on the database and return the result.

        Args:
            query (str): The SQL query to be executed on the database.
        Returns:
            list[list]: A list of lists representing the result of the SQL query.
        """
        with self.connect_cursor() as cursor:
            try:
                cursor.execute(query)
                output = cursor.fetchall()
                if not output:
                    logging.warning(f'No query result for this query: {query}')
                return output
            except sqlite3.OperationalError as e:
                logging.error(f"Error while executing query: {query}")
                logging.error(e)
                raise
