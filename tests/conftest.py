import pathlib

import eccodes
import pytest


@pytest.fixture
def grib_path() -> pathlib.Path:
    return pathlib.Path(eccodes.codes_samples_path())
