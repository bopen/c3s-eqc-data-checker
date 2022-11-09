from typing import Any

import netCDF4

from . import baseformat


class NetCDF(baseformat.BaseFormat):
    @property
    def full_format(self) -> str:
        with netCDF4.Dataset(self.path, "r") as rootgrp:
            return str(rootgrp.data_model)

    @property
    def global_attrs(self) -> dict[str, Any]:
        with netCDF4.Dataset(self.path, "r") as rootgrp:
            return {name: getattr(rootgrp, name) for name in rootgrp.ncattrs()}
