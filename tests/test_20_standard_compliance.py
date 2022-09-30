import pathlib

import pytest
import xarray as xr

from c3s_eqc_data_checker import standard_compliance


@pytest.mark.filterwarnings(
    "ignore:Converting `np.character` to a dtype is deprecated."
)
@pytest.mark.parametrize(
    "ds,error",
    [
        (xr.Dataset(attrs={"Conventions": "CF-1.6"}), False),
        (xr.Dataset(attrs={"Conventions": "error"}), True),
    ],
)
def test_standard_compliance_netcdf(
    tmpdir: pathlib.Path, ds: xr.Dataset, error: bool
) -> None:
    filename = str(tmpdir / "test.nc")
    ds.to_netcdf(filename)
    sc = standard_compliance.StandardCompliance(filename)

    if error:
        with pytest.raises(standard_compliance.StandardComplianceError):
            sc.check_standard_compliance()
    else:
        sc.check_standard_compliance()
