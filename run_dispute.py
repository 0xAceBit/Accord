from __future__ import annotations

import argparse


def resolve_dispute(role: str, salary_offered: int, salary_expected: int) -> str:
    if salary_offered == salary_expected:
        return f"{role}: terms aligned at {salary_offered} USDC/month."

    verdict = round((salary_offered + salary_expected) / 2)
    return (
        f"{role}: settle at {verdict} USDC/month "
        f"between the offered {salary_offered} and expected {salary_expected}."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the dispute contract logic locally.")
    parser.add_argument("--role", default="Senior Engineer")
    parser.add_argument("--offered", type=int, default=100_000)
    parser.add_argument("--expected", type=int, default=120_000)
    args = parser.parse_args()
    print(resolve_dispute(args.role, args.offered, args.expected))
