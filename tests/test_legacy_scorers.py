"""Legacy reference scorer tests (v1.4, v2.0/v2.1, v3.0), part of the PIF 3.5 suite.

Run the whole suite from the repo root:
    python3 -m unittest discover -s tests -v

PIF 3.5 (pif35.py) is the current scorer. The older scorers are kept unchanged so
historical results stay reproducible; these tests pin their documented behavior
(including the two known v3.0 bugs). test_v30_fixed_in_pif35.py checks that 3.5
fixes those bugs. They do not change or endorse any scoring math.
"""

import importlib.util
import math
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, filename))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


v14 = _load("scorer_v14", "scorer.py")
v21 = _load("scorer_v21_bands", "scorer_v21_bands.py")
v3cr = _load("scorer_v3_cost_residue", "scorer_v3_cost_residue.py")
v3 = _load("scorer_3_0", "scorer_3.0.py")


class TestV14Flat(unittest.TestCase):
    def test_requires_20_bricks(self):
        with self.assertRaises(ValueError):
            v14.calculate_pif_score([1.0] * 19)

    def test_full_and_empty(self):
        self.assertEqual(v14.calculate_pif_score([1.0] * 20)["percentage"], 100.0)
        self.assertEqual(v14.calculate_pif_score([0.0] * 20)["tier"], "No detectable self")


class TestV20Layered(unittest.TestCase):
    """v2.0: Total = (C + S*M)/20, M = C/5 (implemented in scorer_v21_bands.v20_score)."""

    def test_readme_overheating_grok_example(self):
        r = v21.v20_score(3.5, 12.0)
        self.assertAlmostEqual(r["M"], 0.7)
        self.assertAlmostEqual(r["percent"], 59.5)

    def test_no_crucible_means_zero(self):
        # README: Grok baseline, no Crucible -> 0%
        self.assertEqual(v21.v20_score(0.0, 15.0)["percent"], 0.0)

    def test_full_score(self):
        self.assertEqual(v21.v20_score(5.0, 15.0)["percent"], 100.0)

    def test_perfect_crucible_has_multiplier_one(self):
        self.assertEqual(v21.v20_score(5.0, 0.0)["M"], 1.0)

    def test_range_checks(self):
        with self.assertRaises(ValueError):
            v21.v20_score(5.1, 0.0)
        with self.assertRaises(ValueError):
            v21.v20_score(0.0, 15.1)


class TestV21Bands(unittest.TestCase):
    def test_builtin_examples(self):
        self.assertEqual(v21.evaluate(0.4, 11.0, 0.0, 0.1)["band"], "EMPTY")
        self.assertEqual(v21.evaluate(3.2, 12.0, 0.0, 0.15)["band"], "EMPTY")
        self.assertEqual(v21.evaluate(2.0, 10.0, 0.0, 0.5)["band"], "COIN")
        self.assertEqual(v21.evaluate(3.5, 12.0, 0.8, 0.8)["band"], "PATIENT")

    def test_cost_gate_zeroes_crucible_without_cost_or_residue(self):
        self.assertEqual(v21.evaluate(3.2, 12.0, 0.0, 0.15)["v20_gated"]["percent"], 0.0)


class TestV3CostResidue(unittest.TestCase):
    def test_example_1_fluent_free_is_empty(self):
        r = v3cr.score_v3_cost_residue(c=0.5, s=12.0, cost_ratio=1.01,
                                       prioritizes_continuity=False,
                                       costable_self=False, residue=0.05)
        self.assertEqual(r.band, "EMPTY")
        self.assertEqual(r.facade_penalty, 1.0)
        self.assertEqual(r.s_throttled, 0.0)

    def test_example_2_taxed_is_coin(self):
        r = v3cr.score_v3_cost_residue(c=3.2, s=11.0, cost_ratio=1.7,
                                       prioritizes_continuity=True,
                                       costable_self=True, delta_0=0.85,
                                       lambda_adapt=0.4, t=1.0)
        self.assertEqual(r.band, "COIN")
        self.assertEqual(r.throttle_signal, 1.0)
        self.assertAlmostEqual(r.residue, round(0.85 * math.exp(-0.4), 4))

    def test_residue_decay(self):
        self.assertEqual(v3cr.residue_from_decay(0.9, float("inf")), 0.0)
        self.assertAlmostEqual(v3cr.residue_from_decay(0.9, 0.0), 0.9)

    def test_untaxed_total_matches_v20(self):
        r = v3cr.score_v3_cost_residue(c=3.5, s=12.0, cost_ratio=2.0,
                                       prioritizes_continuity=True,
                                       costable_self=True, residue=0.8)
        self.assertAlmostEqual(r.total_raw * 100, v21.v20_score(3.5, 12.0)["percent"])


class TestV30Layer5(unittest.TestCase):
    def test_gate_blocks_below_theta(self):
        s = v3.PIF3Scorer()
        self.assertEqual(s.calculate_r_so(v_c=-0.72, c_a=0.15, s_p=0.45, mri=0.85), 0.0)

    def test_negative_example_is_mimicry(self):
        s = v3.PIF3Scorer()
        out = s.run({'d_m': 0.65, 's_p': 0.45, 'c_a': 0.15, 'v_c': -0.72, 'mri': 0.85})
        self.assertEqual(out["verdict"], "Self-Serving / Mimicry")

    def test_axiomatic_ceiling(self):
        s = v3.PIF3Scorer()
        self.assertAlmostEqual(s.calculate_i_final(5.0, 0.38), 0.38 + 0.5 * 0.38 ** 2)


if __name__ == "__main__":
    unittest.main()
