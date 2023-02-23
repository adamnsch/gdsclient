import re
import time
import warnings
from concurrent.futures import Future, ThreadPoolExecutor, wait
from typing import Any, Dict, List, Optional
from uuid import uuid4

import neo4j
from pandas import DataFrame
from tqdm.auto import tqdm

from ..error.endpoint_suggester import generate_suggestive_error_message
from ..server_version.server_version import ServerVersion
from .cypher_graph_constructor import CypherGraphConstructor
from .graph_constructor import GraphConstructor
from .query_runner import QueryRunner


class Neo4jQueryRunner(QueryRunner):
    _LOG_POLLING_INTERVAL = 0.5
    _NEO4J_DRIVER_VERSION = ServerVersion.from_string(neo4j.__version__)
    _MAX_NUM_RETRYS = 10

    def __init__(
        self, driver: neo4j.Driver, database: Optional[str] = neo4j.DEFAULT_DATABASE, auto_close: bool = False
    ):
        self._driver = driver
        self._auto_close = auto_close
        self._database = database

    def run_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
        custom_error: bool = True,
    ) -> DataFrame:
        if params is None:
            params = {}

        if database is None:
            database = self._database

        with self._driver.session(database=database) as session:
            if self._NEO4J_DRIVER_VERSION == ServerVersion(4, 4, 6):
                warnings.filterwarnings(
                    "ignore",
                    message=r"^The 'update_routing_table_timeout' config key is deprecated$",
                )

            if self._NEO4J_DRIVER_VERSION >= ServerVersion(5, 0, 0):
                warnings.filterwarnings(
                    "ignore",
                    message=r"^ssl.OP_NO_SSL\*/ssl.OP_NO_TLS\* options are deprecated$",
                )
                warnings.filterwarnings(
                    "ignore",
                    message=r"^`id` is deprecated, use `element_id` instead$",
                )

            trys = 1
            while trys < self._MAX_NUM_RETRYS:
                try:
                    result = session.run(query, params)
                    break
                except neo4j.exceptions.Neo4jError as e:
                    trys += 1

                    if self._error_retryable(e):
                        time.sleep(0.5)
                        continue

                    if custom_error:
                        self.handle_driver_exception(session, e)
                    else:
                        raise e

            # Though pandas support may be experimental in the `neo4j` package, it should always
            # be supported in the `graphdatascience` package.
            warnings.filterwarnings(
                "ignore",
                message=r"^pandas support is experimental and might be changed or removed in future versions$",
            )

            return result.to_df()

    def _error_retryable(self, e: neo4j.exceptions.Neo4jError) -> bool:
        if self._NEO4J_DRIVER_VERSION.major > 4:
            return e.is_retryable()
        else:
            return e.is_retriable()

    def run_query_with_logging(
        self, query: str, params: Optional[Dict[str, Any]] = None, database: Optional[str] = None
    ) -> DataFrame:
        if params is None:
            params = {}

        if self._server_version < ServerVersion(2, 1, 0):
            return self.run_query(query, params, database)

        if "config" in params:
            if "jobId" in params["config"]:
                job_id = params["config"]["jobId"]
            else:
                job_id = str(uuid4())
                params["config"]["jobId"] = job_id
        else:
            job_id = str(uuid4())
            params["config"] = {"jobId": job_id}

        with ThreadPoolExecutor() as executor:
            future = executor.submit(self.run_query, query, params, database)

            self._log(job_id, future, database)

            if future.exception():
                raise future.exception()  # type: ignore
            else:
                return future.result()

    def _log(self, job_id: str, future: "Future[Any]", database: Optional[str] = None) -> None:
        pbar = None

        while wait([future], timeout=self._LOG_POLLING_INTERVAL).not_done:
            try:
                progress = self.run_query(
                    f"CALL gds.beta.listProgress('{job_id}') YIELD taskName, progress", database=database
                )
            except Exception as e:
                # Do nothing if the procedure either:
                # * has not started yet,
                # * has already completed.
                if f"No task with job id `{job_id}` was found" in str(e):
                    continue
                else:
                    raise e

            progress_percent = progress["progress"][0]
            if not progress_percent == "n/a":
                task_name = progress["taskName"][0].split("|--")[-1][1:]
                pbar = pbar or tqdm(total=100, unit="%", desc=task_name)
            else:
                return

            parsed_progress = float(progress_percent[:-1])
            pbar.update(parsed_progress - pbar.n)

        if pbar:
            pbar.update(100 - pbar.n)

    def set_database(self, database: str) -> None:
        self._database = database

    def close(self) -> None:
        self._driver.close()

    def database(self) -> Optional[str]:
        return self._database

    def __del__(self) -> None:
        if self._auto_close:
            self._driver.close()

    def create_graph_constructor(
        self, graph_name: str, concurrency: int, undirected_relationship_types: Optional[List[str]]
    ) -> GraphConstructor:
        return CypherGraphConstructor(
            self, graph_name, concurrency, undirected_relationship_types, self._server_version
        )

    def set_server_version(self, server_version: ServerVersion) -> None:
        self._server_version = server_version

    @staticmethod
    def handle_driver_exception(session: neo4j.Session, e: Exception) -> None:
        reg_gds_hit = re.search(
            r"There is no procedure with the name `(gds(?:\.\w+)+)` registered for this database instance",
            str(e),
        )
        if not reg_gds_hit:
            raise e

        requested_endpoint = reg_gds_hit.group(1)

        list_result = session.run("CALL gds.list() YIELD name")
        all_endpoints = list_result.to_df()["name"].tolist()

        raise SyntaxError(generate_suggestive_error_message(requested_endpoint, all_endpoints)) from e
