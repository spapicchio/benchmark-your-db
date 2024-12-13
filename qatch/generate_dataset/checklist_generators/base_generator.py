import random
from abc import ABC, abstractmethod
from itertools import chain
from typing import TypedDict, Literal

from sqlalchemy.exc import OperationalError

from qatch.connectors import ConnectorTable
from ..state_orchestrator_generator import StateOrchestratorGenerator


class SingleQA(TypedDict):
    query: str
    question: str
    sql_tag: str


class BaseTest(SingleQA):
    db_id: str
    db_path: str
    tbl_name: str
    test_category: str


class BaseGenerator(ABC):
    """
    A Base class for all types of generators. This class provides the basic skeleton for a template
    generator.
    """

    def __init__(self, seed=2023):
        random.seed(seed)
        self.connector = None
        self.column_to_include = None  # column to include in the generation if present

    @property
    @abstractmethod
    def test_name(self):
        """This name represent the test_category in the output"""
        raise NotImplementedError

    @abstractmethod
    def template_generator(self, table: ConnectorTable) -> list[SingleQA]:
        """
       An abstract method that should be implemented in each subclass of the `BaseGenerator` class.

       The goal of this method is to generate templates which are in the form of `SingleQA` type.
       These templates contain multiple parts including a query, question, and sql tag,
       which are built using the `ConnectorTable` parameter.

       Args:
           table (ConnectorTable): A ConnectorTable class object that holds information about a
           specific table within a database, such as its name, columns, primary and foreign keys,
           and related metadata.

       Returns:
           list[SingleQA]: A list of `SingleQA` objects. Each `SingleQA` contains a string 'query' that
           represents a SQL query, a string 'question' which is a natural language representation of
           the query, and a 'sql_tag' that depicts the type of SQL query (e.g., select, union, intersect etc.)

       Note:
            This method must be overridden in each subclass of the `BaseGenerator` class. The specific
            implementation would depend on how one intends to generate templates based on the information
            provided in the `ConnectorTable` object.
       """
        raise NotImplementedError

    def graph_call(self, state: StateOrchestratorGenerator) -> dict[Literal['generated_templates']: list[BaseTest]]:
        """
        Processes the state of the Orchestrator Generator and generates tests based on the database tables and tests.

        This method goes through each table in the database, generates templates, creates base tests,
        flattens the tests for each table, and removes any tests with empty results.

        Args:
            state (StateOrchestratorGenerator): The input state object for the Orchestrator Generator that contains connector,
            database, and generated templates.

        Returns:
            dict[Literal['generated_templates']: list[BaseTest]]: A dictionary containing the final list of generated tests.
            The dictionary has a single key, 'generated_templates', and the value associated is the list of generated tests.

        Note:
            - The argument `state` must be an instance of StateOrchestratorGenerator.
            - If a table in the database does not yield any test results, those tests are removed.
            - This is the function used by the LangGraph object during its execution
        """
        database = state['database']
        self.column_to_include = state['column_to_include'] if 'column_to_include' in state else None
        connector = self.connector = state['connector']
        tbl_names = state['tbl_names']
        table_tests = []
        for tbl_name in tbl_names:
            table = database[tbl_name]
            if not self._is_table_empty(table):
                tests = self.template_generator(table)

                tests = [self._create_base_test(table, test) for test in tests]

                table_tests.append(tests)
        # flatten the table tests
        table_tests = list(chain.from_iterable(table_tests))

        # remove empty tests
        table_tests = self._remove_test_with_empty_results_or_errors(table_tests, connector)

        return {'generated_templates': table_tests}

    def _create_base_test(self, table, test: SingleQA) -> BaseTest:
        return BaseTest(
            **test,
            db_id=table.db_name,
            db_path=table.db_path,
            tbl_name=table.tbl_name,
            test_category=self.test_name
        )

    def _remove_test_with_empty_results_or_errors(self, tests: list[SingleQA], connector) -> list[SingleQA]:
        new_tests = []
        for test in tests:
            try:
                result = connector.run_query(test['query'])
                if len(result) > 0:
                    new_tests.append(test)
            except OperationalError:
                continue

        return new_tests

    def _is_table_empty(self, table: ConnectorTable) -> bool:
        return len(self.connector.run_query(f'SELECT * FROM `{table.tbl_name}` LIMIT 1')) == 0
