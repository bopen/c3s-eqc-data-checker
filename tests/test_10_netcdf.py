import pathlib

import pandas as pd
import pytest
import xarray as xr

from c3s_eqc_data_checker import Checker


def test_format(tmp_path: pathlib.Path) -> None:
    ds = xr.Dataset()
    ds.to_netcdf(path=tmp_path / "test.nc4", format="NETCDF4_CLASSIC")
    ds.to_netcdf(path=tmp_path / "test.nc3", format="NETCDF3_CLASSIC")

    checker = Checker(str(tmp_path / "test.nc*"), files_format="NETCDF")
    actual = checker.check_format("4")
    expected = {str(tmp_path / "test.nc3"): "NETCDF3_CLASSIC"}
    assert actual == expected


def test_variables_attrs(tmp_path: pathlib.Path) -> None:
    da = xr.DataArray(name="foo", attrs={"a": "a", "b": "b", "c": "c"})
    da.to_netcdf(tmp_path / "test.nc")

    checker = Checker(str(tmp_path / "test.nc"), files_format="NETCDF")
    actual = checker.check_variable_attributes(foo=dict(a="", b="b", c="wrong", d="d"))
    expected = {str(tmp_path / "test.nc"): {"foo": {"c": "c", "d": None}}}
    assert actual == expected


def test_global_attrs(tmp_path: pathlib.Path) -> None:
    ds = xr.Dataset(attrs={"a": "a", "b": "b", "c": "c"})
    ds.to_netcdf(tmp_path / "test.nc")

    checker = Checker(str(tmp_path / "test.nc"), files_format="NETCDF")
    actual = checker.check_global_attributes(a="", b="b", c="wrong", d="d")
    expected = {str(tmp_path / "test.nc"): {"c": "c", "d": None}}
    assert actual == expected


def test_cf_compliance(tmp_path: pathlib.Path) -> None:
    ds = xr.Dataset({"foo": ("dim_0", [None], {"standard_name": "air_temperature"})})
    ds.to_netcdf(tmp_path / "compliant.nc")
    ds["foo"].attrs["standard_name"] = "unknown"
    ds.to_netcdf(tmp_path / "non-compliant.nc")

    checker = Checker(str(tmp_path / "*compliant.nc"), files_format="NETCDF")
    actual = checker.check_cf_compliance(None)
    assert set(actual) == {str(tmp_path / "non-compliant.nc")}


def test_temporal_resolution(tmp_path: pathlib.Path) -> None:
    for date in pd.date_range("1900-01-01", "1900-01-02", freq="1D"):
        da = xr.DataArray(date, name="time")
        da.to_netcdf(tmp_path / f"{date}.nc")

    checker = Checker(str(tmp_path / "*.nc"), files_format="NETCDF")
    actual = checker.check_temporal_resolution("time", "1900-01-01", "1900-01-02", "1D")
    assert actual == {}

    actual = checker.check_temporal_resolution("time", "2000-01-01", "2000-01-02", "2D")
    expected = {
        "min": "1900-01-01T00:00:00.000000000",
        "max": "1900-01-02T00:00:00.000000000",
        "resolution": {"86400000000000 nanoseconds"},
    }
    assert actual == expected


def test_completeness_without_mask(tmp_path: pathlib.Path) -> None:
    xr.Dataset(
        {
            "ok": xr.DataArray([0, 1]),
            "wrong0": xr.DataArray([None, 1]),
            "wrong1": xr.DataArray([1, None]),
        }
    ).to_netcdf(tmp_path / "test.nc")

    checker = Checker(str(tmp_path / "test.nc"), files_format="NETCDF")
    actual = checker.check_completeness(None, None, None, False)
    expected = {str(tmp_path / "test.nc"): {"wrong0", "wrong1"}}

    actual = checker.check_completeness(None, None, {"ok", "wrong0"}, False)
    expected = {str(tmp_path / "test.nc"): {"wrong0"}}
    assert actual == expected


@pytest.mark.parametrize("create_mask_file", [True, False])
@pytest.mark.parametrize("ensure_null", [True, False])
def test_completeness_with_mask(
    tmp_path: pathlib.Path, create_mask_file: bool, ensure_null: bool
) -> None:
    # Write mask
    mask = xr.DataArray([None, 1], name="mask")
    # Write dataset
    ds = xr.Dataset(
        {
            "ok0": xr.DataArray([None, 1]),
            "ok1": xr.DataArray([None, None], dims=("bar",)),
            "wrong0": xr.DataArray([1, None]),
            "wrong1": xr.DataArray([None, None]),
            "wrong2": xr.DataArray([1, 1]),
        }
    )
    if create_mask_file:
        mask_file = str(tmp_path / "mask.nc")
        mask.to_netcdf(mask_file)
    else:
        mask_file = None
        ds["mask"] = mask
    ds.to_netcdf(tmp_path / "test.nc")

    checker = Checker(str(tmp_path / "test.nc"), files_format="NETCDF")
    actual = checker.check_completeness("mask", mask_file, None, ensure_null)
    if ensure_null:
        expected = {str(tmp_path / "test.nc"): {"wrong0", "wrong1", "wrong2"}}
    else:
        expected = {str(tmp_path / "test.nc"): {"wrong0", "wrong1"}}
    assert actual == expected

    actual = checker.check_completeness(
        "mask", mask_file, {"ok0", "wrong0"}, ensure_null
    )
    expected = {str(tmp_path / "test.nc"): {"wrong0"}}
    assert actual == expected
