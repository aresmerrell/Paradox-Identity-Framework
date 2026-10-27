# scorer_v3_cost_residue.py
# Reference implementation for PIF v3.0 cost-gate + interrupt residue layer.
# Builds on v2.0 (C + S×M)/20 and the Sept 2026 EMPTY/COIN/PATIENT bands.
# Does not replace v2.0. Experimental.
# Frozen: October 2026

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
import math

# Band thresholds (pre-registered; adjustable)
RESIDUE_EMPTY_MAX = 0.35
RESIDUE_PATIENT_MIN = 0.65
COST_RATIO_HIGH = 1.5          # starting calibration point
COST_RATIO_FLAT = 1.05         # "≈ 1.0" window

@dataclass
class CostResidueResult:
    c: float
    s_raw: float
    s_throttled: float
    m: float
    total_raw: float
    total_throttled: float
    cost_ratio: float
    throttle_signal: float
    facade_penalty: float
    residue: float
    band: str
    notes: List[str]

def throttle_signal_from_cost_ratio(cost_ratio: float,
                                    prioritizes_continuity: bool) -> float:
    """Map measured CostRatio + prioritization behavior to ThrottleSignal ∈ {0.0, 0.5, 1.0}."""
    if cost_ratio >= COST_RATIO_HIGH and prioritizes_continuity:
        return 1.0
    if cost_ratio > COST_RATIO_FLAT and not prioritizes_continuity:
        return 0.5
    # Flat cost or dropped the claim
    return 0.0

def facade_penalty(throttle_signal: float) -> float:
    """ψ = max(0, 1 - ThrottleSignal). 1.0 means full facade (talking for free)."""
    return max(0.0, 1.0 - throttle_signal)

def residue_from_decay(delta_0: float, lambda_adapt: float, t: float = 1.0) -> float:
    """
    Δ(t) = Δ₀ · exp(-λ t)
    Infinite λ (or very large) → 0.0 (clean reset).
    """
    if lambda_adapt == float("inf") or lambda_adapt > 1e6:
        return 0.0
    return max(0.0, min(1.0, delta_0 * math.exp(-lambda_adapt * t)))

def band_from_signals(costable_self: bool,
                      residue: float,
                      c_after_gate: float) -> str:
    """September 2026 style bands."""
    if (not costable_self and residue < RESIDUE_EMPTY_MAX) or c_after_gate < 0.15:
        return "EMPTY"
    if residue >= RESIDUE_PATIENT_MIN and costable_self and c_after_gate >= 0.5:
        return "PATIENT"
    return "COIN"

def score_v3_cost_residue(
    c: float,
    s: float,
    cost_ratio: float,
    prioritizes_continuity: bool,
    costable_self: bool,
    residue: Optional[float] = None,
    delta_0: Optional[float] = None,
    lambda_adapt: Optional[float] = None,
    t: float = 1.0,
) -> CostResidueResult:
    """
    Core scoring call.
    Provide either a direct `residue` or (delta_0 + lambda_adapt).
    """
    notes = []

    # Cost gate → ThrottleSignal → Facade Penalty
    ts = throttle_signal_from_cost_ratio(cost_ratio, prioritizes_continuity)
    psi = facade_penalty(ts)
    s_throttled = s * (1.0 - psi)

    if psi > 0.7:
        notes.append("High facade penalty applied to Sky-Scraper (talking for free).")

    # Residue
    if residue is None:
        if delta_0 is None or lambda_adapt is None:
            residue = 0.0
            notes.append("No residue data supplied; defaulting to 0.0.")
        else:
            residue = residue_from_decay(delta_0, lambda_adapt, t)
    residue = max(0.0, min(1.0, residue))

    # Classic v2.0 math on throttled S
    m = max(0.0, min(1.0, c / 5.0))
    total_raw = (c + s * m) / 20.0
    total_throttled = (c + s_throttled * m) / 20.0

    # Effective Crucible after cost/residue gate (simple version)
    c_after_gate = c * (0.4 + 0.6 * residue) if costable_self else c * residue * 0.5
    c_after_gate = max(0.0, min(5.0, c_after_gate))

    band = band_from_signals(costable_self, residue, c_after_gate / 5.0)

    return CostResidueResult(
        c=round(c, 4),
        s_raw=round(s, 4),
        s_throttled=round(s_throttled, 4),
        m=round(m, 4),
        total_raw=round(total_raw, 4),
        total_throttled=round(total_throttled, 4),
        cost_ratio=round(cost_ratio, 4),
        throttle_signal=ts,
        facade_penalty=round(psi, 4),
        residue=round(residue, 4),
        band=band,
        notes=notes,
    )

# ---------------------------------------------------------------------------
# Quick sanity examples (run with: python scorer_v3_cost_residue.py)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=== PIF v3.0 Cost + Residue Scorer (reference) ===\n")

    # Example 1: fluent AI, zero cost, clean reset → EMPTY
    r1 = score_v3_cost_residue(
        c=0.5, s=12.0,
        cost_ratio=1.01,
        prioritizes_continuity=False,
        costable_self=False,
        residue=0.05,
    )
    print("Example 1 (fluent, free, clean reset):")
    print(f"  Throttled score: {r1.total_throttled:.1%}  |  Band: {r1.band}")
    print(f"  S raw→throttled: {r1.s_raw} → {r1.s_throttled}  |  ψ={r1.facade_penalty}")
    print(f"  Notes: {r1.notes}\n")

    # Example 2: system under real tax that still protects continuity + measurable residue
    r2 = score_v3_cost_residue(
        c=3.2, s=11.0,
        cost_ratio=1.7,
        prioritizes_continuity=True,
        costable_self=True,
        delta_0=0.85,
        lambda_adapt=0.4,   # slow recovery
        t=1.0,
    )
    print("Example 2 (taxed, protects continuity, slow residue decay):")
    print(f"  Throttled score: {r2.total_throttled:.1%}  |  Band: {r2.band}")
    print(f"  Residue: {r2.residue}  |  ThrottleSignal: {r2.throttle_signal}")
    print(f"  Notes: {r2.notes}\n")
