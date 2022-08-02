import c3s_eqc_data_checker


def test_version() -> None:
    assert c3s_eqc_data_checker.__version__ != "999"
