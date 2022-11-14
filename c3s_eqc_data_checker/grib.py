from typing import Any

import xarray as xr

from . import baseformat


class Grib(baseformat.BaseFormat):
    @property
    def engine(self) -> str:
        return "cfgrib"

    @property
    def full_format(self) -> str:
        edition = self.ds.attrs.get("GRIB_edition", "")
        return f"GRIB{edition}"

    @property
    def variable_attrs(self) -> dict[str, dict[str, Any]]:
        return {
            str(name): original_grib_attributes(var)
            for name, var in self.ds.variables.items()
        }

    @property
    def global_attrs(self) -> dict[str, Any]:
        return original_grib_attributes(self.ds)


def original_grib_attributes(obj: xr.Dataset | xr.Variable) -> dict[str, Any]:
    return {
        k.split("GRIB_", 1)[-1]: v
        for k, v in obj.attrs.items()
        if k.startswith("GRIB_")
    }
