"""Short-lived database server in a Docker container."""

from __future__ import annotations

import subprocess
import time
import uuid
from abc import ABC, abstractmethod
from types import TracebackType


class DockerDatabase(ABC):
    """Starts a throwaway container on enter and removes it on exit.

    SQL is handed over as a UTF-8 file inside the container instead of a command-line
    argument; this avoids quoting and code page problems of the host shell.
    """

    image: str = ""
    startup_timeout_seconds: int = 180

    def __init__(self) -> None:
        self.container = f"examdb-verify-{uuid.uuid4().hex[:8]}"

    def __enter__(self) -> DockerDatabase:
        self._docker("run", "-d", "--name", self.container, *self._run_options(), self.image)
        try:
            self._wait_until_ready()
            self._prepare()
        except BaseException:
            self._remove()
            raise
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None,
                 tb: TracebackType | None) -> None:
        self._remove()

    @abstractmethod
    def _run_options(self) -> list[str]:
        """Options for ``docker run`` such as environment variables."""

    @abstractmethod
    def _is_ready(self) -> bool:
        """True once the server accepts queries."""

    def _prepare(self) -> None:
        """Creates whatever the dump expects to exist (e.g. a database)."""

    def _wait_until_ready(self) -> None:
        deadline = time.monotonic() + self.startup_timeout_seconds
        while not self._is_ready():
            if time.monotonic() > deadline:
                logs = self._docker("logs", "--tail", "20", self.container, check=False).stdout
                raise RuntimeError(f"{self.image} did not start within {self.startup_timeout_seconds}s:\n{logs}")
            time.sleep(1)

    def _write_file(self, path: str, content: str) -> None:
        subprocess.run(["docker", "exec", "-i", self.container, "sh", "-c", f"cat > {path}"],
                       input=content.encode("utf-8"), check=True, capture_output=True)

    def _exec(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        """Runs a command inside the container and decodes its output as UTF-8."""
        result = subprocess.run(["docker", "exec", self.container, *args], capture_output=True)
        return subprocess.CompletedProcess(result.args, result.returncode,
                                           result.stdout.decode("utf-8", errors="replace"),
                                           result.stderr.decode("utf-8", errors="replace"))

    def _docker(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(["docker", *args], capture_output=True, text=True, encoding="utf-8",
                                errors="replace")
        if check and result.returncode != 0:
            raise RuntimeError(f"docker {' '.join(args[:2])} failed: {result.stderr.strip()}")
        return result

    def _remove(self) -> None:
        self._docker("rm", "-f", "-v", self.container, check=False)
