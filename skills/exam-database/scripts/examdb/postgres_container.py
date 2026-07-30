"""PostgreSQL in Docker, driven through psql inside the container."""

from __future__ import annotations

import csv
import io
import re

from .docker_database import DockerDatabase

_PASSWORD = "examdb"
_NULL = "<<NULL>>"
_COMMAND_TAG = re.compile(r"^(?:INSERT \d+|UPDATE|DELETE) (\d+)$", re.MULTILINE)


class PostgresContainer(DockerDatabase):
    """PostgreSQL (latest image); the dump is loaded into the default database."""

    image = "postgres"

    def _run_options(self) -> list[str]:
        return ["-e", f"POSTGRES_PASSWORD={_PASSWORD}"]

    def _psql(self, *args: str) -> list[str]:
        # TCP instead of the socket: the init phase runs a temporary server that only
        # listens on the socket and restarts afterwards.
        return ["env", f"PGPASSWORD={_PASSWORD}", "psql", "-h", "127.0.0.1", "-U", "postgres", "-d", "postgres",
                "-X", "-v", "ON_ERROR_STOP=1", *args]

    def _is_ready(self) -> bool:
        return self._exec(self._psql("-c", "SELECT 1")).returncode == 0

    def load_script(self, script: str) -> None:
        """Executes the complete dump; raises RuntimeError with the first error messages."""
        self._run(script, "-q")

    def query(self, sql: str) -> list[tuple[str | None, ...]]:
        """Runs a SELECT and returns its rows as text cells, None for NULL."""
        output = self._run(sql, "-q", "--csv", "-t", "-P", f"null={_NULL}")
        rows = []
        for record in csv.reader(io.StringIO(output)):
            # psql prints booleans as t/f; normalize to the 1/0 of SQLite and SQL Server.
            rows.append(tuple(None if c == _NULL else {"t": "1", "f": "0"}.get(c, c) for c in record))
        return rows

    def execute_dml(self, sql: str) -> int:
        """Runs DML inside a rolled-back transaction and returns the affected row count."""
        output = self._run(f"BEGIN;\n{sql}\n;\nROLLBACK;")
        return sum(int(n) for n in _COMMAND_TAG.findall(output))

    def _run(self, sql: str, *args: str) -> str:
        self._write_file("/tmp/run.sql", sql)
        result = self._exec(self._psql(*args, "-f", "/tmp/run.sql"))
        if result.returncode != 0:
            raise RuntimeError((result.stderr or result.stdout).strip())
        return result.stdout
