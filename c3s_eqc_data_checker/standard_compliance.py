import dataclasses
import functools

import cfchecker.cfchecks

from . import file_format


class StandardComplianceError(Exception):
    pass


@dataclasses.dataclass
class StandardCompliance:
    filename: str

    @functools.cached_property
    def file_format(self) -> file_format.FileFormat:
        return file_format.FileFormat(self.filename)

    def check_standard_compliance(self) -> None:
        if self.file_format.is_netcdf:
            checker = cfchecker.cfchecks.CFChecker(
                silent=True, version=cfchecker.cfchecks.CFVersion()
            )
            checker.checker(self.filename)
            count = checker.get_total_counts()
            if count["FATAL"] or count["ERROR"]:
                raise StandardComplianceError(
                    "\n".join(
                        [f"{self.filename!r} is not CF-compliant."]
                        + checker.all_messages
                    )
                )
