import pathlib

import eccodes
import pytest

from c3s_eqc_data_checker import Checker


@pytest.fixture
def grib_path() -> pathlib.Path:
    return pathlib.Path(eccodes.codes_samples_path())


def test_format(grib_path: pathlib.Path) -> None:
    checker = Checker(str(grib_path / "GRIB*.tmpl"), format="GRIB")
    assert checker.check_format(2) == {str(grib_path / "GRIB1.tmpl"): "GRIB1"}


def test_variable_attrs(grib_path: pathlib.Path) -> None:
    checker = Checker(str(grib_path / "GRIB*.tmpl"), format="GRIB")
    actual = checker.check_variable_attributes(
        t=dict(edition=2, cfName=None, cfVarName="t", units="wrong", foo="foo")
    )
    expected = {
        str(grib_path / "GRIB1.tmpl"): {"t": None},
        str(grib_path / "GRIB2.tmpl"): {"t": {"units": "K", "foo": None}},
    }

    assert expected == actual


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


def test_temporal_resolution(grib_path: pathlib.Path) -> None:
    checker = Checker(str(grib_path / "GRIB2.tmpl"), format="GRIB")
    actual = checker.check_temporal_resolution(
        "time", "2007-03-23T12", "2007-03-23T12", "0"
    )
    assert actual == {}

    actual = checker.check_temporal_resolution(
        "time", "1907-03-23T12", "1907-03-23T12", "1D"
    )
    expected = {
        "max": "2007-03-23T12:00:00.000000000",
        "min": "2007-03-23T12:00:00.000000000",
        "resolution": "0",
    }
    assert actual == expected


def test_horizontal_grid(grib_path: pathlib.Path) -> None:
    checker = Checker(str(grib_path / "GRIB2.tmpl"), format="GRIB")
    actual = checker.check_horizontal_grid(gridtype="lonlat", xinc="2", yinc="-2")
    assert actual == {}

    actual = checker.check_horizontal_grid(xinc="2", yinc="wrong", foo="foo")
    expected = {str(grib_path / "GRIB2.tmpl"): {"yinc": "-2", "foo": None}}
    assert actual == expected
