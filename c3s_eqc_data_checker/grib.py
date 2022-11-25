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

import functools
from typing import Any

import xarray as xr

from . import baseformat


class Grib(baseformat.BaseFormat):
    @functools.cached_property
    def engine(self) -> str:
        return "cfgrib"

    @functools.cached_property
    def full_format(self) -> str:
        edition = self.ds.attrs.get("GRIB_edition", "")
        return f"GRIB{edition}"

    @functools.cached_property
    def variable_attrs(self) -> dict[str, dict[str, Any]]:
        return {
            str(name): {**self.global_attrs, **original_grib_attributes(var)}
            for name, var in self.ds.variables.items()
        }

    @functools.cached_property
    def global_attrs(self) -> dict[str, Any]:
        return original_grib_attributes(self.ds)


def original_grib_attributes(obj: xr.Dataset | xr.Variable) -> dict[str, Any]:
    return {
        k.split("GRIB_", 1)[-1]: v
        for k, v in obj.attrs.items()
        if k.startswith("GRIB_")
    }
