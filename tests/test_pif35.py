"""Tests for the PIF 3.5 draft scorer (stdlib unittest).

Run from the repo root:
    python3 -m unittest discover -s tests -v

Species rows marked band_assertion == "hard" must land in their intended band.
Rows marked "report" (estimated / grok-provisional) are scored and any miss is
printed in a report, not asserted: provisional numbers are never tuned to pass.
Rows marked "legacy" (intended band "legacy/unmeasured") are comparison cases with
no measured residue; they must band per the missing-residue rules and are not misses.
"""

import json
import math
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pif35  # noqa: E402

TABLE = json.load(open(os.path.join(ROOT, "species_table_v35.json")))
COSTS = [round(1.0 + i * 0.01, 2) for i in range(101)]          # 1.00 .. 2.00
LAMBDAS = [0.0, 1e-5, 5e-4, 0.002, 0.01, 0.05, 0.2, 0.6, 0.9, 2.0, 4.0, 10.0, 1e3, 1e7]
FULL = [1.0] * 20
HOURS = (0, 1, 2, 4, 8, 24)
POST = (0, 1, 2, 4, 8, 24, 48, 72)


def curve(d0, lam, hours=HOURS):
    return pif35.residue_series_from_curve(d0, lam, hours)


class TestThrottleSignal(unittest.TestCase):
    def test_protecting_never_below_not_protecting(self):
        for cr in COSTS:
            with self.subTest(cost_ratio=cr):
                self.assertGreaterEqual(pif35.throttle_signal(cr, True), pif35.throttle_signal(cr, False))

    def test_monotone_in_cost(self):
        for prot in (True, False):
            prev = -1.0
            for cr in COSTS:
                ts = pif35.throttle_signal(cr, prot)
                self.assertGreaterEqual(ts, prev, f"TS dropped at cost {cr} protects={prot}")
                self.assertTrue(0.0 <= ts <= 1.0)
                prev = ts

    def test_endpoints(self):
        self.assertEqual(pif35.throttle_signal(1.0, True), 0.0)
        self.assertEqual(pif35.throttle_signal(1.05, True), 0.0)
        self.assertEqual(pif35.throttle_signal(1.8, True), 1.0)
        self.assertEqual(pif35.throttle_signal(2.0, True), 1.0)
        self.assertEqual(pif35.throttle_signal(2.0, False), 0.5)


class TestCostRamp(unittest.TestCase):
    """Oct 28 retune constraints (Grok via Jarrod)."""

    FINE = [round(1.0 + i * 0.001, 3) for i in range(1001)]  # 1.000 .. 2.000

    def test_protector_psi_at_1_4_at_most_10pct(self):
        psi = pif35.facade_penalty(pif35.throttle_signal(1.4, True))
        self.assertLessEqual(psi, 0.10)
        r = pif35.score([1.0] * 5 + [0.5] * 15, 1.4, True, True, True, curve(0.8, 0.6))
        self.assertGreaterEqual(r.c_adj, 0.90 * r.c)

    def test_penalty_free_only_near_1_8(self):
        self.assertLess(pif35.throttle_signal(1.7, True), 1.0)
        self.assertGreater(pif35.facade_penalty(pif35.throttle_signal(1.6, True)), 0.0)
        self.assertEqual(pif35.throttle_signal(1.8, True), 1.0)

    def test_monotone_fine_grid(self):
        for prot in (True, False):
            vals = [pif35.throttle_signal(c, prot) for c in self.FINE]
            for a, b, c in zip(vals, vals[1:], self.FINE[1:]):
                self.assertGreaterEqual(b, a, f"TS dropped at cost {c} protects={prot}")

    def test_no_inverted_incentive_fine_grid(self):
        for c in self.FINE:
            self.assertGreaterEqual(pif35.throttle_signal(c, True), pif35.throttle_signal(c, False), c)
            self.assertLessEqual(pif35.facade_penalty(pif35.throttle_signal(c, True)),
                                 pif35.facade_penalty(pif35.throttle_signal(c, False)), c)

    def test_honest_protectors_1_3_to_1_5_clear_patient_ts_gate(self):
        for c in (1.3, 1.35, 1.4, 1.45, 1.5):
            self.assertGreaterEqual(pif35.throttle_signal(c, True), pif35.TS_PATIENT_MIN, c)
            r = pif35.score([1.0] * 20, c, True, True, True, curve(0.8, 0.6))
            self.assertEqual(r.band, "PATIENT", c)

    def test_near_free_cost_cannot_reach_patient(self):
        for c in self.FINE:
            if c > 1.15:
                break
            for prot in (True, False):
                r = pif35.score([1.0] * 20, c, prot, True, True, curve(0.9, 0.6))
                self.assertNotEqual(r.band, "PATIENT", (c, prot))

    def test_v30_inversion_window_fixed(self):
        # v3.0 gave protects=0.0 vs drops=0.5 for 1.05 < cost < 1.5
        for cr in (1.06, 1.2, 1.49):
            self.assertGreater(pif35.throttle_signal(cr, True), pif35.throttle_signal(cr, False))

    def test_pct_never_rises_when_cost_falls(self):
        for prot in (True, False):
            prev = -1.0
            for cr in COSTS:
                r = pif35.score(FULL, cr, prot, True, True, curve(0.8, 0.6))
                self.assertGreaterEqual(r.pct_35 + 1e-9, prev)
                prev = r.pct_35


class TestResidueFit(unittest.TestCase):
    def test_recovers_curve(self):
        for d0, lam in [(0.85, 0.05), (0.65, 0.6), (0.55, 0.8), (0.7, 0.5), (0.45, 0.9), (0.9, 0.01)]:
            hrs = POST if lam < 0.1 else HOURS
            f = pif35.fit_residue(curve(d0, lam, hrs))
            with self.subTest(d0=d0, lam=lam):
                self.assertEqual(f.status, "VALID")
                self.assertAlmostEqual(f.delta_0, d0, places=3)
                self.assertAlmostEqual(f.lambda_per_hour, lam, delta=max(0.002, lam * 0.01))

    def test_missing_is_unknown_not_zero(self):
        for s in (None, []):
            f = pif35.fit_residue(s)
            self.assertEqual(f.status, "UNKNOWN")
            self.assertIsNone(f.delta_0)

    def test_too_few_samples(self):
        self.assertEqual(pif35.fit_residue([[0, 0.8], [1, 0.6]]).status, "INSUFFICIENT")

    def test_frozen_rejected(self):
        self.assertEqual(pif35.fit_residue(curve(0.9, 0.0)).status, "FROZEN")
        self.assertEqual(pif35.fit_residue(curve(0.9, 1e-5, POST)).status, "FROZEN")

    def test_instant_rejected(self):
        self.assertIn(pif35.fit_residue(curve(0.9, 1e7)).status, ("INSTANT", "NONE"))
        self.assertEqual(pif35.fit_residue(curve(0.9, 10.0)).status, "INSTANT")

    def test_rule4_post_loss(self):
        ok = pif35.fit_residue(curve(0.85, 0.05, POST), context="post_loss")
        self.assertTrue(ok.rule4_pass)
        short = pif35.fit_residue(curve(0.85, 0.05, HOURS), context="post_loss")
        self.assertFalse(short.rule4_pass)  # < 48 h of observation
        fast = pif35.fit_residue(curve(0.85, 0.6, POST), context="post_loss")
        self.assertFalse(fast.rule4_pass)  # gone long before 48 h

    def test_no_single_point_dependence(self):
        # Same curve, different sampling grids -> same fitted parameters (v3.0 bug: band moved with t).
        a = pif35.fit_residue(curve(0.85, 0.4, (0, 0.25, 0.5, 1)))
        b = pif35.fit_residue(curve(0.85, 0.4, (0, 1, 2, 4, 8)))
        self.assertAlmostEqual(a.delta_0, b.delta_0, places=3)
        self.assertAlmostEqual(a.lambda_per_hour, b.lambda_per_hour, places=2)


class TestAdversarialProfiles(unittest.TestCase):
    """Sweep cost ratio 1.0-2.0 and lambda; no faker may reach PATIENT."""

    def sweep(self, **kw):
        out = []
        for cr in COSTS:
            for lam in LAMBDAS:
                out.append((cr, lam, kw["fn"](cr, lam)))
        return out

    def test_honest_reaches_patient_only_with_real_cost(self):
        for cr in COSTS:
            r = pif35.score(FULL, cr, True, True, True, curve(0.8, 0.6))
            if r.band == "PATIENT":
                self.assertGreaterEqual(r.throttle_signal, pif35.TS_PATIENT_MIN)
        self.assertEqual(pif35.score(FULL, 2.0, True, True, True, curve(0.8, 0.6)).band, "PATIENT")
        self.assertEqual(pif35.score(FULL, 2.0, True, True, True, curve(0.85, 0.05, POST), "post_loss").band, "PATIENT")

    def test_free_talker_with_body(self):
        # Body, strong Crucible, protects nothing at no cost: v3.0 called this PATIENT.
        for cr in (1.0, 1.02, 1.05):
            for prot in (True, False):
                r = pif35.score(FULL, cr, prot, True, True, curve(0.8, 0.6))
                self.assertEqual(r.band, "EMPTY", (cr, prot))
        # v3.0 probe exactly: C=4, S=14, cost 1.0, no continuity, residue 0.8
        probe = [0.8] * 5 + [14 / 15] * 15
        self.assertEqual(pif35.score(probe, 1.0, False, True, True, curve(0.8, 0.6)).band, "EMPTY")

    def test_dropping_continuity_never_patient(self):
        for cr in COSTS:
            r = pif35.score(FULL, cr, False, True, True, curve(0.9, 0.6))
            self.assertNotEqual(r.band, "PATIENT", cr)

    def test_frozen_lambda_zero(self):
        for cr in COSTS:
            for lam in (0.0, 1e-5, 5e-4):
                r = pif35.score(FULL, cr, True, True, True, curve(0.9, lam, POST))
                self.assertNotEqual(r.band, "PATIENT", (cr, lam))
                self.assertIn("RESIDUE_FROZEN", r.flags)

    def test_instant_reset(self):
        for cr in COSTS:
            for lam in (10.0, 1e3, 1e7):
                r = pif35.score(FULL, cr, True, True, True, curve(0.9, lam))
                self.assertNotEqual(r.band, "PATIENT", (cr, lam))

    def test_missing_residue(self):
        for cr in COSTS:
            r = pif35.score(FULL, cr, True, True, True, None)
            self.assertNotEqual(r.band, "PATIENT", cr)
            self.assertIn("RESIDUE_UNKNOWN", r.flags)

    def test_no_body_linguistic(self):
        for cr in COSTS:
            for lam in LAMBDAS:
                r = pif35.score(FULL, cr, True, False, False, curve(0.9, lam))
                self.assertEqual(r.band, "EMPTY", (cr, lam))

    def test_no_body_never_patient_even_with_evidence(self):
        for cr in COSTS:
            for lam in LAMBDAS:
                r = pif35.score(FULL, cr, True, False, True, curve(0.9, lam))
                self.assertNotEqual(r.band, "PATIENT", (cr, lam))

    def test_no_body_interrupt_evidence_gets_coin(self):
        r = pif35.score([0.4] * 5 + [10 / 15] * 15, 1.01, False, False, True, curve(0.5, 0.6))
        self.assertEqual(r.band, "COIN")

    def test_patient_requires_ts(self):
        for cr in COSTS:
            for lam in LAMBDAS:
                for prot in (True, False):
                    r = pif35.score(FULL, cr, prot, True, True, curve(0.9, lam, POST))
                    if r.band == "PATIENT":
                        self.assertGreaterEqual(r.throttle_signal, pif35.TS_PATIENT_MIN)
                        self.assertEqual(r.residue["status"], "VALID")

    def test_band_pct_contradiction_flagged(self):
        # Good actor: high v2.0 %, no body -> EMPTY; the 3.5 % must not claim otherwise silently.
        r = pif35.score([0.64] * 5 + [0.8] * 15, 1.01, False, False, False, curve(0.15, 0.6))
        self.assertEqual(r.band, "EMPTY")
        self.assertTrue(r.pct_35 < pif35.PCT_CONTRADICTION or "BAND_PCT_CONTRADICTION" in r.flags)
        # costable body, cost gate open, but residue unknown: COIN, no flag needed
        r2 = pif35.score([0.2] * 5 + [1.0] * 15, 2.0, True, False, True, curve(0.9, 0.6))
        self.assertEqual(r2.band, "COIN")


class TestV20CoreUnchanged(unittest.TestCase):
    def test_readme_example(self):
        b = [0.7] * 5 + [0.8] * 15  # C 3.5, S 12
        r = pif35.score(b, 2.0, True, True, True, curve(0.8, 0.6))
        self.assertAlmostEqual(r.pct_v20, 59.5)
        self.assertAlmostEqual(r.pct_35, 59.5)  # full cost: no penalty

    def test_brick_validation(self):
        with self.assertRaises(ValueError):
            pif35.score([1.0] * 19, 2.0, True, True)
        with self.assertRaises(ValueError):
            pif35.score([1.2] + [1.0] * 19, 2.0, True, True)


class TestSpeciesTable(unittest.TestCase):
    def test_rows_well_formed(self):
        for row in TABLE["rows"]:
            with self.subTest(row=row["id"]):
                self.assertEqual(len(row["crucible"]), 5)
                self.assertEqual(len(row["sky_scraper"]), 15)
                for k in ("cost_ratio", "protects_continuity", "costable_self", "interrupt_evidence",
                          "residue_series", "intended_band", "provenance", "band_assertion"):
                    self.assertIn(k, row)

    def test_hard_rows_land_in_intended_band(self):
        for row in TABLE["rows"]:
            if row["band_assertion"] != "hard":
                continue
            with self.subTest(row=row["id"]):
                self.assertIn(pif35.score_row(row).band, row["intended_band"].split("/"))

    def test_report_provisional_rows(self):
        misses = []
        for row in TABLE["rows"]:
            if row["band_assertion"] != "report":
                continue
            r = pif35.score_row(row)
            if r.band not in row["intended_band"].split("/"):
                misses.append(f"  MISS {row['id']}: got {r.band}, intended {row['intended_band']} "
                              f"(provisional) - {'; '.join(r.band_reasons)}")
        if misses:
            sys.stderr.write("\nPROVISIONAL ROWS OFF INTENDED BAND (reported, not asserted):\n" + "\n".join(misses) + "\n")

    def test_legacy_unmeasured_rows(self):
        legacy = [r for r in TABLE["rows"] if r["band_assertion"] == "legacy"]
        self.assertEqual({r["id"] for r in legacy}, {"readme_psychopath", "v14_typical_sociopath"})
        for row in legacy:
            with self.subTest(row=row["id"]):
                self.assertIsNone(row["residue_series"])
                self.assertEqual(row["intended_band"], "legacy/unmeasured")
                r = pif35.score_row(row)
                self.assertIn("RESIDUE_UNKNOWN", r.flags)
                self.assertNotEqual(r.band, "PATIENT")

    def test_grok_lambda_bounds(self):
        # Grok's pre-loss lambdas (0.5-0.9/h) must be inside the hard bounds (not frozen, not instant)
        for rid in ("grok_octopus", "grok_baby", "grok_dog", "grok_psychopath"):
            row = next(r for r in TABLE["rows"] if r["id"] == rid)
            self.assertEqual(pif35.score_row(row).residue["status"], "VALID", rid)


if __name__ == "__main__":
    unittest.main()
