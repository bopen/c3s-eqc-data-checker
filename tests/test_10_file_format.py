import pathlib
from typing import Any, Literal

import cfgrib.xarray_to_grib
import numpy as np
import pandas as pd
import pytest
import xarray as xr

from c3s_eqc_data_checker import file_format


@pytest.fixture()
def ds() -> xr.Dataset:
    coords: list[Any] = [
        pd.date_range("2018-01-01T00:00", "2018-01-02T12:00", periods=4),
        pd.timedelta_range(0, "12h", periods=2),
        [1000.0, 850.0, 500.0],
        np.linspace(90.0, -90.0, 5),
        np.linspace(0.0, 360.0, 6, endpoint=False),
    ]
    da = xr.DataArray(
        np.zeros((4, 2, 3, 5, 6)),
        coords=coords,
        dims=["time", "step", "isobaricInhPa", "latitude", "longitude"],
    )
    return da.to_dataset(name="t")


@pytest.mark.parametrize(
    "format,error",
    [
        ("NETCDF4", False),
        ("NETCDF4_CLASSIC", False),
        ("NETCDF3_64BIT", True),
        ("NETCDF3_CLASSIC", True),
    ],
)
def test_file_format_netcdf(
    tmpdir: pathlib.Path,
    ds: xr.Dataset,
    format: Literal["NETCDF4", "NETCDF4_CLASSIC", "NETCDF3_64BIT", "NETCDF3_CLASSIC"],
    error: bool,
) -> None:
    filename = str(tmpdir / "test.nc")
    ds.to_netcdf(filename, format=format)
    ff = file_format.FileFormat(filename)

    assert ff.is_grib is False
    assert ff.is_netcdf is True
    if error:
        with pytest.raises(file_format.FileFormatError):
            ff.check_file_format()
    else:
        ff.check_file_format()


@pytest.mark.parametrize("edition,error", [(1, True), (2, False)])
@pytest.mark.filterwarnings(
    "ignore:GRIB write support is experimental, DO NOT RELY ON IT!"
)
@pytest.mark.filterwarnings(
    "ignore:distutils Version classes are deprecated. Use packaging.version instead."
)
def test_file_format_grib(
    tmpdir: pathlib.Path, ds: xr.Dataset, edition: int, error: bool
) -> None:
    filename = str(tmpdir / "test.grib")
    cfgrib.xarray_to_grib.to_grib(ds, filename, grib_keys={"edition": edition})
    ff = file_format.FileFormat(filename)

    assert ff.is_grib is True
    assert ff.is_netcdf is False
    if error:
        with pytest.raises(file_format.FileFormatError):
            ff.check_file_format()
    else:
        ff.check_file_format()


def test_file_format_error() -> None:
    ff = file_format.FileFormat("foo.txt")
    with pytest.raises(file_format.FileFormatError):
        ff.check_file_format()
