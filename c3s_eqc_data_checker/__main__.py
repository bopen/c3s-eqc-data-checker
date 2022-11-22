# Copyright 2022, European Union.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import collections
import logging
import pathlib
from typing import Any

import rich.logging
import typer

import c3s_eqc_data_checker

logging.basicConfig(
    level="INFO",
    format="%(message)s",
    handlers=[
        rich.logging.RichHandler(
            show_time=False,
            show_path=False,
            rich_tracebacks=True,
            markup=True,
            highlighter=None,
        )
    ],
)


def make_error_prints(
    errors: dict[str, Any],
    prints: list[str] | None = None,
    nest: int = 1,
    indent: int = 2,
) -> list[str]:
    prints = prints or []
    tab = " " * indent * nest
    for key, value in errors.items():
        if isinstance(value, dict):
            prints.append(f"{tab}{key}:")
            make_error_prints(value, prints, nest + 1)
        elif isinstance(value, str):
            for line in value.split("\n"):
                prints.append(f"{tab}{key}: {line}")
        else:
            prints.append(f"{tab}{key}: {value!r}")
    return prints


def main(
    configfile: str = typer.Argument(..., help="Path to configuration file")
) -> None:
    logging.info(f"CONFIGFILE: {pathlib.Path(configfile).resolve()}")

    checker = c3s_eqc_data_checker.ConfigChecker(configfile)
    counter: dict[str, int] = collections.defaultdict(int)
    reports = []

    for check_name in checker.available_checks:
        if check_name not in checker.config:
            counter["SKIPPED"] += 1
            reports.append(f"{check_name}: [yellow]SKIPPED[/]")
            continue

        logging.info(f"Checking {check_name}")
        try:
            errors = checker.check(check_name)
        except Exception:
            counter["FAILED"] += 1
            reports.append(f"{check_name}: [red]FAILED[/]")
            logging.exception(check_name)
        else:
            if errors:
                counter["FAILED"] += 1
                reports.append(f"{check_name}: [red]FAILED[/]")
                logging.error("\n".join([check_name] + make_error_prints(errors)))
            else:
                counter["PASSED"] += 1
                reports.append(f"{check_name}: [green]PASSED[/]")

    for key in ("PASSED", "SKIPPED", "FAILED"):
        reports.append(f"[bold]{key}: {counter[key]}[/]")
    logging.info("\n".join(reports))
    raise typer.Exit(code=counter["FAILED"] == 0)


def run() -> None:
    logging.info(f"VERSION: {c3s_eqc_data_checker.__version__}")
    typer.run(main)


if __name__ == "__main__":
    run()
