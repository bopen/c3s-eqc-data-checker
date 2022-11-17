import logging
from typing import Any

import typer

import c3s_eqc_data_checker

try:
    import rich.logging

    HANDLERS = [rich.logging.RichHandler(rich_tracebacks=True)]
except ImportError:
    HANDLERS = []

logging.basicConfig(level="INFO", format="%(message)s", handlers=HANDLERS)

CHECKS = (
    "format",
    "variable_attributes",
    "variable_dimensions",
    "temporal_resolution",
    "horizontal_resolution",
    "vertical_resolution",
    "global_attributes",
    "global_dimensions",
    "cf_compliance",
)

logging.basicConfig(level="INFO")


def log_errors(errors: dict[str, Any], nest: int = 1, indent: int = 4) -> None:
    tab = " " * indent * nest
    for key, value in errors.items():
        if isinstance(value, dict):
            if set(value) == {"FATAL", "ERROR", "WARN", "INFO", "VERSION"}:
                # CFChecks
                for log in ("FATAL", "ERROR"):
                    for line in value[log]:
                        logging.error(f"{tab}{key}: {line}")
            else:
                logging.error(f"{tab}{key}:")
                log_errors(value, nest + 1)
        else:
            logging.error(f"{tab}{key}: {value}")


def main(configfile: str) -> None:
    checker = c3s_eqc_data_checker.ConfigChecker(configfile)
    logging.info(f"data-checker version {c3s_eqc_data_checker.__version__!r}")
    for check_name in CHECKS:
        if check_name not in checker.config:
            logging.info(f"{check_name}: SKIPPED")
            continue

        logging.info(f"{check_name}: STARTED")
        try:
            errors = checker.check(check_name)
        except Exception:
            logging.exception(f"{check_name}: FATAL ERROR")
        else:
            if errors:
                logging.error(f"{check_name}: ERROR")
                log_errors(errors)
            else:
                logging.info(f"{check_name}: PASSED")


def run() -> None:
    typer.run(main)


if __name__ == "__main__":
    run()
