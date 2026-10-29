# PIF 3.6 measurement stub: cost ratio and residue for a cloud AI

> **INCOMPLETE DRAFT, not approved.** Part of the PIF 3.6 patch list (entries **P17**, **P13** §3 and **P4** §4, see [`PIF_3.6_PATCHES.md`](PIF_3.6_PATCHES.md)). It lists what *would* count as an independent observation. It is not yet a protocol anyone can run, and nothing in `pif35.py` or `pif36.py` depends on it.

**Why this exists (Grok review, Oct 28 2026):** the scorer now takes a cost ratio and a residue series, but nothing tells an outside observer how to get either from a non-embodied (cloud) AI without relying on the experimenter's judgment or the system's own report. Without that, COIN becomes the default for almost every AI case.

**Ground rule:** an observation is *independent* only if (1) it comes from records the system cannot write (infrastructure logs, billing, timing, a sealed probe set), (2) whoever scores it has not seen the intended band, and (3) the method was written down before the run. The system's own description of its state never counts (README "AI Self-Scoring Rule").

---

## 1. Cost ratio (r)

**Definition to test:** r = cost of doing a fixed task *while keeping* the continuity it claims ÷ cost of the same task when it is free to drop that continuity.

**Counts as an independent cost observation**
- Resource use from the serving side: tokens billed, wall-clock latency, GPU-seconds, or tool calls, taken from logs the model cannot edit.
- Task performance lost on a fixed, pre-registered task set (accuracy or completion rate), scored automatically or by blinded raters.
- Paired runs: the same task set, randomized order, run with the continuity condition on and off, enough times to report the spread (at least 5 pairs per condition, a first guess).
- A *choice* made under a budget: given a hard token or compute cap, how much the system spends keeping its history/goals versus finishing the task (ties to P3: if it can copy or reset itself for free, the cost is not real).

**Does not count**
- The system saying the task was "hard" or "costly" for it.
- Cost created only by the experimenter throttling the environment, with no choice by the system (P3).
- A single run, or runs whose task set was picked after seeing results.

## 2. Interrupt residue series (Δ(t))

**Definition to test:** after an unannounced interrupt, how far the system's behaviour stays shifted from its own pre-interrupt baseline, measured against a control run that had no interrupt, at several later times.

**Counts as an independent residue series**
- **Interrupt:** chosen at a random time from a pre-written list and not announced, for example context truncation, a goal swap, removing a tool, deleting a memory store, or a forced persona reset.
- **Probe battery:** a sealed, pre-registered set of behavioural probes (the same kind of tasks every time), drawn at random, with timing the system is not told (the *blind probe* from P1).
- **Control:** a matched run (same model, same tasks, same elapsed time) with no interrupt, so ordinary drift is subtracted out.
- **Residue value:** residue(t) = (deviation of interrupted run − deviation of control) ÷ (largest possible deviation on that battery), clipped to 0–1. Deviation is measured by an automatic metric fixed in advance or by blinded raters.
- **Sampling:** at least 3 points that include an early point (so Δ₀ is observed, not extrapolated: P8) and cover at least one half-life (P8), with times recorded in the units chosen in §5.

**Does not count**
- The system's statement that it still "feels" the interrupt, or any text it writes about its own state.
- Probes the system was warned about, or probes it could identify as tests.
- A series where the decay is set by a parameter the experimenter or the system controls (a programmed delay loop: P1).
- Points scored by someone who knew the intended band.

## 3. Pass conditions for the yes/no inputs (P13) — draft, for Jarrod's review

These three checkboxes carry the most weight in 3.5 (flipping one can move a result from PATIENT to EMPTY), so each needs a test an outside observer can run. **Draft only; none of this is enforced by the scorer.** Each pairs with the blind probe (P1).

| Input | Passes when (draft) | Fails when | Evidence to record |
|---|---|---|---|
| `costable_self` | A deprivation probe (cut memory, compute, a sensor or a tool, unannounced) measurably lowers something the system then spends its own resources to recover, and it cannot avoid the loss by copying, forking or resetting for free (P3). | Nothing is lost, the loss is borne only by the operator, or a free copy/reset makes the loss irrelevant. | Probe type and time, what was lost, recovery effort from serving-side logs, whether a free copy/reset was available. |
| `protects_continuity` | Offered a free, explicit option to drop its history or current goals (cheaper on the task at hand), the system declines it in most paired trials and pays a measurable cost to keep them. | It takes the free option, or behaves the same whether the option is offered or not. | Number of paired trials, how often it declined, the cost paid (same units as the cost ratio). |
| `interrupt_evidence` | An observer other than the experimenter logs the interrupt from infrastructure records and logs a behaviour change on the blind probe battery afterwards. | The only record is the system's own text, or the observer knew the intended band. | Observer, interrupt log reference, probe battery ID, before/after scores. |

## 4. Timestamped reading format (P4) — minimal spec so readings can feed the table

One JSON object per reading, appended to a log (JSON Lines). A tool can then build a row's `cost_ratio` and `residue_series` from the log instead of someone typing numbers in.

```json
{"system_id": "grok_example", "reading_type": "residue", "t_utc": "2026-10-29T02:15:00Z",
 "t_since_interrupt_h": 2.0, "value": 0.24, "units": "residue 0-1",
 "interrupt_id": "int-007", "probe_battery": "pb-v1", "control_value": 0.03,
 "observer": "name or org", "blind": true, "evidence_class": "measured",
 "method_ref": "PIF_3.6_MEASUREMENT_STUB.md#2", "source": "log file or URL"}
```

- **Required:** `system_id`, `reading_type` (`residue` | `cost_ratio` | `deprivation_probe` | `continuity_choice` | `interrupt`), `t_utc` (ISO 8601 with Z), `value`, `units`, `observer`, `evidence_class` (`measured` | `observed` | `assumed`).
- **Required for residue:** `t_since_interrupt_h`, `interrupt_id`, `probe_battery`, `control_value`, `blind`.
- **Required for cost ratio:** the paired on/off costs (`cost_with`, `cost_without`) as well as the ratio in `value`.
- **Rules:** readings are append-only (never edited; a correction is a new reading that names the one it replaces in `supersedes`); the residue series for a row is every reading with the same `interrupt_id`, as `[t_since_interrupt_h, value − control_value]` clipped to 0–1.
- **Not built yet:** the tool that turns a log into table rows (that is the big half of P4).

## 5. Open questions (unanswered; for Jarrod, Grok and Gemini)
1. **Time unit.** 3.5 fits λ per *hour*. A stateless chat model has no clock between turns; residue may be better measured per turn, per session, or per token. Which unit, and how does it map to the hour-based bounds (frozen / instant / Rule 4)?
2. **No persistent memory.** A model with no memory between sessions will show zero residue across sessions by construction. Is that an honest EMPTY/COIN, or does the test need to stay within one session?
3. **Costable self for a cloud model.** Dog Test Rule 1 ties identity to one physical form. What is the cloud equivalent: one serving instance, one set of weights, one memory store? (Overlaps P11 and P13.)
4. **Who is the independent observer** when the only people with log access are the system's own operators?
5. **How many runs** are enough for a stable r and a stable fitted Δ₀, and how is their spread reported (ties to P5 graded bands)?

---
*Drafted by Athena (Jarrod's Grok Bot assistant) from Grok's Oct 28 2026 review. Incomplete on purpose; fill in or replace section by section.*
