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
import tempfile
from typing import Any, Iterator, Literal

import cdo
import cfchecker.cfchecks
import pandas as pd
import xarray as xr


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

    def check_format(self, version: float | int | None = None) -> dict[str, str]:
        expected_prefix = f"{self.format}{version if version else ''}"
        errors = {}
        for path in self.paths:
            full_format = self.backend(path).full_format
            if not full_format.startswith(expected_prefix):
                errors[path] = full_format
        return errors

    def check_variable_attributes(
        self, **expected_attrs: dict[str, Any]
    ) -> dict[str, dict[str, None | dict[str, Any]]]:
        errors: dict[str, dict[str, None | dict[str, Any]]] = collections.defaultdict(
            dict
        )
        for path in self.paths:
            actual_attrs = self.backend(path).variable_attrs
            for var, expected_var_attrs in expected_attrs.items():
                if var not in actual_attrs:
                    errors[path][var] = None
                else:
                    error = check_attributes(expected_var_attrs, actual_attrs[var])
                    if error:
                        errors[path][var] = error
        return errors

    def check_global_attributes(
        self, **expected_global_attrs: Any
    ) -> dict[str, dict[str, Any]]:
        errors = {}
        for path in self.paths:
            actual_global_attrs = self.backend(path).global_attrs
            error = check_attributes(expected_global_attrs, actual_global_attrs)
            if error:
                errors[path] = error
        return errors

    def check_cf_compliance(self, version: float | str | None = None) -> dict[str, Any]:

        version = (
            cfchecker.cfchecks.CFVersion()
            if version is None
            else cfchecker.cfchecks.CFVersion(str(version))
        )

        errors = {}
        with tempfile.TemporaryDirectory() as tmpdir:
            inst = cfchecker.cfchecks.CFChecker(
                cacheTables=True,
                cacheTime=10 * 24 * 60 * 60,
                cacheDir=tmpdir,
                version=version,
                silent=True,
            )
            for path in self.paths:
                if self.format == "NETCDF":
                    inst.checker(path)
                else:
                    # Save a small sample as netcdf
                    with tempfile.NamedTemporaryFile(suffix=".nc") as tmpfile:
                        ds = self.backend(path).ds
                        ds = ds.isel(
                            **{dim: [0] for dim, size in ds.sizes.items() if size}
                        )
                        self.backend(path).ds.to_netcdf(tmpfile.name)
                        inst.checker(tmpfile.name)

                counts = inst.get_counts()
                if counts["ERROR"] or counts["FATAL"]:
                    errors[path] = inst.results
        return errors

    def check_temporal_resolution(
        self, name: str, min: str, max: str, resolution: str
    ) -> dict[str, str | set[str]]:
        min = pd.to_datetime(min)
        max = pd.to_datetime(max)
        resolution = pd.to_timedelta(resolution)

        times = []
        for path in self.paths:
            times.append(self.backend(path).ds[name])
        time = xr.concat(times, name)
        time = time.sortby(time)

        errors: dict[str, str | set[str]] = {}
        if (actual_min := time.min()) != min:
            errors["min"] = str(actual_min.values)

        if (actual_max := time.max()) != max:
            errors["max"] = str(actual_max.values)

        if time.size <= 1 and resolution != pd.to_timedelta(0):
            errors["resolution"] = "0"
        elif ((actual_res := time.diff(name)) != resolution).any():
            errors["resolution"] = {str(value) for value in actual_res.values}

        return errors

    def check_masked_variables(
        self, mask_file: str, mask_variable: str
    ) -> dict[str, set[str]]:
        mask = self.backend(mask_file).ds[mask_variable]
        errors: dict[str, set[str]] = collections.defaultdict(set)
        for path in self.paths:
            for var, da in self.backend(path).ds.data_vars.items():
                if set(mask.dims) <= set(da.dims):
                    if not xr.where(mask, da.notnull(), da.isnull()).all():  # type: ignore[no-untyped-call]
                        errors[path].add(var)
        return errors

    def check_spatial_resolution(
        self, destype: str, expected_attrs: dict[str, str]
    ) -> dict[str, dict[str, str | None]]:
        errors = {}
        for path in self.paths:
            actual_attrs = cdo_des_to_dict(path, destype)
            error = check_attributes(expected_attrs, actual_attrs)
            if error:
                errors[path] = error
        return errors

    def check_horizontal_resolution(
        self, **expected_griddes: str
    ) -> dict[str, dict[str, str | None]]:
        return self.check_spatial_resolution("griddes", expected_griddes)

    def check_vertical_resolution(
        self, **expected_griddes: str
    ) -> dict[str, dict[str, str | None]]:
        return self.check_spatial_resolution("zaxisdes", expected_griddes)


def check_attributes(
    expected: dict[str, Any], actual: dict[str, Any]
) -> dict[str, Any]:
    errors: dict[str, Any] = {}
    for key, value in expected.items():
        if key not in actual:
            errors[key] = None
        elif value is not None and actual[key] != value:
            errors[key] = actual[key]

    return errors


def cdo_des_to_dict(path: str, destype: str) -> dict[str, str]:
    griddes_dict = {}
    for string in getattr(cdo.Cdo(), destype)(input=path):
        if "=" in string:
            string = string.replace("'", "").replace('"', "")
            key, value = string.split("=")
            griddes_dict[key.strip()] = value.strip()
    return griddes_dict
