import subprocess

import toml

import c3s_eqc_data_checker.__main__


def test_template_configfile() -> None:
    res = subprocess.run(
        ["data-checker", "--template-configfile"],
        capture_output=True,
        text=True,
    )
    actual = set(toml.loads(res.stdout))
    available_checks = c3s_eqc_data_checker.__main__.available_checks()
    assert {"files_pattern", "files_format"} | set(available_checks) == actual
