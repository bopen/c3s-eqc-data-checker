import pathlib

import pandas as pd
import pytest
import xarray as xr

from c3s_eqc_data_checker import Checker

pytest.importorskip("netCDF4")


def test_format(tmp_path: pathlib.Path) -> None:
    ds = xr.Dataset()
    ds.to_netcdf(path=tmp_path / "test.nc4", format="NETCDF4_CLASSIC")
    ds.to_netcdf(path=tmp_path / "test.nc3", format="NETCDF3_CLASSIC")

    checker = Checker(str(tmp_path / "test.nc*"), format="NETCDF")
    actual = checker.check_format(4)
    expected = {str(tmp_path / "test.nc3"): "NETCDF3_CLASSIC"}
    assert actual == expected


def test_variables_attrs(tmp_path: pathlib.Path) -> None:
    da = xr.DataArray(name="foo", attrs={"a": "a", "b": "b", "c": "c"})
    da.to_netcdf(tmp_path / "test.nc")

    checker = Checker(str(tmp_path / "test.nc"), format="NETCDF")
    actual = checker.check_variable_attributes(
        foo=dict(a=None, b="b", c="wrong", d="d")
    )
    expected = {str(tmp_path / "test.nc"): {"foo": {"c": "c", "d": None}}}
    assert actual == expected


def test_global_attrs(tmp_path: pathlib.Path) -> None:
    ds = xr.Dataset(attrs={"a": "a", "b": "b", "c": "c"})
    ds.to_netcdf(tmp_path / "test.nc")

    checker = Checker(str(tmp_path / "test.nc"), format="NETCDF")
    actual = checker.check_global_attributes(a=None, b="b", c="wrong", d="d")
    expected = {str(tmp_path / "test.nc"): {"c": "c", "d": None}}
    assert actual == expected


def test_cf_compliance(tmp_path: pathlib.Path) -> None:
    pytest.importorskip("cfchecker")
    ds = xr.Dataset({"foo": ("dim_0", [None], {"standard_name": "air_temperature"})})
    ds.to_netcdf(tmp_path / "compliant.nc")
    ds["foo"].attrs["standard_name"] = "unknown"
    ds.to_netcdf(tmp_path / "non-compliant.nc")

    checker = Checker(str(tmp_path / "*compliant.nc"), format="NETCDF")
    actual = checker.check_cf_compliance()
    assert set(actual) == {str(tmp_path / "non-compliant.nc")}


def test_temporal_resolution(tmp_path: pathlib.Path) -> None:
    for i, date in enumerate(pd.date_range("1900-01-01", "1900-01-03", freq="1D")):
        da = xr.DataArray(date, name="time")
        da.to_netcdf(tmp_path / f"test{i}.nc")

    checker = Checker(str(tmp_path / "*.nc"), format="NETCDF")
    actual = checker.check_temporal_resolution("time", "1900-01-01", "1900-01-03", "1d")
    expected: dict[str, str | set[str]] = {}
    assert actual == expected

    (tmp_path / "test1.nc").unlink()
    actual = checker.check_temporal_resolution("time", "2000-01-01", "2000-01-03", "1d")
    expected = {
        "min": "1900-01-01T00:00:00.000000000",
        "max": "1900-01-03T00:00:00.000000000",
        "resolution": {"172800000000000 nanos"},
    }
    assert actual == expected
