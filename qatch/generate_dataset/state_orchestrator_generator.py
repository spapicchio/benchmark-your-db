import operator
from typing import Annotated, TypedDict

from ..connectors import ConnectorTable, BaseConnector


class StateOrchestratorGenerator(TypedDict):
    connector: BaseConnector
    database: dict[str, ConnectorTable]
    generated_templates: Annotated[list, operator.add]
    column_to_include: str
    tbl_names: list[str]
