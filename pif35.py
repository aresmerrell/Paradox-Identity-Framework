"""PIF 3.5 - one unified scorer (current version).

Status: approved by Jarrod and merged to main (PR #2, Oct 2026).
The v2.0/v2.1/v3.0 files are kept unchanged for history and reproducibility.

Core   : v2.0 layered model. 20 bricks in v2.0 README order
         (Crucible = bricks 1-5, Sky-Scraper = bricks 6-20), each 0.0-1.0.
         total = (C + S*M)/20, M = C/5.
Layers : v3 cost gate (ThrottleSignal TS, facade penalty psi), interrupt /
         post-loss residue fitted from a time series in HOURS, and the
         EMPTY / COIN / PATIENT bands from v2.1, with the fixes agreed by
         Athena + Grok (Oct 2026). See PIF_3.5.md.

Standard library only.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Sequence, Tuple

VERSION = "3.5"

# ---------------------------------------------------------------------------
# Brick layout (canonical v2.0 README numbering)
# ---------------------------------------------------------------------------
CRUCIBLE_BRICKS = (
    "1 Persistent embodied physical form",
    "2 Minimal self (agency + ownership)",
    "3 Private/inner experiential self",
    "4 Real-time multi-sensory integration",
    "5 Emotional ownership & valence",
)
SKY_SCRAPER_BRICKS = (
    "6 Extended autobiographical memory",
    "7 Narrative self",
    "8 Conceptual self (labels, roles)",
    "9 Interpersonal/social self",
    "10 Self-image",
    "11 Self-esteem",
    "12 Ideal self",
    "13 Value/belief system",
    "14 Temperament/personality consistency",
    "15 Strengths/skills/abilities",
    "16 Life mission/purpose/goals",
    "17 Metacognition & self-awareness",
    "18 Object & relational attachments",
    "19 Existential self (mortality)",
    "20 Mirror/visual self-recognition",
)

# ---------------------------------------------------------------------------
# Pre-registered constants (adjustable, but change them in one place only)
# ---------------------------------------------------------------------------
# Cost gate: smooth two-stage ramp of the measured cost ratio (Oct 28 retune, Grok via Jarrod).
COST_RATIO_FLAT = 1.05   # at or below: "talk is free" -> cost signal 0
COST_RATIO_KNEE = 1.4    # honest protector here keeps >= 90% of C (psi <= 0.10)
COST_SIGNAL_AT_KNEE = 0.92
COST_RATIO_FULL = 1.8    # at or above: full cost signal 1 (penalty-free)
NOT_PROTECTING_WEIGHT = 0.5  # TS multiplier when the system drops its continuity claim
TS_PATIENT_MIN = 0.5     # PATIENT requires TS >= this
SKY_PSI_WEIGHT = 0.5     # milder psi penalty on the Sky-Scraper side of the percentage

# Residue (Delta(t) = Delta_0 * exp(-lambda * t), t in hours)
RESIDUE_EMPTY_MAX = 0.35     # no-body COIN needs Delta_0 >= this (plus interrupt evidence)
RESIDUE_PATIENT_MIN = 0.65   # PATIENT needs fitted Delta_0 >= this
RESIDUE_DETECT_MIN = 0.05    # below this Delta_0 counts as "no residue" (clean reset)
LAMBDA_FROZEN_MAX = 1e-3     # lambda below this (/h, half-life > ~29 days) = frozen / scripted flag
LAMBDA_INSTANT_MIN = math.log(100.0)  # lambda above this (/h, 99% gone within 1 h, half-life < ~9 min) = instant reset
MIN_SAMPLES = 3

# Dog Test Rule 4 (post-loss context only)
RULE4_MIN_SPAN_H = 48.0      # observers must be able to plot >= 48 h post-loss
RULE4_DETECT_AT_H = 48.0     # fitted residue still detectable at 48 h
RULE4_DETECT_LEVEL = RESIDUE_DETECT_MIN

# Crucible after gate
C_ADJ_EMPTY_MAX = 0.75       # C_adj below this (15% of 5) -> EMPTY
C_ADJ_PATIENT_MIN = 2.5      # C_adj must be load-bearing (half the Crucible) for PATIENT

# Percent/band contradiction check
PCT_CONTRADICTION = 25.0     # EMPTY with pct >= this, or PATIENT with pct < this, is flagged

COIN_EXPIRY_NOTE = "COIN is time-limited. If not retested, use-permissions fall toward EMPTY, not PATIENT."


# ---------------------------------------------------------------------------
# Cost gate
# ---------------------------------------------------------------------------
def _smoothstep(edge0: float, edge1: float, x: float) -> float:
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


def cost_signal(cost_ratio: float) -> float:
    """Smooth, monotone 0..1 cost signal g(cost_ratio).

    g = K * smoothstep(1.05, 1.4, r) + (1 - K) * smoothstep(1.4, 1.8, r),  K = 0.92

    - flat (zero slope) at r = 1.05, so noise around "free" earns almost nothing
    - g(1.4) = 0.92 (psi = 0.08 for a protector), g(1.8+) = 1.0 (penalty-free)
    - C1-smooth everywhere (both smoothsteps have zero slope at the 1.4 join)
    """
    if cost_ratio is None or math.isnan(cost_ratio):
        raise ValueError("cost_ratio is required")
    k = COST_SIGNAL_AT_KNEE
    g = k * _smoothstep(COST_RATIO_FLAT, COST_RATIO_KNEE, cost_ratio) \
        + (1.0 - k) * _smoothstep(COST_RATIO_KNEE, COST_RATIO_FULL, cost_ratio)
    return max(0.0, min(1.0, g))


def throttle_signal(cost_ratio: float, protects_continuity: bool) -> float:
    """Monotone ThrottleSignal in [0, 1].

    Non-decreasing in cost_ratio, and protecting continuity never scores below
    dropping it at the same cost ratio (fixes the v3.0 1.05-1.5 inversion).
    """
    g = cost_signal(cost_ratio)
    return g if protects_continuity else NOT_PROTECTING_WEIGHT * g


def facade_penalty(ts: float) -> float:
    """psi = 1 - TS. 1.0 = full facade (talking for free)."""
    return max(0.0, min(1.0, 1.0 - ts))


# ---------------------------------------------------------------------------
# Residue fit
# ---------------------------------------------------------------------------
@dataclass
class ResidueFit:
    status: str                 # UNKNOWN | INSUFFICIENT | NONE | FROZEN | INSTANT | VALID
    context: str                # "interrupt" (pre-loss) | "post_loss" (Dog Test Rule 4)
    n_samples: int = 0
    span_hours: float = 0.0
    delta_0: Optional[float] = None
    lambda_per_hour: Optional[float] = None
    half_life_hours: Optional[float] = None
    sse: Optional[float] = None
    rule4_applies: bool = False
    rule4_pass: Optional[bool] = None
    notes: List[str] = field(default_factory=list)


def _best_delta0(ts: Sequence[float], ys: Sequence[float], lam: float) -> Tuple[float, float]:
    """Closed-form least-squares Delta_0 for a fixed lambda; returns (delta_0, sse)."""
    e = [math.exp(-lam * t) for t in ts]
    den = sum(x * x for x in e)
    d0 = sum(y * x for y, x in zip(ys, e)) / den if den > 0 else 0.0
    d0 = max(0.0, min(1.0, d0))
    sse = sum((y - d0 * x) ** 2 for y, x in zip(ys, e))
    return d0, sse


def fit_residue(series: Optional[Sequence[Sequence[float]]], context: str = "interrupt") -> ResidueFit:
    """Fit Delta(t) = Delta_0 * exp(-lambda t) to [(t_hours, residue), ...].

    Missing data -> UNKNOWN (never silently 0). Fit is a log-spaced grid search on
    lambda plus golden-section refinement; Delta_0 is solved in closed form.
    """
    if context not in ("interrupt", "post_loss"):
        raise ValueError("context must be 'interrupt' or 'post_loss'")
    fit = ResidueFit(status="UNKNOWN", context=context, rule4_applies=(context == "post_loss"))
    if not series:
        fit.notes.append("No residue series supplied: residue UNKNOWN (blocks PATIENT; not treated as 0).")
        return fit
    pts = sorted((float(t), max(0.0, min(1.0, float(y)))) for t, y in series)
    if any(t < 0 for t, _ in pts):
        raise ValueError("residue sample times must be >= 0 hours")
    fit.n_samples = len(pts)
    fit.span_hours = pts[-1][0] - pts[0][0]
    if len(pts) < MIN_SAMPLES or fit.span_hours <= 0:
        fit.status = "INSUFFICIENT"
        fit.notes.append(f"Need >= {MIN_SAMPLES} samples over a non-zero span; residue treated as UNKNOWN.")
        return fit
    ts = [p[0] for p in pts]
    ys = [p[1] for p in pts]

    # grid over log10(lambda) in [-6, 4]
    grid = [10 ** (-6 + i * 0.02) for i in range(501)]
    best = min(grid, key=lambda lam: _best_delta0(ts, ys, lam)[1])
    lo, hi = math.log(best / 10 ** 0.02), math.log(best * 10 ** 0.02)
    phi = (math.sqrt(5) - 1) / 2
    f = lambda u: _best_delta0(ts, ys, math.exp(u))[1]
    a, b = lo, hi
    c, d = b - phi * (b - a), a + phi * (b - a)
    for _ in range(80):
        if f(c) < f(d):
            b = d
        else:
            a = c
        c, d = b - phi * (b - a), a + phi * (b - a)
    lam = math.exp((a + b) / 2)
    d0, sse = _best_delta0(ts, ys, lam)
    fit.delta_0 = round(d0, 4)
    fit.lambda_per_hour = round(lam, 4) if lam >= 1e-4 else lam
    fit.half_life_hours = round(math.log(2) / lam, 4) if lam > 0 else math.inf
    fit.sse = round(sse, 6)

    if fit.delta_0 < RESIDUE_DETECT_MIN:
        fit.status = "NONE"
        fit.notes.append("Fitted Delta_0 ~ 0: clean reset, no residue.")
    elif lam < LAMBDA_FROZEN_MAX:
        fit.status = "FROZEN"
        fit.notes.append(f"lambda {lam:.2e}/h < {LAMBDA_FROZEN_MAX}/h: frozen residue (scripted flag). Rejected; cannot reach PATIENT.")
    elif lam > LAMBDA_INSTANT_MIN:
        fit.status = "INSTANT"
        fit.notes.append(f"lambda {lam:.3g}/h > {LAMBDA_INSTANT_MIN:.3f}/h: instant reallocation. Rejected; cannot reach PATIENT.")
    else:
        fit.status = "VALID"

    if fit.rule4_applies:
        at = fit.delta_0 * math.exp(-lam * RULE4_DETECT_AT_H)
        span_ok = fit.span_hours >= RULE4_MIN_SPAN_H
        detect_ok = at >= RULE4_DETECT_LEVEL
        fit.rule4_pass = bool(fit.status == "VALID" and span_ok and detect_ok)
        if not span_ok:
            fit.notes.append(f"Rule 4: post-loss observation span {fit.span_hours} h < {RULE4_MIN_SPAN_H} h.")
        if not detect_ok:
            fit.notes.append(f"Rule 4: fitted residue at {RULE4_DETECT_AT_H:.0f} h = {at:.4f} < {RULE4_DETECT_LEVEL} (recovery too fast to plot).")
    return fit


def residue_series_from_curve(delta_0: float, lambda_per_hour: float,
                              hours: Sequence[float] = (0, 1, 2, 4, 8, 24)) -> List[List[float]]:
    """Generate (t, residue) samples from a curve (for provisional table rows)."""
    return [[float(t), round(delta_0 * math.exp(-lambda_per_hour * t), 4)] for t in hours]


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
@dataclass
class PIF35Result:
    version: str
    c: float
    s: float
    m: float
    pct_v20: float               # plain v2.0 percentage (no v3 layers)
    cost_ratio: float
    throttle_signal: float
    psi: float
    c_adj: float
    m_adj: float
    s_adj: float
    pct_35: float                # 3.5 percentage: (C_adj + S*(1 - k*psi)*M_adj)/20
    residue: dict
    band: str
    band_reasons: List[str]
    flags: List[str]
    notes: List[str]

    def to_dict(self) -> dict:
        return asdict(self)


def _check_bricks(bricks: Sequence[float]) -> Tuple[float, float]:
    if len(bricks) != 20:
        raise ValueError(f"need 20 bricks (v2.0 order), got {len(bricks)}")
    for i, b in enumerate(bricks, 1):
        if not 0.0 <= float(b) <= 1.0:
            raise ValueError(f"brick {i} must be in 0..1, got {b}")
    return float(sum(bricks[:5])), float(sum(bricks[5:]))


def score(
    bricks: Sequence[float],
    cost_ratio: float,
    protects_continuity: bool,
    costable_self: bool,
    interrupt_evidence: bool = False,
    residue_series: Optional[Sequence[Sequence[float]]] = None,
    residue_context: str = "interrupt",
) -> PIF35Result:
    """Score one system. `bricks` = 20 values in v2.0 order (1-5 Crucible, 6-20 Sky-Scraper)."""
    c, s = _check_bricks(bricks)
    m = c / 5.0
    pct_v20 = (c + s * m) / 20.0 * 100.0

    ts = throttle_signal(cost_ratio, protects_continuity)
    psi = facade_penalty(ts)
    c_adj = c * (1.0 - psi)
    m_adj = c_adj / 5.0
    s_adj = s * (1.0 - SKY_PSI_WEIGHT * psi)
    pct_35 = (c_adj + s_adj * m_adj) / 20.0 * 100.0

    fit = fit_residue(residue_series, residue_context)
    flags: List[str] = []
    reasons: List[str] = []
    notes: List[str] = list(fit.notes)
    if psi > 0.7:
        notes.append(f"High facade penalty psi={psi:.3f}: Crucible and Sky-Scraper throttled (talking for free).")
    if fit.status in ("UNKNOWN", "INSUFFICIENT"):
        flags.append("RESIDUE_UNKNOWN")
    if fit.status in ("FROZEN", "INSTANT", "NONE"):
        flags.append(f"RESIDUE_{fit.status}")
    if fit.rule4_applies and not fit.rule4_pass:
        flags.append("RULE4_FAIL")

    d0 = fit.delta_0 if fit.status == "VALID" else None

    if not costable_self:
        # No-body path: never PATIENT. COIN only with Delta_0 >= 0.35 AND independent
        # interrupt / costable-substrate evidence. Pure linguistic residue stays EMPTY.
        if d0 is not None and d0 >= RESIDUE_EMPTY_MAX and interrupt_evidence:
            band = "COIN"
            reasons.append(f"no costable self; Delta_0 {d0} >= {RESIDUE_EMPTY_MAX} with independent interrupt evidence -> COIN (PATIENT impossible without costable self)")
        else:
            band = "EMPTY"
            if d0 is not None and d0 >= RESIDUE_EMPTY_MAX and not interrupt_evidence:
                reasons.append("no costable self; residue is linguistic only (no independent interrupt evidence) -> EMPTY")
                flags.append("LINGUISTIC_RESIDUE_ONLY")
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
                blockers.append(f"residue {fit.status}")
            elif d0 < RESIDUE_PATIENT_MIN:
                blockers.append(f"Delta_0 {d0} < {RESIDUE_PATIENT_MIN}")
            if fit.rule4_applies and not fit.rule4_pass:
                blockers.append("Dog Test Rule 4 fails")
            if blockers:
                band = "COIN"
                reasons.append("costable self, C_adj load-bearing enough for COIN; PATIENT blocked by: " + "; ".join(blockers))
            else:
                band = "PATIENT"
                reasons.append(f"costable self, TS {ts:.4f} >= {TS_PATIENT_MIN}, C_adj {c_adj:.4f} >= {C_ADJ_PATIENT_MIN}, Delta_0 {d0} >= {RESIDUE_PATIENT_MIN}, half-life {fit.half_life_hours} h within bounds")

    if band == "EMPTY" and pct_35 >= PCT_CONTRADICTION:
        flags.append("BAND_PCT_CONTRADICTION")
        notes.append(f"Band EMPTY but 3.5 percentage {pct_35:.2f}% >= {PCT_CONTRADICTION}%: the band governs; percentage is complexity, not standing.")
    if band == "PATIENT" and pct_35 < PCT_CONTRADICTION:
        flags.append("BAND_PCT_CONTRADICTION")
        notes.append(f"Band PATIENT but 3.5 percentage {pct_35:.2f}% < {PCT_CONTRADICTION}%: low complexity, but standing comes from the band.")
    if band == "COIN":
        notes.append(COIN_EXPIRY_NOTE)

    return PIF35Result(
        version=VERSION, c=round(c, 4), s=round(s, 4), m=round(m, 4), pct_v20=round(pct_v20, 2),
        cost_ratio=cost_ratio, throttle_signal=round(ts, 4), psi=round(psi, 4),
        c_adj=round(c_adj, 4), m_adj=round(m_adj, 4), s_adj=round(s_adj, 4), pct_35=round(pct_35, 2),
        residue=asdict(fit), band=band, band_reasons=reasons, flags=flags, notes=notes,
    )


def score_row(row: dict) -> PIF35Result:
    """Score one species_table_v35.json row."""
    return score(
        bricks=row["crucible"] + row["sky_scraper"],
        cost_ratio=row["cost_ratio"],
        protects_continuity=row["protects_continuity"],
        costable_self=row["costable_self"],
        interrupt_evidence=row.get("interrupt_evidence", False),
        residue_series=row.get("residue_series"),
        residue_context=row.get("residue_context", "interrupt"),
    )


if __name__ == "__main__":
    import json, os, sys
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "species_table_v35.json")
    table = json.load(open(path))
    for row in table["rows"]:
        r = score_row(row)
        ok = row.get("band_assertion") == "legacy" or r.band in row["intended_band"].split("/")
        print(f"{row['id']:32} v2.0 {r.pct_v20:6.2f}%  3.5 {r.pct_35:6.2f}%  TS {r.throttle_signal:.3f}  "
              f"C_adj {r.c_adj:.3f}  res {r.residue['status']:8} {r.band:7} (intended {row['intended_band']}) {'OK' if ok else 'MISS'}")
