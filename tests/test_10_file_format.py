import os
import pathlib
from typing import Literal

import eccodes
import pytest
import xarray as xr

from c3s_eqc_data_checker import file_format


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
    format: Literal["NETCDF4", "NETCDF4_CLASSIC", "NETCDF3_64BIT", "NETCDF3_CLASSIC"],
    error: bool,
) -> None:
    filename = str(tmpdir / "test.nc")
    xr.Dataset({"foo": [0]}).to_netcdf(filename, format=format)
    ff = file_format.FileFormat(filename)

    assert ff.is_grib is False
    assert ff.is_netcdf is True
    if error:
        with pytest.raises(file_format.FileFormatError):
            ff.check_file_format()
    else:
        ff.check_file_format()


@pytest.mark.parametrize("sample,error", [("GRIB1", True), ("GRIB2", False)])
def test_file_format_grib(tmpdir: pathlib.Path, sample: str, error: bool) -> None:
    eccodes_filename = os.path.join(eccodes.codes_samples_path(), sample + ".tmpl")
    filename = os.path.join(tmpdir, sample + ".grib")
    os.symlink(eccodes_filename, filename)

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
