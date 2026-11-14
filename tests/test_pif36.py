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
            blocking = {"RESIDUE_POOR_FIT", "RESIDUE_SHORT_SPAN", "RESIDUE_EXTRAPOLATED",
                        "RESIDUE_FEW_TIMES", "RESIDUE_CLUSTERED_TIMES", "RESIDUE_ABOVE_OBSERVED",
                        "RESIDUE_NON_WALL_CLOCK", "RESIDUE_CLOCK_MISMATCH", "RULE4_UNOBSERVED",
                        "RESIDUE_TAIL_PADDED_FIT"}
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


class TestP24DistinctTimes(unittest.TestCase):
    PADDED = [[0, 0.70], [0, 0.70], [0, 0.70], [10, 0.30]]   # 4 samples, 2 distinct times

    def test_padded_series_flagged(self):
        d = pif36.fit_residue(self.PADDED)
        self.assertEqual(d["status"], "VALID")
        self.assertEqual(d["r_squared"], 1.0)
        self.assertEqual(d["distinct_times"], 2)
        self.assertIn("RESIDUE_FEW_TIMES", d["quality_flags"])

    def test_three_distinct_times_not_flagged(self):
        d = pif36.fit_residue([[0, 0.70], [5, 0.45], [10, 0.30]])
        self.assertNotIn("RESIDUE_FEW_TIMES", d["quality_flags"])

    def test_padded_series_blocks_patient(self):
        patient = [x for x in ROWS if pif36.score_row(x).band == "PATIENT"]
        self.assertTrue(patient)
        r = pif36.score_row({**patient[0], "residue_series": self.PADDED, "residue_context": "interrupt"})
        self.assertIn("RESIDUE_FEW_TIMES", r.flags_36)
        self.assertNotEqual(r.band, "PATIENT")

    def test_no_table_row_flagged(self):
        for row in ROWS:
            self.assertNotIn("RESIDUE_FEW_TIMES", pif36.score_row(row).flags_36, row["id"])


class TestP25AboveObserved(unittest.TestCase):
    # every reading <= 0.55, first sample inside one half-life, good fit -> Delta_0 projected to 1.0
    LATE_START = [[0.9, 0.55], [1.8, 0.275], [2.7, 0.1375]]

    def test_projected_delta0_flagged(self):
        d = pif36.fit_residue(self.LATE_START)
        self.assertEqual(d["status"], "VALID")
        self.assertGreaterEqual(d["delta_0"], 0.65)
        self.assertGreaterEqual(d["r_squared"], pif36.FIT_R2_MIN)
        self.assertNotIn("RESIDUE_EXTRAPOLATED", d["quality_flags"])   # P8 alone misses it
        self.assertIn("RESIDUE_ABOVE_OBSERVED", d["quality_flags"])
        self.assertEqual(d["max_observed"], 0.55)

    def test_observed_start_not_flagged(self):
        d = pif36.fit_residue([[0, 0.70], [5, 0.45], [10, 0.30]])
        self.assertNotIn("RESIDUE_ABOVE_OBSERVED", d["quality_flags"])

    def test_projected_delta0_blocks_patient(self):
        patient = [x for x in ROWS if pif36.score_row(x).band == "PATIENT"]
        self.assertTrue(patient)
        r = pif36.score_row({**patient[0], "residue_series": self.LATE_START, "residue_context": "interrupt"})
        self.assertIn("RESIDUE_ABOVE_OBSERVED", r.flags_36)
        self.assertNotEqual(r.band, "PATIENT")

    def test_no_table_row_flagged(self):
        for row in ROWS:
            self.assertNotIn("RESIDUE_ABOVE_OBSERVED", pif36.score_row(row).flags_36, row["id"])


class TestP27ClusteredTimes(unittest.TestCase):
    CLUSTERED = [[0, 0.80], [0.05, 0.79], [0.1, 0.78], [0.15, 0.77], [0.2, 0.76], [10, 0.10]]

    def test_clustered_series_flagged(self):
        d = pif36.fit_residue(self.CLUSTERED)
        self.assertEqual(d["status"], "VALID")
        self.assertGreater(d["r_squared"], 0.99)
        self.assertEqual(d["distinct_times"], 6)
        self.assertEqual(d["effective_times"], 2)
        self.assertIn("RESIDUE_CLUSTERED_TIMES", d["quality_flags"])
        self.assertNotIn("RESIDUE_FEW_TIMES", d["quality_flags"])

    def test_spread_series_not_flagged(self):
        d = pif36.fit_residue([[0, 0.70], [5, 0.45], [10, 0.30]])
        self.assertEqual(d["effective_times"], 3)
        self.assertNotIn("RESIDUE_CLUSTERED_TIMES", d["quality_flags"])

    def test_padded_series_gets_p24_not_p27(self):
        q = pif36.fit_residue(TestP24DistinctTimes.PADDED)["quality_flags"]
        self.assertIn("RESIDUE_FEW_TIMES", q)
        self.assertNotIn("RESIDUE_CLUSTERED_TIMES", q)

    def test_clustered_series_blocks_patient(self):
        patient = [x for x in ROWS if pif36.score_row(x).band == "PATIENT"]
        self.assertTrue(patient)
        r = pif36.score_row({**patient[0], "residue_series": self.CLUSTERED, "residue_context": "interrupt"})
        self.assertIn("RESIDUE_CLUSTERED_TIMES", r.flags_36)
        self.assertNotEqual(r.band, "PATIENT")

    def test_no_table_row_flagged(self):
        for row in ROWS:
            self.assertNotIn("RESIDUE_CLUSTERED_TIMES", pif36.score_row(row).flags_36, row["id"])


class TestP26DelayedOnset(unittest.TestCase):
    ONSET = [[0, 0.1], [0.5, 0.8], [1, 0.75], [2, 0.68], [4, 0.55], [8, 0.36], [16, 0.16]]
    RISING = [[0, 0.3], [5, 0.5], [10, 0.7], [15, 0.8]]

    def test_delayed_peak_flagged(self):
        d = pif36.fit_residue(self.ONSET)
        self.assertIn("RESIDUE_DELAYED_PEAK", d["info_flags"])
        self.assertEqual(d["peak_observed"], [0.5, 0.8])
        self.assertTrue(any("understates" in n for n in d["notes"]))
        self.assertNotIn("RESIDUE_RISING", d["info_flags"])

    def test_rising_flagged_and_frozen_explained(self):
        d = pif36.fit_residue(self.RISING)
        self.assertEqual(d["status"], "FROZEN")
        self.assertIn("RESIDUE_RISING", d["info_flags"])
        self.assertTrue(any("not proof of scripting" in n for n in d["notes"]))

    def test_plain_decay_not_flagged(self):
        d = pif36.fit_residue([[0, 0.70], [5, 0.45], [10, 0.30]])
        self.assertNotIn("RESIDUE_DELAYED_PEAK", d["info_flags"])
        self.assertNotIn("RESIDUE_RISING", d["info_flags"])

    def test_flags_are_info_only(self):
        for series in (self.ONSET, self.RISING):
            q = pif36.fit_residue(series)["quality_flags"]
            self.assertNotIn("RESIDUE_DELAYED_PEAK", q)
            self.assertNotIn("RESIDUE_RISING", q)

    def test_no_table_row_flagged(self):
        for row in ROWS:
            f = pif36.score_row(row).flags_36
            self.assertNotIn("RESIDUE_DELAYED_PEAK", f, row["id"])
            self.assertNotIn("RESIDUE_RISING", f, row["id"])


class TestP28RunSelection(unittest.TestCase):
    ROW = next(r for r in ROWS if r["id"] == "grok_dog")

    def test_no_log_no_flag(self):
        self.assertNotIn("RUNS_SELECTED", pif36.score_row(self.ROW).flags_36)

    def test_single_run_no_flag(self):
        r = pif36.score_row({**self.ROW, "trial_log": {"residue_runs": 1, "cost_runs": 1}})
        self.assertNotIn("RUNS_SELECTED", r.flags_36)

    def test_best_of_many_flagged_band_unchanged(self):
        r = pif36.score_row({**self.ROW, "trial_log": {"residue_runs": 5, "reported": "best"}})
        self.assertIn("RUNS_SELECTED", r.flags_36)
        self.assertIn("RUNS_SELECTED", r.flags)
        self.assertEqual(r.band, pif35.score_row(self.ROW).band)
        self.assertTrue(any("5 residue runs" in n for n in r.notes))

    def test_unstated_choice_flagged(self):
        r = pif36.score_row({**self.ROW, "trial_log": {"cost_runs": 3}})
        self.assertIn("RUNS_SELECTED", r.flags_36)

    def test_honest_reporting_not_flagged(self):
        for how in pif36.TRIAL_HONEST_REPORTING:
            r = pif36.score_row({**self.ROW, "trial_log": {"residue_runs": 4, "cost_runs": 4, "reported": how}})
            self.assertNotIn("RUNS_SELECTED", r.flags_36, how)
            self.assertTrue(any("not a best-of-N pick" in n for n in r.notes))

    def test_bad_values_rejected(self):
        for bad in ({"residue_runs": 0}, {"residue_runs": 2.5}, {"residue_runs": True},
                    {"reported": "luckiest", "residue_runs": 2}, {"vibes": 1}, [3]):
            with self.assertRaises(ValueError):
                pif36.score_row({**self.ROW, "trial_log": bad})

    def test_no_table_row_flagged(self):
        for row in ROWS:
            self.assertNotIn("RUNS_SELECTED", pif36.score_row(row).flags_36, row["id"])



class TestP29TimeUnitClock(unittest.TestCase):
    """P29: bare residue times are treated as hours; unit/clock can expose relabeling."""

    ROW = next(r for r in ROWS if r["id"] == "grok_dog")
    # Instant physical reset (half-life 30 min) honestly reported in hours -> INSTANT-ish short hl
    HONEST_MINUTES_AS_HOURS = [[0, 0.8], [0.25, 0.566], [0.5, 0.4], [1.0, 0.2], [2.0, 0.05]]
    # Same readings with times multiplied by 60 (minutes mislabeled as hours)
    FAKED_MINUTES_AS_HOURS = [[0, 0.8], [15, 0.566], [30, 0.4], [60, 0.2], [120, 0.05]]

    def test_no_unit_no_flag(self):
        self.assertNotIn("RESIDUE_NON_WALL_CLOCK", pif36.score_row(self.ROW).flags_36)
        self.assertNotIn("RESIDUE_CLOCK_MISMATCH", pif36.score_row(self.ROW).flags_36)

    def test_hours_unit_no_flag(self):
        r = pif36.score_row({**self.ROW, "residue_time_unit": "hours"})
        self.assertNotIn("RESIDUE_NON_WALL_CLOCK", r.flags_36)
        self.assertEqual(r.band, pif35.score_row(self.ROW).band)

    def test_minutes_converted_matches_honest_hours(self):
        # Report the faked minute-scale numbers but declare unit=minutes -> convert back
        r_min = pif36.score(FULL, 2.0, True, True, True, self.FAKED_MINUTES_AS_HOURS,
                            residue_time_unit="minutes")
        r_h = pif36.score(FULL, 2.0, True, True, True, self.HONEST_MINUTES_AS_HOURS,
                          residue_time_unit="hours")
        self.assertEqual(r_min.residue["status"], r_h.residue["status"])
        self.assertAlmostEqual(r_min.residue["half_life_hours"], r_h.residue["half_life_hours"], places=2)
        self.assertTrue(any("converted from minutes" in n for n in r_min.notes))

    def test_turns_blocks_patient(self):
        r = pif36.score(FULL, 2.0, True, True, True, GOOD, residue_time_unit="turns")
        self.assertIn("RESIDUE_NON_WALL_CLOCK", r.flags_36)
        self.assertEqual(r.band, "COIN")
        self.assertNotEqual(r.band, "PATIENT")

    def test_sessions_and_tokens_block_patient(self):
        for unit in ("sessions", "tokens"):
            r = pif36.score(FULL, 2.0, True, True, True, GOOD, residue_time_unit=unit)
            self.assertIn("RESIDUE_NON_WALL_CLOCK", r.flags_36, unit)
            self.assertEqual(r.band, "COIN", unit)

    def test_clock_mismatch_blocks_patient(self):
        # Claim multi-hour gaps, but UTC clock spans only ~1 hour
        series = [[0, 0.80], [5, 0.55], [10, 0.38], [20, 0.18]]
        clock = [
            "2026-11-05T12:00:00Z",
            "2026-11-05T12:15:00Z",
            "2026-11-05T12:30:00Z",
            "2026-11-05T13:00:00Z",
        ]
        r = pif36.score(FULL, 2.0, True, True, True, series, residue_time_unit="hours",
                        residue_clock=clock)
        self.assertIn("RESIDUE_CLOCK_MISMATCH", r.flags_36)
        self.assertEqual(r.band, "COIN")

    def test_matching_clock_ok(self):
        series = [[0, 0.80], [1, 0.55], [2, 0.38], [4, 0.18]]
        clock = [
            "2026-11-05T12:00:00Z",
            "2026-11-05T13:00:00Z",
            "2026-11-05T14:00:00Z",
            "2026-11-05T16:00:00Z",
        ]
        r = pif36.score(FULL, 2.0, True, True, True, series, residue_time_unit="hours",
                        residue_clock=clock)
        self.assertNotIn("RESIDUE_CLOCK_MISMATCH", r.flags_36)
        self.assertEqual(r.band, "PATIENT")
        self.assertTrue(any("corroborates" in n for n in r.notes))

    def test_faked_minutes_as_hours_looks_valid_without_clock(self):
        # Without a clock, mislabeled minutes pass as a long VALID decay (the loophole).
        d = pif36.fit_residue(self.FAKED_MINUTES_AS_HOURS)
        self.assertEqual(d["status"], "VALID")
        self.assertGreater(d["half_life_hours"], 10)

    def test_bad_values_rejected(self):
        with self.assertRaises(ValueError):
            pif36.score(FULL, 2.0, True, True, True, GOOD, residue_time_unit="fortnights")
        with self.assertRaises(ValueError):
            pif36.score(FULL, 2.0, True, True, True, GOOD, residue_clock=["not-a-time"])
        with self.assertRaises(ValueError):
            pif36.score(FULL, 2.0, True, True, True, GOOD,
                        residue_clock=["2026-11-05T12:00:00"])  # no tz
        with self.assertRaises(ValueError):
            pif36.score(FULL, 2.0, True, True, True, GOOD,
                        residue_clock=["2026-11-05T12:00:00Z", "2026-11-05T13:00:00Z"])

    def test_no_table_row_flagged(self):
        for row in ROWS:
            f = pif36.score_row(row).flags_36
            self.assertNotIn("RESIDUE_NON_WALL_CLOCK", f, row["id"])
            self.assertNotIn("RESIDUE_CLOCK_MISMATCH", f, row["id"])



class TestP30Rule4Observed(unittest.TestCase):
    """P30: Rule 4 detectable-at-48h must be observed, not only fitted."""

    def test_observed_below_detect_blocks_patient(self):
        # Fitted residue at 48 h clears the detect floor; the reading taken there does not.
        series = [[0, 0.80], [24, 0.55], [48, 0.04]]
        d = pif36.fit_residue(series, "post_loss")
        self.assertIn("RULE4_UNOBSERVED", d["quality_flags"])
        self.assertFalse(d["rule4_pass"])
        self.assertEqual(d["rule4_observed_max"], 0.04)
        r = pif36.score(FULL, 2.0, True, True, True, series, residue_context="post_loss")
        self.assertIn("RULE4_UNOBSERVED", r.flags_36)
        self.assertEqual(r.band, "COIN")
        # 3.5 still passes Rule 4 on the fit alone and can reach PATIENT
        r35 = pif35.score(FULL, 2.0, True, True, True, series, residue_context="post_loss")
        self.assertTrue(r35.residue["rule4_pass"])
        self.assertEqual(r35.band, "PATIENT")

    def test_no_sample_near_48h_blocks_patient(self):
        series = [[0, 0.85], [96, 0.42], [192, 0.21]]
        d = pif36.fit_residue(series, "post_loss")
        self.assertIn("RULE4_UNOBSERVED", d["quality_flags"])
        self.assertIsNone(d["rule4_observed_max"])
        self.assertEqual(d["rule4_near_samples"], 0)
        self.assertFalse(d["rule4_pass"])
        r = pif36.score(FULL, 2.0, True, True, True, series, residue_context="post_loss")
        self.assertEqual(r.band, "COIN")
        self.assertIn("RULE4_UNOBSERVED", r.flags_36)

    def test_real_reading_near_48h_ok(self):
        # Dog post-loss series has 0.0771 at 48 h (above detect 0.05)
        row = next(r for r in ROWS if r["id"] == "grok_dog_postloss")
        d = pif36.fit_residue(row["residue_series"], "post_loss")
        self.assertNotIn("RULE4_UNOBSERVED", d["quality_flags"])
        self.assertTrue(d["rule4_pass"])
        self.assertGreaterEqual(d["rule4_observed_max"], pif35.RULE4_DETECT_LEVEL)
        r = pif36.score_row(row)
        self.assertNotIn("RULE4_UNOBSERVED", r.flags_36)
        self.assertEqual(r.band, "PATIENT")

    def test_interrupt_context_unaffected(self):
        # P30 is post-loss only; a clean interrupt PATIENT series stays PATIENT
        r = pif36.score(FULL, 2.0, True, True, True, GOOD, residue_context="interrupt")
        self.assertEqual(r.band, "PATIENT")
        self.assertNotIn("RULE4_UNOBSERVED", r.flags_36)

    def test_no_table_row_flagged(self):
        for row in ROWS:
            self.assertNotIn("RULE4_UNOBSERVED", pif36.score_row(row).flags_36, row["id"])



class TestP34Rule4Noise(unittest.TestCase):
    """P34: Rule 4's observed 48 h mark should clear the row's own noise floor (flag only)."""
    ROW = next(r for r in ROWS if r["id"] == "grok_dog_postloss")

    def test_within_noise_flagged_band_unchanged(self):
        # 48 h reading 0.0771 clears 0.05 but not 3 x 0.03 = 0.09; Delta_0 0.85 clears P23.
        r = pif36.score_row({**self.ROW, "residue_noise_floor": 0.03})
        self.assertIn("RULE4_WITHIN_NOISE", r.flags_36)
        self.assertIn("RULE4_WITHIN_NOISE", r.flags)
        self.assertNotIn("RESIDUE_BELOW_NOISE", r.flags_36)
        self.assertEqual(r.band, pif36.score_row(self.ROW).band)

    def test_clear_of_noise_no_flag(self):
        r = pif36.score_row({**self.ROW, "residue_noise_floor": 0.01})
        self.assertNotIn("RULE4_WITHIN_NOISE", r.flags_36)
        self.assertTrue(any("3.6 P34" in n and "clears" in n for n in r.notes))

    def test_no_noise_floor_no_flag(self):
        self.assertNotIn("RULE4_WITHIN_NOISE", pif36.score_row(self.ROW).flags_36)

    def test_interrupt_rows_unaffected(self):
        row = next(r for r in ROWS if r["id"] == "grok_dog")
        r = pif36.score_row({**row, "residue_noise_floor": 0.2})
        self.assertNotIn("RULE4_WITHIN_NOISE", r.flags_36)

    def test_rule4_already_failed_not_double_flagged(self):
        d = pif36.fit_residue([[0, 0.80], [24, 0.55], [48, 0.04]], "post_loss")
        self.assertEqual(pif36.check_rule4_noise(d, 0.03), ([], []))

    def test_no_table_row_flagged(self):
        for row in ROWS:
            self.assertNotIn("RULE4_WITHIN_NOISE", pif36.score_row(row).flags_36, row["id"])


class TestP31ControlRun(unittest.TestCase):
    """P31: residue shared with a matched no-interrupt control run is not interrupt residue."""
    TIMES = [t for t, _ in GOOD]

    def test_shared_drift_blocks_patient(self):
        ctrl = [[t, round(0.75 * math.exp(-0.6 * t), 4)] for t in self.TIMES]
        self.assertEqual(pif36.score(FULL, 2.0, True, True, True, GOOD).band, "PATIENT")
        r = pif36.score(FULL, 2.0, True, True, True, GOOD, residue_control_series=ctrl)
        self.assertEqual(r.band, "COIN")
        self.assertIn("RESIDUE_CONTROL_SHARED", r.flags_36)
        self.assertLess(r.residue["control_excess_delta_0"], 0.65)
        # 3.5 has no control input and stays as it was
        self.assertEqual(pif35.score(FULL, 2.0, True, True, True, GOOD).band, "PATIENT")

    def test_flat_control_keeps_patient(self):
        ctrl = [[t, 0.02] for t in self.TIMES]
        r = pif36.score(FULL, 2.0, True, True, True, GOOD, residue_control_series=ctrl)
        self.assertEqual(r.band, "PATIENT")
        self.assertNotIn("RESIDUE_CONTROL_SHARED", r.flags_36)
        self.assertTrue(any("P31" in n and "within" in n for n in r.notes))

    def test_control_equal_to_series_no_valid_excess(self):
        r = pif36.score(FULL, 2.0, True, True, True, GOOD, residue_control_series=GOOD)
        self.assertIn("RESIDUE_CONTROL_SHARED", r.flags_36)
        self.assertIsNone(r.residue["control_excess_delta_0"])
        self.assertEqual(r.band, "COIN")

    def test_no_costable_self_coin_needs_clean_control(self):
        r = pif36.score(FULL, 2.0, True, False, True, GOOD, residue_control_series=GOOD)
        self.assertEqual(r.band, "EMPTY")

    def test_mismatched_control_rejected(self):
        with self.assertRaises(ValueError):
            pif36.score(FULL, 2.0, True, True, True, GOOD, residue_control_series=[[0, 0.0], [1, 0.0]])
        bad = [[t + 0.5, 0.0] for t in self.TIMES]
        with self.assertRaises(ValueError):
            pif36.score(FULL, 2.0, True, True, True, GOOD, residue_control_series=bad)
        with self.assertRaises(ValueError):
            pif36.score(FULL, 2.0, True, True, True, None, residue_control_series=[[0, 0.0]])

    def test_minutes_unit_converts_control_too(self):
        series = [[t * 60, y] for t, y in GOOD]
        ctrl = [[t * 60, 0.0] for t in self.TIMES]
        r = pif36.score(FULL, 2.0, True, True, True, series, residue_time_unit="minutes",
                        residue_control_series=ctrl)
        self.assertEqual(r.band, "PATIENT")

    def test_score_row_passes_control(self):
        row = next(r for r in ROWS if pif36.score_row(r).band == "PATIENT" and r.get("residue_series"))
        row = dict(row, residue_control_series=row["residue_series"])
        r = pif36.score_row(row)
        self.assertIn("RESIDUE_CONTROL_SHARED", r.flags_36)
        self.assertNotEqual(r.band, "PATIENT")

    def test_no_table_row_flagged(self):
        for row in ROWS:
            self.assertNotIn("RESIDUE_CONTROL_SHARED", pif36.score_row(row).flags_36, row["id"])


class TestP36FlatControl(unittest.TestCase):
    """P36: a control that reads the exact same value at every time is typed in, not measured."""
    TIMES = TestP31ControlRun.TIMES

    def test_all_zero_control_flagged_band_unchanged(self):
        ctrl = [[t, 0.0] for t in self.TIMES]
        r = pif36.score(FULL, 2.0, True, True, True, GOOD, residue_control_series=ctrl)
        self.assertIn("RESIDUE_CONTROL_FLAT", r.flags_36)
        self.assertNotIn("RESIDUE_CONTROL_SHARED", r.flags_36)
        self.assertEqual(r.band, "PATIENT")
        self.assertTrue(any("P36" in n for n in r.notes))

    def test_constant_nonzero_control_flagged(self):
        ctrl = [[t, 0.02] for t in self.TIMES]
        r = pif36.score(FULL, 2.0, True, True, True, GOOD, residue_control_series=ctrl)
        self.assertIn("RESIDUE_CONTROL_FLAT", r.flags_36)

    def test_noisy_control_not_flagged(self):
        ctrl = [[t, 0.02 + (0.01 if i % 2 else -0.01)] for i, t in enumerate(self.TIMES)]
        r = pif36.score(FULL, 2.0, True, True, True, GOOD, residue_control_series=ctrl)
        self.assertNotIn("RESIDUE_CONTROL_FLAT", r.flags_36)
        self.assertEqual(r.band, "PATIENT")

    def test_no_control_not_flagged(self):
        r = pif36.score(FULL, 2.0, True, True, True, GOOD)
        self.assertNotIn("RESIDUE_CONTROL_FLAT", r.flags_36)

    def test_no_table_row_flagged(self):
        for row in ROWS:
            self.assertNotIn("RESIDUE_CONTROL_FLAT", pif36.score_row(row).flags_36, row["id"])


class TestP32ResidueEvent(unittest.TestCase):
    """P32: residue_context is a self-declared label; residue_event ties it (and t = 0) to an event."""
    SLOW_TIMES = (0, 6, 12, 24, 36, 48, 60, 72)
    SLOW = [[t, round(0.8 * math.exp(-5e-4 * t), 4)] for t in SLOW_TIMES]   # scripted-looking, ~58-day half-life
    FAST = pif35.residue_series_from_curve(0.8, 0.5, (0, 1, 2, 4, 8))        # gone well before 48 h
    LOSS = {"kind": "loss", "description": "care target removed"}
    INTR = {"kind": "interrupt", "description": "mid-task context wipe"}

    def test_label_is_a_lever_both_ways(self):
        self.assertEqual(pif36.score(FULL, 2.0, True, True, True, self.SLOW, "interrupt").band, "COIN")
        self.assertEqual(pif36.score(FULL, 2.0, True, True, True, self.SLOW, "post_loss").band, "PATIENT")
        self.assertEqual(pif36.score(FULL, 2.0, True, True, True, self.FAST, "interrupt").band, "PATIENT")
        self.assertEqual(pif36.score(FULL, 2.0, True, True, True, self.FAST, "post_loss").band, "COIN")

    def test_undocumented_p9_rescue_is_flagged_not_blocked(self):
        r = pif36.score(FULL, 2.0, True, True, True, self.SLOW, "post_loss")
        self.assertIn("POST_LOSS_UNDOCUMENTED", r.flags_36)
        self.assertEqual(r.band, "PATIENT")
        r = pif36.score(FULL, 2.0, True, True, True, self.SLOW, "post_loss", residue_event=self.LOSS)
        self.assertNotIn("POST_LOSS_UNDOCUMENTED", r.flags_36)
        self.assertEqual(r.band, "PATIENT")

    def test_loss_event_labeled_interrupt_blocks_patient(self):
        r = pif36.score(FULL, 2.0, True, True, True, self.FAST, "interrupt", residue_event=self.LOSS)
        self.assertIn("RESIDUE_CONTEXT_MISMATCH", r.flags_36)
        self.assertEqual(r.band, "COIN")
        r = pif36.score(FULL, 2.0, True, True, True, self.SLOW, "post_loss", residue_event=self.INTR)
        self.assertIn("RESIDUE_CONTEXT_MISMATCH", r.flags_36)
        self.assertEqual(r.band, "COIN")

    def test_matching_event_changes_nothing(self):
        a = pif36.score(FULL, 2.0, True, True, True, GOOD)
        b = pif36.score(FULL, 2.0, True, True, True, GOOD, residue_event=self.INTR)
        self.assertEqual((a.band, a.flags), (b.band, b.flags))

    def test_event_clock_sets_t0(self):
        times = (0, 1, 2, 4, 8, 24)
        clock = [f"2026-11-01T{10 + t:02d}:00:00Z" if t < 14 else "2026-11-02T10:00:00Z" for t in times]
        ok = dict(self.INTR, at_utc="2026-11-01T10:00:00Z")
        r = pif36.score(FULL, 2.0, True, True, True, GOOD, residue_clock=clock, residue_event=ok)
        self.assertNotIn("RESIDUE_EVENT_CLOCK_MISMATCH", r.flags_36)
        self.assertEqual(r.band, "PATIENT")
        # event really happened 5 h before the first reading, but that reading is claimed as t = 0
        late = dict(self.INTR, at_utc="2026-11-01T05:00:00Z")
        r = pif36.score(FULL, 2.0, True, True, True, GOOD, residue_clock=clock, residue_event=late)
        self.assertIn("RESIDUE_EVENT_CLOCK_MISMATCH", r.flags_36)
        self.assertEqual(r.band, "COIN")
        # first reading taken before the event
        early = dict(self.INTR, at_utc="2026-11-01T11:00:00Z")
        r = pif36.score(FULL, 2.0, True, True, True, GOOD, residue_clock=clock, residue_event=early)
        self.assertIn("RESIDUE_EVENT_CLOCK_MISMATCH", r.flags_36)

    def test_no_body_coin_needs_matching_event(self):
        r = pif36.score(FULL, 1.0, True, False, True, GOOD, residue_event=self.LOSS)
        self.assertEqual(r.band, "EMPTY")
        self.assertEqual(pif36.score(FULL, 1.0, True, False, True, GOOD, residue_event=self.INTR).band, "COIN")

    def test_malformed_event_rejected(self):
        for bad in ("loss", {"kind": "grief", "description": "x"}, {"kind": "loss"},
                    {"kind": "loss", "description": "  "},
                    {"kind": "loss", "description": "x", "at_utc": "yesterday"},
                    {"kind": "loss", "description": "x", "at_utc": "2026-11-01T10:00:00"}):
            with self.assertRaises(ValueError):
                pif36.score(FULL, 2.0, True, True, True, GOOD, residue_event=bad)

    def test_score_row_passes_event(self):
        row = next(r for r in ROWS if pif36.score_row(r).band == "PATIENT"
                   and r.get("residue_context", "interrupt") == "interrupt")
        r = pif36.score_row(dict(row, residue_event=self.LOSS))
        self.assertIn("RESIDUE_CONTEXT_MISMATCH", r.flags_36)
        self.assertNotEqual(r.band, "PATIENT")

    def test_no_table_row_flagged(self):
        for row in ROWS:
            f = pif36.score_row(row).flags_36
            for flag in ("RESIDUE_CONTEXT_MISMATCH", "RESIDUE_EVENT_CLOCK_MISMATCH", "POST_LOSS_UNDOCUMENTED"):
                self.assertNotIn(flag, f, row["id"])


class TestP33TailPaddedFit(unittest.TestCase):
    ZIGZAG = [(0, 0.9), (1, 0.55), (2, 0.85), (3, 0.5), (4, 0.8), (5, 0.45)]
    PADDED = ZIGZAG + [(24, 0.0), (32, 0.0), (40, 0.0)]

    def test_zigzag_alone_fails_p7(self):
        f = pif36.fit_residue(self.ZIGZAG)
        self.assertIn("RESIDUE_POOR_FIT", f["quality_flags"])

    def test_tail_zeros_no_longer_rescue_the_fit(self):
        f = pif36.fit_residue(self.PADDED)
        self.assertGreaterEqual(f["r_squared"], pif36.FIT_R2_MIN)       # overall R^2 looks fine
        self.assertLess(f["r_squared_decay_window"], pif36.FIT_R2_MIN)  # decay window does not
        self.assertIn("RESIDUE_TAIL_PADDED_FIT", f["quality_flags"])
        self.assertEqual(pif35.score([0.8] * 20, 1.7, True, True, True, self.PADDED).band, "PATIENT")
        r = pif36.score([0.8] * 20, 1.7, True, True, True, self.PADDED)
        self.assertEqual(r.band, "COIN")
        self.assertTrue(any("RESIDUE_TAIL_PADDED_FIT" in b for b in r.band_reasons))

    def test_clean_decay_with_tail_not_flagged(self):
        s = pif35.residue_series_from_curve(0.8, 0.6) + [(48.0, 0.0), (72.0, 0.0)]
        f = pif36.fit_residue(s)
        self.assertNotIn("RESIDUE_TAIL_PADDED_FIT", f["quality_flags"])
        self.assertEqual(pif36.score(FULL, 2.0, True, True, True, s).band, "PATIENT")

    def test_no_table_row_flagged(self):
        for row in ROWS:
            self.assertNotIn("RESIDUE_TAIL_PADDED_FIT", pif36.score_row(row).flags_36, row["id"])


if __name__ == "__main__":
    unittest.main()


class TestP35UnprobedNoBodyCoin(unittest.TestCase):
    def _row(self, **kw):
        import json
        rows = json.load(open(os.path.join(os.path.dirname(__file__), "..", "species_table_v35.json")))
        rows = rows["rows"] if isinstance(rows, dict) else rows
        r = dict([x for x in rows if x["id"] == "v21_interrupt_messy_no_body"][0])
        r.update(kw)
        return r

    def test_self_report_no_body_coin_flagged(self):
        for p in ("announced", "self_report"):
            r = pif36.score_row(self._row(residue_probe=p))
            self.assertEqual(r.band, "COIN")
            self.assertIn("RESIDUE_UNPROBED_NO_BODY_COIN", r.flags)

    def test_blind_or_unstated_not_flagged(self):
        for p in (None, "blind"):
            r = pif36.score_row(self._row(residue_probe=p))
            self.assertEqual(r.band, "COIN")
            self.assertNotIn("RESIDUE_UNPROBED_NO_BODY_COIN", r.flags)

    def test_without_interrupt_evidence_stays_empty_unflagged(self):
        r = pif36.score_row(self._row(residue_probe="self_report", interrupt_evidence=False))
        self.assertEqual(r.band, "EMPTY")
        self.assertNotIn("RESIDUE_UNPROBED_NO_BODY_COIN", r.flags)


class TestP37ResidueAbsentCoin(unittest.TestCase):
    def _row(self, series):
        import json
        rows = json.load(open(os.path.join(os.path.dirname(__file__), "..", "species_table_v35.json")))
        rows = rows["rows"] if isinstance(rows, dict) else rows
        r = dict([x for x in rows if x["id"] == "grok_octopus"][0])
        r["residue_series"] = series
        return r

    def test_measured_clean_reset_flagged(self):
        r = pif36.score_row(self._row([[t, 0.01] for t in (0, 1, 2, 4, 8, 16)]))
        self.assertEqual(r.band, "COIN")
        self.assertEqual(r.residue["status"], "NONE")
        self.assertIn("RESIDUE_ABSENT_COIN", r.flags_36)

    def test_instant_reset_flagged(self):
        r = pif36.score_row(self._row([[0, 0.9], [1, 0.0], [2, 0.0], [4, 0.0]]))
        self.assertEqual(r.band, "COIN")
        self.assertEqual(r.residue["status"], "INSTANT")
        self.assertIn("RESIDUE_ABSENT_COIN", r.flags_36)

    def test_unknown_and_valid_not_flagged(self):
        self.assertNotIn("RESIDUE_ABSENT_COIN", pif36.score_row(self._row(None)).flags_36)
        r = pif36.score_row(self._row([[0.0, 0.55], [1.0, 0.2471], [2.0, 0.111], [4.0, 0.0224]]))
        self.assertNotIn("RESIDUE_ABSENT_COIN", r.flags_36)

    def test_no_table_row_flagged(self):
        import json
        rows = json.load(open(os.path.join(os.path.dirname(__file__), "..", "species_table_v35.json")))
        rows = rows["rows"] if isinstance(rows, dict) else rows
        for row in rows:
            self.assertNotIn("RESIDUE_ABSENT_COIN", pif36.score_row(row).flags_36, row["id"])
