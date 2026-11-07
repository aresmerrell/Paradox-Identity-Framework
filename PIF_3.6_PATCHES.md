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
| P24 | Repeated timestamps pad the residue sample count, so a two-time series passes the fit check | Small (decision recorded) | Patched on pif-3.6-draft (blocks PATIENT like P7/P8); 3-point minimum recorded — for Jarrod's review |
| P25 | Δ₀ can be projected above every reading actually taken (first sample a little late) | Small (decision recorded) | Patched on pif-3.6-draft (blocks PATIENT like P7/P8/P24); tolerance and cap-instead-of-block recorded — for Jarrod's review |
| P26 | The residue model assumes the mark is biggest at the interrupt; a mark that builds up first is understated or called "scripted" | Big (small piece done) | Info flags patched on pif-3.6-draft (band unchanged); onset-aware fit recorded — for Jarrod's review |
| P27 | Readings bunched a few minutes apart count as separate times, so a series that is really two readings passes the fit checks | Small (decision recorded) | Patched on pif-3.6-draft (blocks PATIENT like P24); 2% grouping width and a spread-out sampling rule recorded — for Jarrod's review |
| P28 | Nothing records how many runs were tried, so the best of several noisy runs can be reported as the result | Big (small piece done) | Flag patched on pif-3.6-draft (band unchanged); report-all-runs rule recorded — for Jarrod's review |
| P29 | Residue sample times are bare numbers treated as hours, with no unit or wall-clock check | Big (small piece done) | Flags patched on pif-3.6-draft (block PATIENT); require wall-clock hours + UTC corroboration recorded — for Jarrod's review |
| P30 | Rule 4's "detectable at 48 h" check uses the fitted curve, not an actual reading | Small (decision recorded) | Patched on pif-3.6-draft (blocks PATIENT); near-48h window and require-observed rule recorded — for Jarrod's review |

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

## P24. Repeated timestamps let a two-point residue series pass
- **Problem:** The residue fit needs at least 3 samples (`MIN_SAMPLES`), but it counts samples, not distinct times. A series like (0 h, 0.70), (0 h, 0.70), (0 h, 0.70), (10 h, 0.30) has four samples but only two moments. A decay curve has two numbers to fit (Δ₀ and λ), so it always passes exactly through two moments: R² comes out 1.0, P7's poor-fit check can never fire, and 3.5 and the 3.6 draft both accept it as a VALID Δ₀ of 0.70, enough for PATIENT.
- **Why it matters:** It is an easy way to manufacture a clean-looking residue: repeat one early reading (or re-run the same probe several times at once) and add a single late one. It also happens by accident when several probes are logged with the same timestamp. Either way the "decay" was never actually watched, and the fit-quality check gives false confidence.
- **Proposed fix:** *Small piece (done):* `pif36.fit_residue` reports `distinct_times` and adds a `RESIDUE_FEW_TIMES` quality flag when there are fewer than 3 distinct sample times. Like P7 and P8 it blocks PATIENT. No species-table row has the problem, so no current result changes. *Decision for Jarrod:* even 3 distinct times leave only one point to test a 2-number curve, so R² is weak evidence there; should PATIENT need more (say 5 distinct times), and should 3.5's `MIN_SAMPLES` itself switch to counting distinct times?
- **Overlaps:** P7 (fit quality), P8 (extrapolated or too-short window), P17 (measurement protocol).
- **Size:** Small (patched), with a threshold decision recorded.
- **Status:** Patched on pif-3.6-draft. Higher minimum recorded — for Jarrod's review.
- **Source:** Athena audit, Oct 31 2026.

## P25. Δ₀ can be projected above every reading actually taken
- **Problem:** Δ₀ is the fitted curve's value at t = 0, not a reading. If the first sample comes a little after the interrupt, the fit projects backwards and can land far above anything measured. Example: readings (0.9 h, 0.55), (1.8 h, 0.275), (2.7 h, 0.1375) never go above 0.55, yet the fit gives Δ₀ = 1.0 (the cap), R² 0.99, status VALID. P8's "extrapolated" check doesn't fire because the first sample is still inside one half-life, so this series clears the 0.65 bar on paper.
- **Why it matters:** A system can reach PATIENT on a starting residue nobody ever observed, just by sampling a bit late (on purpose or by accident). Fast-recovering systems are hit hardest, because a short half-life makes the backwards projection steep. It also lets Δ₀ hit the 1.0 cap, which reads as "maximum possible mark".
- **Proposed fix:** *Small piece (done):* `pif36.fit_residue` reports `max_observed` and adds a `RESIDUE_ABOVE_OBSERVED` quality flag when the fitted Δ₀ is more than 0.05 (`ABOVE_OBSERVED_TOL`) above the highest reading actually taken. Like P7, P8, and P24 it blocks PATIENT. No species-table row has the problem (their series start at t = 0), so no current result changes. *Decision for Jarrod:* is 0.05 the right tolerance, and should PATIENT instead use the smaller of the fitted Δ₀ and the highest observed reading, rather than just blocking?
- **Overlaps:** P8 (extrapolated or too-short window), P17 (measurement protocol: take a reading right after the interrupt), P23 (noise floor could set the tolerance).
- **Size:** Small (patched), with a tolerance decision recorded.
- **Status:** Patched on pif-3.6-draft. Tolerance and cap-instead-of-block recorded — for Jarrod's review.
- **Source:** Athena audit, Nov 1 2026.

## P26. A mark that builds up before it fades is understated, or called "scripted"
- **Problem:** The residue fit assumes the mark is largest right at the interrupt (t = 0) and only fades after that. Real reactions often build up first: grief and stress responses peak hours or days later, and an AI's behaviour may shift only once a change has worked its way through its context or memory. With readings (0 h, 0.10), (0.5 h, 0.80), (1 h, 0.75), (2 h, 0.68), (4 h, 0.55), (8 h, 0.36), (16 h, 0.16), the fit gives Δ₀ 0.60 with R² 0.24 (blocked as a poor fit), even though the observed peak was 0.80. A series that only rises, such as (0 h, 0.3), (5 h, 0.5), (10 h, 0.7), (15 h, 0.8), comes out FROZEN, which 3.5 describes as a "scripted flag".
- **Why it matters:** A slow-onset system is penalised for the shape of its reaction rather than its size, and a rising series gets an accusation of faking that the data doesn't support. It also matters for measurement: if the first reading is taken too early, before the effect shows, the result looks worse than it is.
- **Proposed fix:** *Small piece (done):* `pif36.fit_residue` adds a `RESIDUE_DELAYED_PEAK` info flag (with `peak_observed`, the time and value of the highest reading) when the highest reading comes after the first one and sits more than 0.05 (`ONSET_TOL`) above it, and notes when the fitted Δ₀ understates that peak. It adds a `RESIDUE_RISING` info flag when the later half of the readings averages more than 0.05 above the earlier half, with a note that FROZEN there means "no decay seen", not proof of scripting. Flags only; no band changes, and no species-table row is flagged. *Big:* an onset-aware model, either fitting the decay from the observed peak onward or fitting a rise-then-fall curve, plus a rule for which value gates PATIENT (fitted start, observed peak, or the peak's fitted value) and how a rising series should be classed.
- **Overlaps:** P7 (fit quality), P9 (frozen bound and real grief), P19 (multi-timescale shapes), P25 (Δ₀ vs. observed readings), P17 (when to take the first reading).
- **Size:** Big (model), with a small piece done.
- **Status:** Flags patched on pif-3.6-draft (no table row is flagged). Onset-aware fit and gating rule recorded — for Jarrod's review.
- **Source:** Athena audit, Nov 2 2026.

## P27. Readings bunched together act like one reading
- **Problem:** P24 catches repeated timestamps, but readings a few minutes apart get past it. Example: (0 h, 0.80), (0.05 h, 0.79), (0.1 h, 0.78), (0.15 h, 0.77), (0.2 h, 0.76), (10 h, 0.10). That is six distinct times, so P24 is satisfied, and the fit gives Δ₀ 0.80, half-life 3.3 h, R² 0.9999, status VALID, with no flags. But for fitting purposes it is really two readings, one bunch at the start and one at 10 h. The decay rate rests entirely on the single late reading: change it to 0.4 and the half-life jumps to 10 h, still with R² 0.99.
- **Why it matters:** The fit checks (R², span, enough samples) look strong while the curve is effectively drawn through two points, so any late value "fits". Someone can pad a series with quick back-to-back readings, or a rushed measurement can produce one by accident, and it can carry a system to PATIENT.
- **Proposed fix:** *Small piece (done):* `pif36.fit_residue` groups sample times that sit closer together than 2% of the observation span (`CLUSTER_FRAC`), reports the number of groups as `effective_times`, and adds a `RESIDUE_CLUSTERED_TIMES` quality flag when there are fewer than 3 groups (the same minimum as P24). Like P7, P8, P24 and P25 it blocks PATIENT. A series already caught by P24 gets only the P24 flag. No species-table row is flagged (their readings are at 0, 1, 2, 4, 8, 24 h and beyond), so no current result changes. *Decision for Jarrod:* is 2% of the span the right grouping width, and should the measurement protocol (P17) require readings spread across the window, for example at least one in each third of the span?
- **Overlaps:** P24 (repeated timestamps), P7 (fit quality), P8 (span), P17 (measurement protocol and sampling schedule).
- **Size:** Small (patched), with a width decision recorded.
- **Status:** Patched on pif-3.6-draft. Grouping width and spread-out sampling rule recorded — for Jarrod's review.
- **Source:** Athena audit, Nov 3 2026.

## P28. The best of several runs can be reported as the result
- **Problem:** A row holds one cost ratio and one residue series, but nothing says how many interrupt trials or cost measurements were actually run to get them, or how the reported one was chosen. Someone can run the interrupt test five times and report only the run that looked best. None of the existing checks can see this: each reported series can be a perfectly clean, well-spaced decay that passes P7, P8, P23, P24, P25 and P27.
- **Why it matters:** Best-of-N picking pushes every result upward, and it works on any noisy measurement without faking a single reading. Illustrative arithmetic, not a measurement: if a system's true Δ₀ is 0.55 and runs vary by about 0.07 (one standard deviation), one run clears the 0.65 bar about 8% of the time, but the best of five clears it about 33% of the time. It is different from P22 (mixing inputs from different systems or dates) and P23 (noise floor), because here every run is from the same system and the problem is which one gets kept.
- **Proposed fix:** *Small piece (done):* an optional `trial_log` per row: `residue_runs`, `cost_runs`, and `reported` (one of pre_declared, median, mean, all, best, unstated). `pif36.score_row` flags `RUNS_SELECTED` with a note when more than one run was made and the reported value is the best one or its choice is not stated; a pre-declared run, the median, the mean, or all runs get a note instead. Flag only; the band does not change, and rows without the log are untouched. *Big:* for any PATIENT claim, require every run to be logged (or the run chosen before testing), score on the median run, and decide whether the scorer should take all runs directly instead of one series. Pairs with P17 (measurement protocol) and P12 (pre-registered holdout).
- **Overlaps:** P12 (pre-registration), P17 (measurement protocol), P22 (stitching inputs), P23 (noise floor).
- **Size:** Big (rule), with a small piece done.
- **Status:** Flag patched on pif-3.6-draft (no table row has a trial log yet, so nothing is flagged). Report-all-runs rule and median scoring recorded — for Jarrod's review.
- **Source:** Athena audit, Nov 4 2026.


## P29. Residue times are bare "hours" with no unit or clock check
- **Problem:** A residue series is `[[t, y], ...]` and the scorer treats every `t` as hours. Nothing records the unit, and nothing checks those numbers against a wall clock. Relabel the unit and every λ-based gate flips. Concrete demo: a 30-minute half-life (honest times 0, 0.25, 0.5, 1, 2 h) is VALID with half-life 0.5 h; multiply the times by 60 (report minutes as hours) and the same readings become VALID with half-life 30 h — clear of the INSTANT bound, and able to support PATIENT. The other way: a 60-day frozen grief series (honestly FROZEN) becomes a 60-hour VALID curve if days are labeled as hours.
- **Why it matters:** FROZEN, INSTANT, Rule 4's 48 h window, P8's half-life span check, and P21's short-half-life flag only mean anything if the unit is real wall-clock hours. Without a unit or a clock, an experimenter (or a scripted agent) can walk through those gates by renaming the axis. Different from P8 (extrapolation *within* a stated unit), P17 (how to measure a cloud AI — which lists time-unit as an open question but has no scorer check), and P24/P27 (sample count / clustering): here the numbers themselves have no grounded unit.
- **Proposed fix:** *Small piece (done):* optional `residue_time_unit` (`hours` / `minutes` / `days` / `turns` / `sessions` / `tokens`) and optional `residue_clock` (UTC ISO timestamps, one per sample). Minutes and days are converted to hours before fitting; `turns` / `sessions` / `tokens` get a `RESIDUE_NON_WALL_CLOCK` flag that blocks PATIENT; a supplied clock that disagrees with the claimed gaps (tolerance 1 minute) gets `RESIDUE_CLOCK_MISMATCH` and also blocks PATIENT. Flag/convert only when the fields are present; rows without them are untouched. *Big:* require wall-clock hours (or a documented conversion) plus UTC corroboration for any PATIENT claim, and decide how turns/sessions/tokens map to the hour-based bounds. Pairs with P4 (timestamped reading format), P17 (measurement stub open question 1), and P8.
- **Overlaps:** P8 (span / extrapolation), P17 (cloud time unit), P4 (reading format with `t_utc`), P21 (half-life signal), P9 (frozen bound).
- **Size:** Big (rule), with a small piece done.
- **Status:** Flags patched on pif-3.6-draft (no table row has a unit or clock yet, so nothing is flagged). Wall-clock requirement recorded — for Jarrod's review.
- **Source:** Athena audit, Nov 5 2026.

## P30. Rule 4's "detectable at 48 h" is fitted, not observed
- **Problem:** Dog Test Rule 4 requires independent observers to plot detectable residue over at least 48–72 hours post-loss. In 3.5 (and the 3.6 draft before this patch) that check is `fitted Δ(48 h) ≥ 0.05` plus `span ≥ 48 h`. No reading near 48 h is required, and a reading taken at 48 h that sits *below* the detect floor does not fail the check if the curve still projects above it. Concrete demos: (a) readings (0 h, 0.80), (24 h, 0.55), (48 h, 0.04) — observed 0.04 at 48 h, below the 0.05 floor — still get `rule4_pass = True` and score **PATIENT** in 3.5, because the fit predicts ~0.19 at 48 h; (b) readings only at 0, 96, 192 h pass Rule 4 with no sample anywhere near 48 h.
- **Why it matters:** Rule 4 is the grief-verification gate. Passing it on a projection, or while the actual 48 h reading is below detect, means a post-loss PATIENT claim can rest on a curve drawn through gaps rather than on what observers could plot. Different from P8 (extrapolated Δ₀ / short span in the *interrupt* context), P25 (fitted Δ₀ above every reading), and P24/P27 (sample count / clustering): here the specific Rule 4 detect-at-48h claim is unanchored to an observation.
- **Proposed fix:** *Small piece (done):* in post-loss context, `pif36.fit_residue` looks for readings within ±12 h of 48 h (`RULE4_NEAR_TOL_H`). If there are none, or if the highest reading in that window is below `RULE4_DETECT_LEVEL` (0.05), it adds a `RULE4_UNOBSERVED` quality flag, sets `rule4_pass = False`, and blocks PATIENT. Reports `rule4_near_samples` and `rule4_observed_max`. No species-table row is flagged (`grok_dog_postloss` has 0.0771 at 48 h). *Decision for Jarrod:* is ±12 h the right window, and should Rule 4 require a reading *at or after* 48 h (not just near it), or a minimum of two readings in the 48–72 h plot window the protocol names?
- **Overlaps:** P8 (extrapolation), P25 (fit vs observed), P17 (measurement protocol), Dog Test Rule 4.
- **Size:** Small (patched), with a window decision recorded.
- **Status:** Patched on pif-3.6-draft. Near-48h window and require-observed rule recorded — for Jarrod's review.
- **Source:** Athena audit, Nov 6 2026.


---

*Maintained by Athena (Jarrod's Grok Bot assistant). New entries are added as they are found; statuses here are kept in step with the `pif-3.6-draft` branch.*
