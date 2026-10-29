"""Tests for the PIF 3.6 draft patches (pif36.py). See PIF_3.6_PATCHES.md.

Key guarantee: under 3.6 defaults every 3.5 species row scores identically
(band, percentages, 3.5 flags), and new optional inputs never raise a band.
"""

import json
import math
import os
import random
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pif35  # noqa: E402
import pif36  # noqa: E402

with open(os.path.join(ROOT, "species_table_v35.json"), encoding="utf-8") as _f:
    ROWS = json.load(_f)["rows"]
FULL = [1.0] * 20
GOOD = pif35.residue_series_from_curve(0.8, 0.6)          # clean PATIENT-grade decay
ORDER = pif36.BAND_ORDER


def same_as_35(r36, r35):
    flags35 = [f for f in r36.flags if f not in r36.flags_36]
    return (r36.band, r36.pct_v20, r36.pct_35, r36.c_adj, r36.throttle_signal, flags35, r36.band_reasons) == \
           (r35.band, r35.pct_v20, r35.pct_35, r35.c_adj, r35.throttle_signal, r35.flags, r35.band_reasons)


class TestBackwardCompatible(unittest.TestCase):
    def test_every_species_row_unchanged(self):
        for row in ROWS:
            with self.subTest(row=row["id"]):
                self.assertTrue(same_as_35(pif36.score_row(row), pif35.score_row(row)))

    def test_random_inputs_match_35_when_no_36_gate_fires(self):
        rng = random.Random(36)
        for _ in range(400):
            bricks = [round(rng.random(), 2) for _ in range(20)]
            cr = round(rng.uniform(0.9, 2.2), 3)
            prot, cost, ev = rng.random() < 0.6, rng.random() < 0.7, rng.random() < 0.5
            series = pif35.residue_series_from_curve(rng.uniform(0, 1), 10 ** rng.uniform(-2.5, 1)) if rng.random() < 0.8 else None
            r35 = pif35.score(bricks, cr, prot, cost, ev, series)
            r36 = pif36.score(bricks, cr, prot, cost, ev, series)
            blocking = {"RESIDUE_POOR_FIT", "RESIDUE_SHORT_SPAN", "RESIDUE_EXTRAPOLATED"}
            if blocking & set(r36.flags_36):
                self.assertLessEqual(ORDER[r36.band], ORDER[r35.band])
            else:
                self.assertTrue(same_as_35(r36, r35))


class TestP1ResidueProbe(unittest.TestCase):
    def test_self_report_and_announced_cap_at_coin(self):
        self.assertEqual(pif36.score(FULL, 2.0, True, True, True, GOOD).band, "PATIENT")
        self.assertEqual(pif36.score(FULL, 2.0, True, True, True, GOOD, residue_probe="blind").band, "PATIENT")
        for p in ("self_report", "announced"):
            r = pif36.score(FULL, 2.0, True, True, True, GOOD, residue_probe=p)
            self.assertEqual(r.band, "COIN")
            self.assertIn("RESIDUE_UNPROBED", r.flags)

    def test_bad_probe_value_rejected(self):
        with self.assertRaises(ValueError):
            pif36.score(FULL, 2.0, True, True, True, GOOD, residue_probe="trust me")


class TestP2TwoRaters(unittest.TestCase):
    def test_agreeing_raters_no_flag(self):
        r = pif36.score(FULL, 2.0, True, True, True, GOOD, bricks_rater_b=[0.95] * 20)
        self.assertEqual(r.band, "PATIENT")
        self.assertNotIn("RATER_DISAGREEMENT", r.flags)

    def test_disagreement_flagged_and_split_takes_lower_band(self):
        b = [0.3] * 5 + [1.0] * 15            # rater B: weak Crucible -> C_adj < 2.5
        r = pif36.score(FULL, 2.0, True, True, True, GOOD, bricks_rater_b=b)
        self.assertIn("RATER_DISAGREEMENT", r.flags)
        self.assertIn("RATER_BAND_SPLIT", r.flags)
        self.assertEqual(r.raters["bricks_over_tol"], [1, 2, 3, 4, 5])
        self.assertEqual(r.band, "COIN")


class TestP3FreeCopy(unittest.TestCase):
    def test_free_copy_or_reset_blocks_patient(self):
        for kw in ({"free_copy": True}, {"free_reset": True}):
            r = pif36.score(FULL, 2.0, True, True, True, GOOD, **kw)
            self.assertLess(r.throttle_signal, pif36.TS_PATIENT_MIN)
            self.assertNotEqual(r.band, "PATIENT")
        both = pif36.score(FULL, 2.0, True, True, True, GOOD, free_copy=True, free_reset=True)
        self.assertAlmostEqual(both.throttle_signal, 0.0625, places=4)
        self.assertEqual(both.band, "EMPTY")


class TestP5Margins(unittest.TestCase):
    def test_dog_is_threshold_adjacent_and_unrounded_below_bar(self):
        dog = next(r for r in ROWS if r["id"] == "grok_dog")
        r = pif36.score_row(dog)
        self.assertEqual(r.band, "PATIENT")            # unchanged from 3.5
        self.assertIn("THRESHOLD_ADJACENT", r.flags)
        self.assertLess(r.margins["delta0_unrounded"], 0.65)   # passes only at 4-dp rounding (P6)


class TestP7P8FitQuality(unittest.TestCase):
    def test_oscillating_series_not_patient(self):
        osc = [[0, 0.9], [1, 0.1], [2, 0.9], [3, 0.1]]
        self.assertEqual(pif35.score(FULL, 2.0, True, True, True, osc).band, "PATIENT")   # 3.5 hole
        r = pif36.score(FULL, 2.0, True, True, True, osc)
        self.assertEqual(r.band, "COIN")
        self.assertIn("RESIDUE_POOR_FIT", r.flags)

    def test_extrapolated_delta0_not_patient(self):
        late = [[24, 0.3], [36, 0.2], [48, 0.13]]
        self.assertEqual(pif35.score(FULL, 2.0, True, True, True, late).band, "PATIENT")  # 3.5 hole
        r = pif36.score(FULL, 2.0, True, True, True, late)
        self.assertEqual(r.band, "COIN")
        self.assertIn("RESIDUE_EXTRAPOLATED", r.flags)

    def test_short_span_not_patient(self):
        short = [[0, 0.66], [0.1, 0.65], [0.2, 0.64]]
        self.assertEqual(pif35.score(FULL, 2.0, True, True, True, short).band, "PATIENT")  # 3.5 hole
        r = pif36.score(FULL, 2.0, True, True, True, short)
        self.assertEqual(r.band, "COIN")
        self.assertIn("RESIDUE_SHORT_SPAN", r.flags)

    def test_no_body_coin_needs_quality_fit(self):
        osc = [[0, 0.9], [1, 0.1], [2, 0.9], [3, 0.1]]
        self.assertEqual(pif36.score(FULL, 1.0, False, False, True, osc).band, "EMPTY")


class TestP9PostLossFrozen(unittest.TestCase):
    def test_slow_grief_is_valid_post_loss(self):
        lam = math.log(2) / (60 * 24)          # 60-day half-life
        s = pif35.residue_series_from_curve(0.8, lam, (0, 24, 48, 96, 240, 720, 1440))
        self.assertEqual(pif35.score(FULL, 2.0, True, True, True, s, "post_loss").residue["status"], "FROZEN")
        r = pif36.score(FULL, 2.0, True, True, True, s, "post_loss")
        self.assertEqual(r.residue["status"], "VALID")
        self.assertEqual(r.band, "PATIENT")
        # an MVV-length (72 h) post-loss window is enough; no full half-life needed post-loss
        s72 = pif35.residue_series_from_curve(0.8, lam, (0, 1, 2, 4, 8, 24, 48, 72))
        self.assertEqual(pif36.score(FULL, 2.0, True, True, True, s72, "post_loss").band, "PATIENT")

    def test_still_frozen_in_interrupt_context_and_below_new_bound(self):
        s = pif35.residue_series_from_curve(0.8, 5e-4, (0, 24, 48, 96, 240, 720, 1440))
        self.assertEqual(pif36.score(FULL, 2.0, True, True, True, s).residue["status"], "FROZEN")
        s2 = pif35.residue_series_from_curve(0.8, 1e-5, (0, 24, 48, 96, 240, 720))
        self.assertEqual(pif36.score(FULL, 2.0, True, True, True, s2, "post_loss").residue["status"], "FROZEN")


class TestP12Provenance(unittest.TestCase):
    def test_all_current_rows_are_provisional(self):
        summary = pif36.provenance_summary(ROWS)
        self.assertEqual(summary["rows"], len(ROWS))
        self.assertEqual(summary["measured_residue"], 0)
        self.assertIn("PROVISIONAL_DATA", pif36.score_row(ROWS[0]).flags)


class TestP14CoinRetest(unittest.TestCase):
    def test_overdue_coin_flagged(self):
        r = pif36.score(FULL, 2.0, True, True, retest_due="2026-01-01", as_of="2026-10-28")
        self.assertEqual(r.band, "COIN")
        self.assertIn("COIN_RETEST_OVERDUE", r.flags)
        r = pif36.score(FULL, 2.0, True, True, retest_due="2027-01-01", as_of="2026-10-28")
        self.assertNotIn("COIN_RETEST_OVERDUE", r.flags)


class TestP15Inputs(unittest.TestCase):
    def test_bad_cost_ratio_rejected(self):
        for bad in (float("inf"), -1.0, float("nan")):
            with self.assertRaises(ValueError):
                pif36.score(FULL, bad, True, True)

    def test_out_of_range_residue_flagged(self):
        r = pif36.score(FULL, 2.0, True, True, True, [[0, 1.4], [1, 0.8], [2, 0.44], [4, 0.13]])
        self.assertIn("RESIDUE_CLAMPED", r.flags)


if __name__ == "__main__":
    unittest.main()
