import pathlib

import pytest

from c3s_eqc_data_checker import Checker

pytest.importorskip("cfgrib")


@pytest.fixture
def grib_path() -> pathlib.Path:
    import eccodes

    return pathlib.Path(eccodes.codes_samples_path())


def test_format(grib_path: pathlib.Path) -> None:
    checker = Checker(str(grib_path / "GRIB*.tmpl"), format="GRIB")
    assert checker.check_format(2) == {str(grib_path / "GRIB1.tmpl"): "GRIB1"}


def test_global_attrs(grib_path: pathlib.Path) -> None:
    checker = Checker(str(grib_path / "GRIB*.tmpl"), format="GRIB")
    actual = checker.check_global_attributes(
        subCentre=None, centre="ecmf", edition=2, foo="foo"
    )
    expected = {
        str(grib_path / "GRIB1.tmpl"): {"edition": 1, "foo": None},
        str(grib_path / "GRIB2.tmpl"): {"foo": None},
    }
    assert expected == actual


def test_cf_compliance(tmp_path: pathlib.Path, grib_path: pathlib.Path) -> None:
    (tmp_path / "compliant.grib").symlink_to(grib_path / "GRIB2.tmpl")
    (tmp_path / "non-compliant.grib").symlink_to(
        grib_path / "reduced_ll_sfc_grib2.tmpl"
    )

    checker = Checker(str(tmp_path / "*compliant.grib"), format="GRIB")
    actual = checker.check_cf_compliance()
    assert set(actual) == {str(tmp_path / "non-compliant.grib")}
