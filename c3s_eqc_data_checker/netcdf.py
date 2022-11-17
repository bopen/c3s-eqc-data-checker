import functools
from typing import Any

import netCDF4

from . import baseformat


class NetCDF(baseformat.BaseFormat):
    @functools.cached_property
    def engine(self) -> str:
        return "netcdf4"

    @functools.cached_property
    def full_format(self) -> str:
        with netCDF4.Dataset(self.path, "r") as rootgrp:
            return str(rootgrp.data_model)

    @functools.cached_property
    def variable_attrs(self) -> dict[str, dict[str, Any]]:
        return {str(var): da.attrs for var, da in self.ds.variables.items()}

    @functools.cached_property
    def global_attrs(self) -> dict[str, Any]:
        return self.ds.attrs
