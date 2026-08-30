import json
from harness import ROOT, base_request, preserve_request


def main():
    request = json.loads((ROOT / "requests/disordered_weaklink_odd.json").read_text())
    request.update(case_id="disordered_weaklink_cap12_odd", bond_cap=12)
    preserve_request(request, "low_cap_disordered_parity_allocation",
                     "A measured sub-screen v3-v4 difference at bond 24 motivates the advertised lower bond cap; comparisons must remain at cap 12")
    request = base_request("crossover_cap12_even", -0.024, "even")
    request["bond_cap"] = 12
    preserve_request(request, "low_cap_finite_basis_crossover",
                     "Mass lies between measured finite-basis parity-response endpoints -0.020 and -0.034; tests low-cap variational allocation, not an asserted critical point")


if __name__ == "__main__":
    main()
