import pathlib
import subprocess
import textwrap

import toml

import c3s_eqc_data_checker


def parse_stdout(stdout: str) -> str:
    """Parse stdout to join lines split because of terminal size."""
    lines = []
    for line in stdout.splitlines():
        line = line.rstrip()
        if line.split()[0] in {
            "CRITICAL",
            "ERROR",
            "WARNING",
            "INFO",
            "DEBUG",
        } or not line.startswith(" "):
            lines.append(line)
        else:
            line = (" " if lines[-1].endswith(":") else "") + line.lstrip()
            lines[-1] += line
    stdout = "\n".join(lines)
    return stdout


def test_data_checker(tmp_path: pathlib.Path, grib_path: pathlib.Path) -> None:
    # Create config file
    grib_file = str(grib_path / "reduced_ll_sfc_grib2.tmpl")
    with (tmp_path / "test.toml").open("w") as f:
        toml.dump(
            {
                "files_pattern": grib_file,
                "files_format": "GRIB",
                "format": {"version": "1"},  # fail
                "cf_compliance": {},  # fail
                "completeness": {"foo": "foo"},  # pass with warning
            },
            f,
        )

    # Run checker
    res = subprocess.run(
        ["data-checker", str(tmp_path / "test.toml")],
        capture_output=True,
        text=True,
    )
    stdout = parse_stdout(res.stdout)

    expected = textwrap.dedent(
        f"""\
        INFO     VERSION: {c3s_eqc_data_checker.__version__}
        INFO     CONFIGFILE: {tmp_path / 'test.toml'}
        INFO     Checking cf_compliance
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00
        ERROR    cf_compliance
        ERROR      {grib_file}:
        ERROR        variables:
        ERROR          wvsp1: (3.3): Invalid standard_name: unknown
        ERROR                 (3.1): Invalid units: ~
        INFO     Checking completeness
        WARNING  Unused arguments: foo
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00
        INFO     Checking format
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00
        ERROR    format
        ERROR      {grib_file}: GRIB2
        INFO     SUMMARY:
        INFO     cf_compliance: FAILED
        INFO     completeness: PASSED
        INFO     format: FAILED
        INFO     global_attributes: SKIPPED
        INFO     global_dimensions: SKIPPED
        INFO     horizontal_resolution: SKIPPED
        INFO     temporal_resolution: SKIPPED
        INFO     variable_attributes: SKIPPED
        INFO     variable_dimensions: SKIPPED
        INFO     vertical_resolution: SKIPPED
        INFO     PASSED: 1
        INFO     SKIPPED: 7
        INFO     FAILED: 2"""
    )
    assert stdout == expected
    assert res.returncode


def test_data_checker_identical_errors(
    tmp_path: pathlib.Path, grib_path: pathlib.Path
) -> None:
    # Create config file
    grib_files = str(grib_path / "GRIB*.tmpl")
    with (tmp_path / "test.toml").open("w") as f:
        toml.dump(
            {
                "files_pattern": grib_files,
                "files_format": "GRIB",
                "global_attributes": {"foo": ""},
            },
            f,
        )

    # Run checker
    res = subprocess.run(
        ["data-checker", str(tmp_path / "test.toml")],
        capture_output=True,
        text=True,
    )
    stdout = parse_stdout(res.stdout)

    expected = textwrap.dedent(
        f"""\
        ERROR    global_attributes
        ERROR      {grib_files}:
        ERROR        foo: None"""
    )
    assert expected in stdout
    assert res.returncode
