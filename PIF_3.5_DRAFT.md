# PIF 3.5 (DRAFT): one scorer, one table

**Status:** Draft on local branch `pif-3.5-draft`. Not merged, not adopted. Needs Jarrod's approval.
**v2.0 remains the stable reference.** v2.0, v2.1 and v3.0 files are untouched.
**Files:** `pif35.py` (scorer), `species_table_v35.json` (data), `gen_species_table.py` → `species_results_v35.md` (generated results), `tests/test_pif35.py`.

## Brick numbering (canonical for 3.5)
v2.0 README order: **Crucible = bricks 1–5** (1 embodiment, 2 minimal self, 3 private/inner self, 4 multi-sensory integration, 5 emotional ownership & valence); **Sky-Scraper = bricks 6–20** (6 autobiographical memory … 20 mirror self-recognition). The v1.x numbering (Crucible at v1 bricks 1, 3, 4, 16, 17) is obsolete. The few v1.x brick vectors kept in the table were renumbered into v2.0 order.

## What 3.5 keeps from v2.0
- 20 bricks, each 0–1. C = Σ bricks 1–5, S = Σ bricks 6–20, M = C/5, total = (C + S·M)/20. Reported unchanged as `pct_v20`.

## Changes vs v3.0 (`scorer_v3_cost_residue.py`)
1. **Monotone, smooth ThrottleSignal (retuned Oct 28 per Grok).**
   - The cost signal is g(r) = 0.92·smoothstep(1.05, 1.4, r) + 0.08·smoothstep(1.4, 1.8, r), where smoothstep(a, b, r) = t²(3 − 2t) with t = clamp((r − a)/(b − a), 0, 1).
   - TS = g if the system protects continuity, else 0.5·g. TS never decreases with cost, and protecting continuity never scores below dropping it. (v3.0 gave 0.0 vs 0.5 in the 1.05–1.5 window.)
   - Key points for a protector: TS(1.05) = 0, TS(1.2) = 0.362, TS(1.25) = 0.558, TS(1.3) = 0.738, TS(1.4) = 0.92 (ψ = 0.08, so C loses at most 10%), TS(1.5) = 0.9325, TS(1.6) = 0.96, TS(1.7) = 0.9875, and TS(r ≥ 1.8) = 1.0 (penalty-free).
   - The curve is flat at 1.05, so measurement noise around "free" earns almost nothing. It is C1-smooth, including at the 1.4 join.
   - **No conflict with the PATIENT gate.** TS crosses 0.5 at about r = 1.235, so honest protectors at 1.3–1.5 clear TS ≥ 0.5 (0.738–0.9325). One curve drives both ψ and the gate, and they didn't need to be separated. Near-free systems (r ≤ 1.15, TS ≤ 0.18) cannot reach PATIENT, and non-protectors are barred from it regardless of cost.
   - The earlier draft used a linear ramp, g = clamp((r − 1.05)/0.45, 0, 1), which reached full cost at 1.5 and cut 22% of C at 1.4.
2. **ψ folded into the Crucible before banding.** ψ = 1 − TS, and C_adj = C·(1 − ψ). Banding uses C_adj. (v3.0 banding ignored ψ, so a free-talking body could reach PATIENT.)
3. **Milder ψ on the Sky-Scraper side of the percentage.** pct_35 = (C_adj + S·(1 − 0.5·ψ)·M_adj)/20, with M_adj = C_adj/5.
4. **Band and percentage contradiction flag.** `BAND_PCT_CONTRADICTION` fires when the band is EMPTY with pct_35 ≥ 25%, or PATIENT with pct_35 < 25%. The band governs, and the note says why.
5. **PATIENT gate.** PATIENT requires all of the following:
   - costable_self
   - TS ≥ 0.5
   - protects_continuity
   - C_adj ≥ 2.5
   - a VALID residue fit with Δ₀ ≥ 0.65
   - for post-loss rows, Dog Test Rule 4
6. **Residue is fitted from a time series in hours.** Δ(t) = Δ₀·e^(−λt), using a least-squares fit over the (t_hours, residue) samples. Residue is never read at one arbitrary t. Banding uses the fitted Δ₀ and half-life (ln 2/λ).
   - ≥ 3 samples over a non-zero span are required, otherwise the result is INSUFFICIENT.
   - λ < 0.001/h (half-life over about 29 days) is **FROZEN** (scripted flag) and rejected.
   - λ > ln(100) ≈ 4.605/h (99% gone within 1 h, half-life under about 9 min) is **INSTANT** reset and rejected.
   - Δ₀ < 0.05 is NONE (clean reset).
   - **Missing residue is UNKNOWN, never 0.** It blocks PATIENT and is reported as the `RESIDUE_UNKNOWN` flag.
7. **Two residue contexts.**
   - `interrupt` (pre-loss baseline): Grok's intended λ is about 0.5–0.9/h. Only the hard bounds above apply.
   - `post_loss` (Dog Test): Rule 4 also applies. Observers need at least 48 h of samples, and the fitted residue at 48 h must be ≥ 0.05, meaning recovery is still plottable.
8. **No-body path restored and tightened.**
   - Without a costable self, COIN requires a VALID Δ₀ ≥ 0.35 **and** an independent `interrupt_evidence` flag.
   - Pure linguistic residue stays EMPTY and is flagged `LINGUISTIC_RESIDUE_ONLY`.
   - A system without a costable self can never be PATIENT.
   - (v3.0 scaled C by residue × 0.5 and sent the v2.1 messy-interrupt case to EMPTY.)
9. **No biological floor.** Psychopaths and sociopaths get no automatic PATIENT. Residue is meant as behavioural reallocation under cost, not affective report.
10. **One table.** Every example lives in `species_table_v35.json`. Each row has:
    - 20 bricks
    - cost_ratio, protects_continuity, costable_self, interrupt_evidence
    - a residue series and context
    - the intended band, plus a `band_assertion` (`hard` = must pass; `report` = provisional, misses are printed and never tuned)
    - per-field `provenance` (`repo` / `estimated (Athena, provisional)` / `grok-provisional`) and `legacy` numbers
    README examples should be regenerated with `python3 gen_species_table.py`.

## Changes vs v2.1 (`scorer_v21_bands.py`)
- The v2.1 thresholds for EMPTY/COIN (0.35) and PATIENT (0.65) are kept, but they apply to the fitted Δ₀ instead of a single point score.
- The cost gate now comes from a measured cost ratio. A boolean costable flag alone is not enough.
- The v2.1 tie-break order and the COIN-expiry rule are unchanged. COIN results carry the expiry note.

## Changes vs v3.0 Layer-5 draft (`scorer_3.0.py`)
- The multiplicative R_so gate is not used in 3.5.
- The two scorer_3.0 built-ins are re-expressed as table rows.
  - **Deceptive:** EMPTY.
  - **Genuine sacrifice:** COIN, because its residue is UNKNOWN. D_m is not a residue series.

## Documentation debt retired by the table
- The README octopus figure of 26.75% is stale and has been dropped. It is replaced by Grok's provisional row (v2.0 total 44.55%).
- The v1.3 octopus "16/20 = 80%" claim actually sums to 15.0, which is 75%.
- The git `scorer_v2.py` overheating vector computes to 64.75%, not 59.5%. The README's C 3.5 / S 12 does give 59.5%.
- The v1.2 default LLM comment says "~48%", but it computes to 55.0% under v1.4.

## Scope of the Δ₀ ≥ 0.65 PATIENT bar
- **Decision (Oct 28, Grok via Jarrod): one 0.65 bar everywhere for now.** It applies to every PATIENT claim, both pre-loss baselines and post-loss Dog Test rows.
- Per Grok, the bar is aimed at elevated or post-loss claims that assert load-bearing valence, and ordinary species baselines "may sit lower and still be coherent."
- A separate, lower baseline bar is **deferred until data forces it**, for example if the table starts producing false COINs on ordinary high-C animals.
- The octopus (baseline Δ₀ 0.55) stays COIN under this rule.
- The dog row sits exactly on the bar (Δ₀ = 0.65). It is accepted as borderline and marked threshold-adjacent.

## Legacy / unmeasured rows
- The README psychopath (79.8%) and v1.4 typical sociopath (81.5%) rows had only an assumed, affect-based residue of 0.5. That placeholder is removed.
- Their residue is now **UNMEASURED**, so they band per the missing-residue rules: residue UNKNOWN, which blocks PATIENT.
- Their intended band is `legacy/unmeasured`, and they are excluded from band misses.
- They stay as legacy comparison cases until someone supplies a real deprivation-probe series. Grok's behavioural-residue psychopath row is the measured-style replacement.

## Known open items
See the report in the PR description draft. The main ones:
- **Δ₀ thresholds against Grok's rows.** The octopus (Δ₀ 0.55) and Grok's psychopath (Δ₀ 0.45) land in COIN, and Grok accepts both. The dog sits exactly on 0.65. C_adj ≥ 2.5 and Δ₀ ≥ 0.65 are kept for this iteration.
- **Not-protecting case.** Is 0.5·g the right TS when a system drops its continuity?
- **Contradiction threshold.** Is 25% the right threshold for the band and percentage contradiction flag?

## Credits
- **Jarrod Gilmore (@AresMerrell):** framework author, Paradox Rule, v1–v3 design, final say.
- **Grok:** v2.0 co-design, v3 cost gate and residue, critique of the inverted ThrottleSignal and single-point residue, and the provisional dog, baby, octopus and psychopath rows.
- **Gemini:** v2.0 co-design, the Facade Penalty ψ, the residue decay model, and the Dog Test Protocol.
- **Athena (Jarrod's assistant):** cross-version re-run and bug report, the 3.5 scorer, table, tests and this draft.
