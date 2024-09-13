import pandas as pd
import pytest

from qatch.database_reader import SingleDatabase
from qatch.sql_generator.abstract_sql_generator import AbstractSqlGenerator

DB_PATH = 'test_db'
DB_NAME = 'test_database'
TABLE_NAME = 'test_table'


class ConcreteSqlGenerator(AbstractSqlGenerator):
    def sql_generate(self, table_name: str) -> dict:
        # Implement the concrete version of sql_generate for testing
        pass


class TestAbstractSqlGenerator:
    @pytest.fixture
    def sample_data(self):
        # Provide sample data for testing
        # You can customize this fixture based on your requirements
        data = {
            'column1': [1, 2, 3, 4],
            'column2': ['A', 'B', 'A', 'C'],
            'column3': [10.5, 20.3, 15.2, 18.7],
            'column4': ['A', 'B', 'A', 'C'],
            'column5': ['A', 'B', 'A', 'C'],
            'column6': [10.5, 20.3, 15.2, 18.7],
            'column7': [10.5, 20.3, 15.2, 18.7],
            'column8': ['A', 'B', 'A', 'C'],

        }
        df = pd.DataFrame(data)
        return df

    @pytest.fixture
    def mock_single_database(self, sample_data, tmp_path):
        # Setup: Create a temporary database and table for testing
        db = SingleDatabase(db_path=tmp_path, db_name=DB_NAME, tables={TABLE_NAME: sample_data})
        yield db  # Provide the fixture object
        # Teardown: Clean up the temporary database and tables after testing

    @pytest.fixture
    def sql_generator(self, mock_single_database):
        return ConcreteSqlGenerator(mock_single_database)

    def test_init(self, mock_single_database):
        generator = ConcreteSqlGenerator(mock_single_database)
        assert generator.database == mock_single_database
        assert generator.sql_generated == {"sql_tags": [], "queries": [], "questions": []}

    def test_empty_sql_generated(self, sql_generator):
        sql_generator.sql_generated = {"sql_tags": ["tag1"], "queries": ["query1"], "questions": ["question1"]}
        sql_generator.empty_sql_generated()
        assert sql_generator.sql_generated == {"sql_tags": [], "queries": [], "questions": []}

    def test_append_sql_generated(self, sql_generator):
        sql_generator.append_sql_generated(["tag1"], ["query1"], ["question1"])
        assert sql_generator.sql_generated == {"sql_tags": ["tag1"], "queries": ["query1"], "questions": ["question1"]}
        sql_generator.append_sql_generated(["tag1"], ["query1"], ["question1"])
        assert sql_generator.sql_generated == {"sql_tags": ["tag1"] * 2, "queries": ["query1"] * 2,
                                               "questions": ["question1"] * 2}

    @pytest.mark.parametrize("seed", [2023, 1, 10, 453])
    def test_sample_cat_num_cols(self, mock_single_database, seed):
        sql_generator = ConcreteSqlGenerator(mock_single_database, seed=seed)
        cat_cols_iter, num_cols_iter = [], []
        for _ in range(10):
            _, cat_cols, num_cols = sql_generator._sample_cat_num_cols(TABLE_NAME, sample=1)
            cat_cols_iter.append(cat_cols)
            num_cols_iter.append(num_cols)

        assert all([cat_cols_iter[0] == val for val in cat_cols_iter[1:]])
        assert all([num_cols_iter[0] == val for val in num_cols_iter[1:]])

    @pytest.mark.parametrize("seed", [2023, 1, 10, 453])
    def test_get_col_comb_str(self, sample_data, mock_single_database, seed):
        sql_generator = ConcreteSqlGenerator(mock_single_database, seed=seed)
        columns = sample_data.columns.tolist()
        results = [sql_generator._comb_random(columns) for _ in range(10)]
        assert all([results[0] == val for val in results[1:]])

    def test_comb_random(self, sql_generator):
        columns = ['col1', 'col2', 'col3']
        result = sql_generator._comb_random(columns)

        assert isinstance(result, list)
        assert all(isinstance(comb, list) for comb in result)
        assert all(col in columns for comb in result for col in comb)
