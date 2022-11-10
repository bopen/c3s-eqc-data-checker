import pathlib

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


def test_global_attrs(tmp_path: pathlib.Path) -> None:
    ds = xr.Dataset(attrs={"a": "a", "b": "b", "c": "c"})
    ds.to_netcdf(tmp_path / "test.nc")

    checker = Checker(str(tmp_path / "test.nc"), format="NETCDF")
    actual = checker.check_global_attributes(a=None, b="b", c="wrong", d="d")
    expected = {str(tmp_path / "test.nc"): {"c": "c", "d": None}}
    assert actual == expected


def test_cf_compliance(tmp_path: pathlib.Path) -> None:
    ds = xr.Dataset({"foo": ("dim_0", [None], {"standard_name": "air_temperature"})})
    ds.to_netcdf(tmp_path / "compliant.nc")
    ds["foo"].attrs["standard_name"] = "unknown"
    ds.to_netcdf(tmp_path / "non-compliant.nc")

    checker = Checker(str(tmp_path / "*compliant.nc"), format="NETCDF")
    actual = checker.check_cf_compliance()
    assert set(actual) == {str(tmp_path / "non-compliant.nc")}
