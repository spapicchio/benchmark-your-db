from __future__ import annotations

import logging

import pandas as pd
from langgraph.constants import START, END
from langgraph.graph import StateGraph

from .checklist_generators import (
    ProjectGenerator,
    SelectGenerator,
    DistinctGenerator,
    SimpleAggGenerator,
    OrderByGenerator,
    GrouByGenerator,
    HavingGenerator,
    JoinGenerator,
    ManyToManyGenerator

)
from .state_orchestrator_generator import StateOrchestratorGenerator
from ..connectors import BaseConnector

name2generator = {
    'project': ProjectGenerator,
    'distinct': DistinctGenerator,
    'select': SelectGenerator,
    'simple': SimpleAggGenerator,
    'orderby': OrderByGenerator,
    'groupby': GrouByGenerator,
    'having': HavingGenerator,
    'join': JoinGenerator,
    'many-to-many': ManyToManyGenerator,
}


class OrchestratorGenerator:
    """
    Initializes an OrchestratorGenerator object with a list of generator names or
    defaults to all available generator names.

    Args:
        generator_names (list[str] | None): A list of generator names or None to use all available generator names
        if not provided.

    Attributes:
        graph: Compiled StateGraph object containing node functions added from the generator names.

    Methods:
        - generate_dataset(connector: BaseConnector) -> pd.DataFrame:
            Generates a dataset from the database connected by the given connector.
            Loads tables from the database, invokes the graph with the loaded database and connector,
            converts the state's `generated_templates` into a pandas DataFrame.
            Returns a DataFrame with columns 'db_path', 'db_id', 'tbl_name', 'test_category',
             'sql_tag', 'query', 'question'.
            Logs a warning if no dataset can be generated from the connector's database.
    """

    def __init__(self, generator_names: list[str] | None = None):
        graph = StateGraph(StateOrchestratorGenerator)

        generator_names = generator_names or list(name2generator.keys())

        list_node_fun = [
            (name, name2generator[name]().graph_call)
            for name in generator_names
        ]

        for node_name, node_fun in list_node_fun:
            graph.add_node(node_name, node_fun)
            graph.add_edge(START, node_name)
            graph.add_edge(node_name, END)

        self.graph = graph.compile()

    def generate_dataset(self, connector: BaseConnector, tbl_names: list[str] | None = None,
                         column_to_include: str | None = None) -> pd.DataFrame:
        """
        Generates a dataset from the database connected by the given connector.

        This method will load the tables from the database connected by the connector.
        Then, it invokes the graph with the loaded database and connector. Takes the `generated_templates`
        from the state and convert it into a pandas DataFrame. The final DataFrame consists of
        columns 'db_path', 'db_id', 'tbl_name', 'test_category', 'sql_tag', 'query', 'question'
        If no dataset can be generated from the connector's database, a warning is logged.

        Args:
            connector (BaseConnector): An instance of BaseConnector subclass which
            contains database access configurations.
            tbl_names: A list of table names to generate tests for. If None, all tables in the database will be used.
            column_to_include (str): If the column is present in the table, it will be selected in the generation

        Returns:
            pd.DataFrame: The DataFrame created from the `generated_templates` in the state
            containing only specific columns 'db_path', 'db_id', 'tbl_name', 'test_category',
            'sql_tag', 'query', 'question' if any data exists.
            Otherwise, it will be an empty DataFrame.

        Note:
            This could lead to an empty DataFrame if no tests could be generated from the
            database of the provided connector.
            In that case, a warning message will be logged specifying the 'db_path'.
        """

        database = connector.load_tables_from_database()
        tbl_names = tbl_names or list(database.keys())
        state = self.graph.invoke(
            {'database': database,
             'connector': connector,
             'column_to_include': column_to_include,
             'tbl_names': tbl_names})
        dataset = state['generated_templates']
        dataset = pd.DataFrame(dataset)
        if len(dataset) > 0:
            dataset = dataset.loc[:, ['db_path', 'db_id', 'tbl_name', 'test_category', 'sql_tag', 'query', 'question']]
        else:
            logging.warning(f'QATCH not able to generate tests from {connector.db_path}')
        return dataset
