from typing import Any

import netCDF4

from . import baseformat


class NetCDF(baseformat.BaseFormat):
    @property
    def engine(self) -> str:
        return "netcdf4"

    @property
    def full_format(self) -> str:
        with netCDF4.Dataset(self.path, "r") as rootgrp:
            return str(rootgrp.data_model)

    @property
    def global_attrs(self) -> dict[str, Any]:
        return self.ds.attrs