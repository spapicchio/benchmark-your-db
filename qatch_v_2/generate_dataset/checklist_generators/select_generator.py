import random

from .base_generator import BaseGenerator, SingleQA
from .utils import utils_list_sample
from qatch_v_2.connectors import ConnectorTable


class SelectGenerator(BaseGenerator):
    @property
    def test_name(self):
        return 'SELECT'

    def template_generator(self, table: ConnectorTable) -> list[SingleQA]:
        table_name = table.tbl_name
        tests = []
        tests += self.test_where_cat(table.cat_col2metadata, table_name)
        tests += self.test_where_num(table.num_col2metadata, table_name)

        return tests

    def test_where_cat(self, cat_cols, table_name) -> list[SingleQA]:
        # num of tests = len(cat_cols) x len(operations)
        operations = [
            ('==', 'is equal to'),
            ('!=', 'is different from'),
            ('!=', 'not equal to'),
        ]

        cat_cols = utils_list_sample(cat_cols, k=3)

        tests = []
        for cat_col, metadata in cat_cols.items():
            for operation in operations:
                sample_element = random.choice(metadata.sample_data)
                single_test = SingleQA(
                    query=f"""SELECT * FROM `{table_name}` WHERE `{cat_col}` {operation[0]} '{sample_element}'""",
                    question=f'Show the data of the table {table_name} where {cat_col} {operation[1]} {sample_element}',
                    sql_tag=f'WHERE-CAT',
                )
                tests.append(single_test)
        return tests

    def test_where_num(self, num_cols, table_name) -> list[SingleQA]:
        # num of tests = len(num_cols) x len(operations)
        operations = [
            ('>', 'is greater than'),
            ('<', 'is less than'),
        ]
        num_cols_name = utils_list_sample(num_cols.keys(), k=3)

        num_cols = {col: num_cols[col] for col in num_cols_name if 'id' not in col.lower()}

        tests = []
        for num_col, metadata in num_cols.items():
            for operation in operations:
                sample_element = random.choice(metadata.sample_data)
                single_test = SingleQA(
                    query=f'SELECT * FROM `{table_name}` WHERE `{num_col}` {operation[0]} {sample_element}',
                    question=f'Show the data of the table {table_name} where {num_col} {operation[1]} {sample_element}',
                    sql_tag=f'WHERE-NUM',
                )
                tests.append(single_test)
        return tests