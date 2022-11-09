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

import collections
import dataclasses
import glob
from typing import Any, Iterator, Literal


@dataclasses.dataclass
class Checker:
    pattern: str
    format: Literal["GRIB", "NETCDF"]

    @property
    def backend(self) -> type:
        match self.format:
            case "GRIB":
                from . import grib

                return grib.Grib
            case "NETCDF":
                from . import netcdf

                return netcdf.NetCDF

        raise NotImplementedError(f"{self.format=}")

    @property
    def paths(self) -> Iterator[str]:
        return glob.iglob(self.pattern)

    def check_format(self, version: int | None = None) -> dict[str, str]:
        expected_prefix = f"{self.format}{version if version else ''}"
        errors = {}
        for path in self.paths:
            full_format = self.backend(path).full_format
            if not full_format.startswith(expected_prefix):
                errors[path] = full_format
        return errors

    def check_global_attributes(
        self, **expected_attrs: Any
    ) -> dict[str, dict[str, Any]]:
        errors: dict[str, dict[str, Any]] = collections.defaultdict(dict)
        for path in self.paths:
            actual_attrs = self.backend(path).global_attrs
            for key, value in expected_attrs.items():
                if key not in actual_attrs:
                    errors[path][key] = None
                elif value is not None and actual_attrs[key] != value:
                    errors[path][key] = actual_attrs[key]
        return errors
