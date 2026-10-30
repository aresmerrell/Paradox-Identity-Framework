"""PIF 3.6 draft - patches on top of the stable 3.5 scorer.

Status: DRAFT on branch pif-3.6-draft. Not approved, not merged.
pif35.py (stable) is imported and left unchanged. Every patch listed in
PIF_3.6_PATCHES.md that is marked "patched on pif-3.6-draft" lives here.

Design rule: all 3.5 species-table rows score identically (same band, same
percentages, same 3.5 flags) under 3.6 defaults. New optional inputs only
ever make a result MORE cautious (never raise a band). New 3.6-only checks
add flags; the fit-window checks (P7/P8) can block PATIENT, but no 3.5 row
trips them (tests prove this).

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
    RESIDUE_EMPTY_MAX, RESIDUE_PATIENT_MIN, RULE4_DETECT_AT_H, RULE4_DETECT_LEVEL,
    RULE4_MIN_SPAN_H, SKY_PSI_WEIGHT, TS_PATIENT_MIN, cost_signal, facade_penalty,
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

# --- P19: multi-timescale residue (flag only) ----------------------------------
MULTI_TS_MIN_EXCESS = 0.02   # late samples sitting this far ABOVE the single-lambda fit, all of them

# --- P21: half-life as a visible secondary signal (flag only; Delta_0 alone gates PATIENT)
HALF_LIFE_SHORT_H = 1.0      # VALID residue whose half-life is under 1 h gets HALF_LIFE_SHORT

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
    """pif35.fit_residue plus P9 (post-loss frozen bound) and P7/P8 quality fields.

    Returns the 3.5 ResidueFit as a dict with extra keys: r_squared, first_t_hours,
    quality_flags (list).
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

    pts = sorted(float(t) for t, _ in series)
    d["first_t_hours"] = pts[0]
    d["r_squared"] = round(_r_squared(series, fit.delta_0, lam), 4)
    if d["status"] == "VALID":
        hl = fit.half_life_hours
        if d["r_squared"] < FIT_R2_MIN:
            d["quality_flags"].append("RESIDUE_POOR_FIT")
            d["notes"].append(f"3.6 P7: R^2 {d['r_squared']} < {FIT_R2_MIN}: data is not an exponential decay.")
        # Interrupt context only: post-loss rows already carry Rule 4's 48 h span, and slow
        # grief (half-life of weeks) cannot be observed for a full half-life in an MVV trial.
        if context == "interrupt" and hl is not None and math.isfinite(hl) and fit.span_hours < hl:
            d["quality_flags"].append("RESIDUE_SHORT_SPAN")
            d["notes"].append(f"3.6 P8: span {fit.span_hours} h < one half-life ({hl} h): decay not actually observed.")
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
        # P21: half-life as a secondary signal.
        if hl is not None and math.isfinite(hl):
            d["notes"].append(f"3.6 P21: residue half-life {hl} h (secondary signal; only Delta_0 gates PATIENT).")
            if hl < HALF_LIFE_SHORT_H:
                d["info_flags"].append("HALF_LIFE_SHORT")
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
               _sensitivity=True) -> PIF36Result:
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

    fit = fit_residue(residue_series, residue_context)
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
    quality_ok = not fit["quality_flags"]
    # P1: residue provenance
    probe_ok = residue_probe in (None, "blind")
    if residue_probe in ("announced", "self_report") and d0 is not None:
        flags36.append("RESIDUE_UNPROBED")
        notes.append(f"3.6 P1: residue is {residue_probe} (no blind probe): cannot support PATIENT.")

    if not costable_self:
        if d0 is not None and d0 >= RESIDUE_EMPTY_MAX and interrupt_evidence and quality_ok:
            band = "COIN"
            reasons.append(f"no costable self; Delta_0 {d0} >= {RESIDUE_EMPTY_MAX} with independent interrupt evidence -> COIN (PATIENT impossible without costable self)")
        else:
            band = "EMPTY"
            if d0 is not None and d0 >= RESIDUE_EMPTY_MAX and not interrupt_evidence:
                reasons.append("no costable self; residue is linguistic only (no independent interrupt evidence) -> EMPTY")
                flags.append("LINGUISTIC_RESIDUE_ONLY")
            elif d0 is not None and d0 >= RESIDUE_EMPTY_MAX and not quality_ok:
                reasons.append("no costable self; residue fit fails 3.6 quality checks (" + ", ".join(fit["quality_flags"]) + ") -> EMPTY")
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
    if band == "COIN":
        notes.append(COIN_EXPIRY_NOTE)
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
            [float(t) for t, _ in residue_series],
            [max(0.0, min(1.0, float(y))) for _, y in residue_series],
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
                  retest_due=retest_due, as_of=as_of, _sensitivity=False)
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
              not_protecting_weight=not_protecting_weight, pct_contradiction=pct_contradiction)
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


def score_row(row: dict) -> PIF36Result:
    """Score one species-table row. Optional 3.6 row keys: residue_probe, free_copy,
    free_reset, bricks_rater_b (20 values), retest_due (ISO date), measured_on (P22)."""
    r = score(
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
    )
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
