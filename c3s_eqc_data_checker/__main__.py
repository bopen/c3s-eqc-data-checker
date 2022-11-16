import typer

from . import check

CHECKS = (
    "format",
    "variable_attributes",
    "temporal_resolution",
    "horizontal_resolution",
    "vertical_resolution",
    "global_attributes",
    "cf_compliance",
)


def main(configfile: str) -> None:
    checker = check.ConfigChecker(configfile)
    for check_name in CHECKS:
        checker.check(check_name)


def run() -> None:
    typer.run(main)


if __name__ == "__main__":
    run()
