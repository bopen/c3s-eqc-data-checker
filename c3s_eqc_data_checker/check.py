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
import datetime
import functools
import glob
import inspect
import logging
import pathlib
import tempfile
import sys
from collections.abc import Iterable
from typing import Any, Literal

import cdo
import cfchecker.cfchecks
import pandas as pd
import rich.progress
import xarray as xr

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


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


def cdo_des_to_dict(path: str, destype: str) -> dict[str, str]:
    desdict = {}
    for string in getattr(cdo.Cdo(), destype)(input=path):
        if "=" in string:
            string = string.replace("'", "").replace('"', "")
            key, value = string.split("=")
            desdict[key.strip()] = value.strip()
    return desdict


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
class Checker:  # noqa: D205, D400
    """
    # Arguments:
    #   * files_pattern: glob pattern matching files to check
    #   * files_format: format of files to check (GRIB or NETCDF)
    #
    # Example:
    files_pattern = "path/to/files/*.grib"
    files_format = "GRIB"
    """

    files_pattern: str
    files_format: Literal["GRIB", "NETCDF"]

    @classmethod
    def available_checks(cls) -> list[str]:
        return sorted(
            name.split("check_", 1)[-1]
            for name in dir(cls)
            if name.startswith("check_")
        )

    @functools.cached_property
    def backend(self) -> type:
        match self.files_format:  # noqa: E999
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

    def check_format(
        self, version: str | float | None
    ) -> dict[str, Any]:  # noqa: D205, D400
        """
        [format]
        # Check file format.
        #
        # Arguments:
        #   * version: check specific version (optional)
        #
        # Example:
        version = 2
        """
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

    def check_variable_attributes(
        self, **expected: dict[str, Any]
    ) -> dict[str, Any]:  # noqa: D205, D400
        """
        [variable_attributes.var_name1]
        # Check attributes of a specific variable.
        #
        # Repeat for each variable.
        # Arguments are the attributes to check and their values.
        # Use empty strings to ensure attributes exist without checking values.
        #
        # Example 1:
        units = "K"
        name = ""

        [variable_attributes.var_name2]
        # Example 2:
        units = "m"
        """
        return self._check_variable_attrs_or_sizes("variable_attrs", **expected)

    def check_variable_dimensions(
        self, **expected: dict[str, Any]
    ) -> dict[str, Any]:  # noqa: D205, D400
        """
        [variable_dimensions.var_name1]
        # Check variable dimensions.
        #
        # Repeat for each variable.
        # Arguments are the dimensions to check and their sizes.
        # Use empty strings to ensure dimensions exist without checking sizes.
        #
        # Example 1:
        latitude = 180
        longitude = ""

        [variable_dimensions.var_name2]
        # Example 2:
        time = 10
        """
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

    def check_global_attributes(
        self, **expected: Any
    ) -> dict[str, Any]:  # noqa: D205, D400
        """
        [global_attributes]
        # Check global attributes.
        #
        # Arguments are the attributes to check and their values.
        # Use empty strings to ensure attributes exist without checking values.
        #
        # Example:
        centre = "ecmf"
        centreDescription = ""
        """
        return self._check_global_attrs_or_sizes("global_attrs", **expected)

    def check_global_dimensions(
        self, **expected: Any
    ) -> dict[str, Any]:  # noqa: D205, D400
        """
        [global_dimensions]
        # Check global dimensions.
        #
        # Arguments are the dimensions to check and their sizes.
        # Use empty strings to ensure dimensions exist without checking sizes.
        #
        # Example:
        latitude = 180
        longitude = ""
        """
        return self._check_global_attrs_or_sizes("global_sizes", **expected)

    def check_cf_compliance(
        self, version: float | str | None
    ) -> dict[str, Any]:  # noqa: D205, D400
        """
        [cf_compliance]
        # Check CF compliance.
        #
        # Arguments:
        #   * version: CF version to check against (optional, default: infer from attributes)
        #
        # Example:
        version = 1.7
        """
        version = (
            cfchecker.cfchecks.CFVersion(str(version))
            if version
            else cfchecker.cfchecks.CFVersion()
        )

        errors: dict[str, Any] = collections.defaultdict(dict)
        with tempfile.TemporaryDirectory() as tmpdir:
            inst = cfchecker.cfchecks.CFChecker(
                cacheTables=True,
                cacheTime=10 * 24 * 60 * 60,
                cacheDir=tmpdir,
                version=version,
                silent=True,
            )
            for path in self.paths_iterator:
                if version and version not in cfchecker.cfchecks.cfVersions:
                    versions = sorted(
                        str(version) for version in cfchecker.cfchecks.cfVersions
                    )
                    errors[
                        path
                    ] = f"{version=!s} is not available.\nAvailable versions: {versions!r}."
                    continue

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
        min: datetime.date | datetime.datetime | str | None,
        max: datetime.date | datetime.datetime | str | None,
        frequency: str | None,
        name: str | None,
    ) -> dict[str, Any]:  # noqa: D205, D400
        """
        [temporal_resolution]
        # Check temporal resolution.
        #
        # See pandas frequency aliases:
        # https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#timeseries-offset-aliases
        #
        # Arguments:
        #   * min: first time (optional)
        #   * max: last time (optional)
        #   * frequency: time frequency (optional)
        #   * name: name of time dimension (optional, default: "time")
        #
        # Example:
        min = 1900-01-01
        max = 1900-02-01
        frequency = "1MS"
        name = "time"
        """
        if name is None:
            name = "time"

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

        if frequency is not None:
            expected_time = pd.date_range(
                time.min().values, time.max().values, freq=frequency
            )
            if time.size != expected_time.size or not (time == expected_time).all():
                errors["frequency"] = {str(value) for value in time.diff(name).values}

        return errors

    def check_completeness(
        self,
        mask_variable: str | None,
        mask_file: str | None,
        variables: list[str] | set[str] | tuple[str] | None,
        ensure_null: bool | None,
    ) -> dict[str, Any]:  # noqa: D205, D400
        """
        [completeness]
        # Check data completeness.
        # If mask is not provided, ensure that all values are not null.
        #
        # Arguments:
        #   * mask_variable: name of the mask variable (optional)
        #   * mask_file: path to file containing mask variable (optional)
        #   * variables: variables to check (optional)
        #   * ensure_null: ensure that masked values are null (optional)
        #
        # Example:
        mask_variable = "mask_name"
        mask_file = "path/to/file/with/mask"
        variables = ["var1", "var2"]
        ensure_null = true
        """
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

            if variables is None:
                if mask is None:
                    variables = list(ds.data_vars)
                else:
                    variables = [
                        var
                        for var, da in ds.data_vars.items()
                        if set(mask.dims) <= set(da.dims)
                    ]

            for var in variables:
                da = ds[var]
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

    def check_horizontal_resolution(
        self, **expected_griddes: str
    ) -> dict[str, Any]:  # noqa: D205, D400
        """
        [horizontal_resolution]
        # Check horizontal resolution.
        #
        # Arguments are the grid attributes to check and their values.
        # Attributes are inferred using `cdo -griddes`.
        #
        # Example:
        gridtype = "lonlat"
        """
        return self._check_spatial_resolution("griddes", expected_griddes)

    def check_vertical_resolution(
        self, **expected_zaxisdes: str
    ) -> dict[str, Any]:  # noqa: D205, D400
        """
        [vertical_resolution]
        # Check vertical resolution.
        #
        # Arguments are the grid attributes to check and their values.
        # Attributes are inferred using `cdo -zaxisdes`.
        #
        # Example:
        zaxistype = "surface"
        """
        return self._check_spatial_resolution("zaxisdes", expected_zaxisdes)


class ConfigChecker:
    def __init__(self, configfile: str | pathlib.Path):
        with open(configfile, "rb") as f:
            self.config = tomllib.load(f)

    @functools.cached_property
    def checker(self) -> Checker:
        # TODO: make it a classmethod of Checker in python 3.11
        args = set(inspect.getfullargspec(Checker).args) - {"self"}
        kwargs = {arg: self.config[arg] for arg in args}
        return Checker(**kwargs)

    def check(self, name: str) -> Any:
        config_args = self.config[name]

        method = getattr(self.checker, f"check_{name}")
        fullargsspec = inspect.getfullargspec(method)
        args = set(fullargsspec.args) - {"self"}
        kwargs = {arg: config_args.get(arg, None) for arg in args}
        if fullargsspec.varkw:
            kwargs.update(config_args)
        elif extra_args := set(config_args) - args:
            logging.warn(f"Unused arguments: {', '.join(extra_args)}")
        errors = method(**kwargs)

        if set(errors) == set(self.checker.paths):
            values = iter(errors.values())
            first_value = next(values)
            if all(value == first_value for value in values):
                # All errors are identical
                return {self.checker.files_pattern: first_value}

        return errors
