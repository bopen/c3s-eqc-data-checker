import dataclasses
import glob
from typing import Iterator, Literal

import eccodes
import netCDF4


def get_grib_full_format(path: str) -> str:
    with open(path, "r") as f:
        msgid = eccodes.codes_any_new_from_file(f)
        edition = eccodes.codes_get(msgid, "edition")
        eccodes.codes_release(msgid)
    return f"GRIB{edition}"


def get_netcdf_full_format(path: str) -> str:
    with netCDF4.Dataset(path, "r") as ds:
        return str(ds.data_model)


@dataclasses.dataclass
class Overview:
    pattern: str

    @property
    def paths(self) -> Iterator[str]:
        return glob.iglob(self.pattern)

    def check_format(
        self, format: Literal["GRIB", "NETCDF"], version: int | None
    ) -> dict[str, str]:
        match format:
            case "GRIB":
                get_full_format = get_grib_full_format
            case "NETCDF":
                get_full_format = get_netcdf_full_format
            case _:
                raise NotImplementedError(f"{format=}")

        expected_format = f"{format}{version if version else ''}"
        errors = {}
        for path in self.paths:
            full_format = get_full_format(path)
            actual_format = full_format.split("_", 1)[0]
            if actual_format != expected_format:
                errors[path] = full_format

        return errors
