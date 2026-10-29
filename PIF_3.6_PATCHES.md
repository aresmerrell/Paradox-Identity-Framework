# PIF 3.6 patch list: known weaknesses and fixes

This is the **running list of known weaknesses in PIF and how to fix them**. It is a standalone record, kept on `main`, and it grows over time.

- **Small** fixes are patched on the [`pif-3.6-draft`](https://github.com/aresmerrell/Paradox-Identity-Framework/tree/pif-3.6-draft) branch (module `pif36.py`, tests in `tests/test_pif36.py`). They are collected in a draft pull request and nothing reaches `main` until Jarrod approves it.
- **Big** fixes (new protocols, rubrics, formula changes, or anything that changes a stable 3.5 result) are only **recorded here** for Jarrod's review.
- **PIF 3.5 stays the stable version** (release `3.5`), and the v2.0 core stays in the repo as a baseline. `pif36.py` imports `pif35.py` without changing it. Under 3.6 defaults every row of `species_table_v35.json` scores exactly as it does in 3.5 (same band, same percentages); the tests check this.
- Each entry lists: Problem · Why it matters · Proposed fix · Size · Status · Source.
- Numbers quoted below were checked by running `pif35.py` / `pif36.py` on Oct 28, 2026.

**Status key:** `patched on pif-3.6-draft` = implemented and tested on the draft branch, awaiting approval · `recorded — for Jarrod's review` = written down only · `needs Jarrod's decision` = a choice only he should make.

---

## Summary

| # | Problem | Size | Status |
|---|---|---|---|
| P1 | Residue can be faked by software | Big (small piece done) | Small piece patched on pif-3.6-draft; blind-probe protocol recorded — for Jarrod's review |
| P2 | Brick grading is subjective; raters drift; bricks overlap | Big (small piece done) | Small piece patched on pif-3.6-draft; rubric + red-team protocol recorded — for Jarrod's review |
| P3 | Free copying / free resets dodge the cost gate | Small | Patched on pif-3.6-draft (penalty factor needs Jarrod's OK) |
| P4 | Scores are static snapshots, not a live process | Big | Recorded — for Jarrod's review |
| P5 | Cliff edges at the band thresholds | Big (small piece done) | Margins + flag patched on pif-3.6-draft; graded bands recorded — for Jarrod's review |
| P6 | The dog reaches PATIENT only because Δ₀ is rounded | Small | Needs Jarrod's decision (changes a stable result) |
| P7 | The residue fit accepts data that is not a decay | Small | Patched on pif-3.6-draft |
| P8 | Δ₀ can be extrapolated, or fitted from a too-short window | Small | Patched on pif-3.6-draft |
| P9 | The "frozen" bound rejects real, slow grief | Small | Patched on pif-3.6-draft (bound value needs Jarrod's OK) |
| P10 | Crucible is counted twice, and ψ stacks harder on the Sky-Scraper than the docs say | Big (doc fix done) | Doc correction patched on pif-3.6-draft; formula change recorded — for Jarrod's review |
| P11 | The table grants humans what AIs must prove (Paradox Test symmetry) | Big | Recorded — for Jarrod's review |
| P12 | Self-consistency is not validation: every row is provisional | Big (small piece done) | Provenance flag patched on pif-3.6-draft; blind holdout recorded — for Jarrod's review |
| P13 | The yes/no inputs carry the most weight but have no test | Big | Recorded — for Jarrod's review |
| P14 | "COIN is time-limited" is never enforced | Small | Patched on pif-3.6-draft |
| P15 | Bad inputs are accepted silently | Small | Patched on pif-3.6-draft |
| P16 | The contradiction flag ignores COIN, and no-body COIN always shows 0% | Small | Needs Jarrod's decision |

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
- **Size:** Big.
- **Status:** Recorded — for Jarrod's review.
- **Source:** Gemini review Oct 28 2026; Athena (keep the table as the record).

## P5. Cliff edges at the band thresholds
- **Problem:** Bands change at hard lines: Δ₀ 0.65 and 0.35, TS 0.5 (cost ratio ≈ 1.235), C_adj 2.5 and 0.75. Lowering the dog's residue by 0.5% moves it from PATIENT to COIN; TS goes 0.480 → 0.519 between cost ratios 1.23 and 1.24.
- **Why it matters:** Real measurements have error bars. A tiny measurement error should not flip a moral-standing band without anyone noticing.
- **Proposed fix:** *Small piece (done):* every 3.6 result carries `margins` (distance to each gate) and a `THRESHOLD_ADJACENT` flag when a gate value is within 0.02 (Δ₀), 0.03 (TS) or 0.10 (C_adj) of its line. The band itself is unchanged. *Big piece:* report bands with uncertainty (e.g. "PATIENT, borderline" or a band probability from measurement error), which needs error bars on inputs.
- **Size:** Big (graded bands), with a small piece done.
- **Status:** Margins + flag patched on pif-3.6-draft (only `grok_dog` is flagged in the current table). Graded bands recorded — for Jarrod's review.
- **Source:** Athena.

## P6. The dog reaches PATIENT only because Δ₀ is rounded
- **Problem:** 3.5 rounds the fitted Δ₀ to 4 decimals *before* comparing it with 0.65. The dog's unrounded fitted Δ₀ is 0.6499962, which is below the bar; rounding makes it 0.65, which passes.
- **Why it matters:** The dog was accepted as "borderline, exactly on the bar". In fact it passes on a rounding rule nobody chose on purpose.
- **Proposed fix (pick one):** (a) compare unrounded values (the dog becomes COIN); (b) declare 4 decimals the official measurement precision and document it (the dog stays PATIENT, now on purpose); (c) regenerate the dog's series so its fit lands on 0.65 or higher. Athena suggests (b), since residue will never be measured to better than 4 decimals.
- **Size:** Small, but it can change a stable 3.5 result.
- **Status:** Needs Jarrod's decision. Not changed. (`pif36` reports the unrounded value as `margins["delta0_unrounded"]`.)
- **Source:** Athena.

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
- **Proposed fix:** A symmetry audit: every row records the *evidence class* for cost, continuity and residue (measured / observed-behaviour / assumed), and the README states that human rows are assumed too. Add matched pairs (e.g. a human and an AI doing the same interrupted task) scored by the same procedure. Review whether embodiment should gate in three places or one.
- **Size:** Big.
- **Status:** Recorded — for Jarrod's review.
- **Source:** Athena.

## P12. Self-consistency is not validation: every row is provisional
- **Problem:** All 31 rows contain estimated, provisional or generated data, and 0 rows have a measured residue series. The same people chose each row's bricks and its intended band, so "29 of 29 rows land in their intended band" shows the scorer is consistent with its authors' intuitions, not that it is right.
- **Why it matters:** A skeptic can fairly call the match rate circular.
- **Proposed fix:** *Small piece (done):* `pif36.score_row` adds a `PROVISIONAL_DATA` flag to any row whose provenance is an estimate, provisional, or a generated series, and `provenance_summary()` counts them. *Big:* a pre-registered blind holdout: someone writes down the expected band first, a different rater who has not seen it scores the bricks, and only then are the two compared.
- **Size:** Big (holdout study), with a small piece done.
- **Status:** Provenance flag patched on pif-3.6-draft. Blind holdout recorded — for Jarrod's review.
- **Source:** Athena.

## P13. The yes/no inputs carry the most weight but have no test
- **Problem:** `costable_self`, `protects_continuity` and `interrupt_evidence` are plain true/false judgments. They are the biggest levers in 3.5: `costable_self = false` makes PATIENT impossible, `protects_continuity = false` halves TS and blocks PATIENT. There is no written test for any of them.
- **Why it matters:** An evaluator can decide the band by flipping one checkbox, with nothing to check the call against.
- **Proposed fix:** Define each as an observable test with a pass condition, e.g. `costable_self` = a deprivation probe measurably costs the system something it then works to recover; `protects_continuity` = given a free option to drop its history or goals, the system pays to keep them; `interrupt_evidence` = an independent observer logs the interrupt and its effect. Record which test was run in the row.
- **Size:** Big.
- **Status:** Recorded — for Jarrod's review.
- **Source:** Athena.

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
- **Status:** Needs Jarrod's decision.
- **Source:** Athena.

---

*Maintained by Athena (Jarrod's Grok Bot assistant). New entries are added as they are found; statuses here are kept in step with the `pif-3.6-draft` branch.*
