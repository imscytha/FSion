import io
from abc import ABC, abstractmethod
from collections.abc import Iterator
from enum import Flag, auto
from typing import Literal

from fsion.models.drive import GoogleDriveEntry


class ListFlags(Flag):
    NONE = auto()

    ONLY_FILES = auto()
    ONLY_DIRS = auto()

    SORT_TIME = auto()
    SORT_TIME_DESC = auto()
    SORT_NAME = auto()
    SORT_NAME_DESC = auto()

    PRINT_TO_STDOUT = auto()


class ReadFlags(Flag):
    NONE = auto()
    SHOW_PROGRESS = auto()


class Filesystem(ABC):
    @abstractmethod
    def traverse(
        self,
        root: str | None = None,
        mode: Literal["bfs", "dfs"] = "dfs",
        max_depth: int | None = None,
    ) -> Iterator[GoogleDriveEntry]:
        raise NotImplementedError

    @abstractmethod
    def ls(
        self,
        dir: str | None = None,
        flags: ListFlags = ListFlags.NONE,
    ) -> list[GoogleDriveEntry]:
        raise NotImplementedError

    @abstractmethod
    def read(
        self,
        file: str,
        flags: ReadFlags = ReadFlags.NONE,
    ) -> io.BytesIO | None:
        raise NotImplementedError
