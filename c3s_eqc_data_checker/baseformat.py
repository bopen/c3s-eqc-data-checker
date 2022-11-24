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

import abc
import functools
from typing import Any

import xarray as xr


class BaseFormat:
    def __init__(self, path: str) -> None:
        self.path = path

    @property
    @abc.abstractmethod
    def engine(self) -> str:
        pass

    @functools.cached_property
    def ds(self) -> xr.Dataset:
        return xr.open_dataset(self.path, chunks="auto", engine=self.engine)

    @property
    @abc.abstractmethod
    def full_format(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def variable_attrs(self) -> dict[str, dict[str, Any]]:
        pass

    @functools.cached_property
    def variable_sizes(self) -> dict[str, dict[str, int]]:
        return {
            str(name): {str(k): v for k, v in variable.sizes.items()}
            for name, variable in self.ds.variables.items()
        }

    @property
    @abc.abstractmethod
    def global_attrs(self) -> dict[str, Any]:
        pass

    @functools.cached_property
    def global_sizes(self) -> dict[str, int]:
        return {str(k): v for k, v in self.ds.sizes.items()}
