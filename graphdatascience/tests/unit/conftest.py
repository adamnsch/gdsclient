from typing import Any, Dict, List

import pandas
import pytest
from pandas.core.frame import DataFrame

from graphdatascience import QueryRunner
from graphdatascience.graph_data_science import GraphDataScience


class CollectingQueryRunner(QueryRunner):
    def __init__(self) -> None:
        self.queries: List[str] = []
        self.params: List[Dict[str, Any]] = []

    def run_query(self, query: str, params: Dict[str, Any] = {}) -> DataFrame:
        self.queries.append(query)
        self.params.append(params)

        return pandas.DataFrame([{"version": "2.0.0"}])

    def last_query(self) -> str:
        return self.queries[-1]

    def last_params(self) -> Dict[str, Any]:
        return self.params[-1]

    def set_database(self, _: str) -> None:
        pass


@pytest.fixture(scope="package")
def runner() -> CollectingQueryRunner:
    return CollectingQueryRunner()


@pytest.fixture(scope="package")
def gds(runner: CollectingQueryRunner) -> GraphDataScience:
    return GraphDataScience(runner)
