"""SQL Server in Docker, driven through sqlcmd inside the container."""

from __future__ import annotations

import re

from .docker_database import DockerDatabase

_PASSWORD = "ExamDb!Verify2026"
_DATABASE = "examdb"
_SEPARATOR = "\x1f"
_AFFECTED = re.compile(r"\((\d+) rows? affected\)")


class MssqlContainer(DockerDatabase):
    """SQL Server 2025 with an empty database ``examdb`` the dump is loaded into."""

    image = "mcr.microsoft.com/mssql/server:2025-latest"

    def _run_options(self) -> list[str]:
        return ["-e", "ACCEPT_EULA=Y", "-e", f"MSSQL_SA_PASSWORD={_PASSWORD}"]

    def _sqlcmd(self, *args: str, database: str = "master") -> list[str]:
        # -b: exit code on error, -I: QUOTED_IDENTIFIER on, -C: trust the self-signed certificate.
        return ["/opt/mssql-tools18/bin/sqlcmd", "-S", "localhost", "-U", "sa", "-P", _PASSWORD, "-C", "-b",
                "-I", "-f", "i:65001,o:65001", "-d", database, *args]

    def _is_ready(self) -> bool:
        return self._exec(self._sqlcmd("-Q", "SELECT 1")).returncode == 0

    def _prepare(self) -> None:
        self._run(f"CREATE DATABASE {_DATABASE};", database="master")

    def load_script(self, script: str) -> None:
        """Executes the complete dump; raises RuntimeError with the first error messages."""
        self._run("SET NOCOUNT ON;\n" + script)

    def query(self, sql: str) -> list[tuple[str | None, ...]]:
        """Runs a SELECT and returns its rows as text cells, None for NULL."""
        # -h -1: no header, -W: trim padding, a control character as column separator.
        output = self._run("SET NOCOUNT ON;\n" + sql, "-h", "-1", "-W", "-s", _SEPARATOR)
        rows = []
        for line in output.splitlines():
            if line == "":
                continue
            rows.append(tuple(None if cell == "NULL" else cell for cell in line.split(_SEPARATOR)))
        return rows

    def execute_dml(self, sql: str) -> int:
        """Runs DML inside a rolled-back transaction and returns the affected row count."""
        output = self._run(f"SET NOCOUNT OFF;\nBEGIN TRANSACTION;\n{sql}\n;\nROLLBACK;")
        return sum(int(n) for n in _AFFECTED.findall(output))

    def _run(self, sql: str, *args: str, database: str = _DATABASE) -> str:
        self._write_file("/tmp/run.sql", sql)
        result = self._exec(self._sqlcmd("-i", "/tmp/run.sql", *args, database=database))
        if result.returncode != 0:
            raise RuntimeError(_first_errors(result.stdout + result.stderr))
        return result.stdout


def _first_errors(output: str, limit: int = 12) -> str:
    """Keeps the first error messages; later ones are mostly follow-up errors of the first."""
    lines = [line for line in output.splitlines() if line.strip() and not _AFFECTED.fullmatch(line.strip())]
    errors = sum(1 for line in lines if line.startswith("Msg "))
    shown = "\n".join(lines[:limit])
    return shown + (f"\n... {errors} error messages in total" if len(lines) > limit else "")
