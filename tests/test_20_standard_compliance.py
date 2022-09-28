import datetime
import pathlib

import pytest
import xarray as xr

from c3s_eqc_data_checker import standard_compliance


@pytest.fixture
def ds() -> xr.Dataset:
    ds_dict = {
        "coords": {
            "longitude": {
                "dims": ("longitude",),
                "attrs": {"units": "degrees_east", "long_name": "longitude"},
                "data": [0.0],
            },
            "latitude": {
                "dims": ("latitude",),
                "attrs": {"units": "degrees_north", "long_name": "latitude"},
                "data": [90.0],
            },
            "time": {
                "dims": ("time",),
                "attrs": {"long_name": "time"},
                "data": [datetime.datetime(2012, 12, 1, 12, 0)],
            },
        },
        "attrs": {
            "Conventions": "CF-1.6",
        },
        "dims": {"longitude": 1, "latitude": 1, "time": 1},
        "data_vars": {
            "t2m": {
                "dims": ("time", "latitude", "longitude"),
                "attrs": {"units": "K", "long_name": "2 metre temperature"},
                "data": [[[260.9814758300781]]],
            }
        },
    }
    return xr.Dataset.from_dict(ds_dict)


@pytest.mark.filterwarnings(
    "ignore:Converting `np.character` to a dtype is deprecated."
)
@pytest.mark.parametrize("error", [True, False])
def test_standard_compliance_netcdf(
    tmpdir: pathlib.Path, ds: xr.Dataset, error: bool
) -> None:
    if error:
        ds.attrs["Conventions"] = "foo"

    filename = str(tmpdir / "test.nc")
    ds.to_netcdf(filename)
    sc = standard_compliance.StandardCompliance(filename)

    if error:
        with pytest.raises(standard_compliance.StandardComplianceError):
            sc.check_standard_compliance()
    else:
        sc.check_standard_compliance()
