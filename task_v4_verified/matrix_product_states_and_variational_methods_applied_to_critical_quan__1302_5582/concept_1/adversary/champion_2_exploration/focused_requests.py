import numpy as np

from harness import ROOT, base_request, preserve_request, write_json


def main():
    length = 64
    coordinate = np.linspace(0, 1, length)
    generator = np.random.default_rng(1302558220)
    planned = []

    def retain(request, family, rationale):
        preserve_request(request, family, rationale)
        planned.append({"case_id": request["case_id"], "family": family,
                        "sector": request["sector"], "bond_cap": request["bond_cap"], "rationale": rationale})

    request = base_request("f2_odd_asymmetric_links", -0.025, "odd")
    request["bond_cap"] = 12
    request["mass2"] = (-0.025 + 0.006 * np.sin(5 * np.pi * coordinate)
                        + generator.uniform(-0.0035, 0.0035, length)).tolist()
    request["coupling"] = generator.uniform(0.85, 1.5, length - 1).tolist()
    for bond, strength in ((10, 0.05), (29, 0.075), (48, 0.05)):
        request["coupling"][bond] = strength
    retain(request, "odd_disordered_weak_regions", "Unequal region lengths and independently drawn disorder test transferability of the allocation trap")

    request = base_request("f2_even_random_blocks", -0.026, "even")
    request["bond_cap"] = 12
    request["mass2"] = (-0.026 + generator.uniform(-0.009, 0.009, length)).tolist()
    request["coupling"] = generator.uniform(0.75, 1.5, length - 1).tolist()
    request["coupling"][18], request["coupling"][40] = 0.05, 0.075
    retain(request, "even_inhomogeneous_restoration", "Even ground-sector allocation in three spatially random regions, not an odd-case parity flip alone")

    request = base_request("f2_odd_edge_islands", -0.022, "odd")
    request["bond_cap"] = 12
    request["mass2"] = (-0.018 - 0.018 * np.exp(-((coordinate - 0.06) / 0.09) ** 2)
                        - 0.024 * np.exp(-((coordinate - 0.90) / 0.13) ** 2)
                        + generator.uniform(-0.002, 0.002, length)).tolist()
    request["coupling"] = generator.uniform(1.1, 1.5, length - 1).tolist()
    for bond, strength in ((7, 0.06), (35, 0.10), (54, 0.05)):
        request["coupling"][bond] = strength
    retain(request, "odd_competing_excitation_regions", "Inequivalent soft boundary islands with weak contacts and a stiffer interior")

    request = base_request("f2_even_quartic_interfaces", -0.03, "even")
    request["bond_cap"] = 12
    request["lambda4"] = np.repeat([0.05, 0.09, 0.07, 0.12], 16).tolist()
    request["mass2"] = (np.repeat([-0.022, -0.038, -0.030, -0.050], 16)
                        + 0.003 * np.cos(7 * np.pi * coordinate)).tolist()
    request["coupling"] = np.repeat([1.5, 1.0, 1.3, 1.15], 16)[:63].tolist()
    for bond, strength in ((15, 0.08), (31, 0.12), (47, 0.06)):
        request["coupling"][bond] = strength
    retain(request, "even_inhomogeneous_restoration", "Four quartic and spring regions test ground-sector restoration across physically different interfaces")

    request = base_request("f2_odd_correlated_disorder", -0.026, "odd")
    request["bond_cap"] = 14
    request["mass2"] = (-0.026 + 0.007 * np.cos(4 * np.pi * coordinate)
                        + generator.uniform(-0.002, 0.002, length)).tolist()
    request["omega"] = (0.60 + 0.05 * np.sin(2 * np.pi * coordinate)).tolist()
    request["coupling"] = np.clip(1.16 + 0.25 * np.cos(5 * np.pi * coordinate[:-1])
                                  + generator.uniform(-0.08, 0.08, length - 1), 0.8, 1.5).tolist()
    request["coupling"][21], request["coupling"][44] = 0.05, 0.08
    retain(request, "odd_disordered_weak_regions", "Correlated mass and spring disorder at a different cap and site-dependent oscillator basis")

    request = base_request("f2_even_dimerized", -0.034, "even")
    request["bond_cap"] = 14
    request["mass2"] = (-0.034 + generator.uniform(-0.004, 0.004, length)).tolist()
    request["coupling"] = [1.5 if bond % 2 == 0 else 0.65 for bond in range(length - 1)]
    request["coupling"][19], request["coupling"][43] = 0.05, 0.05
    retain(request, "even_inhomogeneous_restoration", "Dimerized internal springs and two weak contacts change the entanglement allocation pattern")

    request = base_request("f2_odd_mixed_quartic", -0.03, "odd")
    request["bond_cap"] = 16
    request["lambda4"] = np.repeat([0.05, 0.075, 0.11, 0.065], 16).tolist()
    request["mass2"] = (np.repeat([-0.024, -0.033, -0.046, -0.029], 16)
                        + 0.003 * np.sin(5 * np.pi * coordinate)).tolist()
    request["omega"] = np.repeat([0.55, 0.60, 0.55, 0.65], 16).tolist()
    request["coupling"] = np.repeat([1.5, 1.15, 1.4, 0.95], 16)[:63].tolist()
    for bond, strength in ((15, 0.07), (31, 0.09), (47, 0.05)):
        request["coupling"][bond] = strength
    retain(request, "odd_competing_excitation_regions", "Odd excitation in four nonidentical quartic regions at bond 16")

    request = base_request("f2_odd_three_soft_regions", 0.008, "odd")
    request["bond_cap"] = 12
    sites = np.arange(length)
    request["mass2"] = (0.008 - 0.046 * np.exp(-((sites - 10) / 6) ** 4)
                        - 0.043 * np.exp(-((sites - 30) / 7) ** 4)
                        - 0.048 * np.exp(-((sites - 53) / 7) ** 4)).tolist()
    request["coupling"] = (1.25 + 0.20 * np.cos(3 * np.pi * coordinate[:-1])).tolist()
    request["coupling"][20], request["coupling"][41] = 0.05, 0.06
    retain(request, "odd_competing_excitation_regions", "Three separated low-mass islands with positive-mass bridges and inequivalent contacts")

    request = base_request("f2_even_disordered_crossover", -0.0218, "even")
    request["bond_cap"] = 16
    request["mass2"] = (-0.0218 + 0.0024 * np.sin(3 * np.pi * coordinate)
                        + generator.uniform(-0.001, 0.001, length)).tolist()
    request["coupling"] = generator.uniform(1.35, 1.5, length - 1).tolist()
    retain(request, "finite_basis_convergence_control", "Weakly disordered crossover coordinate selected from the measured finite-basis parity-response bracket")

    request = base_request("f2_odd_uniform_crossover", -0.023, "odd")
    request["bond_cap"] = 20
    retain(request, "finite_basis_convergence_control", "Uniform odd-sector crossover control at a larger cap, without changing the advertised size domain")

    request = base_request("f2_field_softmode", -0.024, "any")
    request["bond_cap"] = 12
    request["mass2"] = (-0.024 + 0.004 * np.sin(2 * np.pi * coordinate)).tolist()
    request["coupling"] = [1.3] * (length - 1)
    request["field"] = (2e-5 * np.cos(np.pi * coordinate)).tolist()
    retain(request, "weak_field_near_restoration", "Nonzero smooth competing field removes exact parity blocking while retaining a weak collective response")

    request = base_request("f2_field_competing_regions", -0.035, "any")
    request["bond_cap"] = 14
    request["lambda4"] = np.concatenate([np.full(12, 0.05), np.full(23, 0.06), np.full(17, 0.08), np.full(12, 0.05)]).tolist()
    request["mass2"] = np.concatenate([np.full(12, -0.034), np.full(23, -0.040), np.full(17, -0.051), np.full(12, -0.034)]).tolist()
    request["field"] = np.concatenate([np.full(12, 0.0013), np.full(23, -0.0011), np.full(17, 0.0010), np.full(12, -0.0015)]).tolist()
    request["coupling"] = [1.25] * (length - 1)
    for bond, strength in ((11, 0.05), (34, 0.07), (51, 0.05)):
        request["coupling"][bond] = strength
    retain(request, "weak_field_competing_domains", "Unequal tilted regions with distinct quartics test unrestricted variational quality, not a parity-only implementation")

    write_json(ROOT / "tranche_2/PLAN.json", {"initial_configurations": planned,
               "additional_cpu_limit_seconds": 1200, "scientific_screen_total": 6.4e-6,
               "max_initial_configurations": 12, "domain_extension": False,
               "formal_generation": False, "critical_point_certified": False})
    print("\n".join(entry["case_id"] for entry in planned))


if __name__ == "__main__":
    main()
