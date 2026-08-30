import os
import sys

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import copy
import unittest

from assemble import coefficient_profile_key, distinct_profile_selection, family_for, hamiltonian_key, in_bounds, problem_key


def request_for_test():
    return {"version": 1, "case_id": "test", "seed": 1, "n_sites": 32, "local_dim": 8, "bond_cap": 12,
            "sector": "odd", "omega": [1.0] * 32, "mass2": [-0.04] * 32,
            "lambda4": [0.1] * 32, "coupling": [1.0] * 31, "field": [0.0] * 32}


class ProposalTests(unittest.TestCase):
    def test_distinct_physics_families(self):
        request = request_for_test()
        self.assertEqual(family_for(request), "odd_weak_critical")
        request["sector"] = "any"
        self.assertEqual(family_for(request), "symmetry_restoration")
        request["field"] = [1e-5] * 32
        self.assertEqual(family_for(request), "weak_field_response")
        request["coupling"][15] = 0.5
        self.assertEqual(family_for(request), "critical_profiles")

    def test_bounds_and_field_sector_contract(self):
        request = request_for_test()
        self.assertTrue(in_bounds(request))
        request["field"][0] = 1e-5
        self.assertFalse(in_bounds(request))
        request["sector"] = "any"
        self.assertTrue(in_bounds(request))
        request["coupling"][0] = 0.049
        self.assertFalse(in_bounds(request))
        request["coupling"][0] = 0.05
        request["field"] = request["field"][:-1]
        self.assertFalse(in_bounds(request))

    def test_hamiltonian_and_target_problem_counts(self):
        first = request_for_test()
        second = copy.deepcopy(first)
        second.update(case_id="renamed", seed=7, budget_seconds=6, wall_seconds=30)
        self.assertEqual(hamiltonian_key(first), hamiltonian_key(second))
        self.assertEqual(problem_key(first), problem_key(second))
        second.update(sector="any", bond_cap=24)
        self.assertEqual(hamiltonian_key(first), hamiltonian_key(second))
        self.assertNotEqual(problem_key(first), problem_key(second))
        second["field"][0] = 1e-5
        self.assertNotEqual(hamiltonian_key(first), hamiltonian_key(second))

    def test_selection_avoids_basis_only_duplicates(self):
        first = request_for_test()
        second = copy.deepcopy(first)
        second["omega"] = [0.65] * 32
        third = copy.deepcopy(first)
        third["mass2"] = [-0.035] * 32
        self.assertEqual(coefficient_profile_key(first), coefficient_profile_key(second))
        self.assertNotEqual(hamiltonian_key(first), hamiltonian_key(second))
        candidates = [{"record": {"request": request}} for request in (first, second, third)]
        self.assertEqual(distinct_profile_selection(candidates), [candidates[0], candidates[2]])


if __name__ == "__main__":
    unittest.main()
