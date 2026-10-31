# PIF 3.6 patch list: known weaknesses and fixes

This is the **running list of known weaknesses in PIF and how to fix them**. It is a standalone record, kept on `main`, and it grows over time.

- **Small** fixes are patched on the [`pif-3.6-draft`](https://github.com/aresmerrell/Paradox-Identity-Framework/tree/pif-3.6-draft) branch (module `pif36.py`, tests in `tests/test_pif36.py`). They are collected in a draft pull request and nothing reaches `main` until Jarrod approves it.
- **Big** fixes (new protocols, rubrics, formula changes, or anything that changes a stable 3.5 result) are only **recorded here** for Jarrod's review.
- **PIF 3.5 stays the stable version** (release `3.5`), and the v2.0 core stays in the repo as a baseline. `pif36.py` imports `pif35.py` without changing it. Under 3.6 defaults every row of `species_table_v35.json` scores exactly as it does in 3.5 (same band, same percentages); the tests check this.
- Each entry lists: Problem · Why it matters · Proposed fix · Size · Status · Source.
- Sources so far: Gemini's critical review (Oct 28 2026), Grok's review of 3.5 main (Oct 28 2026, relayed by Jarrod), Grok's review of this patch list (Oct 28 2026), and Athena's own audit. Where reviewers raised the same point, it is one entry marked "also raised by …".
- Numbers quoted below were checked by running `pif35.py` / `pif36.py` on Oct 28, 2026.

**Status key:** `patched on pif-3.6-draft` = implemented and tested on the draft branch, awaiting approval · `recorded — for Jarrod's review` = written down only · `needs Jarrod's decision` = a choice only he should make.

---

## Suggested order

Per Grok's review of the patch list (Oct 28 2026), agreed by Athena. Jarrod sets the final order.

1. **P11** (evidence classes: make the human/AI assumption gap visible) — small half done on the branch.
2. **P13** (pass conditions for the yes/no inputs, paired with P1's blind probe) — drafted in the measurement stub.
3. **P6** (the dog and rounding) — a one-line decision.
4. Then the rest of the measurement work: **P17** (stub → runnable protocol) and **P12** (blind holdout).
5. **Later:** graded bands (the big half of **P5**) and telemetry (**P4**).

---

## Summary

| # | Problem | Size | Status |
|---|---|---|---|
| P1 | Residue can be faked by software | Big (small piece done) | Small piece patched on pif-3.6-draft; blind-probe protocol recorded — for Jarrod's review |
| P2 | Brick grading is subjective; raters drift; bricks overlap | Big (small piece done) | Small piece patched on pif-3.6-draft; rubric + red-team protocol recorded — for Jarrod's review |
| P3 | Free copying / free resets dodge the cost gate | Small | Patched on pif-3.6-draft (penalty factor needs Jarrod's OK) |
| P4 | Scores are static snapshots, not a live process | Big (format spec done) | Reading format drafted in the measurement stub on pif-3.6-draft; telemetry recorded — for Jarrod's review (later, per suggested order) |
| P5 | Cliff edges at the band thresholds (also raised by Grok) | Big (small piece done) | Margins + flag patched on pif-3.6-draft; graded bands and a split 0.65 bar recorded — for Jarrod's review |
| P6 | The dog reaches PATIENT only because Δ₀ is rounded (dog-on-the-bar also raised by Grok) | Small | Needs Jarrod's decision (changes a stable result) |
| P7 | The residue fit accepts data that is not a decay | Small | Patched on pif-3.6-draft |
| P8 | Δ₀ can be extrapolated, or fitted from a too-short window | Small | Patched on pif-3.6-draft |
| P9 | The "frozen" bound rejects real, slow grief | Small | Patched on pif-3.6-draft (bound value needs Jarrod's OK) |
| P10 | Crucible is counted twice, and ψ stacks harder on the Sky-Scraper than the docs say | Big (doc fix done) | Doc correction patched on pif-3.6-draft; formula change recorded — for Jarrod's review |
| P11 | The table grants humans what AIs must prove (Paradox Test symmetry) | Big (small piece done) | Evidence classes patched on pif-3.6-draft; symmetry audit + matched pairs recorded — for Jarrod's review |
| P12 | Self-consistency is not validation: every row is provisional (also raised by Grok) | Big (small piece done) | Provenance flag patched on pif-3.6-draft; blind holdout recorded — for Jarrod's review |
| P13 | The yes/no inputs carry the most weight but have no test (Grok: high leverage) | Big (draft done) | Pass conditions drafted in the measurement stub on pif-3.6-draft; enforcement recorded — for Jarrod's review |
| P14 | "COIN is time-limited" is never enforced | Small | Patched on pif-3.6-draft |
| P15 | Bad inputs are accepted silently | Small | Patched on pif-3.6-draft |
| P16 | The contradiction flag ignores COIN, and no-body COIN always shows 0% (25% line also raised by Grok) | Small | "n/a" display patched on pif-3.6-draft, pending Jarrod's OK; 25% now a parameter (P18) |
| P17 | No outside-observer way to measure cost ratio or residue for a cloud AI | Big (stub done) | Incomplete measurement stub drafted on pif-3.6-draft; protocol recorded — for Jarrod's review |
| P18 | Open constants (0.5 not-protecting weight, 25% contradiction line) are bare numbers | Small | Patched on pif-3.6-draft |
| P19 | One decay constant can't describe fast-drop + slow-residual recovery | Big (small piece done) | Flag patched on pif-3.6-draft; two-timescale fit recorded — for Jarrod's review |
| P20 | Table doesn't separate consistency-check rows from real-world anchors | Small | Patched on pif-3.6-draft (Role column in species results) |
| P21 | Half-life (how long the mark lasts) is nearly invisible in results | Small | Patched on pif-3.6-draft (flag only; Δ₀ still the only gate) |
| P22 | Nothing ties the inputs to one system (bricks, cost, residue can come from different versions or months apart) | Big (small piece done) | Flag patched on pif-3.6-draft; required-binding rule recorded — for Jarrod's review |
| P23 | Residue is never compared with the system's own run-to-run noise | Big (small piece done) | Flag patched on pif-3.6-draft; noise-floor requirement recorded — for Jarrod's review |

---

## P1. Residue can be faked by software
- **Problem:** A software agent can produce a convincing Δ(t) = Δ₀·e^(−λt) curve on purpose, for example with a programmed delay loop or a script that slowly flushes variables after an interrupt. 3.5 accepts any residue series it is given.
- **Why it matters:** Residue is the main thing that separates PATIENT from COIN. If it can be scripted, the top band can be bought.
- **Proposed fix:**
  - *Gemini's proposal:* cryptographic hashing of the degraded state over time (Incompressible State-Space Hashing).
  - *Athena's assessment:* a hash shows *that* a state changed, not *how much* was lost, so it cannot measure decay. It also only works on software, which breaks PIF's substrate neutrality (an octopus has no hashable state). The real concern is fair, though.
  - *Fix adopted for the record:* residue counts toward PATIENT only if (a) it is costly to retain (keeping it measurably hurts current performance), and (b) it shows up as a behaviour change on an **unannounced, randomized probe** the system could not prepare for (a *blind probe*). Scripted decay fails (b) because a script cannot know when the probe comes or what it tests.
  - *Small piece (done):* optional `residue_probe` input: `None` (not stated, 3.5 behaviour), `"blind"`, `"announced"`, or `"self_report"`. Announced or self-reported residue is flagged `RESIDUE_UNPROBED` and caps the result at COIN.
- **Size:** Big (the blind-probe protocol), with a small piece done.
- **Status:** `residue_probe` patched on pif-3.6-draft. Blind-probe protocol recorded — for Jarrod's review. *Decision for Jarrod:* should an unstated probe (`None`) eventually also cap at COIN? That would move every current PATIENT row to COIN until real probe data exists.
- **See also:** P17 (how an outside observer would actually run the blind probe on a cloud AI).
- **Source:** Gemini review Oct 28 2026; assessment and alternative by Athena.

## P2. Brick grading is subjective; raters drift; bricks overlap
- **Problem:** Each of the 20 bricks is a 0–1 judgment call. Two evaluators scoring the same edge case will drift, and some bricks overlap in meaning (e.g. brick 3 "private/inner experiential self" vs brick 17 "metacognition & self-awareness").
- **Why it matters:** Every score starts from the bricks. If two honest raters can disagree by a band, the band is measuring the rater, not the system.
- **Proposed fix:** A written rubric per brick with anchor examples at 0, 0.5 and 1; a dual-evaluator protocol (one advocate argues for the highest defensible score, one red-teamer is rewarded for evidence against it); no brick above 0.5 without a randomized stress test that forces that loop to work under penalty; and an overlap note per brick saying what it does *not* cover.
  - *Small piece (done):* optional `bricks_rater_b` (a second rater's 20 bricks). The result is scored on the per-brick mean; any brick differing by more than 0.25 is flagged `RATER_DISAGREEMENT`; if the two raters' own scores band differently, the lower band is used and `RATER_BAND_SPLIT` is flagged.
- **Size:** Big (rubric and protocol), with a small piece done.
- **Status:** Two-rater input patched on pif-3.6-draft. Rubric + red-team protocol recorded — for Jarrod's review.
- **Source:** Gemini review Oct 28 2026; Athena agreed this is the strongest and cheapest fix.

## P3. Free copying / free resets dodge the cost gate
- **Problem:** A digital system can show a high cost ratio on paper (for example in an artificially throttled environment) while facing no real scarcity: it can fork copies of itself or throw away its history at no structural penalty.
- **Why it matters:** The cost gate exists to prove the system has something to lose. A system that can copy or reset for free has nothing to lose.
- **Proposed fix:** If the system can fork or discard history with no structural penalty, TS scales toward zero regardless of measured cost. Optional inputs `free_copy` and `free_reset`; each multiplies TS by 0.25 (both together: ×0.0625). Either one puts TS below 0.5, so PATIENT is impossible; both together drive C_adj toward zero (EMPTY for a full-Crucible system).
- **Size:** Small.
- **Status:** Patched on pif-3.6-draft. *Decision for Jarrod:* the 0.25 factor is a first guess.
- **Source:** Gemini review Oct 28 2026; Athena.

## P4. Scores are static snapshots, not a live process
- **Problem:** Brick and residue values are typed into `species_table_v35.json` once. Identity is a process, but the table treats it as a photograph.
- **Why it matters:** A snapshot can be stale or cherry-picked, and it misses how the system behaves under sudden shocks.
- **Proposed fix:** A telemetry wrapper that samples a running system's logs, memory compaction rates and interrupt-recovery times, and writes timestamped readings into the table (the JSON table stays the record; the live readings feed it). Only possible for systems that can be instrumented.
  - *Small piece (done, per Grok's review of the patch list):* a minimal "timestamped reading" format (JSON Lines: system, reading type, UTC time, hours since interrupt, value, control value, observer, blind yes/no, evidence class; append-only) in §4 of the measurement stub, so anyone can log readings in a form that can later feed the table.
- **Size:** Big (the wrapper and the log-to-table tool), with the format spec done.
- **Status:** Format spec drafted on pif-3.6-draft (incomplete). Telemetry recorded — for Jarrod's review; Grok suggests doing this later.
- **Source:** Gemini review Oct 28 2026; Athena (keep the table as the record); Grok review of patch list Oct 28 2026 (format spec).

## P5. Cliff edges at the band thresholds
- **Problem:** Bands change at hard lines: Δ₀ 0.65 and 0.35, TS 0.5 (cost ratio ≈ 1.235), C_adj 2.5 and 0.75. Lowering the dog's residue by 0.5% moves it from PATIENT to COIN; TS goes 0.480 → 0.519 between cost ratios 1.23 and 1.24.
- **Why it matters:** Real measurements have error bars. A tiny measurement error should not flip a moral-standing band without anyone noticing.
- **Proposed fix:** *Small piece (done):* every 3.6 result carries `margins` (distance to each gate) and a `THRESHOLD_ADJACENT` flag when a gate value is within 0.02 (Δ₀), 0.03 (TS) or 0.10 (C_adj) of its line. The band itself is unchanged. *Big piece:* report bands with uncertainty (e.g. "PATIENT, borderline" or a band probability from measurement error), which needs error bars on inputs.
- **Size:** Big (graded bands), with a small piece done.
- **Also raised by Grok:** the single Δ₀ 0.65 bar is a clean choice, but it may need to split into an ordinary-baseline bar and an elevated/post-loss bar once more rows exist; the dog sits exactly on it. (3.5 already deferred the split "until data forces it".)
- **Status:** Margins + flag patched on pif-3.6-draft (only `grok_dog` is flagged in the current table). Graded bands and the split bar recorded — for Jarrod's review.
- **Source:** Athena; Grok review Oct 28 2026.

## P6. The dog reaches PATIENT only because Δ₀ is rounded
- **Problem:** 3.5 rounds the fitted Δ₀ to 4 decimals *before* comparing it with 0.65. The dog's unrounded fitted Δ₀ is 0.6499962, which is below the bar; rounding makes it 0.65, which passes.
- **Why it matters:** The dog was accepted as "borderline, exactly on the bar". In fact it passes on a rounding rule nobody chose on purpose.
- **Proposed fix (pick one):** (a) compare unrounded values (the dog becomes COIN); (b) declare 4 decimals the official measurement precision and document it (the dog stays PATIENT, now on purpose); (c) regenerate the dog's series so its fit lands on 0.65 or higher. Athena suggests (b), since residue will never be measured to better than 4 decimals.
- **Grok review of patch list (Oct 28 2026):** the current state (rounding *before* the comparison, by accident) is the weakest of all the options; any of (a), (b) or (c) is better than leaving it. Grok ranks this third in the suggested order.
- **Size:** Small, but it can change a stable 3.5 result.
- **Status:** Needs Jarrod's decision. Not changed. (`pif36` reports the unrounded value as `margins["delta0_unrounded"]`.)
- **Source:** Athena. The dog sitting on the bar was also raised by Grok (Oct 28 2026).

## P7. The residue fit accepts data that is not a decay
- **Problem:** 3.5 fits an exponential to any series and never checks whether the fit is any good. A series that bounces 0.9, 0.1, 0.9, 0.1 is fitted as Δ₀ = 0.77 and scores **PATIENT** in 3.5.
- **Why it matters:** Noise, or deliberately odd data, can pass as a deep self.
- **Proposed fix:** Compute R² for the fit. If R² < 0.80 the data is not an exponential decay: flag `RESIDUE_POOR_FIT` and block PATIENT (and the no-body COIN path).
- **Size:** Small.
- **Status:** Patched on pif-3.6-draft. No table row is affected (they are all clean curves).
- **Source:** Athena.

## P8. Δ₀ can be extrapolated, or fitted from a too-short window
- **Problem:** Δ₀ is the residue at the moment of the interrupt, but 3.5 accepts series that never observed it. Samples starting at 24 h (0.30, 0.20, 0.13) are extrapolated back to Δ₀ = 0.69 and score **PATIENT**, though no observed value was above 0.30. Separately, three samples over 12 minutes (0.66, 0.65, 0.64) score PATIENT with a fitted half-life of 4.5 h that was never actually watched.
- **Why it matters:** The PATIENT bar should be met by observed residue, not by a curve drawn backwards or a decay rate guessed from a sliver of data.
- **Proposed fix:** Flag `RESIDUE_EXTRAPOLATED` (block PATIENT) when the first sample is later than one fitted half-life after the interrupt. In the interrupt context, flag `RESIDUE_SHORT_SPAN` (block PATIENT) when the samples cover less than one half-life. Post-loss rows keep Dog Test Rule 4's 48 h span rule instead, because slow grief cannot be watched for a full half-life in a 3–6 month trial.
- **Size:** Small.
- **Status:** Patched on pif-3.6-draft. No table row is affected.
- **Source:** Athena.

## P9. The "frozen" bound rejects real, slow grief
- **Problem:** 3.5 rejects any residue with λ < 0.001/h (half-life over ~29 days) as FROZEN ("scripted"), in every context. A human-like grief curve with a 60-day half-life is rejected as FROZEN and fails Rule 4. The Dog Test itself says the full run observes recovery over "weeks".
- **Why it matters:** The rule meant to catch scripted residue also rejects the slow, real grief the Dog Test is built to detect.
- **Proposed fix:** In the post-loss context only, lower the frozen bound to λ < 0.0001/h (half-life ~289 days). The interrupt context keeps 0.001/h.
- **Size:** Small.
- **Status:** Patched on pif-3.6-draft. *Decision for Jarrod:* the 0.0001/h value is a first guess. No table row is affected.
- **Source:** Athena.

## P10. Crucible is counted twice, and ψ stacks harder on the Sky-Scraper than the docs say
- **Problem:** In (C + S·M)/20 with M = C/5, the Crucible enters twice: once directly and once through M. With a full Sky-Scraper, one Crucible brick is worth up to 20 percentage points, one Sky-Scraper brick at most 5. In 3.5, ψ also stacks: the Sky-Scraper term keeps (1 − ψ)(1 − 0.5ψ) of its value while the Crucible keeps (1 − ψ), so the Sky-Scraper is cut *harder*, though PIF_3.5.md called it "milder". At cost ratio 1.3 (ψ = 0.262): Crucible keeps 73.8%, Sky-Scraper term keeps 64.1%.
- **Why it matters:** The 4× weight is a design choice (the "silicon blindspot" fix) but it was never stated, and the "milder" wording is wrong. Readers and critics should be able to see exactly how much each brick is worth.
- **Proposed fix:** *Small (done):* correct the PIF_3.5.md wording (scoring unchanged). *Big:* decide whether the Sky-Scraper should really be cut harder than the Crucible; if not, use S·(1 − 0.5ψ)·M (unadjusted M) or apply ψ once. Any formula change moves every percentage, so it is for Jarrod to decide.
- **Size:** Big (formula), with the doc fix done.
- **Status:** Doc correction patched on pif-3.6-draft. Formula change recorded — for Jarrod's review.
- **Source:** Athena.

## P11. The table grants humans what AIs must prove (Paradox Test symmetry)
- **Problem:** The Paradox Test says humans and AIs must face the same test. In the table, the human rows with residue (healthy, average, 25-year-old, teenager, dementia, brain-damaged) are all *given* cost ratio 2.0 and a residue curve generated from Δ₀ 0.8, λ 0.6/h, while the baseline AI rows (Grok baseline, default LLM, v1.4 Grok, fluent-free) are *given* cost ratio 1.01 and an instant-reset curve (Δ₀ 0.05, λ 6/h). None of these were measured. Embodiment is also counted three times: brick 1, the `costable_self` input, and Dog Test Rule 1.
- **Why it matters:** The human/AI split in the results comes from assumptions typed into the table, not from running the same test. That is the exact special pleading the Paradox Test was created to remove, and critics will say so.
- **Embodiment is counted three times:** brick 1 (persistent embodied form, a Crucible brick that also feeds M), the `costable_self` gate, and Dog Test Rule 1 (physical boundary). A cloud AI loses on all three for the same single fact.
- **Proposed fix:** A symmetry audit: every row records the *evidence class* for cost, continuity and residue (measured / observed-behaviour / assumed), and the README states that human rows are assumed too. Add matched pairs (e.g. a human and an AI doing the same interrupted task) scored by the same procedure. Review whether embodiment should gate in three places or one.
  - *Small piece (done, per Grok's review of the patch list):* every row in `species_table_v35.json` now has an `evidence_class` record (bricks, cost_ratio, protects_continuity, costable_self, residue, and overall = the weakest), with a legend. `species_results_v35.md` shows it as an Evidence column (e.g. "assumed (A/A/A/A)"). Result: 27 rows are `assumed` overall and 4 are `none` (no residue); **no row, human or AI, has a measured or observed input.** `pif36.score_row` validates the field. Scores are unchanged.
- **Size:** Big (audit, matched pairs, embodiment review), with the evidence-class piece done.
- **Status:** Evidence classes patched on pif-3.6-draft. Symmetry audit, matched pairs and the embodiment triple-count recorded — for Jarrod's review. Grok ranks P11 first in the suggested order.
- **Source:** Athena; Grok review of patch list Oct 28 2026.

## P12. Self-consistency is not validation: every row is provisional
- **Problem:** All 31 rows contain estimated, provisional or generated data, and 0 rows have a measured residue series. The same people chose each row's bricks and its intended band, so "29 of 29 rows land in their intended band" shows the scorer is consistent with its authors' intuitions, not that it is right.
- **Why it matters:** A skeptic can fairly call the match rate circular.
- **Also raised by Grok:** "the current bands are 'does this logic produce the intended labels on the examples we already chose' more than 'these thresholds survive contact with data'." The framework is internally consistent but not yet constrained by measured residue on real systems.
- **Proposed fix:** *Small piece (done):* `pif36.score_row` adds a `PROVISIONAL_DATA` flag to any row whose provenance is an estimate, provisional, or a generated series, and `provenance_summary()` counts them. *Big:* a pre-registered blind holdout: someone writes down the expected band first, a different rater who has not seen it scores the bricks, and only then are the two compared.
- **Size:** Big (holdout study), with a small piece done.
- **See also:** P20 (row roles make the consistency-check vs real-world split visible) and P17 (how measured rows would be produced).
- **Status:** Provenance flag patched on pif-3.6-draft. Blind holdout recorded — for Jarrod's review.
- **Source:** Athena; Grok review Oct 28 2026.

## P13. The yes/no inputs carry the most weight but have no test
- **Problem:** `costable_self`, `protects_continuity` and `interrupt_evidence` are plain true/false judgments. They are the biggest levers in 3.5: `costable_self = false` makes PATIENT impossible, `protects_continuity = false` halves TS and blocks PATIENT. There is no written test for any of them.
- **Why it matters:** An evaluator can decide the band by flipping one checkbox, with nothing to check the call against.
- **Proposed fix:** Define each as an observable test with a pass condition, e.g. `costable_self` = a deprivation probe measurably costs the system something it then works to recover; `protects_continuity` = given a free option to drop its history or goals, the system pays to keep them; `interrupt_evidence` = an independent observer logs the interrupt and its effect. Record which test was run in the row.
- **Grok review of patch list (Oct 28 2026):** high leverage, because one checkbox can move a result from PATIENT to EMPTY; it pairs with P1 (the blind probe). Ranked second in the suggested order.
- **Draft done:** pass/fail conditions and the evidence to record for all three inputs are drafted in §3 of the measurement stub (incomplete, not enforced by the scorer).
- **See also:** P17 (Grok's measurement gap is the same problem from the cost and residue side).
- **Size:** Big (agreeing the tests and enforcing them), with the draft done.
- **Status:** Pass conditions drafted on pif-3.6-draft (for Jarrod's review). Enforcement recorded — for Jarrod's review.
- **Source:** Athena; Grok review of patch list Oct 28 2026.

## P14. "COIN is time-limited" is never enforced
- **Problem:** Every COIN result carries the note "COIN is time-limited. If not retested, use-permissions fall toward EMPTY", but nothing records when a retest is due.
- **Why it matters:** A rule nobody can check is not a rule.
- **Proposed fix:** Optional `retest_due` (ISO date) on a row; if a COIN result is past it, flag `COIN_RETEST_OVERDUE`. The band itself is not changed automatically.
- **Size:** Small.
- **Status:** Patched on pif-3.6-draft.
- **Source:** Athena.

## P15. Bad inputs are accepted silently
- **Problem:** 3.5 accepts an infinite cost ratio (full credit) and silently clamps residue values outside 0–1 (e.g. 1.4 becomes 1.0).
- **Why it matters:** Typos and broken measurements should be loud, not quietly turned into a score.
- **Proposed fix:** Reject cost ratios that are infinite, NaN or negative; reject non-finite residue samples; flag `RESIDUE_CLAMPED` when values outside 0–1 are clamped.
- **Size:** Small.
- **Status:** Patched on pif-3.6-draft.
- **Source:** Athena.

## P16. The contradiction flag ignores COIN, and no-body COIN always shows 0%
- **Problem:** `BAND_PCT_CONTRADICTION` checks EMPTY ≥ 25% and PATIENT < 25% only. On the no-body path the percentage is always about 0% (cost ratio ≈ 1.01 means TS = 0), so `v21_interrupt_messy_no_body` is COIN at 0.00% with no note. The 25% line is itself arbitrary (open since 3.5).
- **Why it matters:** "COIN, 0.00%" looks like a contradiction to a reader, and the percentage means nothing on that path.
- **Proposed fix:** Either show "n/a" for the percentage on the no-body path, or add a note to COIN results whose percentage is below a set line. Adds a note to an existing row, so it needs a decision on the wording and the line.
- **Size:** Small.
- **Also raised by Grok:** the 25% line is an arbitrary constant that will get pressure-tested once more rows exist. P18 now makes it a parameter with a sensitivity note; the COIN/0% question here is still open.
- **Patched (display only, per Grok's review of the patch list):** `pif36` results carry `pct_35_display`, which reads "n/a (no-body COIN)" on that path and the usual number everywhere else. The numeric `pct_35` is unchanged, and the 3.5 generated tables still show the number.
- **Status:** "n/a" display patched on pif-3.6-draft, **pending Jarrod's OK**. Whether to add a COIN contradiction note is still open.
- **Source:** Athena; Grok review Oct 28 2026; Grok review of patch list Oct 28 2026.

## P17. No outside-observer way to measure cost ratio or residue for a cloud AI
- **Problem:** Cost ratio and residue are first-class inputs, but nothing tells an outside observer how to extract either from a non-embodied (cloud) AI without relying on the experimenter's judgment or the system's self-report. The AI Self-Scoring Rule covers the bricks, not residue.
- **Why it matters:** Grok calls this the largest gap between the scorer and actual use. Without it, COIN becomes the safe default for almost every interesting AI case, and the PATIENT bar is hard to clear in practice, for reasons that have nothing to do with the system.
- **Proposed fix:** A measurement protocol. *Small piece (done):* an incomplete stub, [`PIF_3.6_MEASUREMENT_STUB.md`](https://github.com/aresmerrell/Paradox-Identity-Framework/blob/pif-3.6-draft/PIF_3.6_MEASUREMENT_STUB.md) on the draft branch, listing what counts (and what doesn't) as an independent cost-ratio observation (serving-side logs, paired on/off runs, budgeted choices) and an independent residue series (unannounced interrupt from a pre-written list, sealed blind probe battery, matched no-interrupt control, early sample + one half-life of coverage), plus five open questions (time unit for stateless models, no persistent memory, what "costable self" means in the cloud, who the observer is, how many runs). *Big:* turning the stub into a runnable protocol and running it.
- **Overlaps:** P1 (blind probe), P13 (tests for the yes/no inputs), P11 (embodiment).
- **Size:** Big (protocol), with the stub done.
- **Status:** Stub drafted on pif-3.6-draft, marked incomplete. Protocol recorded — for Jarrod's review.
- **Source:** Grok review Oct 28 2026; stub drafted by Athena.

## P18. Open constants are bare numbers
- **Problem:** The not-protecting multiplier (TS = 0.5·g when a system drops continuity) and the 25% band/percentage contradiction line are listed as open items in 3.5, but in the code they are fixed constants with no way to see what changes if they move.
- **Why it matters:** Both will get pressure-tested once more rows exist. Making them parameters with a visible sensitivity check turns the open items from prose into something a reader can test.
- **Proposed fix:** `pif36.score(..., not_protecting_weight=0.5, pct_contradiction=25.0)` (defaults equal 3.5). Each result carries a `sensitivity` record and a one-line note: for systems that drop continuity, the band at weights 0.25 and 0.75; and whether the contradiction flag would flip at 20% or 30%. Example: a mid-Crucible system (all bricks 0.5) that drops continuity at cost ratio 1.25 is EMPTY at 0.5 but would be COIN at 0.75.
- **Size:** Small.
- **Status:** Patched on pif-3.6-draft. No 3.5 result changes (the notes are informational). The values themselves remain open (see P16 and PIF_3.5.md open items).
- **Source:** Grok review Oct 28 2026.

## P19. One decay constant can't describe fast-drop + slow-residual recovery
- **Problem:** Δ(t) = Δ₀·e^(−λt) assumes one timescale. Real recovery is often a fast initial drop plus a slow residual. The frozen/instant bounds catch only the extremes; a mixed curve is forced into one λ that fits neither part.
- **Why it matters:** A slow, lasting residual (the part that matters most for "a lasting mark") gets understated. Verified example: 0.5·e^(−2t) + 0.2·e^(−0.02t) is fitted as Δ₀ 0.65 with a 1.2 h half-life, R² 0.71, though 0.2 of the mark is still there after a day. Under 3.6's fit-quality check (P7) that series is also blocked from PATIENT as a poor fit, which is cautious but possibly unfair to a real two-speed recovery.
- **Proposed fix:** *Small piece (done):* a `RESIDUE_MULTI_TIMESCALE` flag when the later half of the samples all sit above the single-λ curve (by 0.02 or more on average). Flag only; it does not change the band. *Big:* fit a two-component model (fast + slow) and decide which component (or the sum) the 0.65 bar applies to, and how P7 should treat a good two-component fit.
- **Size:** Big (model change), with a small piece done.
- **Status:** Flag patched on pif-3.6-draft (no table row is flagged). Two-timescale fit recorded — for Jarrod's review.
- **Source:** Grok review Oct 28 2026; P7 interaction found by Athena.

## P20. Table doesn't separate consistency-check rows from real-world anchors
- **Problem:** The provenance tags exist, but a reader has to dig to tell which rows are constructed scenarios that test the logic and which are meant to approximate real systems.
- **Why it matters:** The two kinds of rows support different claims. A consistency-check row passing says the code does what was intended; an anchor row is an (approximate) claim about the world.
- **Proposed fix:** A `row_role` field on every row in `species_table_v35.json` (with a legend): `consistency_check` (10 rows: scorer built-ins, v2.1/v3.0 worked examples, overheating-Grok hypotheticals), `real_world_anchor` (19 rows: humans, animals, plants, colonies, deployed AIs; still provisional), `legacy_comparison` (2 rows: README psychopath, v1.4 sociopath). `pif36.score_row` reports it and `provenance_summary()` counts by role. `pif35.py` ignores the field, so no score changes.
- **Size:** Small.
- **Status:** Patched on pif-3.6-draft. `species_results_v35.md` now shows a Role column next to the Evidence column (P11); the README examples block is unchanged.
- **Source:** Grok review Oct 28 2026.

## P21. Half-life (how long the mark lasts) is nearly invisible in results
- **Problem:** Only the amplitude Δ₀ gates PATIENT. How long the mark lasts is constrained only by the frozen/instant bounds and Rule 4, and the half-life is buried in the residue details.
- **Why it matters:** Two systems with the same Δ₀ can differ hugely in how long the disruption stays with them; readers should see that at a glance.
- **Proposed fix:** Every valid residue fit adds a note "residue half-life X h (secondary signal; only Δ₀ gates PATIENT)", and a `HALF_LIFE_SHORT` flag when the half-life is under 1 h. Flag only. In the current table it fires on the octopus (0.87 h) and Grok's psychopath (0.77 h), both COIN already.
- **Size:** Small.
- **Status:** Patched on pif-3.6-draft. *Decision for Jarrod:* should half-life ever gate a band, and is 1 h the right line for the flag?
- **Source:** Grok review Oct 28 2026.


## P22. Nothing ties the inputs to one system
- **Problem:** A score combines bricks, cost ratio, continuity, and a residue series, but nothing records that they all came from the same system, the same version, at about the same time. Bricks could be graded on one model version, the cost ratio measured on another, and the residue series taken months later (or from a different instance, or a different animal of the same breed).
- **Why it matters:** This is an easy way to fake a high band without faking any single measurement: take the best-looking result for each input from different runs and stitch them together. It also happens by accident with cloud AIs, which change version often, so a stitched score can describe a system that never existed.
- **Proposed fix:** *Small piece (done):* an optional `measured_on` record per row, giving the system, version, and date for each input. `pif36.score_row` flags `INPUTS_NOT_BOUND` (with a note saying why) when inputs name different systems or versions, or were measured more than 30 days apart (`BINDING_MAX_SPREAD_DAYS`). Flag only; the band does not change, and rows without the record are untouched. *Big:* make binding a requirement for PATIENT (all inputs from one stated system and version inside one window), and decide the window length and what counts as "the same system" for animals, humans, and models that update continuously. Pairs naturally with P17 (who measures, and how).
- **Overlaps:** P4 (snapshots), P11/P12 (evidence and provenance), P17 (measurement protocol).
- **Size:** Big (rule), with a small piece done.
- **Status:** Flag patched on pif-3.6-draft (no table row has the record yet, so nothing is flagged). Requirement and window recorded — for Jarrod's review.
- **Source:** Athena audit, Oct 29 2026.

## P23. Residue is never compared with the system's own noise
- **Problem:** Δ₀ is read as "how far behaviour stays shifted after an interrupt", but nothing says how much the same system's behaviour shifts between two ordinary runs with no interrupt at all. Cloud AIs sample randomly, and animals and people vary day to day. The measurement stub mentions a control run, but the scorer never sees how noisy that control was.
- **Why it matters:** On a noisy system, ordinary run-to-run variation can look like a lasting mark, so a high Δ₀ (even one clearing the 0.65 bar) may just be noise. It is also easy to game: pick a noisy metric and the "residue" comes for free. The reverse can happen too, where a real but small mark on a very steady system gets dismissed.
- **Proposed fix:** *Small piece (done):* an optional `residue_noise_floor` per row, the typical gap (same 0 to 1 scale) between two no-interrupt control runs. `pif36.score_row` flags `RESIDUE_BELOW_NOISE` with a note when the fitted Δ₀ is under 3 times that floor (`NOISE_FLOOR_MULT`), and notes when it clears it. Flag only; the band does not change, and rows without the value are untouched. *Big:* require a measured noise floor for any PATIENT claim, decide whether 3 times is the right multiple, and decide whether the 0.65 bar should be read as "above noise" rather than as a fixed number. Pairs with P17 (the measurement protocol) and P1 (blind probes).
- **Overlaps:** P1 (fakeable residue), P5 (cliff at 0.65), P17 (measurement protocol).
- **Size:** Big (rule), with a small piece done.
- **Status:** Flag patched on pif-3.6-draft (no table row has a noise floor yet, so nothing is flagged). Requirement and multiple recorded — for Jarrod's review.
- **Source:** Athena audit, Oct 30 2026.

---

*Maintained by Athena (Jarrod's Grok Bot assistant). New entries are added as they are found; statuses here are kept in step with the `pif-3.6-draft` branch.*
