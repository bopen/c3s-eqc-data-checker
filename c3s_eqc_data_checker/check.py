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
import pathlib
import tempfile
from typing import Any, Iterable, Literal

import cdo
import cfchecker.cfchecks
import pandas as pd
import rich.progress
import toml
import xarray as xr


def check_attributes_or_sizes(
    expected: dict[str, Any],
    actual: dict[str, Any],
    always_check_value: bool,
) -> dict[str, Any]:
    errors: dict[str, Any] = {}
    for key, value in expected.items():
        if key not in actual:
            errors[key] = None
        elif (always_check_value or value != "") and actual[key] != value:
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


def filter_cfchecker_results(results: Any) -> None:
    for key, value in dict(results).items():
        if isinstance(value, dict) and {"ERROR", "FATAL"} & set(value):
            to_keep = value["FATAL"] + value["ERROR"]
            if to_keep:
                results[key] = "\n".join(to_keep)
            else:
                results.pop(key)
        else:
            filter_cfchecker_results(value)


@dataclasses.dataclass
class Checker:
    files_pattern: str
    files_format: Literal["GRIB", "NETCDF"]

    @functools.cached_property
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

    @property
    def paths_iterator(self) -> Iterable[str]:
        return rich.progress.track(self.paths, description="")

    def check_format(self, version: str | float | None) -> dict[str, Any]:
        expected_prefix = f"{self.files_format}{version if version else ''}"
        errors = {}
        for path in self.paths_iterator:
            full_format = self.backend(path).full_format
            if not full_format.startswith(expected_prefix):
                errors[path] = full_format
        return errors

    def _check_variable_attrs_or_sizes(
        self, attr_name: str, **expected: dict[str, Any]
    ) -> dict[str, Any]:
        errors: dict[str, dict[str, None | dict[str, Any]]] = collections.defaultdict(
            dict
        )
        for path in self.paths_iterator:
            actual = getattr(self.backend(path), attr_name)
            for var, expected_var_attrs in expected.items():
                if var not in actual:
                    errors[path][var] = None
                else:
                    error = check_attributes_or_sizes(
                        expected_var_attrs, actual[var], always_check_value=False
                    )
                    if error:
                        errors[path][var] = error
        return errors

    def check_variable_attributes(self, **expected: dict[str, Any]) -> dict[str, Any]:

        return self._check_variable_attrs_or_sizes("variable_attrs", **expected)

    def check_variable_dimensions(self, **expected: dict[str, Any]) -> dict[str, Any]:

        return self._check_variable_attrs_or_sizes("variable_sizes", **expected)

    def _check_global_attrs_or_sizes(
        self, attr_name: str, **expected: Any
    ) -> dict[str, Any]:
        errors = {}
        for path in self.paths_iterator:
            actual = getattr(self.backend(path), attr_name)
            error = check_attributes_or_sizes(
                expected, actual, always_check_value=False
            )
            if error:
                errors[path] = error
        return errors

    def check_global_attributes(self, **expected: Any) -> dict[str, Any]:
        return self._check_global_attrs_or_sizes("global_attrs", **expected)

    def check_global_dimensions(self, **expected: Any) -> dict[str, Any]:
        return self._check_global_attrs_or_sizes("global_sizes", **expected)

    def check_cf_compliance(self, version: float | str | None) -> dict[str, Any]:

        version = (
            cfchecker.cfchecks.CFVersion(str(version))
            if version
            else cfchecker.cfchecks.CFVersion()
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
            for path in self.paths_iterator:
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

                counts = inst.get_counts()
                if counts["ERROR"] or counts["FATAL"]:
                    results = dict(inst.results)
                    filter_cfchecker_results(results)
                    errors[path] = {k: v for k, v in results.items() if v}
        return errors

    def check_temporal_resolution(
        self,
        min: str | None,
        max: str | None,
        resolution: str | None,
        name: str = "time",
    ) -> dict[str, Any]:

        times = []
        for path in self.paths_iterator:
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
        ensure_null: bool | None,
    ) -> dict[str, Any]:

        mask = None
        if mask_file:
            if mask_variable is None:
                raise ValueError(
                    "please provide `mask_variable` along with `mask_file`"
                )
            mask = self.backend(mask_file).ds[mask_variable].fillna(0)

        errors: dict[str, set[str]] = collections.defaultdict(set)
        for path in self.paths_iterator:
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
        self, destype: str, expected_attrs: dict[str, Any]
    ) -> dict[str, Any]:
        expected_attrs = {k: str(v) for k, v in expected_attrs.items()}
        errors = {}
        for path in self.paths_iterator:
            actual_attrs = cdo_des_to_dict(path, destype)
            error = check_attributes_or_sizes(
                expected_attrs, actual_attrs, always_check_value=True
            )
            if error:
                errors[path] = error
        return errors

    def check_horizontal_resolution(self, **expected_griddes: str) -> dict[str, Any]:
        return self._check_spatial_resolution("griddes", expected_griddes)

    def check_vertical_resolution(self, **expected_zaxisdes: str) -> dict[str, Any]:
        return self._check_spatial_resolution("zaxisdes", expected_zaxisdes)


class ConfigChecker:
    def __init__(self, configfile: str | pathlib.Path):
        self.config = toml.load(configfile)

    @functools.cached_property
    def checker(self) -> Checker:
        args = set(inspect.getfullargspec(Checker).args) - {"self"}
        kwargs = {arg: self.config[arg] for arg in args}
        return Checker(**kwargs)

    @functools.cached_property
    def available_checks(self) -> list[str]:
        return sorted(
            name.split("check_", 1)[-1]
            for name in dir(self.checker)
            if name.startswith("check_")
        )

    def check(self, name: str) -> Any:
        method = getattr(self.checker, f"check_{name}")
        fullargsspec = inspect.getfullargspec(method)
        args = set(fullargsspec.args) - {"self"}
        kwargs = {arg: self.config.get(name, {}).get(arg, None) for arg in args}
        if fullargsspec.varkw:
            kwargs.update(self.config.get(name, {}))
        return method(**kwargs)
