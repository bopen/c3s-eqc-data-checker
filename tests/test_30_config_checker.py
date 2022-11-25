import pathlib

import toml

from c3s_eqc_data_checker import Checker, ConfigChecker


def test_config_checker_init(tmp_path: pathlib.Path, grib_path: pathlib.Path) -> None:
    grib_file = str(grib_path / "GRIB1.tmpl")
    toml_file = tmp_path / "test.toml"
    with toml_file.open("w") as f:
        toml.dump(
            {
                "files_pattern": grib_file,
                "files_format": "GRIB",
            },
            f,
        )

    expected = Checker(grib_file, "GRIB")
    actual = ConfigChecker(toml_file).checker
    assert expected == actual


def test_config_checker_check(tmp_path: pathlib.Path, grib_path: pathlib.Path) -> None:
    grib_file = str(grib_path / "GRIB1.tmpl")
    toml_file = tmp_path / "test.toml"
    with toml_file.open("w") as f:
        toml.dump(
            {
                "files_pattern": grib_file,
                "files_format": "GRIB",
                "format": {"version": 2},
            },
            f,
        )
    expected = Checker(grib_file, "GRIB").check_format(version=2)
    actual = ConfigChecker(toml_file).check("format")
    assert expected == actual != {}
