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
