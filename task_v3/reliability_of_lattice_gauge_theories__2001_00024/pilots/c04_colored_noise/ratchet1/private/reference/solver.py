from accelerated import solve_detailed


def solve(case: dict) -> dict:
    return solve_detailed(case, method="centered_expm")[0]
