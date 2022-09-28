import dataclasses
import functools
import mimetypes

import netCDF4
import xarray as xr

from . import config

try:
    import dask  # noqa: F401

    HAS_DASK = True
except ImportError:
    HAS_DASK = False

# Add netcdf and grib to mimetypes
mimetypes.add_type("application/netcdf", ".nc", strict=True)
for ext in (".grib", ".grb", ".grb1", ".grb2"):
    mimetypes.add_type("application/x-grib", ext, strict=False)
del ext


class FileFormatError(Exception):
    pass


@dataclasses.dataclass
class FileFormat:
    filename: str

    @functools.cached_property
    def type_from_ext(self) -> str | None:
        return mimetypes.guess_type(self.filename, strict=False)[0]

    @functools.cached_property
    def is_grib(self) -> bool:
        return self.type_from_ext == "application/x-grib"

    @functools.cached_property
    def is_netcdf(self) -> bool:

        return self.type_from_ext == "application/netcdf"

    def check_format(self) -> None:
        if self.is_grib:
            with xr.open_dataset(
                self.filename, engine="cfgrib", chunks="auto" if HAS_DASK else None
            ) as ds:
                edition = ds.attrs["GRIB_edition"]
            if edition < config.MIN_GRIB_EDITION:
                raise FileFormatError(f"GRIB{edition} is not compliant.")

        elif self.is_netcdf:
            with netCDF4.Dataset(self.filename, "r") as rootgrp:
                data_model = rootgrp.data_model
            edition = int(data_model.split("_")[0].replace("NETCDF", ""))
            if edition < config.MIN_NETCDF_EDITION:
                raise FileFormatError(f"{data_model} is not compliant.")

        else:
            raise FileFormatError(
                "MIME type associated with the filename extension"
                f" is not compliant: {self.type_from_ext}."
            )
