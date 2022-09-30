# Copyright 2022, European Union.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import dataclasses
import functools
import mimetypes

import eccodes
import netCDF4

from . import config

# Add netcdf and grib to mimetypes
for ext in config.NETCDF_EXTENSIONS:
    mimetypes.add_type("application/netcdf", ext, strict=True)
for ext in config.GRIB_EXTENSIONS:
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

    def check_file_format(self) -> None:
        if self.is_grib:
            with open(self.filename, "rb") as f:
                msgid = eccodes.codes_any_new_from_file(f)
                identifier = eccodes.codes_get(msgid, "identifier")
                edition = eccodes.codes_get(msgid, "edition")
                eccodes.codes_release(msgid)
            if identifier != "GRIB" or edition < config.MIN_GRIB_EDITION:
                raise FileFormatError(
                    f"{self.filename!r} format is '{identifier}{edition}'."
                )

        elif self.is_netcdf:
            with netCDF4.Dataset(self.filename, "r") as rootgrp:
                data_model = rootgrp.data_model
            edition = data_model.split("_")[0].replace("NETCDF", "")
            if (
                not data_model.startswith("NETCDF")
                or int(edition) < config.MIN_NETCDF_EDITION
            ):
                raise FileFormatError(f"{self.filename!r} format is {data_model!r}.")

        else:
            raise FileFormatError(
                f"{self.filename!r} MIME type is {self.type_from_ext}."
            )
