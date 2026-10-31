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


class TestP18OpenConstants(unittest.TestCase):
    def test_defaults_equal_35_constants(self):
        self.assertEqual(pif36.NOT_PROTECTING_WEIGHT, pif35.NOT_PROTECTING_WEIGHT)
        r = pif36.score(FULL, 1.6, False, True, True, GOOD)
        self.assertEqual(r.throttle_signal, round(pif35.throttle_signal(1.6, False), 4))

    def test_weight_parameter_and_sensitivity_note(self):
        b = [0.5] * 20
        r = pif36.score(b, 1.25, False, True, True)
        self.assertEqual(r.band, "EMPTY")
        self.assertEqual(r.sensitivity["not_protecting_weight"]["alternatives"][0.75], "COIN")
        self.assertTrue(any("band would be COIN at 0.75" in n for n in r.notes))
        self.assertEqual(pif36.score(b, 1.25, False, True, True, not_protecting_weight=0.75).band, "COIN")
        with self.assertRaises(ValueError):
            pif36.score(b, 1.25, False, True, not_protecting_weight=1.5)

    def test_contradiction_threshold_parameter(self):
        baby = next(r for r in ROWS if r["id"] == "grok_baby")          # PATIENT at 30.46%
        args = dict(bricks=baby["crucible"] + baby["sky_scraper"], cost_ratio=baby["cost_ratio"],
                    protects_continuity=True, costable_self=True, interrupt_evidence=baby.get("interrupt_evidence", False),
                    residue_series=baby["residue_series"])
        r = pif36.score(**args)
        self.assertNotIn("BAND_PCT_CONTRADICTION", r.flags)
        self.assertEqual(r.sensitivity["pct_contradiction"]["alternatives"], {20.0: False, 30.0: False})
        r35 = pif36.score(**args, pct_contradiction=35.0)              # 30.46% PATIENT < 35% -> flagged
        self.assertIn("BAND_PCT_CONTRADICTION", r35.flags)
        self.assertTrue(any("would be off at 20.0%/30.0%" in n for n in r35.notes))


class TestP19MultiTimescale(unittest.TestCase):
    def test_fast_plus_slow_flagged(self):
        s = [[t, round(0.5 * math.exp(-2 * t) + 0.2 * math.exp(-0.02 * t), 4)] for t in (0, 1, 2, 4, 8, 24, 48)]
        r = pif36.score(FULL, 2.0, True, True, True, s)
        self.assertIn("RESIDUE_MULTI_TIMESCALE", r.flags)

    def test_clean_single_decay_not_flagged(self):
        for row in ROWS:
            with self.subTest(row=row["id"]):
                self.assertNotIn("RESIDUE_MULTI_TIMESCALE", pif36.score_row(row).flags)


class TestP20RowRoles(unittest.TestCase):
    def test_every_row_has_a_valid_role(self):
        for row in ROWS:
            with self.subTest(row=row["id"]):
                self.assertIn(row.get("row_role"), pif36.ROW_ROLES)
                self.assertEqual(pif36.score_row(row).row_role, row["row_role"])
        legacy = {r["id"] for r in ROWS if r["row_role"] == "legacy_comparison"}
        self.assertEqual(legacy, {r["id"] for r in ROWS if r["intended_band"] == "legacy/unmeasured"})

    def test_bad_role_rejected(self):
        with self.assertRaises(ValueError):
            pif36.score_row({**ROWS[0], "row_role": "vibes"})


class TestP21HalfLife(unittest.TestCase):
    def test_half_life_note_and_short_flag(self):
        r = pif36.score(FULL, 2.0, True, True, True, GOOD)        # lambda 0.6/h -> 1.155 h
        self.assertTrue(any("half-life" in n and "secondary" in n for n in r.notes))
        self.assertNotIn("HALF_LIFE_SHORT", r.flags)
        fast = pif35.residue_series_from_curve(0.8, 1.5, (0, 0.25, 0.5, 1, 2, 4))
        r = pif36.score(FULL, 2.0, True, True, True, fast)
        self.assertIn("HALF_LIFE_SHORT", r.flags)
        self.assertEqual(r.band, "PATIENT")                          # flag only; Delta_0 alone gates


class TestP11EvidenceClass(unittest.TestCase):
    def test_every_row_has_valid_evidence_class(self):
        for row in ROWS:
            with self.subTest(row=row["id"]):
                ev = row["evidence_class"]
                for k in pif36.EVIDENCE_KEYS:
                    self.assertIn(ev[k], pif36.EVIDENCE_CLASSES)
                self.assertEqual(pif36.score_row(row).evidence_class, ev)

    def test_human_and_ai_rows_held_to_same_key(self):
        by_id = {r["id"]: r for r in ROWS}
        human, ai = by_id["readme_healthy_human"], by_id["readme_grok_baseline"]
        self.assertEqual(human["evidence_class"]["cost_ratio"], "assumed")
        self.assertEqual(human["evidence_class"]["residue"], ai["evidence_class"]["residue"])
        self.assertNotIn("measured", {r["evidence_class"]["overall"] for r in ROWS})

    def test_bad_or_inconsistent_class_rejected(self):
        with self.assertRaises(ValueError):
            pif36.score_row({**ROWS[0], "evidence_class": {"bricks": "vibes"}})
        with self.assertRaises(ValueError):
            pif36.score_row({**ROWS[5], "evidence_class": {**ROWS[5]["evidence_class"], "overall": "measured"}})

    def test_species_results_shows_evidence_column(self):
        with open(os.path.join(ROOT, "species_results_v35.md"), encoding="utf-8") as f:
            md = f.read()
        self.assertIn("Evidence (bricks/cost/continuity/residue)", md)
        self.assertIn("| real world anchor | assumed (A/A/A/A) |", md)


class TestP16NoBodyDisplay(unittest.TestCase):
    def test_no_body_coin_shows_na_number_unchanged(self):
        row = next(r for r in ROWS if r["id"] == "v21_interrupt_messy_no_body")
        r36, r35 = pif36.score_row(row), pif35.score_row(row)
        self.assertEqual(r36.band, "COIN")
        self.assertEqual(r36.pct_35_display, "n/a (no-body COIN)")
        self.assertEqual(r36.pct_35, r35.pct_35)

    def test_other_rows_show_number(self):
        row = next(r for r in ROWS if r["id"] == "grok_dog")
        self.assertEqual(pif36.score_row(row).pct_35_display, "39.81%")


class TestP22InputBinding(unittest.TestCase):
    ROW = next(r for r in ROWS if r["id"] == "grok_dog")

    def test_no_metadata_no_flag(self):
        self.assertNotIn("INPUTS_NOT_BOUND", pif36.score_row(self.ROW).flags_36)

    def test_same_system_same_window_no_flag(self):
        mo = {k: {"system": "rex", "version": "1", "date": "2026-10-01"} for k in ("bricks", "cost_ratio", "residue")}
        mo["residue"]["date"] = "2026-10-20"
        self.assertNotIn("INPUTS_NOT_BOUND", pif36.score_row({**self.ROW, "measured_on": mo}).flags_36)

    def test_mixed_version_flagged_band_unchanged(self):
        mo = {"bricks": {"system": "bot", "version": "4.1"}, "residue": {"system": "bot", "version": "4.2"}}
        r = pif36.score_row({**self.ROW, "measured_on": mo})
        self.assertIn("INPUTS_NOT_BOUND", r.flags_36)
        self.assertEqual(r.band, pif35.score_row(self.ROW).band)

    def test_mixed_system_and_wide_dates_flagged(self):
        mo = {"bricks": {"system": "a", "date": "2026-01-01"}, "cost_ratio": {"system": "b", "date": "2026-06-01"}}
        r = pif36.score_row({**self.ROW, "measured_on": mo})
        self.assertIn("INPUTS_NOT_BOUND", r.flags)
        self.assertTrue(any("different systems" in n and "days apart" in n for n in r.notes))

    def test_bad_key_rejected(self):
        with self.assertRaises(ValueError):
            pif36.score_row({**self.ROW, "measured_on": {"vibes": {"system": "a"}}})


class TestP23NoiseFloor(unittest.TestCase):
    ROW = next(r for r in ROWS if r["id"] == "grok_dog")

    def test_no_noise_floor_no_flag(self):
        self.assertNotIn("RESIDUE_BELOW_NOISE", pif36.score_row(self.ROW).flags_36)

    def test_clear_of_noise_no_flag(self):
        r = pif36.score_row({**self.ROW, "residue_noise_floor": 0.05})
        self.assertNotIn("RESIDUE_BELOW_NOISE", r.flags_36)
        self.assertTrue(any("clears" in n for n in r.notes))

    def test_below_noise_flagged_band_unchanged(self):
        r = pif36.score_row({**self.ROW, "residue_noise_floor": 0.3})
        self.assertIn("RESIDUE_BELOW_NOISE", r.flags_36)
        self.assertIn("RESIDUE_BELOW_NOISE", r.flags)
        self.assertEqual(r.band, pif35.score_row(self.ROW).band)

    def test_no_residue_fit_no_flag(self):
        row = next(x for x in ROWS if not x.get("residue_series"))
        self.assertNotIn("RESIDUE_BELOW_NOISE", pif36.score_row({**row, "residue_noise_floor": 0.9}).flags_36)

    def test_bad_value_rejected(self):
        for bad in (-0.1, 1.5, float("nan"), "0.1", True):
            with self.assertRaises(ValueError):
                pif36.score_row({**self.ROW, "residue_noise_floor": bad})


if __name__ == "__main__":
    unittest.main()
