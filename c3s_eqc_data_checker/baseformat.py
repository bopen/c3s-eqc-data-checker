import abc
from typing import Any


class BaseFormat:
    slots = "path"

    def __init__(self, path: str) -> None:
        self.path = path

    @property
    @abc.abstractmethod
    def full_format(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def global_attrs(self) -> dict[str, Any]:
        pass
