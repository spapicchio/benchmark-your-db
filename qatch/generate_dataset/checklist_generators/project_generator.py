import random

from qatch.connectors import ConnectorTable
from .base_generator import BaseGenerator, SingleQA
from .utils import utils_list_sample


class ProjectGenerator(BaseGenerator):
    @property
    def test_name(self):
        return 'PROJECT'

    def template_generator(self, table: ConnectorTable) -> list[SingleQA]:
        """
        Generate project-based tests in the form of queries and questions based on the input table structure.

        Given the table's structure, it generates tests that project single columns, the entire table, and
        random combinations of columns. For each type of test, specific methods are used.

        Args:
            table (ConnectorTable): The table structure based on which the tests will be generated.

        Returns:
            list[SingleQA]: A list of SingleQA dictionary objects. Each SingleQA contains a 'query', 'question',
            'sql_tag' key-value pair based on column(s) of the input table.

        """

        columns = list(table.tbl_col2metadata.keys())
        tbl_name = table.tbl_name

        select_tests = []
        select_tests += self.generate_project_single_col(columns, tbl_name)
        select_tests += self.generate_project_all_table(tbl_name)
        # select_tests += self._project_add_col(columns, tbl_name)
        select_tests += self.generate_project_random_combination_cols(columns, tbl_name)

        return select_tests

    def generate_project_all_table(self, tbl_name) -> list[SingleQA]:
        """Generates one test to check the projection of the entire table.

        This method creates a single SQL query that selects all data from a certain table, which
        is specified by the argument `tbl_name`. The question related to the query is generated
        accordingly, and a static tag `SELECT-ALL` is added to each query.

        Args:
            tbl_name (str): The name of the table in the database for which the SQL query is to be generated.

        Returns:
            list: A list containing a dict of the SQL query, question and tag. The dict uses the 'SingleQA'
                  data type, which is structured as follows:
                  {'query': string, 'question': string, 'sql_tag': string}
        """

        return [SingleQA(
            query=f'SELECT * FROM `{tbl_name}`',
            question=f"Show all the rows in the table {tbl_name}",
            sql_tag='PROJECT-ALL',
        )]

    def generate_project_single_col(self, columns, tbl_name) -> list[SingleQA]:
        """
        This method generates a list of SingleQA objects based on the provided list of columns and table name.
        SingleQA is a TypedDict that contains information needed to construct SQL queries.

        Each SingleQA will contain a SELECT query for a single column from the provided list,
        targeting the provided table. The amount of SingleQA objects generated equals to the number of
        columns or 5, whichever is less.

        Notes:
             This method uses utility function utils_list_sample() to limit the amount of queries to 5.

        Args:
            columns (Iterable[str]): A list or any iterable of column names as strings.
            tbl_name (str): The name of the table in the database.

        Returns:
            list[SingleQA]: A list of SingleQA objects. Each SingleQA object contains a single
                             SELECT SQL query, a corresponding question in natural language, and SQL tag.

        """

        output = []
        columns = utils_list_sample(columns, k=5, val=self.column_to_include)
        for col_name in columns:
            test = SingleQA(
                query=f'SELECT `{col_name}` FROM `{tbl_name}`',
                question=f'Show all {col_name} in the table {tbl_name}',
                sql_tag='PROJECT-SINGLE-COL',
            )
            output.append(test)
        return output

    def generate_project_add_col(self, columns, tbl_name) -> list[SingleQA]:
        """
        Generate a list of SingleQA instances, where each SingleQA correspond to a SQL query that selects
        incrementally added columns from the specified table. The starting point includes the first column only,
        then in each subsequent query, a new column is added.

        Args:
            columns (Iterable of str): The names of the columns from the SQL table.
            tbl_name (str): The name of the SQL table.

        Returns:
            list[SingleQA]: A list with SingleQA type instances. Each instance represents a SQL query
            that selects increasingly multiple columns from the specified table.
        """

        output = []
        for i in range(1, len(columns) - 1):
            selected_cols = columns[:i]
            query_cols = ", ".join([f'`{col}`' for col in selected_cols])
            question_cols = ", ".join([col for col in selected_cols])
            test = SingleQA(
                query=f'SELECT {query_cols} FROM `{tbl_name}`',
                question=f'Show all {question_cols} in the table {tbl_name}',
                sql_tag='PROJECT-ADD-COL',
            )
            output.append(test)
        return output

    def generate_project_random_combination_cols(self, columns, tbl_name) -> list[SingleQA]:
        """Generates a list of `SingleQA` instances with queries and questions for random combinations of columns.

        This method generates a random combination of columns to form SQL SELECT queries, which are paired
        with corresponding descriptive questions.

        The test queries generated by this method do not have a specific sequence and are intended
        for checking versatility in handling varying combinations of columns in SQL queries. Moreover, the
        number of tests is determined by the total number of columns minus one. Queries are encapsulated
        in instances of the `SingleQA` class for uniformity and ease of handling further.

        Args:
            columns (list[str]): A list of column names from which random combinations are generated.
            tbl_name (str): Name of the table from which columns are selected.

        Returns:
            list[SingleQA]: A list of `SingleQA` instances, each mapping an SQL query to a corresponding question.
        """

        # num of tests = len(columns) - 1
        output = []
        for i in range(1, len(columns)):
            random_columns = random.sample(columns, i)
            query_cols = ", ".join([f'`{col}`' for col in random_columns])
            question_cols = ", ".join([col for col in random_columns])
            test = SingleQA(
                query=f'SELECT {query_cols} FROM `{tbl_name}`',
                question=f'Show all {question_cols} in the table {tbl_name}',
                sql_tag='PROJECT-RANDOM-COL',
            )
            output.append(test)
        return output
