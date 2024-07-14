from __future__ import annotations

import pandas as pd
from tqdm import tqdm

from .database_reader import MultipleDatabases
from .sql_generator import (SelectGenerator,
                            OrderByGenerator,
                            DistinctGenerator,
                            WhereGenerator,
                            GroupByGenerator,
                            HavingGenerator,
                            SimpleAggGenerator,
                            NullGenerator,
                            JoinGenerator)


class TestGenerator:
    """
    The interface to connect the MultipleDatabase with the SQL generators.
    Use this class to generate queries and questions from the databases.

    Attributes:
        databases (MultipleDatabases): The MultipleDatabases object representing the database connections.
    """

    def __init__(self, databases: MultipleDatabases):
        self.databases = databases

        self._generators = {'select': SelectGenerator,
                            'orderby': OrderByGenerator,
                            'distinct': DistinctGenerator,
                            'where': WhereGenerator,
                            'groupby': GroupByGenerator,
                            'having': HavingGenerator,
                            'simpleAgg': SimpleAggGenerator,
                            'nullCount': NullGenerator,
                            'join': JoinGenerator}

    def generate(self,
                 generators: list[str] | str | None = None,
                 db_names: str | list[str] | None = None,
                 seed=2023
                 ) -> pd.DataFrame:
        """
        Generate test queries and questions for specified generators and databases.

        Args:
            generators (list[str] | str | None): Optional. A list of generator names to be used.
                                                  Default is to use all available generators
                                                  ['select', 'orderby', 'distinct', 'where', 'groupby',
                                                   'having', 'simpleAgg', 'nullCount'].
            db_names (str | list[str] | None): Optional. The name or list of names of databases to generate tests for.
                                                Default is to use all available databases.
            seed (int): Optional. Seed value for randomization. Default is 2023.

        Returns:
            pd.DataFrame: A DataFrame containing generated test queries, questions, and related information.

        Examples:
            Given a MultipleDatabases object "database", with three databases 'sakila', 'world', and 'employees'
            >>> generator = TestGenerator(databases)
            >>> tests_df = generator.generate(generators=['select', 'orderby'], db_names=['sakila', 'world'])
            generate tests only for select and orderby generators, and only for sakila and world databases
        """
        # TODO possible change of the db_name, add dictionary to specify also the tbl_names
        generators, db_names, = self._init_params(generators, db_names)

        tests_df_list = []
        for db_name in tqdm(db_names, desc='Generating test for each database'):
            # for each db_name
            for generator_name in generators:
                # init generator
                db = self.databases[db_name]
                generator = self._generators[generator_name](db, seed)
                for tbl in db.table_names:
                    sql_generated = generator.sql_generate(tbl)
                    df = self._build_df(db_name, tbl, sql_generated)
                    df['sql_generator'] = generator_name.upper()
                    tests_df_list.append(df)

        tests_df = pd.concat(tests_df_list, ignore_index=True)
        return tests_df

    def _init_params(self, generators: list[str] | str | None,
                     db_names: str | list[str] | None) -> tuple[list[str], list[str]]:
        """
        Validate and initialize generator names and database names.

        Args:
            generators (list[str] | str | None): The list of generator names or a single generator name.
            db_names (str | list[str] | None): The name or list of names of databases to generate tests for.

        Returns:
            tuple[list[str], list[str]]: Validated generator names and database names.
        """
        # generators check
        if generators is None:
            generators = list(self._generators.keys())
        else:
            if isinstance(generators, str):
                generators = [generators]
            for generator in generators:
                if generator not in self._generators.keys():
                    raise KeyError(f'Generators must be one of {list(self._generators.keys())}')

        # db_names check
        available_dbs = self.databases.get_db_names()
        if db_names is None:
            db_names = available_dbs
        else:
            if isinstance(db_names, str):
                db_names = [db_names]
            for db_name in db_names:
                if db_name not in available_dbs:
                    raise KeyError(f'Database name "{db_name}" must be one of {available_dbs}')
        return generators, db_names

    @staticmethod
    def _build_df(db_name: str, tbl_name: str, sql_generated: dict[str, list]) -> pd.DataFrame:
        """
        Build a DataFrame from generated SQL queries, questions, and related information.

        Args:
            db_name (str): The name of the database.
            tbl_name (str): The name of the table in the database.
            sql_generated (dict[str, list]): A dictionary containing generated SQL tags, queries, and questions.

        Returns:
            pd.DataFrame: A DataFrame containing generated test queries, questions, and related information.
        """

        sql_tags = sql_generated['sql_tags']
        queries = sql_generated['queries']
        questions = sql_generated['questions']
        return pd.DataFrame({
            'db_id': [db_name] * len(sql_tags),
            'tbl_name': [tbl_name] * len(sql_tags),
            'sql_tags': sql_tags,
            'query': queries,
            'question': questions
        })
