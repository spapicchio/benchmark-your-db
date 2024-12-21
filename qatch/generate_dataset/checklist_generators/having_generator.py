from qatch.connectors import ConnectorTable
from .base_generator import BaseGenerator, SingleQA
from .utils import utils_list_sample


class HavingGenerator(BaseGenerator):
    @property
    def test_name(self):
        return 'HAVING'

    def template_generator(self, table: ConnectorTable) -> list[SingleQA]:
        """
        Generates test templates by leveraging having statements with count and aggregate operations
        on categorical and numerical columns of the input table, respectively.

        Args:
            table (ConnectorTable): An instance of 'ConnectorTable' class which includes properties related to a
            defined table.

        Returns:
            list[SingleQA]: A list of Q&A pairs generated based on the input table where each instance
            of 'SingleQA' represents a query, a question and a corresponding SQL tag.

        Note:
            - The function is depending on `generate_having_count_cat` and `generate_having_agg_num` methods
            to generate Q&A pairs for categorical and numerical columns.
            - Additional steps are performed to
            avoid running statistical operations over id like fields in the table.
            - Max number of tests: 16 + 6 = 22
        """

        table_name = table.tbl_name
        tests = []
        cat_cols = list(table.cat_col2metadata.keys())
        num_cols = list(table.num_col2metadata.keys())
        tests += self.generate_having_count_cat(cat_cols, table_name)
        tests += self.generate_having_agg_num(cat_cols, num_cols, table_name)
        return tests

    def generate_having_count_cat(self, cat_cols: list[str], table_name: str) -> list[SingleQA]:
        """
        Generates tests for SQL queries that group results by category, and return groups that have a certain count.

        The method samples the category columns and for each of them, it constructs a SQL query
        that groups records by that column and filters groups by their count with an HAVING clause.
        'SingleQA' objects are created for each test and added to the tests list which is then returned.

        Args:
            cat_cols (list[str]): A list of string, where each string is the name of a categorical column.
            table_name (str): Name of the table to perform the operations on.

        Returns:
            list[SingleQA]: A list of 'SingleQA' objects representing tests for SQL queries.

        Note:
            - This function relies on a private helper method
              `_get_average_of_count_cat_col` to calculate the average count
              of records for each category column.
            - Three categorical columns are sampled to avoid explosion
            - The maximum number of tests: len(cat_cols) x len(operations) = 3 x 2 = 6
        """

        # num tests = len(cat_cols) x len(operations)
        cat_cols = utils_list_sample(cat_cols, k=3, val=self.column_to_include)

        operations = [
            ('>=', 'at least'),
            ('<=', 'at most'),
        ]
        tests = []

        for cat_col in cat_cols:
            average_count = self._get_average_of_count_cat_col(table_name, cat_col)
            for op in operations:
                single_test = SingleQA(
                    query=f"SELECT `{cat_col}` FROM `{table_name}` GROUP BY `{cat_col}`"
                          f" HAVING count(*) {op[0]} {average_count}",
                    question=f'Find all the {cat_col} that have {op[1]} {average_count} records in table {table_name}',
                    sql_tag=f'HAVING-COUNT',
                )
                tests.append(single_test)
        return tests

    def generate_having_agg_num(self, cat_cols: list[str], num_cols: list[str], table_name: str):
        """
        Constructs a list of SingleQA objects for SQL aggregate tests (avg, sum) with 'having' clause.

        This function generates SQL queries with a 'having' clause that tests aggregate functions
        (i.e., 'avg' and 'sum') on numerical columns. The clauses are constructed such that
        the aggregate value is compared against the average of those aggregate values for each category.

        Note:
        - Only two items are randomly sampled from both 'cat_cols' and 'num_cols' to avoid explosion.
        - Columns considered for aggregation are filtered to remove ID related columns.
        - Max number of tests generated = len(cat_cols_sampled) * len(num_cols_sampled) * len(operations) * len(symbols)
          = 2 x 2 x 2 x 2 = 16


        Args:
            cat_cols (List[str]): List of categorical column names to be used in group by clause.
            num_cols (List[str]): List of numerical column names to be used in aggregate functions.
            table_name (str): Name of the table on which queries will be generated.

        Returns:
            List[SingleQA]: Returns a list of SingleQA objects, each representing a test case for SQL 'having'
            clause with aggregate functions.
        """

        # num tests = len(cat_cols) x len(num_cols) x len(operations) x len(symbols)
        cat_cols = utils_list_sample(cat_cols, k=2, val=self.column_to_include)
        num_cols = utils_list_sample(num_cols, k=2, val=self.column_to_include)

        tests = []
        operations = [
            ('AVG', 'average'),
            ('SUM', 'summation'),
        ]
        symbols = [
            (">=", "at least"),
            ("<=", "at most"),
        ]

        # remove num_cols with ID. No sense to calculate sum/avg over ids
        num_cols = [col for col in num_cols if 'id' not in col.lower()]

        for cat_col in cat_cols:
            for num_col in num_cols:
                mean_mean_sum, mean_mean_mean = self._get_average_of_sum_avg_cat_col(table_name, cat_col, num_col)
                for op in operations:
                    for symbol in symbols:
                        value = mean_mean_mean if op[0] == 'AVG' else mean_mean_sum
                        single_test = SingleQA(
                            query=f'SELECT `{cat_col}` FROM `{table_name}`'
                                  f' GROUP BY `{cat_col}` HAVING {op[0]}(`{num_col}`) {symbol[0]} {value}',
                            question=f'List the {cat_col} which {op[1]} of {num_col} '
                                     f'is {symbol[1]} {value} in table {table_name}',
                            sql_tag=f'HAVING-AGG-{op[0]}',
                        )
                        tests.append(single_test)
        return tests

    def _get_average_of_count_cat_col(self, table_name: str, cat_col: list[str]) -> int:
        """
        Helper method to calculate the average count of rows for each category in a categorical column.

        Args:
            table_name (str): The name of the table in the database.
            cat_col (str): The name of the categorical column.

        Returns:
            int: The average count of rows for each category.
        """
        # SQL query to get the average count for each category
        inner_query = f'SELECT COUNT(*) AS row_count FROM `{table_name}` GROUP BY `{cat_col}`'
        # Run the inner query and get the average of row counts
        average = self.connector.run_query(f'SELECT AVG(row_count) FROM ({inner_query})')[0][0]
        return int(average)

    def _get_average_of_sum_avg_cat_col(self, table_name: str, cat_col: list[str], num_col: list[str]
                                        ) -> tuple[float, float]:
        """
        This method calculates the average sum and average of a specified numerical column for each category in a
        specified categorical column. It presents these results as a tuple.

        Note: The calculations are based on SQL queries and are run on the provided table in which the specific
        categorical and numerical columns are located.

        Args:
            table_name (str): Name of the table in the database where calculations are to be performed.
            cat_col (str): Name of the categorical column in the specified table.
            num_col (str): Name of the numerical column in the specified table.

        Returns:
            tuple: A tuple of two float values. The first value represents the average sum of the numerical column
            for each category in the categorical column. The second value represents the average of the numerical
            column for each category in the categorical column. Both values are rounded to 2 decimal places.
        """
        # SQL queries to get the average sum and average of numerical column for each category
        inner_query_sum = f'SELECT SUM(`{num_col}`) AS sum_col FROM `{table_name}` GROUP BY `{cat_col}`'
        inner_query_avg = f'SELECT AVG(`{num_col}`) AS avg_col FROM `{table_name}` GROUP BY `{cat_col}`'
        # Run the inner queries and get the average of sums and averages
        average_sum = self.connector.run_query(f'SELECT AVG(sum_col) FROM ({inner_query_sum})')[0][0]
        average_avg = self.connector.run_query(f'SELECT AVG(avg_col) FROM ({inner_query_avg})')[0][0]
        return round(average_sum, 2), round(average_avg, 2)
