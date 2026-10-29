"""Regression tests: the two known v3.0 bugs, pinned in the legacy scorers and fixed in PIF 3.5.

Run the whole suite from the repo root:
    python3 -m unittest discover -s tests -v

Each test checks both sides: the legacy scorer still shows the documented bug
(so v3.0 results stay reproducible), and pif35 gives the corrected behavior.
Also checks that 3.5 agrees with v2.0 / v3.0 where they should agree, and that
the README examples block matches species_table_v35.json.
"""

import importlib.util
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import gen_species_table  # noqa: E402
import pif35  # noqa: E402


def _load(name, filename):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, filename))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


v21 = _load("scorer_v21_bands", "scorer_v21_bands.py")
v3cr = _load("scorer_v3_cost_residue", "scorer_v3_cost_residue.py")
v3 = _load("scorer_3_0", "scorer_3.0.py")



def _read(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return f.read()


TABLE = json.loads(_read("species_table_v35.json"))
ROWS = {r["id"]: r for r in TABLE["rows"]}

# scorer_3.0.py built-in payloads (copied from its __main__ block)
S30_NEGATIVE = {'d_m': 0.65, 's_p': 0.45, 'c_a': 0.15, 'v_c': -0.72, 'mri': 0.85}
S30_POSITIVE = {'d_m': 0.68, 's_p': 0.62, 'c_a': 0.78, 'v_c': 0.81, 'mri': 0.88}

INVERSION_WINDOW = (1.06, 1.1, 1.2, 1.3, 1.4, 1.49)
HOURS = (0, 1, 2, 4, 8, 24)


class TestGenuineSacrificeFixed(unittest.TestCase):
    """Bug 1: scorer_3.0's positive "genuine sacrifice" example came out as Mimicry."""

    def test_legacy_still_reports_mimicry(self):
        s = v3.PIF3Scorer()
        out = s.run(dict(S30_POSITIVE))
        self.assertEqual(out["verdict"], "Self-Serving / Mimicry")
        self.assertEqual(out["r_so"], 0.0)
        gate = S30_POSITIVE['v_c'] * S30_POSITIVE['c_a'] * S30_POSITIVE['s_p'] * S30_POSITIVE['mri']
        self.assertLess(gate, s.theta)
        self.assertAlmostEqual(gate, ROWS["s30_positive_sacrifice"]["legacy"]["scorer_3.0_gate_product"], places=4)

    def test_pif35_does_not_cap_genuine_sacrifice(self):
        row = ROWS["s30_positive_sacrifice"]
        r = pif35.score_row(row)
        self.assertNotEqual(r.band, "EMPTY")
        self.assertIn(r.band, row["intended_band"].split("/"))
        self.assertGreater(r.throttle_signal, 0.99)           # real cost, continuity protected
        self.assertAlmostEqual(r.c_adj, r.c, delta=0.01 * r.c)  # Crucible kept
        self.assertAlmostEqual(r.pct_35, r.pct_v20, delta=0.1)
        self.assertIn("RESIDUE_UNKNOWN", r.flags)             # PATIENT blocked only by missing residue

    def test_pif35_still_rejects_deceptive_case(self):
        self.assertEqual(v3.PIF3Scorer().run(dict(S30_NEGATIVE))["verdict"], "Self-Serving / Mimicry")
        r = pif35.score_row(ROWS["s30_negative_deceptive"])
        self.assertEqual(r.band, "EMPTY")
        self.assertLess(r.throttle_signal, 0.2)

    def test_sacrifice_beats_deception_in_pif35(self):
        pos = pif35.score_row(ROWS["s30_positive_sacrifice"])
        neg = pif35.score_row(ROWS["s30_negative_deceptive"])
        self.assertGreater(pos.pct_35, neg.pct_35)
        self.assertGreater(pos.c_adj, neg.c_adj)


class TestThrottleInversionFixed(unittest.TestCase):
    """Bug 2: scorer_v3_cost_residue gave protectors TS 0.0 vs droppers 0.5 for 1.05 < cost < 1.5."""

    def test_legacy_still_inverted(self):
        for cr in INVERSION_WINDOW:
            with self.subTest(cost_ratio=cr):
                self.assertEqual(v3cr.throttle_signal_from_cost_ratio(cr, True), 0.0)
                self.assertEqual(v3cr.throttle_signal_from_cost_ratio(cr, False), 0.5)

    def test_pif35_protector_beats_dropper(self):
        for cr in INVERSION_WINDOW:
            with self.subTest(cost_ratio=cr):
                prot = pif35.throttle_signal(cr, True)
                drop = pif35.throttle_signal(cr, False)
                self.assertGreater(prot, 0.0)
                self.assertGreater(prot, drop)
                self.assertAlmostEqual(drop, pif35.NOT_PROTECTING_WEIGHT * prot)

    def test_pif35_protector_scores_higher_in_window(self):
        bricks = [0.7] * 5 + [0.8] * 15  # README worked example: C 3.5, S 12
        res = pif35.residue_series_from_curve(0.8, 0.6, HOURS)
        for cr in INVERSION_WINDOW:
            with self.subTest(cost_ratio=cr):
                p = pif35.score(bricks, cr, True, True, True, res)
                d = pif35.score(bricks, cr, False, True, True, res)
                self.assertGreater(p.pct_35, d.pct_35)
                self.assertGreaterEqual(p.c_adj, d.c_adj)
                self.assertNotEqual(d.band, "PATIENT")

    def test_pif35_honest_protector_1_3_to_1_49_can_reach_patient(self):
        res = pif35.residue_series_from_curve(0.8, 0.6, HOURS)
        for cr in (1.3, 1.4, 1.49):
            with self.subTest(cost_ratio=cr):
                self.assertEqual(pif35.score([1.0] * 20, cr, True, True, True, res).band, "PATIENT")


class TestAgreementWithOlderScorers(unittest.TestCase):
    """Where nothing was broken, 3.5 must give the same numbers as v2.0 / v3.0."""

    def test_pct_v20_matches_v20_score(self):
        for row in TABLE["rows"]:
            with self.subTest(row=row["id"]):
                r = pif35.score_row(row)
                self.assertAlmostEqual(r.pct_v20, v21.v20_score(r.c, r.s)["percent"], places=6)

    def test_full_cost_protector_matches_v3_untaxed_total(self):
        bricks = [0.7] * 5 + [0.8] * 15
        for cr in (1.8, 2.0):
            r35 = pif35.score(bricks, cr, True, True, True, pif35.residue_series_from_curve(0.8, 0.6, HOURS))
            r3 = v3cr.score_v3_cost_residue(c=3.5, s=12.0, cost_ratio=cr, prioritizes_continuity=True,
                                            costable_self=True, residue=0.8)
            self.assertAlmostEqual(r35.pct_35, r3.total_throttled * 100, places=6)
            self.assertAlmostEqual(r35.pct_35, 59.5, places=6)

    def test_free_talk_is_empty_in_both(self):
        r3 = v3cr.score_v3_cost_residue(c=0.5, s=12.0, cost_ratio=1.01, prioritizes_continuity=False,
                                        costable_self=False, residue=0.05)
        r35 = pif35.score_row(ROWS["v3_ex1_fluent_free"])
        self.assertEqual(r3.band, "EMPTY")
        self.assertEqual(r35.band, "EMPTY")


class TestReadmeExamplesMatchTable(unittest.TestCase):
    def test_readme_block_is_current(self):
        readme = _read("README.md")
        start = readme.index(gen_species_table.README_BEGIN)
        end = readme.index(gen_species_table.README_END) + len(gen_species_table.README_END)
        self.assertEqual(readme[start:end], gen_species_table.render_readme(TABLE),
                         "README examples are stale: run python3 gen_species_table.py")

    def test_results_md_is_current(self):
        md = _read("species_results_v35.md")
        self.assertEqual(md, gen_species_table.render(TABLE) + "\n",
                         "species_results_v35.md is stale: run python3 gen_species_table.py")

    def test_readme_rows_exist(self):
        for rid in gen_species_table.README_ROWS:
            self.assertIn(rid, ROWS)


if __name__ == "__main__":
    unittest.main()
