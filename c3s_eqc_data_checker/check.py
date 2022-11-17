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
import functools
import glob
import inspect
import tempfile
from typing import Any, Literal

import cdo
import cfchecker.cfchecks
import pandas as pd
import toml
import xarray as xr


def check_attributes_or_sizes(
    expected: dict[str, Any], actual: dict[str, Any]
) -> dict[str, Any]:
    errors: dict[str, Any] = {}
    for key, value in expected.items():
        if key not in actual:
            errors[key] = None
        elif value != "" and actual[key] != value:
            errors[key] = actual[key]

    return errors


def recursive_defaultdict() -> dict[Any, Any]:
    return collections.defaultdict(recursive_defaultdict)


def cdo_des_to_dict(path: str, destype: str) -> dict[str, str]:
    griddes_dict = {}
    for string in getattr(cdo.Cdo(), destype)(input=path):
        if "=" in string:
            string = string.replace("'", "").replace('"', "")
            key, value = string.split("=")
            griddes_dict[key.strip()] = value.strip()
    return griddes_dict


@dataclasses.dataclass
class Checker:
    files_pattern: str
    files_format: Literal["GRIB", "NETCDF"]

    @property
    def backend(self) -> type:
        match self.files_format:
            case "GRIB":
                from . import grib

                return grib.Grib
            case "NETCDF":
                from . import netcdf

                return netcdf.NetCDF

        raise NotImplementedError(f"{self.files_format=}")

    @functools.cached_property
    def paths(self) -> list[str]:
        paths = glob.glob(self.files_pattern)
        if not len(paths):
            raise ValueError(f"No match for {self.files_pattern=}")
        return paths

    def check_format(self, version: str | float | None) -> dict[str, str]:
        expected_prefix = f"{self.files_format}{version if version else ''}"
        errors = {}
        for path in self.paths:
            full_format = self.backend(path).full_format
            if not full_format.startswith(expected_prefix):
                errors[path] = full_format
        return errors

    def _check_variable_attrs_or_sizes(
        self, attr_name: str, **expected: dict[str, Any]
    ) -> dict[str, dict[str, None | dict[str, Any]]]:
        errors: dict[str, dict[str, None | dict[str, Any]]] = collections.defaultdict(
            dict
        )
        for path in self.paths:
            actual = getattr(self.backend(path), attr_name)
            for var, expected_var_attrs in expected.items():
                if var not in actual:
                    errors[path][var] = None
                else:
                    error = check_attributes_or_sizes(expected_var_attrs, actual[var])
                    if error:
                        errors[path][var] = error
        return errors

    def check_variable_attributes(
        self, **expected: dict[str, Any]
    ) -> dict[str, dict[str, None | dict[str, Any]]]:

        return self._check_variable_attrs_or_sizes("variable_attrs", **expected)

    def check_variable_dimensions(
        self, **expected: dict[str, Any]
    ) -> dict[str, dict[str, None | dict[str, int | None]]]:

        return self._check_variable_attrs_or_sizes("variable_sizes", **expected)

    def _check_global_attrs_or_sizes(
        self, attr_name: str, **expected: Any
    ) -> dict[str, dict[str, Any]]:
        errors = {}
        for path in self.paths:
            actual = getattr(self.backend(path), attr_name)
            error = check_attributes_or_sizes(expected, actual)
            if error:
                errors[path] = error
        return errors

    def check_global_attributes(self, **expected: Any) -> dict[str, dict[str, Any]]:
        return self._check_global_attrs_or_sizes("global_attrs", **expected)

    def check_global_dimensions(
        self, **expected: Any
    ) -> dict[str, dict[str, int | None]]:
        return self._check_global_attrs_or_sizes("global_sizes", **expected)

    def check_cf_compliance(self, version: float | str | None) -> dict[str, Any]:

        version = (
            cfchecker.cfchecks.CFVersion()
            if version is None
            else cfchecker.cfchecks.CFVersion(str(version))
        )

        errors = recursive_defaultdict()
        with tempfile.TemporaryDirectory() as tmpdir:
            inst = cfchecker.cfchecks.CFChecker(
                cacheTables=True,
                cacheTime=10 * 24 * 60 * 60,
                cacheDir=tmpdir,
                version=version,
                silent=True,
            )
            for path in self.paths:
                if self.files_format == "NETCDF":
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

                for log in ("FATAL", "ERROR"):
                    if error := inst.results["global"][log]:
                        errors[path].get("global", []).extend(
                            [f"{log}: {err}" for err in error]
                        )
                    for key, value in inst.results["variables"].items():
                        if error := value[log]:
                            errors[path]["variables"].get(key, []).extend(
                                [f"{log}: {err}" for err in error]
                            )
        return errors

    def check_temporal_resolution(
        self, name: str, min: str | None, max: str | None, resolution: str | None
    ) -> dict[str, str | set[str]]:

        times = []
        for path in self.paths:
            times.append(self.backend(path).ds[name])
        time = xr.concat(times, name)
        time = time.sortby(time)

        errors: dict[str, str | set[str]] = {}

        if min is not None:
            if (actual_min := time.min()) != pd.to_datetime(min):
                errors["min"] = str(actual_min.values)

        if max is not None:
            if (actual_max := time.max()) != pd.to_datetime(max):
                errors["max"] = str(actual_max.values)

        if resolution is not None:
            res_td = pd.to_timedelta(resolution)
            if time.size <= 1 and res_td != pd.to_timedelta(0):
                errors["resolution"] = "0"
            elif ((actual_res := time.diff(name)) != res_td).any():
                errors["resolution"] = {str(value) for value in actual_res.values}

        return errors

    def check_completeness(
        self,
        mask_variable: str | None,
        mask_file: str | None,
        variables: list[str] | set[str] | tuple[str] | None,
        ensure_null: bool,
    ) -> dict[str, set[str]]:

        mask = None
        if mask_file:
            if mask_variable is None:
                raise ValueError(
                    "please provide `mask_variable` along with `mask_file`"
                )
            mask = self.backend(mask_file).ds[mask_variable].fillna(0)

        errors: dict[str, set[str]] = collections.defaultdict(set)
        for path in self.paths:
            ds = self.backend(path).ds
            if mask is None and mask_variable:
                mask = ds[mask_variable].fillna(0)

            for var in variables if variables is not None else ds.data_vars:
                da = ds[var]
                if variables is not None:
                    if var not in variables:
                        continue
                else:
                    if mask is not None and not set(mask.dims) <= set(da.dims):
                        continue

                if mask is None and da.isnull().any():
                    errors[path].add(var)
                elif not xr.where(
                    mask, da.notnull(), da.isnull() if ensure_null else 1
                ).all():  # type: ignore[no-untyped-call]
                    errors[path].add(var)

        return errors

    def _check_spatial_resolution(
        self, destype: str, expected_attrs: dict[str, str]
    ) -> dict[str, dict[str, str | None]]:
        errors = {}
        for path in self.paths:
            actual_attrs = cdo_des_to_dict(path, destype)
            error = check_attributes_or_sizes(expected_attrs, actual_attrs)
            if error:
                errors[path] = error
        return errors

    def check_horizontal_resolution(
        self, **expected_griddes: str
    ) -> dict[str, dict[str, str | None]]:
        return self._check_spatial_resolution("griddes", expected_griddes)

    def check_vertical_resolution(
        self, **expected_zaxisdes: str
    ) -> dict[str, dict[str, str | None]]:
        return self._check_spatial_resolution("zaxisdes", expected_zaxisdes)


class ConfigChecker:
    def __init__(self, configfile: str):
        self.config = toml.load(configfile)
        self.errors: dict[str, Any] = {}

    def get_kwargs_from_config(
        self, keys: set[str], allow_missing: bool
    ) -> dict[str, Any]:
        kwargs = {}
        for key in keys:
            config = self.config

            split = key.split(".")
            for k in split[:-1]:
                if allow_missing:
                    config = config.get(k, {})
                else:
                    config = config[k]

            k = split[-1]
            if allow_missing:
                kwargs[k] = config.pop(k, None)
            else:
                kwargs[k] = config.pop(k)
        return kwargs

    @functools.cached_property
    def checker(self) -> Checker:
        kwargs = self.get_kwargs_from_config(
            set(inspect.getfullargspec(Checker).args) - {"self"}, allow_missing=False
        )
        return Checker(**kwargs)

    def check(self, name: str) -> None:
        if name not in self.config:
            return None

        method = getattr(self.checker, "_".join(["check", name]))
        keys = {
            ".".join([name, key])
            for key in inspect.getfullargspec(method).args
            if key != "self"
        }
        kwargs = self.get_kwargs_from_config(keys, allow_missing=True)
        self.errors[name] = method(**kwargs)
