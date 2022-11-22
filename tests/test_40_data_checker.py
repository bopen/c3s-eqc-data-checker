import pathlib
import subprocess

import pytest
import toml


@pytest.mark.parametrize("grib_version, expected", [("2", "PASSED"), ("1", "FAILED")])
def test_data_checker(
    tmp_path: pathlib.Path, grib_path: pathlib.Path, grib_version: str, expected: str
) -> None:
    with (tmp_path / "test.toml").open("w") as f:
        toml.dump(
            {
                "files_pattern": str(grib_path / "GRIB2.tmpl"),
                "files_format": "GRIB",
                "format": {"version": grib_version},
            },
            f,
        )
    res = subprocess.run(
        ["data-checker", str(tmp_path / "test.toml")], capture_output=True, text=True
    )
    assert f"format: {expected}" in res.stdout
    if expected == "FAILED":
        assert "FAILED: 1" in res.stdout and "PASSED: 0" in res.stdout
    else:
        assert "FAILED: 0" in res.stdout and "PASSED: 1" in res.stdout
