import inspect
import subprocess

import toml

import c3s_eqc_data_checker.cli
from c3s_eqc_data_checker import Checker


def test_template_configfile() -> None:
    res = subprocess.run(
        ["data-checker", "--template-configfile"],
        capture_output=True,
        text=True,
    )
    loaded_toml = toml.loads(res.stdout)

    expected_args = set(inspect.getfullargspec(Checker).args) - {"self"}
    assert expected_args <= set(loaded_toml)

    for check_name in c3s_eqc_data_checker.cli.available_checks():
        assert check_name in set(loaded_toml)

        method = getattr(Checker, f"check_{check_name}")
        fullargsspec = inspect.getfullargspec(method)
        expected_args = set(fullargsspec.args) - {"self"}
        actual_args = set(loaded_toml[check_name])

        if fullargsspec.varkw:
            assert expected_args < actual_args
        else:
            assert expected_args == actual_args
