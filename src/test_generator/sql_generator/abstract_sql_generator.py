import random
from abc import ABC, abstractmethod

import pandas as pd

from ..database_reader import SingleDatabase


class AbstractSqlGenerator(ABC):
    def __init__(self, database: SingleDatabase, seed=2023):
        self.database = database
        random.seed(seed)

    @abstractmethod
    def sql_generate(self, table_name: str) -> dict[str, list]:
        """generate the sql_tags, the queries, the questions, and the answers.
        the returned table is a dictionary:
            "sql_tags": list[str],
            "queries": list[str],
            "questions": list[str],
            "answers": list[str]
         """
        raise NotImplementedError

    def _get_df_cat_num_cols(self, table_name: str, sample=None) -> tuple[pd.DataFrame, list, list]:
        """given the table name, return the categorical and numerical columns"""
        df = self.database.get_table_from_name(table_name)
        df = df.infer_objects()
        cat_cols = df.select_dtypes(include=['object']).columns.tolist()
        num_cols = df.select_dtypes(include=['float']).columns.tolist()
        num_cols += df.select_dtypes(include=['int']).columns.tolist()
        for col in cat_cols:
            df[col] = df[col].fillna("unknown")
        for col in num_cols:
            df[col] = df[col].fillna(0)
        if sample is not None:
            # sample the categorical columns
            cat_cols = random.sample(cat_cols, sample) if len(cat_cols) >= sample else cat_cols
            num_cols = random.sample(num_cols, sample) if len(num_cols) >= sample else num_cols
        return df, cat_cols, num_cols

    @staticmethod
    def _get_col_comb_str(comb: list):
        """given a comibination of columns, return a string with the columns names"""
        return ", ".join([f'"{str(c)}"' for c in comb])

    @staticmethod
    def _comb_random(columns: list[str]) -> list[list[str]]:
        """randomly select columns for each possible combinations between cols"""
        all_comb_num_cols = [num_cols for num_cols in range(1, len(columns) + 1)]
        return [random.sample(columns, k) for k in all_comb_num_cols]
