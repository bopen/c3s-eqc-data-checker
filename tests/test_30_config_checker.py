import pathlib

import toml

from c3s_eqc_data_checker import Checker, ConfigChecker


def test_initialize_checker(tmp_path: pathlib.Path) -> None:
    with (tmp_path / "test.toml").open("w") as f:
        toml.dump({"files_pattern": str(tmp_path), "files_format": "GRIB"}, f)
    expected = Checker(str(tmp_path), "GRIB")
    actual = ConfigChecker(tmp_path / "test.toml").checker
    assert expected == actual
