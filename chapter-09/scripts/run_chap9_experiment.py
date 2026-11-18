from __future__ import annotations

from rca.experiment_runner import run_all_workloads


def main() -> None:
    # This script is kept very small. The main contract is implemented in
    # run.py which also writes the required evidence file.
    runs = run_all_workloads()
    for r in runs:
        print(r)


if __name__ == "__main__":
    main()
