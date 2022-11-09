import pathlib

import eccodes
import netCDF4
import pytest

from c3s_eqc_data_checker import Checker


@pytest.fixture
def grib_path() -> pathlib.Path:
    return pathlib.Path(eccodes.codes_samples_path())


def test_netcdf_format(tmp_path: pathlib.Path) -> None:
    for format in ("NETCDF4", "NETCDF3_CLASSIC"):
        with netCDF4.Dataset(tmp_path / f"{format}.nc", "w", format=format):
            pass

    checker = Checker(str(tmp_path / "NETCDF*.nc"), format="NETCDF")
    assert checker.check_format(4) == {
        str(tmp_path / "NETCDF3_CLASSIC.nc"): "NETCDF3_CLASSIC"
    }


def test_grib_format(grib_path: pathlib.Path) -> None:
    checker = Checker(str(grib_path / "GRIB*.tmpl"), format="GRIB")
    assert checker.check_format(2) == {str(grib_path / "GRIB1.tmpl"): "GRIB1"}
