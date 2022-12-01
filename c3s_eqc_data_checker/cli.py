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
import textwrap
from typing import Any

import rich
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
        )
    ],
)


def errors_to_list_of_strings(
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
            errors_to_list_of_strings(value, prints, nest + 1)
        elif isinstance(value, str):
            prefix = f"{tab}{key}: "
            header, *lines = value.splitlines()
            prints.append(f"{prefix}{header}")
            prefix = " " * len(prefix)
            for line in lines:
                prints.append(f"{prefix}{line}")
        else:
            prints.append(f"{tab}{key}: {value!r}")
    return prints


def template_callback(value: bool) -> None:
    if value:
        toml_string = f"# Template configuration file for data-checker v{c3s_eqc_data_checker.__version__}\n"
        toml_string += textwrap.dedent(c3s_eqc_data_checker.Checker.__doc__ or "")
        toml_string += "\n".join(
            [
                "",
                "# All checks are optional (skip checks removing their sections).",
                "# Unless otherwise specified, optional arguments default to None.",
                "",
            ]
        )

        for check_name in c3s_eqc_data_checker.Checker.available_checks():
            toml_string += textwrap.dedent(
                getattr(c3s_eqc_data_checker.Checker, f"check_{check_name}").__doc__
            )
        print(toml_string)
        raise typer.Exit()


def version_callback(value: bool) -> None:
    if value:
        print(c3s_eqc_data_checker.__version__)
        raise typer.Exit()


CONFIGFILE = typer.Argument(..., help="Path to configuration file.")
TEMPLATE = typer.Option(
    False,
    "--template-configfile",
    help="Show configuration file template and exit.",
    callback=template_callback,
)
VERSION = typer.Option(
    False, "--version", help="Show version and exit.", callback=version_callback
)


def data_checker(
    configfile: str = CONFIGFILE, template: bool = TEMPLATE, version: bool = VERSION
) -> None:
    logging.info(f"VERSION: {c3s_eqc_data_checker.__version__}")
    logging.info(f"CONFIGFILE: {pathlib.Path(configfile).resolve()}")

    configchecker = c3s_eqc_data_checker.ConfigChecker(configfile)
    counter: dict[str, int] = collections.defaultdict(int)
    summary = ["[bold]SUMMARY:[/]"]

    for check_name in configchecker.checker.available_checks():
        if check_name not in configchecker.config:
            counter["SKIPPED"] += 1
            summary.append(f"{check_name}: [yellow]SKIPPED[/]")
            continue

        logging.info(f"Checking {check_name}")
        try:
            errors = configchecker.check(check_name)
        except Exception:
            counter["FAILED"] += 1
            summary.append(f"{check_name}: [red]FAILED[/]")
            logging.exception(check_name)
        else:
            if errors:
                counter["FAILED"] += 1
                summary.append(f"{check_name}: [red]FAILED[/]")
                logging.error(f"[bold]{check_name}[/]")
                for line in errors_to_list_of_strings(errors):
                    logging.error(line, extra={"highlighter": None})
            else:
                counter["PASSED"] += 1
                summary.append(f"{check_name}: [green]PASSED[/]")

    for key in ("PASSED", "SKIPPED", "FAILED"):
        summary.append(f"[bold]{key}: {counter[key]}[/]")
    for line in summary:
        logging.info(line)
    raise typer.Exit(code=counter["FAILED"] != 0)
