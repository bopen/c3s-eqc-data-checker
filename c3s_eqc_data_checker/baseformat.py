import abc
import importlib
from typing import Any, Literal

import xarray as xr


class BaseFormat:
    slots = "path"

    def __init__(self, path: str) -> None:
        self.path = path

    @property
    def chunks(self) -> Literal["auto", None]:
        return "auto" if importlib.util.find_spec("dask") else None

    @property
    @abc.abstractmethod
    def engine(self) -> str:
        pass

    @property
    def ds(self) -> xr.Dataset:
        return xr.open_dataset(self.path, chunks=self.chunks, engine=self.engine)

    @property
    @abc.abstractmethod
    def full_format(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def variable_attrs(self) -> dict[str, dict[str, Any]]:
        pass

    @property
    @abc.abstractmethod
    def global_attrs(self) -> dict[str, Any]:
        pass
