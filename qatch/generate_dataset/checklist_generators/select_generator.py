import random

from qatch.connectors import ConnectorTable, ConnectorTableColumn
from .base_generator import BaseGenerator, SingleQA
from .utils import utils_list_sample


class SelectGenerator(BaseGenerator):
    @property
    def test_name(self):
        return 'SELECT'

    def template_generator(self, table: ConnectorTable) -> list[SingleQA]:
        """
        Generate a list of SingleQA (queries and questions) for a given table.

        The method generates SingleQA instances for categorical and numerical columns
        of a table using the `generate_where_cat` and `generate_where_num` methods respectively.
        The output list is the aggregation of these two sets of tests.

        Args:
            table (ConnectorTable): A ConnectorTable instance for which the tests need to be generated.

        Returns:
            list[SingleQA]: A list of SingleQA instances which contain queries, questions and sql_tags generated
             for the input `table`.
        """

        table_name = table.tbl_name
        tests = self.generate_where_cat(table.cat_col2metadata, table_name)
        tests += self.generate_where_num(table.num_col2metadata, table_name)
        return tests

    def generate_where_cat(self, cat_cols: dict[str, ConnectorTableColumn], table_name: str) -> list[SingleQA]:
        """
        Generates a set of SQL query tests based on a provided dictionary of categories.

        Each test queries a specific category column from the given table and compares a randomly chosen element
        with predefined operation types (equal to, different from, not equal to). It returns a list of SingleQA
        objects, each representing an individual query test.

        Args:
            cat_cols (dict[str, ConnectorTableColumn]): A dictionary that maps category column names to their metadata.
            table_name (str): The name of the table to query against.

        Returns:
            list[SingleQA]: A list of SingleQA objects representing the generated query tests.

        Notes:
            - The number of tests generated is equal to the product of the number of category columns and
            the number of operations (3 in this case).

            - The function uses a utility named 'utils_list_sample' to randomly sample 3 columns from provided cat_cols.
        """
        # num of tests = len(cat_cols) x len(operations)
        operations = [
            ('==', 'is equal to'),
            ('!=', 'is different from'),
            ('!=', 'not equal to'),
        ]

        cat_cols_name = utils_list_sample(list(cat_cols.keys()), k=3, val=self.column_to_include)

        tests = []
        for cat_col in cat_cols_name:
            metadata = cat_cols[cat_col]
            for operation in operations:
                sample_element = random.choice(metadata.sample_data)
                single_test = SingleQA(
                    query=f"""SELECT * FROM `{table_name}` WHERE `{cat_col}` {operation[0]} '{sample_element}'""",
                    question=f'Show the data of the table {table_name} where {cat_col} {operation[1]} {sample_element}',
                    sql_tag=f'SELECT-CAT',
                )
                tests.append(single_test)
        return tests

    def generate_where_num(self, num_cols: dict[str, ConnectorTableColumn], table_name: str) -> list[SingleQA]:
        """
        Generate a collection of SingleQA objects showcasing 'greater than' and 'less than' comparisons
        with numerical data from columns of a specific table.

        Args:
            num_cols (dict[str, ConnectorTableColumn]): A dictionary mapping column names from a table to
            ConnectorTableColumn objects containing metadata about the columns. Only columns with numerical
            data type are included.

            table_name (str): The name of the table from which the columns are taken.

        Returns:
            list[SingleQA]: A list of SingleQA objects. Each SingleQA contains a 'query', 'question' and 'sql_tag'.
            The 'query' is a string of SQL SELECT statement, the 'question' is a formatted string explaining which
            data is being requested by the query, and the 'sql_tag' is a string identifying the type of the SQL
            operation being performed.

        Note:
            - The function does NOT handle 'id' columns for the comparison.
            - The function automatically picks 3 columns at random from num_cols for the comparison.
        """

        # num of tests = len(num_cols) x len(operations)
        operations = [
            ('>', 'is greater than'),
            ('<', 'is less than'),
        ]
        num_cols_name = utils_list_sample(list(num_cols.keys()), k=3, val=self.column_to_include)

        num_cols = {col: num_cols[col] for col in num_cols_name if 'id' not in col.lower()}

        tests = []
        for num_col, metadata in num_cols.items():
            for operation in operations:
                sample_element = random.choice(metadata.sample_data)
                single_test = SingleQA(
                    query=f'SELECT * FROM `{table_name}` WHERE `{num_col}` {operation[0]} {sample_element}',
                    question=f'Show the data of the table {table_name} where {num_col} {operation[1]} {sample_element}',
                    sql_tag=f'SELECT-NUM',
                )
                tests.append(single_test)
        return tests
