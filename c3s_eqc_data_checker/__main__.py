import logging
from typing import Any

import rich.logging
import typer

import c3s_eqc_data_checker

logging.basicConfig(
    level="INFO",
    format="%(message)s",
    handlers=[rich.logging.RichHandler(rich_tracebacks=True)],
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
            if set(value) == {"FATAL", "ERROR", "WARN", "INFO", "VERSION"}:
                # CFChecks
                for log in ("FATAL", "ERROR"):
                    for line in value[log]:
                        prints.append(f"{tab}{key}: {line}")
            else:
                prints.append(f"{tab}{key}:")
                make_error_prints(value, prints, nest + 1)
        else:
            prints.append(f"{tab}{key}: {value!r}")
    return prints


def main(
    configfile: str = typer.Argument(..., help="Path to configuration file")
) -> None:
    logging.info(f"CONFIGFILE: {configfile}")

    checker = c3s_eqc_data_checker.ConfigChecker(configfile)
    error_count = 0
    reports = []

    for check_name in checker.available_checks:
        if check_name not in checker.config:
            reports.append(f"{check_name}: [yellow]SKIPPED[/]")
            continue

        logging.info(f"Checking {check_name}")
        try:
            errors = checker.check(check_name)
        except Exception:
            error_count += 1
            reports.append(f"{check_name}: [red]ERROR[/]")
            logging.exception("FATAL ERROR")
        else:
            reports.append(
                f"{check_name}: {'[red]ERROR[/]' if errors else '[green]PASSED[/]'}"
            )
            if errors:
                error_count += 1
                logging.error("\n".join(make_error_prints(errors)))

    logging.info("\n".join(reports), extra={"markup": True})
    logging.info(f"[bold]Number of errors: {error_count}[/]", extra={"markup": True})
    raise typer.Exit(code=error_count != 0)


def run() -> None:
    logging.info(f"VERSION: {c3s_eqc_data_checker.__version__}")
    typer.run(main)


if __name__ == "__main__":
    run()
