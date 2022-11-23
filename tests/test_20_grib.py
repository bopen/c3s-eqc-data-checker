import pathlib

from c3s_eqc_data_checker import Checker


def test_format(grib_path: pathlib.Path) -> None:
    checker = Checker(str(grib_path / "GRIB*.tmpl"), files_format="GRIB")
    assert checker.check_format("2") == {str(grib_path / "GRIB1.tmpl"): "GRIB1"}


def test_variable_attrs(grib_path: pathlib.Path) -> None:
    checker = Checker(str(grib_path / "GRIB*.tmpl"), files_format="GRIB")
    actual = checker.check_variable_attributes(
        t=dict(edition=2, cfName="", cfVarName="t", units="wrong", foo="foo")
    )
    expected = {
        str(grib_path / "GRIB1.tmpl"): {"t": None},
        str(grib_path / "GRIB2.tmpl"): {"t": {"units": "K", "foo": None}},
    }

    assert expected == actual


def test_variable_dimensions(grib_path: pathlib.Path) -> None:
    checker = Checker(str(grib_path / "GRIB*.tmpl"), files_format="GRIB")
    actual = checker.check_variable_dimensions(
        t=dict(longitude=16, latitude="", foo=10)
    )
    expected = {
        str(grib_path / "GRIB1.tmpl"): {"t": None},
        str(grib_path / "GRIB2.tmpl"): {"t": {"foo": None}},
    }

    assert expected == actual


def test_global_attrs(grib_path: pathlib.Path) -> None:
    checker = Checker(str(grib_path / "GRIB*.tmpl"), files_format="GRIB")
    actual = checker.check_global_attributes(
        subCentre="", centre="ecmf", edition=2, foo="foo"
    )
    expected = {
        str(grib_path / "GRIB1.tmpl"): {"edition": 1, "foo": None},
        str(grib_path / "GRIB2.tmpl"): {"foo": None},
    }
    assert expected == actual


def test_global_dimensions(grib_path: pathlib.Path) -> None:
    checker = Checker(str(grib_path / "GRIB*.tmpl"), files_format="GRIB")
    actual = checker.check_global_dimensions(longitude=16, latitude="", foo=10)
    expected = {
        str(grib_path / "GRIB1.tmpl"): {"longitude": 360, "foo": None},
        str(grib_path / "GRIB2.tmpl"): {"foo": None},
    }

    assert expected == actual


def test_cf_compliance(tmp_path: pathlib.Path, grib_path: pathlib.Path) -> None:
    (tmp_path / "compliant.grib").symlink_to(grib_path / "GRIB2.tmpl")
    (tmp_path / "non-compliant.grib").symlink_to(
        grib_path / "reduced_ll_sfc_grib2.tmpl"
    )

    checker = Checker(str(tmp_path / "*compliant.grib"), files_format="GRIB")
    actual = checker.check_cf_compliance(None)
    assert set(actual) == {str(tmp_path / "non-compliant.grib")}


def test_temporal_resolution(grib_path: pathlib.Path) -> None:
    checker = Checker(str(grib_path / "GRIB2.tmpl"), files_format="GRIB")
    actual = checker.check_temporal_resolution("2007-03-23T12", "2007-03-23T12", "0")
    assert actual == {}

    actual = checker.check_temporal_resolution("1907-03-23T12", "1907-03-23T12", "1D")
    expected = {
        "max": "2007-03-23T12:00:00.000000000",
        "min": "2007-03-23T12:00:00.000000000",
        "resolution": "0",
    }
    assert actual == expected


def test_horizontal_resolution(grib_path: pathlib.Path) -> None:
    checker = Checker(str(grib_path / "GRIB2.tmpl"), files_format="GRIB")
    actual = checker.check_horizontal_resolution(gridtype="lonlat", xinc="2", yinc="-2")
    assert actual == {}

    actual = checker.check_horizontal_resolution(xinc="2", yinc="wrong", foo="foo")
    expected = {str(grib_path / "GRIB2.tmpl"): {"yinc": "-2", "foo": None}}
    assert actual == expected


def test_vertical_resolution(grib_path: pathlib.Path) -> None:
    checker = Checker(str(grib_path / "GRIB2.tmpl"), files_format="GRIB")
    actual = checker.check_vertical_resolution(
        zaxistype="surface", size="1", levels="0"
    )
    assert actual == {}

    actual = checker.check_vertical_resolution(
        zaxistype="surface", size="wrong", foo="foo"
    )
    expected = {str(grib_path / "GRIB2.tmpl"): {"size": "1", "foo": None}}
    assert actual == expected
