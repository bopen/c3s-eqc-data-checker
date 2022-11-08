import pathlib

import eccodes
import netCDF4
import pytest

import c3s_eqc_data_checker


@pytest.fixture
def grib_path() -> pathlib.Path:
    return pathlib.Path(eccodes.codes_samples_path())


def test_netcdf_format(tmp_path: pathlib.Path) -> None:
    for format in ("NETCDF4", "NETCDF3_CLASSIC"):
        with netCDF4.Dataset(tmp_path / f"{format}.nc", "w", format=format):
            pass

    overview = c3s_eqc_data_checker.Overview(str(tmp_path / "NETCDF*.nc"))
    assert overview.check_format("NETCDF", 4) == {
        str(tmp_path / "NETCDF3_CLASSIC.nc"): "NETCDF3_CLASSIC"
    }


def test_grib_format(grib_path: pathlib.Path) -> None:
    overview = c3s_eqc_data_checker.Overview(str(grib_path / "GRIB*.tmpl"))
    assert overview.check_format("GRIB", 2) == {str(grib_path / "GRIB1.tmpl"): "GRIB1"}
