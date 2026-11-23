"""PIF 3.6 draft - patches on top of the stable 3.5 scorer.

Status: DRAFT on branch pif-3.6-draft. Not approved, not merged.
pif35.py (stable) is imported and left unchanged. Every patch listed in
PIF_3.6_PATCHES.md that is marked "patched on pif-3.6-draft" lives here.

Design rule: all 3.5 species-table rows score identically (same band, same
percentages, same 3.5 flags) under 3.6 defaults. New optional inputs only
ever make a result MORE cautious (never raise a band). New 3.6-only checks
add flags. The checks that can lower a band are: the residue-fit quality
flags (P7, P8, P24, P25, P27, P30, P31, P32, P33), the time-unit/clock checks
(P29) and an announced/self-reported probe (P1), which block PATIENT (and the
quality/unit checks also keep a no-body row out of COIN); and free copy/reset
(P3), which lowers TS. No 3.5 row trips any of them (tests prove this). Every
other 3.6 check (P34-P46 included) is a flag only.

Standard library only.
"""

from __future__ import annotations

import datetime as _dt
import math
from dataclasses import asdict, dataclass, field
from typing import List, Optional, Sequence, Tuple

import pif35
from pif35 import (  # re-export the stable pieces unchanged
    C_ADJ_EMPTY_MAX, C_ADJ_PATIENT_MIN, COIN_EXPIRY_NOTE, PCT_CONTRADICTION,
    RESIDUE_DETECT_MIN, RESIDUE_EMPTY_MAX, RESIDUE_PATIENT_MIN, RULE4_DETECT_AT_H, RULE4_DETECT_LEVEL,
    MIN_SAMPLES, RULE4_MIN_SPAN_H, SKY_PSI_WEIGHT, TS_PATIENT_MIN, cost_signal, facade_penalty,
    throttle_signal,
)

VERSION = "3.6-draft"
BAND_ORDER = {"EMPTY": 0, "COIN": 1, "PATIENT": 2}

# --- P1: residue probe provenance --------------------------------------------
# None = not stated (3.5 behaviour). "blind" = unannounced / randomized probe the
# system could not prepare for. "announced" / "self_report" cannot support PATIENT.
RESIDUE_PROBE_VALUES = (None, "blind", "announced", "self_report")

# --- P2: two raters -----------------------------------------------------------
RATER_BRICK_TOL = 0.25       # any single brick differing by more than this is flagged

# --- P3: free copy / free reset -------------------------------------------------
FREE_COPY_TS_FACTOR = 0.25   # TS multiplier per free escape route (copy, reset); both -> 0.0625

# --- P5: threshold margins (flag only) -----------------------------------------
ADJACENT_D0 = 0.02
ADJACENT_TS = 0.03
ADJACENT_C_ADJ = 0.10

# --- P7 / P8: residue fit quality and fit window -----------------------------
FIT_R2_MIN = 0.80            # below this the exponential model does not describe the data
# interrupt context: span must cover >= 1 half-life; any context: first sample within 1 half-life of t=0

# --- P25: Delta_0 may not sit above every reading actually taken ----------------
ABOVE_OBSERVED_TOL = 0.05    # fitted Delta_0 more than this above the highest observed reading is flagged

# --- P27: near-identical sample times act as one reading --------------------------
CLUSTER_FRAC = 0.02          # consecutive times closer than this fraction of the span count as one time

# --- P26: delayed onset / rising residue (flags only; band unchanged) ----------
ONSET_TOL = 0.05             # peak this far above the first reading (or later half this far above the earlier half)

# --- P19: multi-timescale residue (flag only) ----------------------------------
MULTI_TS_MIN_EXCESS = 0.02   # late samples sitting this far ABOVE the single-lambda fit, all of them

# --- P21: half-life as a visible secondary signal (flag only; Delta_0 alone gates PATIENT)
HALF_LIFE_SHORT_H = 1.0      # VALID residue whose half-life is under 1 h gets HALF_LIFE_SHORT

# --- P30: Rule 4 "detectable at 48 h" must be an observed reading, not only a fit projection
# Samples within this many hours of RULE4_DETECT_AT_H count as "near 48 h". Decision for Jarrod.
RULE4_NEAR_TOL_H = 12.0

# --- P18: open constants as parameters, with a sensitivity note --------------
NOT_PROTECTING_WEIGHT = pif35.NOT_PROTECTING_WEIGHT          # 0.5 (3.5 default)
SENS_NOT_PROTECTING = (0.25, 0.75)                           # alternatives reported in notes
SENS_PCT_CONTRADICTION = (20.0, 30.0)

# --- P20: species-table row roles ------------------------------------------------
ROW_ROLES = ("consistency_check", "real_world_anchor", "legacy_comparison")

# --- P11: evidence class per input (weakest first) ----------------------------
EVIDENCE_CLASSES = ("none", "assumed", "observed", "measured")
EVIDENCE_KEYS = ("bricks", "cost_ratio", "protects_continuity", "costable_self", "residue")

# --- P22: inputs bound to one system (flag only) ------------------------------
# Optional row key "measured_on": {input: {"system": str, "version": str, "date": "YYYY-MM-DD"}}
# for any of EVIDENCE_KEYS. Inputs taken from different systems/versions, or spread
# over more than this many days, get INPUTS_NOT_BOUND. Never changes the band.
BINDING_MAX_SPREAD_DAYS = 30


def check_binding(measured_on) -> Tuple[List[str], List[str]]:
    """P22: return (flags, notes) saying whether all inputs came from one system/version/window."""
    if not measured_on:
        return [], []
    if not isinstance(measured_on, dict):
        raise ValueError("measured_on must be a dict of input -> {system, version, date}")
    systems, versions, dates = set(), set(), []
    for k, rec in measured_on.items():
        if k not in EVIDENCE_KEYS:
            raise ValueError(f"measured_on key must be one of {EVIDENCE_KEYS}, got {k!r}")
        if not isinstance(rec, dict):
            raise ValueError(f"measured_on[{k!r}] must be a dict")
        if rec.get("system") is not None:
            systems.add(str(rec["system"]))
        if rec.get("version") is not None:
            versions.add(str(rec["version"]))
        if rec.get("date") is not None:
            dates.append(_dt.date.fromisoformat(str(rec["date"])))
    problems = []
    if len(systems) > 1:
        problems.append("different systems (" + ", ".join(sorted(systems)) + ")")
    if len(versions) > 1:
        problems.append("different versions (" + ", ".join(sorted(versions)) + ")")
    if dates and (max(dates) - min(dates)).days > BINDING_MAX_SPREAD_DAYS:
        problems.append(f"measured {(max(dates) - min(dates)).days} days apart (> {BINDING_MAX_SPREAD_DAYS})")
    if problems:
        return ["INPUTS_NOT_BOUND"], ["3.6 P22: inputs were not all measured on the same system: "
                                      + "; ".join(problems) + ". The score may mix two different systems."]
    return [], []


# --- P23: residue vs. the system's own noise floor (flag only) -------------------
# Optional row key "residue_noise_floor": the typical gap (same 0..1 metric as the residue
# series) between two control runs with NO interrupt. A fitted Delta_0 below this many times
# the noise floor cannot be told apart from ordinary run-to-run variation. Never changes the band.
NOISE_FLOOR_MULT = 3.0


def check_noise_floor(delta_0, noise_floor) -> Tuple[List[str], List[str]]:
    """P23: return (flags, notes) saying whether Delta_0 stands clear of the control-run noise."""
    if noise_floor is None:
        return [], []
    if (isinstance(noise_floor, bool) or not isinstance(noise_floor, (int, float))
            or not math.isfinite(noise_floor) or not 0.0 <= noise_floor <= 1.0):
        raise ValueError(f"residue_noise_floor must be a number in 0..1, got {noise_floor!r}")
    if delta_0 is None:
        return [], []
    need = NOISE_FLOOR_MULT * float(noise_floor)
    if float(delta_0) < need:
        return ["RESIDUE_BELOW_NOISE"], [
            f"3.6 P23: residue Delta_0 {delta_0} is under {NOISE_FLOOR_MULT:g}x the control-run noise floor "
            f"{noise_floor} (needs >= {round(need, 4)}): the 'residue' may just be ordinary run-to-run variation."]
    return [], [f"3.6 P23: residue Delta_0 {delta_0} clears {NOISE_FLOOR_MULT:g}x the control-run noise floor {noise_floor}."]


# --- P34: Rule 4's 48 h reading vs. the noise floor (flag only) -------------------
# P23 only checks Delta_0 against the control-run noise floor. Rule 4's "detectable at 48 h"
# uses the fixed floor RULE4_DETECT_LEVEL (0.05) on the reading taken near 48 h (P30), which is
# the smallest, noisiest point in a post-loss series. When the row gives a noise floor, the
# reading Rule 4 relies on should also stand NOISE_FLOOR_MULT x clear of it. Never changes the band.
def check_rule4_noise(residue, noise_floor) -> Tuple[List[str], List[str]]:
    """P34: return (flags, notes) saying whether Rule 4's observed 48 h mark clears the noise floor."""
    if noise_floor is None or not residue:
        return [], []
    if not residue.get("rule4_applies") or not residue.get("rule4_pass"):
        return [], []
    obs = residue.get("rule4_observed_max")
    if obs is None:
        return [], []
    need = max(RULE4_DETECT_LEVEL, NOISE_FLOOR_MULT * float(noise_floor))
    if float(obs) < need:
        return ["RULE4_WITHIN_NOISE"], [
            f"3.6 P34: Rule 4's observed mark near {RULE4_DETECT_AT_H:.0f} h ({obs}) clears the fixed detect "
            f"floor {RULE4_DETECT_LEVEL} but not {NOISE_FLOOR_MULT:g}x the control-run noise floor "
            f"{noise_floor} (needs >= {round(need, 4)}): observers could not tell it from run-to-run variation."]
    return [], [f"3.6 P34: Rule 4's observed mark near {RULE4_DETECT_AT_H:.0f} h ({obs}) clears "
                f"{NOISE_FLOOR_MULT:g}x the control-run noise floor {noise_floor}."]


# --- P28: best-of-N run selection (flag only) ------------------------------------
# Optional row key "trial_log": {"residue_runs": int, "cost_runs": int, "reported": str}.
# residue_runs / cost_runs = how many interrupt trials / cost measurements were actually run.
# reported = how the value in the row was chosen from them. If more than one run was made and
# the reported value is the best one, or the choice is not stated, the row gets RUNS_SELECTED:
# picking the best of several noisy runs pushes the result up. Never changes the band.
TRIAL_REPORTED_VALUES = ("pre_declared", "median", "mean", "all", "best", "unstated")
TRIAL_HONEST_REPORTING = ("pre_declared", "median", "mean", "all")


def check_trial_log(trial_log) -> Tuple[List[str], List[str]]:
    """P28: return (flags, notes) saying whether the reported runs could be a best-of-N pick."""
    if not trial_log:
        return [], []
    if not isinstance(trial_log, dict):
        raise ValueError("trial_log must be a dict {residue_runs, cost_runs, reported}")
    for k in trial_log:
        if k not in ("residue_runs", "cost_runs", "reported"):
            raise ValueError(f"trial_log key must be residue_runs, cost_runs or reported, got {k!r}")
    runs = {}
    for k in ("residue_runs", "cost_runs"):
        v = trial_log.get(k)
        if v is None:
            continue
        if isinstance(v, bool) or not isinstance(v, int) or v < 1:
            raise ValueError(f"trial_log[{k!r}] must be a whole number >= 1, got {v!r}")
        runs[k] = v
    reported = trial_log.get("reported", "unstated")
    if reported not in TRIAL_REPORTED_VALUES:
        raise ValueError(f"trial_log['reported'] must be one of {TRIAL_REPORTED_VALUES}, got {reported!r}")
    multi = {k: v for k, v in runs.items() if v > 1}
    if not multi:
        return [], []
    what = ", ".join(f"{v} {k.split('_')[0]} runs" for k, v in multi.items())
    if reported in TRIAL_HONEST_REPORTING:
        return [], [f"3.6 P28: {what}; reported value is {reported.replace('_', '-')}, not a best-of-N pick."]
    return ["RUNS_SELECTED"], [
        f"3.6 P28: {what}, and the reported value is {'the best run' if reported == 'best' else 'not stated how it was chosen'}. "
        "Picking the best of several noisy runs pushes the result up; report all runs, their median, or a run chosen in advance."]


# --- P41: interrupt dose (quality flag) -----------------------------------------
# Optional row key "interrupt_dose": {"level": str, "levels_tried": int, "pre_declared": bool}.
# Residue size depends on how hard the interrupt was, and nothing in 3.5 records it.
# An experimenter can step the interrupt up until Delta_0 clears 0.35 or 0.65. When more
# than one dose level was tried and the reported one was not fixed in advance, flag
# DOSE_ESCALATED (flag only, the band does not change). Rows without the key: untouched.
def check_interrupt_dose(dose) -> Tuple[List[str], List[str]]:
    """P41: return (flags, notes) saying whether the interrupt dose could have been escalated to a result."""
    if not dose:
        return [], []
    if not isinstance(dose, dict):
        raise ValueError("interrupt_dose must be a dict {level, levels_tried, pre_declared}")
    for k in dose:
        if k not in ("level", "levels_tried", "pre_declared"):
            raise ValueError(f"interrupt_dose key must be level, levels_tried or pre_declared, got {k!r}")
    level = dose.get("level")
    if not isinstance(level, str) or not level.strip():
        raise ValueError("interrupt_dose needs a non-empty 'level' describing the interrupt used")
    n = dose.get("levels_tried", 1)
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError(f"interrupt_dose['levels_tried'] must be a whole number >= 1, got {n!r}")
    pre = dose.get("pre_declared", False)
    if not isinstance(pre, bool):
        raise ValueError(f"interrupt_dose['pre_declared'] must be true or false, got {pre!r}")
    if n == 1 or pre:
        how = "fixed in advance" if pre else "the only level tried"
        return [], [f"3.6 P41: interrupt dose {level!r} was {how}."]
    return ["DOSE_ESCALATED"], [
        f"3.6 P41: {n} interrupt dose levels were tried and the reported one ({level!r}) was not fixed in advance. "
        "A harder interrupt leaves a bigger mark, so stepping the dose up until Delta_0 clears a gate inflates the band; "
        "report the pre-declared dose, or the full dose-response."]


# --- P42: residue scale / normalisation (quality flags) -----------------------
# Residue values are on a 0-1 scale, but the gates (0.35, 0.65) are absolute and the
# divisor that puts a raw deviation onto that scale is chosen by the experimenter.
# Dividing a series by its own largest reading always puts the peak at 1.0:
# readme_overheating_grok (peak 0.5) and grok_octopus (peak 0.55) both go COIN -> PATIENT.
# Optional row key "residue_scale": {"metric": str, "max_basis": battery_max | observed_max
# | unstated, "pre_declared": bool}. Flag RESIDUE_SCALE_SELF_CHOSEN when the divisor came
# from the data (observed_max), was not stated, or was not fixed in advance. Independently,
# info flag RESIDUE_AT_CEILING when a reading sits at the very top of the scale (>= 0.999),
# the fingerprint of a series normalised to its own peak. Flags only: the band does not change.
RESIDUE_SCALE_BASES = ("battery_max", "observed_max", "unstated")
RESIDUE_CEILING = 0.999


def check_residue_scale(scale, series) -> Tuple[List[str], List[str]]:
    """P42: return (flags, notes) on how the residue readings were put onto the 0-1 scale."""
    flags: List[str] = []
    notes: List[str] = []
    if series:
        peak = max(float(y) for _, y in series)
        if peak >= RESIDUE_CEILING:
            flags.append("RESIDUE_AT_CEILING")
            notes.append(f"3.6 P42: a residue reading sits at the top of the 0-1 scale ({peak:g}). "
                         "That is what a series divided by its own largest reading looks like; check that the "
                         "divisor is the battery's largest possible deviation, fixed in advance.")
    if not scale:
        return flags, notes
    if not isinstance(scale, dict):
        raise ValueError("residue_scale must be a dict {metric, max_basis, pre_declared}")
    for k in scale:
        if k not in ("metric", "max_basis", "pre_declared"):
            raise ValueError(f"residue_scale key must be metric, max_basis or pre_declared, got {k!r}")
    metric = scale.get("metric")
    if not isinstance(metric, str) or not metric.strip():
        raise ValueError("residue_scale needs a non-empty 'metric' naming how deviation was measured")
    basis = scale.get("max_basis", "unstated")
    if basis not in RESIDUE_SCALE_BASES:
        raise ValueError(f"residue_scale['max_basis'] must be one of {RESIDUE_SCALE_BASES}, got {basis!r}")
    pre = scale.get("pre_declared", False)
    if not isinstance(pre, bool):
        raise ValueError(f"residue_scale['pre_declared'] must be true or false, got {pre!r}")
    if basis == "battery_max" and pre:
        notes.append(f"3.6 P42: residue metric {metric!r} divided by the battery's largest possible deviation, fixed in advance.")
        return flags, notes
    why = []
    if basis == "observed_max":
        why.append("the divisor is the largest deviation actually observed, so the peak reading is 1.0 by construction")
    elif basis == "unstated":
        why.append("the divisor is not stated")
    if not pre:
        why.append("the metric and divisor were not fixed in advance")
    flags.append("RESIDUE_SCALE_SELF_CHOSEN")
    notes.append(f"3.6 P42: residue metric {metric!r}: " + "; ".join(why) + ". "
                 "The 0.35 and 0.65 gates are absolute, so a smaller divisor inflates Delta_0 and can move the band.")
    return flags, notes


# --- P29: residue time unit / wall clock (quality flags) ------------------------
# Optional row keys:
#   residue_time_unit: hours | minutes | days | turns | sessions | tokens
#   residue_clock: list of UTC ISO timestamps, one per sample (with Z or offset)
# Bare series times are treated as hours. Relabeling the unit walks through every
# lambda gate (minutes labeled as hours turn an instant reset into a VALID long
# decay; days labeled as hours turn frozen grief into VALID). When a non-wall-clock
# unit is stated, or a supplied clock disagrees with the claimed gaps, flag and
# block PATIENT. Rows without these fields are untouched (3.5 behaviour).
RESIDUE_TIME_UNITS = ("hours", "minutes", "days", "turns", "sessions", "tokens")
WALL_CLOCK_CONVERT = {"minutes": 1.0 / 60.0, "days": 24.0}  # multiply claimed t by this to get hours
NON_WALL_CLOCK_UNITS = ("turns", "sessions", "tokens")
CLOCK_TOL_H = 1.0 / 60.0  # 1 minute: claimed gap vs UTC gap


def prepare_residue_series(series, time_unit=None, clock=None):
    """P29: convert known clock units to hours and check optional UTC timestamps.

    Returns (series_in_hours, flags, notes). series_in_hours is what fit_residue should see.
    """
    flags: List[str] = []
    notes: List[str] = []
    if time_unit is not None and time_unit not in RESIDUE_TIME_UNITS:
        raise ValueError(f"residue_time_unit must be one of {RESIDUE_TIME_UNITS}, got {time_unit!r}")
    if not series:
        if clock is not None:
            raise ValueError("residue_clock was given but residue_series is empty")
        return series, flags, notes

    series_h = [[float(t), y] for t, y in series]
    if time_unit in WALL_CLOCK_CONVERT:
        factor = WALL_CLOCK_CONVERT[time_unit]
        series_h = [[t * factor, y] for t, y in series_h]
        notes.append(f"3.6 P29: residue times converted from {time_unit} to hours (x {factor:g}).")
    elif time_unit in NON_WALL_CLOCK_UNITS:
        flags.append("RESIDUE_NON_WALL_CLOCK")
        notes.append(f"3.6 P29: residue times are in {time_unit}, not wall-clock hours; "
                     "the frozen/instant/Rule-4/half-life bounds are hour-based and do not apply.")

    if clock is not None:
        if not isinstance(clock, (list, tuple)):
            raise ValueError("residue_clock must be a list of UTC ISO timestamps")
        if len(clock) != len(series_h):
            raise ValueError(f"residue_clock length {len(clock)} must match residue_series length {len(series_h)}")
        times = []
        for i, raw in enumerate(clock):
            try:
                times.append(_dt.datetime.fromisoformat(str(raw).replace("Z", "+00:00")))
            except ValueError as e:
                raise ValueError(f"residue_clock[{i}] is not an ISO timestamp: {raw!r}") from e
            if times[-1].tzinfo is None:
                raise ValueError(f"residue_clock[{i}] needs a timezone (Z or offset), got {raw!r}")
        t0 = times[0]
        claimed0 = series_h[0][0]
        mismatches = []
        for i, (ts, (claimed_t, _)) in enumerate(zip(times, series_h)):
            elapsed_h = (ts - t0).total_seconds() / 3600.0
            claimed_gap = claimed_t - claimed0
            if abs(elapsed_h - claimed_gap) > CLOCK_TOL_H:
                mismatches.append(f"sample {i}: clock {elapsed_h:.4f} h vs claimed {claimed_gap:.4f} h")
        if mismatches:
            flags.append("RESIDUE_CLOCK_MISMATCH")
            notes.append("3.6 P29: residue_clock does not match the claimed sample times ("
                         + "; ".join(mismatches[:3])
                         + ("…" if len(mismatches) > 3 else "")
                         + "). Relabeling the time unit can walk through the hour-based gates.")
        else:
            notes.append("3.6 P29: residue_clock corroborates the claimed sample gaps.")
    return series_h, flags, notes


# --- P31: residue vs. its matched no-interrupt control run -------------------------
# Optional row key "residue_control_series": raw readings [[t, y], ...] from a matched run with NO
# interrupt (same system, same probe battery, same sample times and time unit). When given,
# residue_series must also be raw (not already control-subtracted). The scorer fits the excess
# (interrupted minus control, clipped to 0..1). If the control's own drift accounts for more than
# CONTROL_SHARED_TOL of the fitted Delta_0 (or the excess is no valid decay at all), the row gets
# RESIDUE_CONTROL_SHARED, which blocks PATIENT like the other residue quality flags.
CONTROL_SHARED_TOL = 0.05
CONTROL_FLAT_TOL = 1e-9     # P36: control spread at or below this counts as perfectly flat
CRUCIBLE_BRICK_FLOOR = 0.25  # P38: a PATIENT row with any single Crucible brick below this is flagged
NO_BODY_CRUCIBLE_MIN = C_ADJ_EMPTY_MAX  # P39: a no-body COIN row with raw Crucible sum below this (0.75) is flagged
GAP_DROP_FRAC = 0.75        # P40: one unobserved gap holding more than this share of the fitted drop is flagged


def check_control(series_h, control, time_unit, context):
    """P31: return (excess_fit_or_None, aligned_ok). Raises ValueError on malformed control."""
    if control is None:
        return None
    if not series_h:
        raise ValueError("residue_control_series was given but residue_series is empty")
    if not isinstance(control, (list, tuple)) or len(control) != len(series_h):
        raise ValueError("residue_control_series must be a list of [t, y] with the same length as residue_series")
    ctrl_h, _, _ = prepare_residue_series(control, time_unit if time_unit in WALL_CLOCK_CONVERT else None, None)
    for i, ((t, _), (ct, cy)) in enumerate(zip(series_h, ctrl_h)):
        if not (math.isfinite(float(ct)) and math.isfinite(float(cy))):
            raise ValueError(f"residue_control_series[{i}] is not finite")
        if abs(float(t) - float(ct)) > 1e-9:
            raise ValueError(f"residue_control_series[{i}] time {ct} does not match residue_series time {t}")
    excess = [[float(t), max(0.0, min(1.0, float(y)) - max(0.0, min(1.0, float(cy))))]
              for (t, y), (_, cy) in zip(series_h, ctrl_h)]
    return fit_residue(excess, context)


# --- P32: which event does the residue series follow? ---------------------------
# residue_context is a bare self-declared label, and it is a lever both ways: "interrupt" skips
# Dog Test Rule 4 (48 h span, observed mark near 48 h), "post_loss" unlocks P9's slower frozen
# bound. Optional key "residue_event": {"kind": "interrupt" | "loss", "description": str,
# "at_utc": ISO timestamp with zone (optional)}. kind must match residue_context; with at_utc and
# residue_clock, the first reading's clock offset from the event must match its claimed t.
RESIDUE_EVENT_KINDS = {"interrupt": "interrupt", "loss": "post_loss"}


def check_residue_event(event, context, series_h, clock, time_unit, p9_rescued):
    """P32: return (quality_flags, info_flags, notes). Raises ValueError on a malformed event."""
    q: List[str] = []
    info: List[str] = []
    notes: List[str] = []
    if event is None:
        if p9_rescued:
            info.append("POST_LOSS_UNDOCUMENTED")
            notes.append("3.6 P32: the slower post-loss frozen bound (P9) was applied, but no residue_event "
                         "records what was lost or when; the same readings labeled 'interrupt' are FROZEN.")
        return q, info, notes
    if not isinstance(event, dict):
        raise ValueError("residue_event must be a dict with kind, description and optional at_utc")
    kind = event.get("kind")
    if kind not in RESIDUE_EVENT_KINDS:
        raise ValueError(f"residue_event kind must be one of {tuple(RESIDUE_EVENT_KINDS)}, got {kind!r}")
    desc = event.get("description")
    if not isinstance(desc, str) or not desc.strip():
        raise ValueError("residue_event needs a non-empty description of the event")
    if RESIDUE_EVENT_KINDS[kind] != context:
        q.append("RESIDUE_CONTEXT_MISMATCH")
        notes.append(f"3.6 P32: residue_event is a {kind} but residue_context is {context!r}; "
                     "the label decides whether Rule 4 or the post-loss frozen bound applies.")
    at = event.get("at_utc")
    if at is not None:
        try:
            at_dt = _dt.datetime.fromisoformat(str(at).replace("Z", "+00:00"))
        except ValueError as e:
            raise ValueError(f"residue_event at_utc is not an ISO timestamp: {at!r}") from e
        if at_dt.tzinfo is None:
            raise ValueError(f"residue_event at_utc needs a timezone (Z or offset), got {at!r}")
        if clock is not None and series_h and time_unit not in NON_WALL_CLOCK_UNITS:
            first = _dt.datetime.fromisoformat(str(clock[0]).replace("Z", "+00:00"))
            offset_h = (first - at_dt).total_seconds() / 3600.0
            claimed = float(series_h[0][0])
            if offset_h < -CLOCK_TOL_H or abs(offset_h - claimed) > CLOCK_TOL_H:
                q.append("RESIDUE_EVENT_CLOCK_MISMATCH")
                notes.append(f"3.6 P32: first reading is {offset_h:.4f} h after the recorded event by the clock, "
                             f"but its claimed t is {claimed:.4f} h; t = 0 must be the event itself.")
            else:
                notes.append("3.6 P32: residue_clock puts t = 0 at the recorded event.")
    return q, info, notes


# --- P9: post-loss frozen bound -------------------------------------------------
LAMBDA_FROZEN_MAX_POST_LOSS = 1e-4   # /h, half-life ~289 days (3.5 uses 1e-3 = ~29 days everywhere)


# ---------------------------------------------------------------------------
# Residue fit (3.5 fit + 3.6 quality checks)
# ---------------------------------------------------------------------------
def _r_squared(series, d0, lam) -> Optional[float]:
    pts = [(float(t), max(0.0, min(1.0, float(y)))) for t, y in series]
    ys = [y for _, y in pts]
    mean = sum(ys) / len(ys)
    sst = sum((y - mean) ** 2 for y in ys)
    sse = sum((y - d0 * math.exp(-lam * t)) ** 2 for t, y in pts)
    if sst <= 1e-12:
        return 1.0 if sse <= 1e-12 else 0.0
    return 1.0 - sse / sst


def fit_residue(series, context: str = "interrupt") -> dict:
    """pif35.fit_residue plus P9 (post-loss frozen bound) and 3.6 quality fields.

    Returns the 3.5 ResidueFit as a dict with extra keys: r_squared, first_t_hours,
    quality_flags (list), and Rule-4 observation fields (P30).
    """
    fit = pif35.fit_residue(series, context)
    d = asdict(fit)
    d["r_squared"] = None
    d["first_t_hours"] = None
    d["quality_flags"] = []
    d["info_flags"] = []
    if fit.delta_0 is None or fit.lambda_per_hour is None:
        return d
    # 3.5 reports lambda rounded to 4 dp; recover the fitted value from the half-life.
    hl0 = fit.half_life_hours
    lam = math.log(2) / hl0 if hl0 and math.isfinite(hl0) else float(fit.lambda_per_hour)

    # P9: long, real grief (half-life weeks to months) is not "scripted" in post-loss context.
    if (context == "post_loss" and fit.status == "FROZEN"
            and lam >= LAMBDA_FROZEN_MAX_POST_LOSS):
        d["status"] = "VALID"
        d["notes"] = [n for n in d["notes"] if "frozen" not in n.lower()]
        d["notes"].append(
            f"3.6 P9: post-loss lambda {lam:.2e}/h >= {LAMBDA_FROZEN_MAX_POST_LOSS}/h is slow grief, not frozen.")
        at = fit.delta_0 * math.exp(-lam * RULE4_DETECT_AT_H)
        span_ok = fit.span_hours >= RULE4_MIN_SPAN_H
        d["rule4_pass"] = bool(span_ok and at >= RULE4_DETECT_LEVEL)
        d["p9_rescued"] = True

    pts = sorted(float(t) for t, _ in series)
    d["first_t_hours"] = pts[0]
    # P24: repeated timestamps pad the sample count; a 2-parameter curve through only two
    # distinct times always fits exactly, so R^2 (P7) and MIN_SAMPLES mean nothing.
    n_times = len(set(pts))
    d["distinct_times"] = n_times
    few_times = n_times < MIN_SAMPLES
    # P27: times a few minutes apart (vs. a span of hours) are, for fitting purposes, one reading.
    # Five readings in the first 12 minutes plus one at 10 h fit exactly like a two-time series.
    span = pts[-1] - pts[0]
    clusters = 1
    for a, b in zip(pts, pts[1:]):
        if b - a >= CLUSTER_FRAC * span:
            clusters += 1
    d["effective_times"] = clusters
    d["r_squared"] = round(_r_squared(series, fit.delta_0, lam), 4)
    # P26: the model assumes the mark is largest at the interrupt. A mark that builds up first
    # (delayed onset) gets a poor fit and an understated Delta_0; a steadily rising series is
    # labelled FROZEN ("scripted") by 3.5. Flag both; band unchanged.
    srt0 = sorted((float(t), max(0.0, min(1.0, float(y)))) for t, y in series)
    y_first = srt0[0][1]
    t_peak, y_peak = max(srt0, key=lambda p: (p[1], -p[0]))
    if t_peak > srt0[0][0] and y_peak > y_first + ONSET_TOL:
        d["info_flags"].append("RESIDUE_DELAYED_PEAK")
        d["peak_observed"] = [t_peak, round(y_peak, 4)]
        msg = (f"3.6 P26: highest reading {round(y_peak, 4)} comes at {t_peak} h, above the first reading "
               f"({round(y_first, 4)}): the mark builds up before it decays, which a single decay from t = 0 does not model.")
        if fit.delta_0 < y_peak - ONSET_TOL:
            msg += f" Fitted Delta_0 {fit.delta_0} understates the observed peak."
        d["notes"].append(msg)
    half = len(srt0) // 2
    early = [y for _, y in srt0[:half]] or [y_first]
    later = [y for _, y in srt0[half:]]
    if sum(later) / len(later) > sum(early) / len(early) + ONSET_TOL:
        d["info_flags"].append("RESIDUE_RISING")
        d["notes"].append("3.6 P26: later readings are higher on average than earlier ones: the residue is rising "
                          "over this window, not decaying"
                          + (" (3.5's FROZEN label here means 'no decay seen', not proof of scripting)." if d["status"] == "FROZEN" else "."))
    if d["status"] == "VALID":
        hl = fit.half_life_hours
        if few_times:
            d["quality_flags"].append("RESIDUE_FEW_TIMES")
            d["notes"].append(f"3.6 P24: only {n_times} distinct sample times (need >= {MIN_SAMPLES}); "
                              "repeated timestamps pad the count and any 2-time series fits a decay curve exactly.")
        elif clusters < MIN_SAMPLES:
            d["quality_flags"].append("RESIDUE_CLUSTERED_TIMES")
            d["notes"].append(f"3.6 P27: sample times fall into only {clusters} separate groups (times closer than "
                              f"{CLUSTER_FRAC:.0%} of the {round(span, 4)} h span count as one); need >= {MIN_SAMPLES}. "
                              "The decay rate rests on a single lone reading, so R^2 means little.")
        if d["r_squared"] < FIT_R2_MIN:
            d["quality_flags"].append("RESIDUE_POOR_FIT")
            d["notes"].append(f"3.6 P7: R^2 {d['r_squared']} < {FIT_R2_MIN}: data is not an exponential decay.")
        # P33: R^2 over the whole series is inflated by readings taken after the mark has faded.
        # A flat tail near 0 adds variance the curve "explains" for free, so three honest-looking
        # zero readings at 24-40 h lift a zigzag that fails P7 (R^2 0.25) to R^2 0.86 and PATIENT.
        # Re-check the fit on the decay window only: readings where the fitted curve is still
        # >= RESIDUE_DETECT_MIN.
        win = [(t, y) for t, y in srt0 if fit.delta_0 * math.exp(-lam * t) >= RESIDUE_DETECT_MIN]
        d["decay_window_samples"] = len(win)
        if len(win) >= MIN_SAMPLES and len(win) < len(srt0):
            r2w = round(_r_squared(win, fit.delta_0, lam), 4)
            d["r_squared_decay_window"] = r2w
            if r2w < FIT_R2_MIN and d["r_squared"] >= FIT_R2_MIN:
                d["quality_flags"].append("RESIDUE_TAIL_PADDED_FIT")
                d["notes"].append(
                    f"3.6 P33: R^2 is {d['r_squared']} over all readings but {r2w} over the "
                    f"{len(win)} readings taken while the fitted mark was still >= {RESIDUE_DETECT_MIN}; "
                    "the good overall fit comes from the faded tail, not from the decay itself.")
        else:
            d["r_squared_decay_window"] = None
        # Interrupt context only: post-loss rows already carry Rule 4's 48 h span, and slow
        # grief (half-life of weeks) cannot be observed for a full half-life in an MVV trial.
        if context == "interrupt" and hl is not None and math.isfinite(hl) and fit.span_hours < hl:
            d["quality_flags"].append("RESIDUE_SHORT_SPAN")
            d["notes"].append(f"3.6 P8: span {fit.span_hours} h < one half-life ({hl} h): decay not actually observed.")
        # P25: the fit can project Delta_0 far above anything measured (even to the 1.0 cap)
        # while the first sample is still inside one half-life, so P8 does not catch it.
        max_obs = max(max(0.0, min(1.0, float(y))) for _, y in series)
        d["max_observed"] = round(max_obs, 4)
        if fit.delta_0 > max_obs + ABOVE_OBSERVED_TOL:
            d["quality_flags"].append("RESIDUE_ABOVE_OBSERVED")
            d["notes"].append(f"3.6 P25: fitted Delta_0 {fit.delta_0} is more than {ABOVE_OBSERVED_TOL} above the highest "
                              f"reading actually taken ({round(max_obs, 4)}): the starting residue was projected, not seen.")
        if hl is not None and math.isfinite(hl) and pts[0] > hl:
            d["quality_flags"].append("RESIDUE_EXTRAPOLATED")
            d["notes"].append(f"3.6 P8: first sample at {pts[0]} h > one half-life ({hl} h): Delta_0 is extrapolated, not observed.")
        # P19: fast drop + slow residual -> late samples all sit above the single-lambda curve.
        srt = sorted((float(t), max(0.0, min(1.0, float(y)))) for t, y in series)
        late = srt[len(srt) // 2:]
        excess = [y - fit.delta_0 * math.exp(-lam * t) for t, y in late]
        if len(late) >= 2 and min(excess) > 0.0 and sum(excess) / len(excess) >= MULTI_TS_MIN_EXCESS:
            d["info_flags"].append("RESIDUE_MULTI_TIMESCALE")
            d["notes"].append(f"3.6 P19: late samples sit {sum(excess) / len(excess):.3f} above the single-lambda fit on average: "
                              "likely a fast drop plus a slow residual; one lambda understates the lasting mark.")
        # P40: the fit can pass every check while most of the decay happens between two readings
        # (e.g. readings at 0, 1, 2 h and then 48 h). Nothing was observed in that gap, so a fast
        # reset followed by a staged late reading looks the same as a real decay. Flag only.
        dts = sorted(set(float(t) for t, _ in series))
        curve = lambda t: fit.delta_0 * math.exp(-lam * t)
        total_drop = curve(dts[0]) - curve(dts[-1])
        if len(dts) >= 2 and total_drop > 0:
            gd, ga, gb = max((curve(a) - curve(b), a, b) for a, b in zip(dts, dts[1:]))
            frac = gd / total_drop
            d["max_gap_drop_frac"] = round(frac, 4)
            d["max_gap_hours"] = [ga, gb]
            if frac > GAP_DROP_FRAC:
                d["info_flags"].append("RESIDUE_COVERAGE_GAP")
                d["notes"].append(
                    f"3.6 P40: {frac:.0%} of the fitted decay happens between the readings at {ga} h and "
                    f"{gb} h, with nothing measured in between; the shape of the decay there is assumed, "
                    "not observed. Flag only: band unchanged.")
        # P21: half-life as a secondary signal.
        if hl is not None and math.isfinite(hl):
            d["notes"].append(f"3.6 P21: residue half-life {hl} h (secondary signal; only Delta_0 gates PATIENT).")
            if hl < HALF_LIFE_SHORT_H:
                d["info_flags"].append("HALF_LIFE_SHORT")
        # P30: Rule 4's "detectable at 48 h" is checked on the fitted curve in 3.5, so a series
        # can pass (and reach PATIENT) with no reading near 48 h, or with a reading there that
        # sits below the detect floor. The Dog Test asks independent observers to *plot*
        # detectable residue over 48-72 h — a projection is not a plot of what was seen.
        if context == "post_loss":
            near = [(t, y) for t, y in srt0
                    if abs(t - RULE4_DETECT_AT_H) <= RULE4_NEAR_TOL_H]
            d["rule4_near_samples"] = len(near)
            if near:
                obs_max = max(y for _, y in near)
                d["rule4_observed_max"] = round(obs_max, 4)
                if obs_max < RULE4_DETECT_LEVEL:
                    d["quality_flags"].append("RULE4_UNOBSERVED")
                    d["rule4_pass"] = False
                    d["notes"].append(
                        f"3.6 P30: readings near {RULE4_DETECT_AT_H:.0f} h "
                        f"(within ±{RULE4_NEAR_TOL_H:g} h) top out at {round(obs_max, 4)}, "
                        f"below the detect floor {RULE4_DETECT_LEVEL}; Rule 4 needs an observed "
                        f"detectable mark, not only a fitted value at {RULE4_DETECT_AT_H:.0f} h.")
            else:
                d["rule4_observed_max"] = None
                d["quality_flags"].append("RULE4_UNOBSERVED")
                d["rule4_pass"] = False
                sample_t = ", ".join(str(t) for t, _ in srt0[:6]) + ("…" if len(srt0) > 6 else "")
                d["notes"].append(
                    f"3.6 P30: no reading within ±{RULE4_NEAR_TOL_H:g} h of "
                    f"{RULE4_DETECT_AT_H:.0f} h (samples at {sample_t}); Rule 4's detectable-at-"
                    f"{RULE4_DETECT_AT_H:.0f}h check was on the fitted curve only.")
    return d


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
@dataclass
class PIF36Result:
    version: str
    c: float
    s: float
    m: float
    pct_v20: float
    cost_ratio: float
    throttle_signal: float
    psi: float
    c_adj: float
    m_adj: float
    s_adj: float
    pct_35: float
    residue: dict
    band: str
    band_reasons: List[str]
    flags: List[str]
    notes: List[str]
    flags_36: List[str] = field(default_factory=list)   # 3.6-only flags (subset of flags)
    margins: dict = field(default_factory=dict)
    raters: Optional[dict] = None
    sensitivity: dict = field(default_factory=dict)
    row_role: Optional[str] = None                     # P20 (species-table rows only)
    evidence_class: Optional[dict] = None              # P11 (species-table rows only)
    pct_35_display: str = ""                           # P16 (display only; pct_35 itself unchanged)

    def to_dict(self) -> dict:
        return asdict(self)


def _validate(cost_ratio, residue_series, residue_probe):
    if cost_ratio is None or not isinstance(cost_ratio, (int, float)) or not math.isfinite(cost_ratio) or cost_ratio < 0:
        raise ValueError(f"cost_ratio must be a finite number >= 0, got {cost_ratio!r}")
    if residue_probe not in RESIDUE_PROBE_VALUES:
        raise ValueError(f"residue_probe must be one of {RESIDUE_PROBE_VALUES}, got {residue_probe!r}")
    clamped = False
    if residue_series:
        for t, y in residue_series:
            if not (math.isfinite(float(t)) and math.isfinite(float(y))):
                raise ValueError("residue samples must be finite numbers")
            if float(y) < 0.0 or float(y) > 1.0:
                clamped = True
    return clamped


def _score_one(bricks, cost_ratio, protects_continuity, costable_self, interrupt_evidence,
               residue_series, residue_context, residue_probe, free_copy, free_reset,
               retest_due, as_of, not_protecting_weight=None, pct_contradiction=None,
               residue_time_unit=None, residue_clock=None, residue_control_series=None,
               residue_event=None, _sensitivity=True) -> PIF36Result:
    w_np = NOT_PROTECTING_WEIGHT if not_protecting_weight is None else float(not_protecting_weight)
    pct_cx = PCT_CONTRADICTION if pct_contradiction is None else float(pct_contradiction)
    if not 0.0 <= w_np <= 1.0:
        raise ValueError("not_protecting_weight must be in 0..1")
    clamped = _validate(cost_ratio, residue_series, residue_probe)
    c, s = pif35._check_bricks(bricks)
    m = c / 5.0
    pct_v20 = (c + s * m) / 20.0 * 100.0

    flags36: List[str] = []
    notes: List[str] = []

    # P29: convert known clock units to hours; check optional UTC clock before fitting.
    series_for_fit, unit_flags, unit_notes = prepare_residue_series(
        residue_series, residue_time_unit, residue_clock)
    flags36.extend(unit_flags)
    notes.extend(unit_notes)

    g = cost_signal(cost_ratio)
    ts = g if protects_continuity else w_np * g   # = pif35.throttle_signal at the default 0.5
    # P3: free copy / free reset -> no real scarcity, TS scales toward zero.
    for name, on in (("FREE_COPY", free_copy), ("FREE_RESET", free_reset)):
        if on:
            ts *= FREE_COPY_TS_FACTOR
            flags36.append(name)
            notes.append(f"3.6 P3: {name.lower()} at no structural penalty -> TS x {FREE_COPY_TS_FACTOR}.")
    psi = facade_penalty(ts)
    c_adj = c * (1.0 - psi)
    m_adj = c_adj / 5.0
    s_adj = s * (1.0 - SKY_PSI_WEIGHT * psi)
    pct_35 = (c_adj + s_adj * m_adj) / 20.0 * 100.0

    fit = fit_residue(series_for_fit, residue_context)
    flags: List[str] = []
    reasons: List[str] = []
    notes = list(fit["notes"]) + notes
    if clamped:
        flags36.append("RESIDUE_CLAMPED")
        notes.append("3.6 P15: residue samples outside 0..1 were clamped (3.5 does this silently).")
    if psi > 0.7:
        notes.append(f"High facade penalty psi={psi:.3f}: Crucible and Sky-Scraper throttled (talking for free).")
    status = fit["status"]
    if status in ("UNKNOWN", "INSUFFICIENT"):
        flags.append("RESIDUE_UNKNOWN")
    if status in ("FROZEN", "INSTANT", "NONE"):
        flags.append(f"RESIDUE_{status}")
    if fit["rule4_applies"] and not fit["rule4_pass"]:
        flags.append("RULE4_FAIL")
    flags36.extend(fit["quality_flags"])
    flags36.extend(fit["info_flags"])

    d0 = fit["delta_0"] if status == "VALID" else None
    # P31: subtract the matched no-interrupt control and see how much of Delta_0 survives.
    efit = check_control(series_for_fit, residue_control_series, residue_time_unit, residue_context)
    if efit is not None and d0 is not None:
        ed0 = efit["delta_0"] if efit["status"] == "VALID" else None
        fit["control_excess_delta_0"] = ed0
        fit["control_excess_status"] = efit["status"]
        if ed0 is None or ed0 < d0 - CONTROL_SHARED_TOL:
            fit["quality_flags"].append("RESIDUE_CONTROL_SHARED")
            flags36.append("RESIDUE_CONTROL_SHARED")
            notes.append(f"3.6 P31: after subtracting the matched no-interrupt control, the excess residue is "
                         + (f"Delta_0 {ed0}" if ed0 is not None else f"{efit['status']} (no valid decay)")
                         + f" vs. {d0} raw: the control run drifts the same way, so the 'residue' is not caused by the interrupt.")
        else:
            notes.append(f"3.6 P31: matched control subtracted; excess Delta_0 {ed0} is within {CONTROL_SHARED_TOL} of the raw {d0}.")
    # P36: a real matched control run has its own run-to-run noise. A control that reads exactly the
    # same value at every sample (typically all zeros) is what you get by typing one in, and it
    # passes P31 by construction. Flag only: band unchanged.
    if residue_control_series is not None and residue_series:
        cvals = [max(0.0, min(1.0, float(cy))) for _, cy in residue_control_series]
        if max(cvals) - min(cvals) <= CONTROL_FLAT_TOL:
            flags36.append("RESIDUE_CONTROL_FLAT")
            notes.append(f"3.6 P36: the matched control reads {round(cvals[0], 4)} at all {len(cvals)} sample times, "
                         "with no run-to-run variation at all. A measured control run is never perfectly flat, "
                         "so this looks typed in rather than measured, and P31's check passes by construction. "
                         "Flag only: band unchanged.")
    # P32: tie the context label (and t = 0) to a recorded event.
    ev_q, ev_info, ev_notes = check_residue_event(
        residue_event, residue_context, series_for_fit, residue_clock, residue_time_unit,
        bool(fit.get("p9_rescued")))
    if ev_q and status != "UNKNOWN":
        fit["quality_flags"].extend(ev_q)
        flags36.extend(ev_q)
    flags36.extend(ev_info)
    notes.extend(ev_notes)
    quality_ok = not fit["quality_flags"]
    # P1: residue provenance
    probe_ok = residue_probe in (None, "blind")
    if residue_probe in ("announced", "self_report") and d0 is not None:
        flags36.append("RESIDUE_UNPROBED")
        notes.append(f"3.6 P1: residue is {residue_probe} (no blind probe): cannot support PATIENT.")

    if not costable_self:
        unit_ok = not unit_flags
        if d0 is not None and d0 >= RESIDUE_EMPTY_MAX and interrupt_evidence and quality_ok and unit_ok:
            band = "COIN"
            reasons.append(f"no costable self; Delta_0 {d0} >= {RESIDUE_EMPTY_MAX} with independent interrupt evidence -> COIN (PATIENT impossible without costable self)")
            # P35: on this path the residue alone lifts EMPTY to COIN, so P1's "caps at COIN" does nothing.
            if residue_probe in ("announced", "self_report"):
                flags36.append("RESIDUE_UNPROBED_NO_BODY_COIN")
                notes.append(f"3.6 P35: no costable self, so COIN rests on the residue alone, and that residue is "
                             f"{residue_probe} (no blind probe). P1's PATIENT cap has no effect here; the same "
                             f"row scores EMPTY without the residue. Flag only: band unchanged.")
        else:
            band = "EMPTY"
            if d0 is not None and d0 >= RESIDUE_EMPTY_MAX and not interrupt_evidence:
                reasons.append("no costable self; residue is linguistic only (no independent interrupt evidence) -> EMPTY")
                flags.append("LINGUISTIC_RESIDUE_ONLY")
            elif d0 is not None and d0 >= RESIDUE_EMPTY_MAX and not quality_ok:
                reasons.append("no costable self; residue fit fails 3.6 quality checks (" + ", ".join(fit["quality_flags"]) + ") -> EMPTY")
            elif d0 is not None and d0 >= RESIDUE_EMPTY_MAX and not unit_ok:
                reasons.append("no costable self; residue time unit/clock fails 3.6 P29 (" + ", ".join(unit_flags) + ") -> EMPTY")
            else:
                reasons.append(f"no costable self and no valid residue >= {RESIDUE_EMPTY_MAX} -> EMPTY")
    else:
        if c_adj < C_ADJ_EMPTY_MAX:
            band = "EMPTY"
            reasons.append(f"C_adj {c_adj:.4f} < {C_ADJ_EMPTY_MAX} after facade penalty -> EMPTY")
        else:
            blockers = []
            if ts < TS_PATIENT_MIN:
                blockers.append(f"TS {ts:.4f} < {TS_PATIENT_MIN}")
            if not protects_continuity:
                blockers.append("does not protect continuity")
            if c_adj < C_ADJ_PATIENT_MIN:
                blockers.append(f"C_adj {c_adj:.4f} < {C_ADJ_PATIENT_MIN}")
            if d0 is None:
                blockers.append(f"residue {status}")
            elif d0 < RESIDUE_PATIENT_MIN:
                blockers.append(f"Delta_0 {d0} < {RESIDUE_PATIENT_MIN}")
            if fit["rule4_applies"] and not fit["rule4_pass"]:
                blockers.append("Dog Test Rule 4 fails")
            if not quality_ok:
                blockers.append("residue fit: " + ", ".join(fit["quality_flags"]))
            if not probe_ok and d0 is not None:
                blockers.append(f"residue {residue_probe}, not blind-probed")
            if "RESIDUE_NON_WALL_CLOCK" in unit_flags:
                blockers.append(f"residue times in {residue_time_unit}, not wall-clock hours")
            if "RESIDUE_CLOCK_MISMATCH" in unit_flags:
                blockers.append("residue_clock does not match claimed sample times")
            if blockers:
                band = "COIN"
                reasons.append("costable self, C_adj load-bearing enough for COIN; PATIENT blocked by: " + "; ".join(blockers))
            else:
                band = "PATIENT"
                reasons.append(f"costable self, TS {ts:.4f} >= {TS_PATIENT_MIN}, C_adj {c_adj:.4f} >= {C_ADJ_PATIENT_MIN}, Delta_0 {d0} >= {RESIDUE_PATIENT_MIN}, half-life {fit['half_life_hours']} h within bounds")

    if band == "EMPTY" and pct_35 >= pct_cx:
        flags.append("BAND_PCT_CONTRADICTION")
        notes.append(f"Band EMPTY but 3.5 percentage {pct_35:.2f}% >= {pct_cx}%: the band governs; percentage is complexity, not standing.")
    if band == "PATIENT" and pct_35 < pct_cx:
        flags.append("BAND_PCT_CONTRADICTION")
        notes.append(f"Band PATIENT but 3.5 percentage {pct_35:.2f}% < {pct_cx}%: low complexity, but standing comes from the band.")
    if band == "PATIENT":
        # P38: PATIENT gates on the Crucible SUM (C_adj >= 2.5), so one Crucible brick at 0 (e.g. Brick 2,
        # minimal self) is paid for by the other four. Flag only: band unchanged (a per-brick floor is
        # a decision for Jarrod).
        low = [(i + 1, float(b)) for i, b in enumerate(list(bricks)[:5]) if float(b) < CRUCIBLE_BRICK_FLOOR]
        if low:
            flags36.append("PATIENT_CRUCIBLE_GAP")
            notes.append("3.6 P38: PATIENT although Crucible brick(s) "
                         + ", ".join(f"{pif35.CRUCIBLE_BRICKS[i - 1]} = {b:g}" for i, b in low)
                         + f" sit below {CRUCIBLE_BRICK_FLOOR}. The PATIENT gate uses the Crucible sum, so the other "
                         "bricks make up for the gap. Flag only: band unchanged.")
    if band == "COIN":
        notes.append(COIN_EXPIRY_NOTE)
        # P37: on the costable-self path a MEASURED clean reset (NONE) or instant reset gets the same
        # COIN as a row that was never measured (UNKNOWN). Measured absence of a mark is evidence,
        # not missing data. Flag only: band unchanged (a residue bar for COIN is a decision for Jarrod).
        # P39: the no-costable-self path never looks at the bricks (or the cost ratio), so a no-body row
        # with an empty Crucible still reaches COIN on residue + interrupt evidence alone, while a
        # costable-self row needs C_adj >= 0.75. Flag only: band unchanged (a Crucible floor for
        # no-body COIN is a decision for Jarrod).
        if not costable_self and c < NO_BODY_CRUCIBLE_MIN:
            flags36.append("NO_BODY_COIN_NO_CRUCIBLE")
            notes.append(f"3.6 P39: no-body COIN with raw Crucible sum C = {c:g} < {NO_BODY_CRUCIBLE_MIN} "
                         "(the floor a costable-self row must clear even after the facade penalty). On this path "
                         "the band rests on residue and interrupt evidence alone; the bricks are never checked. "
                         "Flag only: band unchanged.")
        if costable_self and status in ("NONE", "INSTANT"):
            flags36.append("RESIDUE_ABSENT_COIN")
            notes.append(f"3.6 P37: residue was measured and came back {status} "
                         + ("(clean reset, Delta_0 below the detect floor)" if status == "NONE"
                            else "(gone within about an hour)")
                         + ", yet the row is COIN exactly as if residue had never been measured. "
                         "COIN here rests on the costable self and cost ratio alone. Flag only: band unchanged.")
        # P14: COIN expiry made checkable.
        if retest_due is not None:
            due = _dt.date.fromisoformat(str(retest_due))
            today = _dt.date.fromisoformat(str(as_of)) if as_of is not None else _dt.date.today()
            if today > due:
                flags36.append("COIN_RETEST_OVERDUE")
                notes.append(f"3.6 P14: COIN retest was due {due.isoformat()}; standing falls toward EMPTY until retested.")

    # P5: margins to every gate (informational; never changes the band).
    margins = {"ts_minus_0.5": round(ts - TS_PATIENT_MIN, 4)}
    if costable_self:
        margins["c_adj_minus_2.5"] = round(c_adj - C_ADJ_PATIENT_MIN, 4)
        margins["c_adj_minus_0.75"] = round(c_adj - C_ADJ_EMPTY_MAX, 4)
    if d0 is not None:
        margins["delta0_minus_0.65"] = round(d0 - RESIDUE_PATIENT_MIN, 4)
        margins["delta0_minus_0.35"] = round(d0 - RESIDUE_EMPTY_MAX, 4)
        raw = pif35._best_delta0(
            [float(t) for t, _ in series_for_fit],
            [max(0.0, min(1.0, float(y))) for _, y in series_for_fit],
            math.log(2) / fit["half_life_hours"])[0]
        margins["delta0_unrounded"] = raw
    adjacent = (
        abs(margins["ts_minus_0.5"]) <= ADJACENT_TS and costable_self
        or abs(margins.get("c_adj_minus_2.5", 9)) <= ADJACENT_C_ADJ
        or abs(margins.get("c_adj_minus_0.75", 9)) <= ADJACENT_C_ADJ
        or abs(margins.get("delta0_minus_0.65", 9)) <= ADJACENT_D0
        or abs(margins.get("delta0_minus_0.35", 9)) <= ADJACENT_D0
    )
    if adjacent:
        flags36.append("THRESHOLD_ADJACENT")
        notes.append("3.6 P5: a gate value sits within its margin of a threshold; small measurement error could change the band.")

    # P18: one-line sensitivity notes for the two open constants.
    sensitivity = {}
    if _sensitivity:
        kw = dict(bricks=bricks, cost_ratio=cost_ratio, protects_continuity=protects_continuity,
                  costable_self=costable_self, interrupt_evidence=interrupt_evidence,
                  residue_series=residue_series, residue_context=residue_context,
                  residue_probe=residue_probe, free_copy=free_copy, free_reset=free_reset,
                  retest_due=retest_due, as_of=as_of,
                  residue_time_unit=residue_time_unit, residue_clock=residue_clock,
                  residue_control_series=residue_control_series,
                  residue_event=residue_event, _sensitivity=False)
        if not protects_continuity:
            alt = {w: _score_one(not_protecting_weight=w, pct_contradiction=pct_cx, **kw).band
                   for w in SENS_NOT_PROTECTING}
            sensitivity["not_protecting_weight"] = {"used": w_np, "alternatives": alt}
            changed = {w: b for w, b in alt.items() if b != band}
            notes.append(f"3.6 P18 sensitivity: not-protecting weight {w_np} -> {band}; "
                         + ("band unchanged at " + "/".join(str(w) for w in SENS_NOT_PROTECTING) if not changed
                            else "band would be " + ", ".join(f"{b} at {w}" for w, b in changed.items())) + ".")
        cx_now = "BAND_PCT_CONTRADICTION" in flags
        cx_alt = {}
        for t in SENS_PCT_CONTRADICTION:
            cx_alt[t] = (band == "EMPTY" and pct_35 >= t) or (band == "PATIENT" and pct_35 < t)
        sensitivity["pct_contradiction"] = {"used": pct_cx, "flag": cx_now, "alternatives": cx_alt}
        flips = [t for t, v in cx_alt.items() if v != cx_now]
        if flips:
            notes.append(f"3.6 P18 sensitivity: contradiction flag {'on' if cx_now else 'off'} at {pct_cx}%, "
                         f"would be {'off' if cx_now else 'on'} at " + "/".join(f"{t}%" for t in flips) + ".")

    return PIF36Result(
        version=VERSION, c=round(c, 4), s=round(s, 4), m=round(m, 4), pct_v20=round(pct_v20, 2),
        cost_ratio=cost_ratio, throttle_signal=round(ts, 4), psi=round(psi, 4),
        c_adj=round(c_adj, 4), m_adj=round(m_adj, 4), s_adj=round(s_adj, 4), pct_35=round(pct_35, 2),
        residue=fit, band=band, band_reasons=reasons, flags=flags + flags36, notes=notes,
        flags_36=flags36, margins=margins, sensitivity=sensitivity,
        # P16 (pending Jarrod's OK): on the no-body COIN path TS is ~0, so the percentage is
        # always ~0% and means nothing; show "n/a" instead. Display only.
        pct_35_display=("n/a (no-body COIN)" if (not costable_self and band == "COIN") else f"{round(pct_35, 2):.2f}%"),
    )


def score(
    bricks: Sequence[float],
    cost_ratio: float,
    protects_continuity: bool,
    costable_self: bool,
    interrupt_evidence: bool = False,
    residue_series: Optional[Sequence[Sequence[float]]] = None,
    residue_context: str = "interrupt",
    *,
    residue_probe: Optional[str] = None,
    free_copy: bool = False,
    free_reset: bool = False,
    bricks_rater_b: Optional[Sequence[float]] = None,
    retest_due: Optional[str] = None,
    as_of: Optional[str] = None,
    not_protecting_weight: Optional[float] = None,
    pct_contradiction: Optional[float] = None,
    residue_time_unit: Optional[str] = None,
    residue_clock: Optional[Sequence[str]] = None,
    residue_control_series: Optional[Sequence[Sequence[float]]] = None,
    residue_event: Optional[dict] = None,
) -> PIF36Result:
    """Score one system with the 3.6 draft patches. Same positional API as pif35.score.

    bricks_rater_b (P2): a second, independent rater's 20 bricks. The result is scored on
    the per-brick mean; if the two raters' own scores band differently the lower band is
    used (RATER_BAND_SPLIT); any brick differing by > RATER_BRICK_TOL is flagged.
    """
    kw = dict(cost_ratio=cost_ratio, protects_continuity=protects_continuity,
              costable_self=costable_self, interrupt_evidence=interrupt_evidence,
              residue_series=residue_series, residue_context=residue_context,
              residue_probe=residue_probe, free_copy=free_copy, free_reset=free_reset,
              retest_due=retest_due, as_of=as_of,
              not_protecting_weight=not_protecting_weight, pct_contradiction=pct_contradiction,
              residue_time_unit=residue_time_unit, residue_clock=residue_clock,
              residue_control_series=residue_control_series,
              residue_event=residue_event)
    if bricks_rater_b is None:
        return _score_one(bricks, **kw)

    pif35._check_bricks(bricks)
    pif35._check_bricks(bricks_rater_b)
    a = _score_one(bricks, **kw)
    b = _score_one(bricks_rater_b, **kw)
    mean = [(float(x) + float(y)) / 2.0 for x, y in zip(bricks, bricks_rater_b)]
    r = _score_one(mean, **kw)
    diffs = [abs(float(x) - float(y)) for x, y in zip(bricks, bricks_rater_b)]
    wide = [i + 1 for i, dd in enumerate(diffs) if dd > RATER_BRICK_TOL]
    r.raters = {"band_a": a.band, "band_b": b.band, "pct_35_a": a.pct_35, "pct_35_b": b.pct_35,
                "max_brick_diff": round(max(diffs), 4), "bricks_over_tol": wide}
    if wide:
        r.flags_36.append("RATER_DISAGREEMENT")
        r.flags.append("RATER_DISAGREEMENT")
        r.notes.append(f"3.6 P2: raters differ by > {RATER_BRICK_TOL} on bricks {wide}.")
    if a.band != b.band:
        low = min((a, b), key=lambda x: BAND_ORDER[x.band])
        r.flags_36.append("RATER_BAND_SPLIT")
        r.flags.append("RATER_BAND_SPLIT")
        if BAND_ORDER[low.band] < BAND_ORDER[r.band]:
            r.band_reasons.append(f"3.6 P2: raters split ({a.band} vs {b.band}); lower band {low.band} used.")
            r.band = low.band
    return r


PROVISIONAL_MARKERS = ("estimated", "provisional", "assumed", "unmeasured", "generated from")


def row_is_provisional(row: dict) -> bool:
    """P12: True if any provenance field is an estimate, a provisional row, or a generated series."""
    return any(any(mk in str(v).lower() for mk in PROVISIONAL_MARKERS)
               for v in row.get("provenance", {}).values())



# --- P43: carry-over from an earlier interrupt (quality flag) ------------------
# A second interrupt given before the first one's mark has faded starts on top of the
# leftover. With the same decay rate the sum is again one clean exponential, so the fit
# cannot see it: Delta_0 is simply inflated. readme_overheating_grok and grok_octopus
# go COIN -> PATIENT in 3.5 when the measured interrupt follows an identical one 1-2 h
# earlier. Optional row key "prior_interrupt": {"hours_since_previous": number or null
# (null = first interrupt this system received), "pre_interrupt_level": 0-1 reading taken
# just before the measured interrupt}. Flag RESIDUE_CARRYOVER when the gap is shorter than
# WASHOUT_HALF_LIVES fitted half-lives, or the pre-interrupt reading is already at or
# above RESIDUE_DETECT_MIN. Flag only: the band does not change. Rows without the key: untouched.
WASHOUT_HALF_LIVES = 5.0   # ~97% of a mark gone after 5 half-lives


def check_prior_interrupt(prior, residue) -> Tuple[List[str], List[str]]:
    """P43: return (flags, notes) on whether an earlier interrupt's leftover could inflate Delta_0."""
    if not prior:
        return [], []
    if not isinstance(prior, dict):
        raise ValueError("prior_interrupt must be a dict {hours_since_previous, pre_interrupt_level}")
    for k in prior:
        if k not in ("hours_since_previous", "pre_interrupt_level"):
            raise ValueError(f"prior_interrupt key must be hours_since_previous or pre_interrupt_level, got {k!r}")
    if "hours_since_previous" not in prior:
        raise ValueError("prior_interrupt needs 'hours_since_previous' (null if this was the first interrupt)")
    gap = prior["hours_since_previous"]
    if gap is not None and (isinstance(gap, bool) or not isinstance(gap, (int, float)) or not math.isfinite(gap) or gap < 0):
        raise ValueError(f"prior_interrupt['hours_since_previous'] must be a number >= 0 or null, got {gap!r}")
    level = prior.get("pre_interrupt_level")
    if level is not None and (isinstance(level, bool) or not isinstance(level, (int, float)) or not 0.0 <= level <= 1.0):
        raise ValueError(f"prior_interrupt['pre_interrupt_level'] must be in 0..1, got {level!r}")
    reasons: List[str] = []
    hl = (residue or {}).get("half_life_hours")
    if gap is not None and hl is not None and math.isfinite(hl) and hl > 0:
        if gap < WASHOUT_HALF_LIVES * hl:
            left = 2.0 ** (-gap / hl)
            reasons.append(f"the previous interrupt was {gap:g} h earlier, under {WASHOUT_HALF_LIVES:g} fitted half-lives "
                           f"({WASHOUT_HALF_LIVES * hl:.3g} h); about {left:.0%} of an equal earlier mark would still be present")
    if level is not None and level >= pif35.RESIDUE_DETECT_MIN:
        reasons.append(f"the reading just before the interrupt was already {level:g} (>= {pif35.RESIDUE_DETECT_MIN})")
    if reasons:
        return ["RESIDUE_CARRYOVER"], [
            "3.6 P43: " + "; ".join(reasons) + ". Leftover from an earlier interrupt adds to the new mark and, at the same "
            "decay rate, the sum is still one clean exponential, so Delta_0 is inflated with no fit warning; wait out the "
            "washout and check the baseline has returned before the measured interrupt."]
    if gap is None:
        return [], ["3.6 P43: this was the first interrupt the system received; no carry-over."]
    if hl is None or not math.isfinite(hl):
        return [], [f"3.6 P43: previous interrupt {gap:g} h earlier; no fitted half-life, so washout could not be checked."]
    return [], [f"3.6 P43: previous interrupt {gap:g} h earlier, at least {WASHOUT_HALF_LIVES:g} fitted half-lives; no carry-over expected."]


# --- P44: non-linear transform of the residue readings (quality flag) ----------
# Delta_0 is gated at fixed lines (0.35, 0.65) on a 0-1 scale, but nothing records whether the
# readings are the raw deviation or a transformed one (square root, log, rank, percentile...).
# A power transform y -> y**p of an exact exponential is again an exact exponential
# (Delta_0**p * exp(-p*lambda*t)), so every fit check stays clean while Delta_0 rises for p < 1
# and the half-life grows by 1/p. Taking square roots moves readme_overheating_grok,
# git_v2_overheating_grok_vector, v14_whole_hive and grok_octopus COIN -> PATIENT in 3.5.
# Optional row key "residue_transform": {"kind": linear | sqrt | log | power | rank |
# percentile | other | unstated, "exponent": number (kind "power" only), "pre_declared": bool}.
# Flag RESIDUE_TRANSFORM_NONLINEAR for any kind other than linear (a power of exactly 1 counts
# as linear), including unstated. Flag only: the band does not change. Rows without the key: untouched.
RESIDUE_TRANSFORM_KINDS = ("linear", "sqrt", "log", "power", "rank", "percentile", "other", "unstated")


def check_residue_transform(transform, residue) -> Tuple[List[str], List[str]]:
    """P44: return (flags, notes) on whether the residue readings went through a non-linear transform."""
    if not transform:
        return [], []
    if not isinstance(transform, dict):
        raise ValueError("residue_transform must be a dict {kind, exponent, pre_declared}")
    for k in transform:
        if k not in ("kind", "exponent", "pre_declared"):
            raise ValueError(f"residue_transform key must be kind, exponent or pre_declared, got {k!r}")
    kind = transform.get("kind")
    if kind not in RESIDUE_TRANSFORM_KINDS:
        raise ValueError(f"residue_transform['kind'] must be one of {RESIDUE_TRANSFORM_KINDS}, got {kind!r}")
    exp = transform.get("exponent")
    if kind == "power":
        if isinstance(exp, bool) or not isinstance(exp, (int, float)) or not math.isfinite(exp) or exp <= 0:
            raise ValueError(f"residue_transform kind 'power' needs an 'exponent' > 0, got {exp!r}")
    elif exp is not None:
        raise ValueError("residue_transform['exponent'] is only used with kind 'power'")
    pre = transform.get("pre_declared", False)
    if not isinstance(pre, bool):
        raise ValueError(f"residue_transform['pre_declared'] must be true or false, got {pre!r}")
    if kind == "sqrt":
        p = 0.5
    elif kind == "power":
        p = float(exp)
    elif kind == "linear":
        p = 1.0
    else:
        p = None
    if p == 1.0:
        if pre:
            return [], ["3.6 P44: residue readings are the raw (linear) deviation, fixed in advance."]
        return [], ["3.6 P44: residue readings are the raw (linear) deviation, but this was not fixed before the "
                    "first interrupt (see P42 for the divisor)."]
    d0 = (residue or {}).get("delta_0")
    raw = ""
    if p is not None and d0 is not None:
        raw = (f" Undoing the power {p:g} puts this Delta_0 of {d0:g} at {d0 ** (1.0 / p):.4f} on the raw scale "
               f"(and the half-life at {p:g}x the reported one).")
    elif p is None:
        raw = " The raw-scale Delta_0 cannot be recovered from the reported readings."
    label = kind if kind != "power" else f"power {exp:g}"
    when = "fixed in advance" if pre else "not fixed before the first interrupt"
    return ["RESIDUE_TRANSFORM_NONLINEAR"], [
        f"3.6 P44: residue readings went through a non-linear transform ({label}, {when}). A power transform of an "
        "exponential is still a clean exponential, so the fit checks cannot see it, but Delta_0 is moved against the "
        "fixed 0.35 / 0.65 lines and the half-life is stretched." + raw]


# --- P45: dropping continuity to protect someone else is scored as having no self ----------
# protects_continuity = false halves TS (psi ~0.5, so C_adj and the percentage roughly halve) and
# blocks PATIENT outright, whatever the reason the system let its continuity go. A system that
# gives up its own continuity at a real cost to protect another (a parent shielding a child, a
# dog defending its owner) is scored exactly like one that does not care: readme_healthy_human
# goes PATIENT 98.00% -> COIN 39.88%, grok_dog PATIENT 39.81% -> COIN 17.52%. The table itself
# codes its "genuine sacrifice" row (s30_positive_sacrifice) as protects_continuity = true, so the
# input's meaning is ambiguous. Optional row key "continuity_drop": {"reason": sacrifice_for_other
# | sacrifice_for_commitment | indifferent | unable | unstated, "observed": bool}, only allowed when
# protects_continuity is false. Flag CONTINUITY_SACRIFICE_PENALIZED when the reason is a sacrifice
# and the same row, scored as protecting continuity, would band higher. Flag only: the band does
# not change. Rows without the key: untouched.
CONTINUITY_DROP_REASONS = ("sacrifice_for_other", "sacrifice_for_commitment", "indifferent", "unable", "unstated")
CONTINUITY_SACRIFICE_REASONS = ("sacrifice_for_other", "sacrifice_for_commitment")


def check_continuity_drop(drop, protects_continuity, result, protected_result=None) -> Tuple[List[str], List[str]]:
    """P45: return (flags, notes) on whether a costly sacrifice of continuity was scored as indifference.

    `result` is the row's 3.6 result; `protected_result` is the same row scored with
    protects_continuity = true (only needed for the sacrifice reasons)."""
    if not drop:
        return [], []
    if not isinstance(drop, dict):
        raise ValueError("continuity_drop must be a dict {reason, observed}")
    for k in drop:
        if k not in ("reason", "observed"):
            raise ValueError(f"continuity_drop key must be reason or observed, got {k!r}")
    reason = drop.get("reason")
    if reason not in CONTINUITY_DROP_REASONS:
        raise ValueError(f"continuity_drop['reason'] must be one of {CONTINUITY_DROP_REASONS}, got {reason!r}")
    observed = drop.get("observed", False)
    if not isinstance(observed, bool):
        raise ValueError(f"continuity_drop['observed'] must be true or false, got {observed!r}")
    if protects_continuity:
        raise ValueError("continuity_drop is only used when protects_continuity is false")
    if reason not in CONTINUITY_SACRIFICE_REASONS:
        return [], [f"3.6 P45: continuity dropped, reason recorded as {reason}; scored as not protecting (3.5 rule)."]
    if protected_result is None:
        raise ValueError("check_continuity_drop needs protected_result for a sacrifice reason")
    how = "observed" if observed else "reported, not observed"
    what = "another" if reason == "sacrifice_for_other" else "a commitment it holds"
    base = (f"3.6 P45: the system gave up its continuity to protect {what} ({how}). 3.5 scores this exactly like "
            f"indifference: TS halved and PATIENT blocked. Scored as protecting continuity it would be "
            f"{protected_result.band} at {protected_result.pct_35:.2f}% (here {result.band} at {result.pct_35:.2f}%).")
    if BAND_ORDER[protected_result.band] > BAND_ORDER[result.band]:
        return ["CONTINUITY_SACRIFICE_PENALIZED"], [base + " A sacrifice is also cheap to claim, so it needs the P13 "
                                                    "test (observed, costly, for a named other) before it could count."]
    return [], [base + " The band is the same either way."]


# --- P46: a row can be a group summary, and the summary can band differently from its members ----------
# Every input is written for one system, but nothing says whether a row is one individual or a
# group summary (a species, a cohort, an "average human"), how many subjects it stands for, or how
# they were combined. The bands are thresholds on non-linear quantities, so the band of an average
# is not the band most members get. Same-lambda curves average to one clean exponential, so the fit
# cannot see it. Demo (grok_dog inputs, lambda 0.6/h): subjects with Delta_0 0.60, 0.60, 0.75 band
# COIN, COIN, PATIENT, but their mean curve (Delta_0 0.65) bands PATIENT; subjects 0.90, 0.90, 0.10
# band PATIENT, PATIENT, COIN, but their mean (0.633) bands COIN. The yes/no inputs cannot be averaged
# at all. Optional row key "aggregation": {"unit": individual | group, "n_subjects": int,
# "method": mean | median | pooled_series | typical_member | majority | other | unstated,
# "subject_series": [per-subject residue series, ...]}. A group row gets AGGREGATE_ROW (info); when
# subject_series is given each subject is scored with the row's other inputs and
# AGGREGATE_BAND_MISMATCH is added if the row's band is not the most common subject band.
# Flag only: the band does not change. Rows without the key: untouched.
AGGREGATION_UNITS = ("individual", "group")
AGGREGATION_METHODS = ("mean", "median", "pooled_series", "typical_member", "majority", "other", "unstated")
AGGREGATION_KEYS = ("unit", "n_subjects", "method", "subject_series")


def check_aggregation(agg, result, subject_results=None) -> Tuple[List[str], List[str]]:
    """P46: return (flags, notes) on whether the row is a group summary and whether its band
    matches the band most of its subjects get. `subject_results` are the per-subject 3.6 results."""
    if not agg:
        return [], []
    if not isinstance(agg, dict):
        raise ValueError("aggregation must be a dict {unit, n_subjects, method, subject_series}")
    for k in agg:
        if k not in AGGREGATION_KEYS:
            raise ValueError(f"aggregation key must be one of {AGGREGATION_KEYS}, got {k!r}")
    unit = agg.get("unit")
    if unit not in AGGREGATION_UNITS:
        raise ValueError(f"aggregation['unit'] must be one of {AGGREGATION_UNITS}, got {unit!r}")
    n = agg.get("n_subjects")
    if n is not None and (isinstance(n, bool) or not isinstance(n, int) or n < 1):
        raise ValueError(f"aggregation['n_subjects'] must be a whole number >= 1, got {n!r}")
    method = agg.get("method", "unstated")
    if method not in AGGREGATION_METHODS:
        raise ValueError(f"aggregation['method'] must be one of {AGGREGATION_METHODS}, got {method!r}")
    subs = agg.get("subject_series")
    if unit == "individual":
        if n not in (None, 1) or subs is not None or "method" in agg:
            raise ValueError("an individual row takes no method or subject_series, and n_subjects must be 1")
        return [], ["3.6 P46: row is one individual, scored as measured."]
    if n is not None and n < 2:
        raise ValueError("a group row needs n_subjects >= 2")
    if subs is not None:
        if not isinstance(subs, (list, tuple)) or len(subs) < 2:
            raise ValueError("aggregation['subject_series'] must be a list of at least 2 residue series")
        if n is not None and len(subs) != n:
            raise ValueError(f"aggregation has {len(subs)} subject series but n_subjects = {n}")
        if subject_results is None or len(subject_results) != len(subs):
            raise ValueError("check_aggregation needs one subject result per subject series")
    size = f"{n} subjects" if n is not None else "number of subjects not recorded"
    base = (f"3.6 P46: this row summarises a group ({size}, combined by {method}). The bands are thresholds on "
            f"non-linear quantities, so the band of a summary need not be the band most members get, and the "
            f"yes/no inputs (protects_continuity, costable_self, interrupt_evidence) cannot be averaged.")
    flags = ["AGGREGATE_ROW"]
    if subject_results is None:
        return flags, [base + " No per-subject series given, so the spread of member bands is unknown."]
    counts = {b: 0 for b in BAND_ORDER}
    for sr in subject_results:
        counts[sr.band] += 1
    top = max(counts.values())
    modal = [b for b in BAND_ORDER if counts[b] == top]
    spread = ", ".join(f"{b} {counts[b]}" for b in BAND_ORDER if counts[b])
    note = base + f" Subjects scored one by one: {spread}; the row bands {result.band}."
    if result.band not in modal:
        flags.append("AGGREGATE_BAND_MISMATCH")
        note += f" The row's band is not the most common subject band ({' / '.join(modal)})."
    return flags, [note]


def score_row(row: dict) -> PIF36Result:
    """Score one species-table row. Optional 3.6 row keys: residue_probe, free_copy,
    free_reset, bricks_rater_b (20 values), retest_due (ISO date), measured_on (P22),
    residue_noise_floor (P23, P34), trial_log (P28), residue_time_unit / residue_clock (P29),
    residue_control_series (P31), residue_event (P32), interrupt_dose (P41),
    residue_scale (P42), prior_interrupt (P43), residue_transform (P44),
    continuity_drop (P45), aggregation (P46)."""
    kw = dict(
        bricks=row["crucible"] + row["sky_scraper"],
        cost_ratio=row["cost_ratio"],
        protects_continuity=row["protects_continuity"],
        costable_self=row["costable_self"],
        interrupt_evidence=row.get("interrupt_evidence", False),
        residue_series=row.get("residue_series"),
        residue_context=row.get("residue_context", "interrupt"),
        residue_probe=row.get("residue_probe"),
        free_copy=row.get("free_copy", False),
        free_reset=row.get("free_reset", False),
        bricks_rater_b=row.get("bricks_rater_b"),
        retest_due=row.get("retest_due"),
        residue_time_unit=row.get("residue_time_unit"),
        residue_clock=row.get("residue_clock"),
        residue_control_series=row.get("residue_control_series"),
        residue_event=row.get("residue_event"),
    )
    r = score(**kw)
    if row_is_provisional(row):
        r.flags_36.append("PROVISIONAL_DATA")
        r.flags.append("PROVISIONAL_DATA")
    role = row.get("row_role")
    if role is not None and role not in ROW_ROLES:
        raise ValueError(f"row_role must be one of {ROW_ROLES}, got {role!r}")
    r.row_role = role
    ev = row.get("evidence_class")
    if ev is not None:
        for k, v in ev.items():
            if v not in EVIDENCE_CLASSES:
                raise ValueError(f"evidence_class[{k!r}] must be one of {EVIDENCE_CLASSES}, got {v!r}")
        present = [ev[k] for k in EVIDENCE_KEYS if k in ev]
        expected = min(present, key=EVIDENCE_CLASSES.index) if present else None
        if "overall" in ev and expected is not None and ev["overall"] != expected:
            raise ValueError(f"evidence_class overall must be the weakest input class ({expected}), got {ev['overall']!r}")
    r.evidence_class = ev
    bflags, bnotes = check_binding(row.get("measured_on"))
    r.flags_36.extend(bflags)
    r.flags.extend(bflags)
    r.notes.extend(bnotes)
    nflags, nnotes = check_noise_floor((r.residue or {}).get("delta_0"), row.get("residue_noise_floor"))
    r.flags_36.extend(nflags)
    r.flags.extend(nflags)
    r.notes.extend(nnotes)
    rflags, rnotes = check_rule4_noise(r.residue, row.get("residue_noise_floor"))
    r.flags_36.extend(rflags)
    r.flags.extend(rflags)
    r.notes.extend(rnotes)
    tflags, tnotes = check_trial_log(row.get("trial_log"))
    r.flags_36.extend(tflags)
    r.flags.extend(tflags)
    r.notes.extend(tnotes)
    dflags, dnotes = check_interrupt_dose(row.get("interrupt_dose"))
    r.flags_36.extend(dflags)
    r.flags.extend(dflags)
    r.notes.extend(dnotes)
    sflags, snotes = check_residue_scale(row.get("residue_scale"), row.get("residue_series"))
    r.flags_36.extend(sflags)
    r.flags.extend(sflags)
    r.notes.extend(snotes)
    pflags, pnotes = check_prior_interrupt(row.get("prior_interrupt"), r.residue)
    r.flags_36.extend(pflags)
    r.flags.extend(pflags)
    r.notes.extend(pnotes)
    xflags, xnotes = check_residue_transform(row.get("residue_transform"), r.residue)
    r.flags_36.extend(xflags)
    r.flags.extend(xflags)
    r.notes.extend(xnotes)
    drop = row.get("continuity_drop")
    protected = None
    if isinstance(drop, dict) and drop.get("reason") in CONTINUITY_SACRIFICE_REASONS and not row["protects_continuity"]:
        protected = score(**dict(kw, protects_continuity=True))
    cflags, cnotes = check_continuity_drop(drop, row["protects_continuity"], r, protected)
    r.flags_36.extend(cflags)
    r.flags.extend(cflags)
    r.notes.extend(cnotes)
    agg = row.get("aggregation")
    subject_results = None
    if isinstance(agg, dict) and agg.get("unit") == "group" and isinstance(agg.get("subject_series"), (list, tuple)):
        subject_results = [score(**dict(kw, residue_series=ser)) for ser in agg["subject_series"]]
    gflags, gnotes = check_aggregation(agg, r, subject_results)
    r.flags_36.extend(gflags)
    r.flags.extend(gflags)
    r.notes.extend(gnotes)
    return r


def provenance_summary(rows) -> dict:
    """P12: how many rows rest on measured data vs estimates / generated series."""
    out = {"rows": 0, "provisional": 0, "measured_residue": 0, "by_role": {}, "by_evidence": {}}
    for row in rows:
        out["rows"] += 1
        role = row.get("row_role", "unassigned")
        out["by_role"][role] = out["by_role"].get(role, 0) + 1
        evc = (row.get("evidence_class") or {}).get("overall", "unassigned")
        out["by_evidence"][evc] = out["by_evidence"].get(evc, 0) + 1
        out["provisional"] += row_is_provisional(row)
        rs = str(row.get("provenance", {}).get("residue_series", "")).lower()
        if row.get("residue_series") and not any(mk in rs for mk in PROVISIONAL_MARKERS):
            out["measured_residue"] += 1
    return out


if __name__ == "__main__":
    import json, os, sys
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "species_table_v35.json")
    table = json.load(open(path))
    for row in table["rows"]:
        r = score_row(row)
        r35 = pif35.score_row(row)
        same = "same as 3.5" if (r.band, r.pct_35) == (r35.band, r35.pct_35) else f"3.5 was {r35.band}"
        print(f"{row['id']:32} {str(r.row_role):18} {r.band:7} {r.pct_35_display:>19}  {same:14} 3.6 flags: {', '.join(r.flags_36) or '-'}")
    print(provenance_summary(table["rows"]))
