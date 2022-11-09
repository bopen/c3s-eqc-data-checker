from typing import Any

from . import baseformat

import eccodes


class Grib(baseformat.BaseFormat):
    @property
    def full_format(self) -> str:
        with open(self.path, "r") as f:
            msgid = eccodes.codes_any_new_from_file(f)
            edition = eccodes.codes_get(msgid, "edition")
            eccodes.codes_release(msgid)
        return f"GRIB{edition}"

    @property
    def global_attrs(self) -> dict[str, Any]:
        raise NotImplementedError
