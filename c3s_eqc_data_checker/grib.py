from typing import Any

from . import baseformat


class Grib(baseformat.BaseFormat):
    @property
    def engine(self) -> str:
        return "cfgrib"

    @property
    def full_format(self) -> str:
        edition = self.ds.attrs.get("GRIB_edition", "")
        return f"GRIB{edition}"

    @property
    def global_attrs(self) -> dict[str, Any]:
        return {
            k.split("GRIB_", 1)[-1]: v
            for k, v in self.ds.attrs.items()
            if k.startswith("GRIB_")
        }
