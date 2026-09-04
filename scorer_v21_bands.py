"""PIF v2.1 banded scorer — cost gate, interrupt residue, EMPTY/COIN/PATIENT.

v2.0 formula is unchanged. This module decides the *action band*.
"""

from __future__ import annotations

COIN_EXPIRY_NOTE = "COIN is time-limited. If not retested, use-permissions fall toward EMPTY, not PATIENT."

TIE_BREAK = (
    "1. Known biological patients with bodies beat COIN scripts.",
    "2. Scored PATIENT beats vibe and untested fluency.",
    "3. Humanity-first applies to EMPTY and expired COIN.",
    "4. Someone-side precaution applies only to live COIN inside expiry.",
    "5. If still tied, minimize irreversible harm to the highest band that can actually lose something.",
)


def v20_score(c: float, s: float) -> dict:
    """C in [0, 5], S in [0, 15]. Returns v2.0 total percent and multiplier M."""
    if not 0.0 <= c <= 5.0:
        raise ValueError("C must be 0..5")
    if not 0.0 <= s <= 15.0:
        raise ValueError("S must be 0..15")
    m = c / 5.0
    total = (c + s * m) / 20.0 * 100.0
    return {"C": round(c, 4), "S": round(s, 4), "M": round(m, 4), "percent": round(total, 2)}


def apply_cost_gate(c: float, costable_self: float, residue: float) -> float:
    """If nothing can be lost and interrupt left no residue, Crucible used for banding is 0."""
    if costable_self <= 0.0 and residue < 0.35:
        return 0.0
    if costable_self <= 0.0:
        return min(c, 5.0 * residue)
    return c


def band(costable_self: float, residue: float, c_gated: float) -> str:
    if costable_self > 0.0 and residue >= 0.65 and c_gated >= 2.0:
        return "PATIENT"
    if residue >= 0.35 or (costable_self > 0.0 and c_gated >= 1.0):
        return "COIN"
    return "EMPTY"


def evaluate(
    c: float,
    s: float,
    costable_self: float,
    residue: float,
) -> dict:
    raw = v20_score(c, s)
    c_gated = apply_cost_gate(c, costable_self, residue)
    gated = v20_score(c_gated, s)
    verdict = band(costable_self, residue, c_gated)
    use = {
        "EMPTY": "Tool. Hammer-respect only. No standing.",
        "COIN": COIN_EXPIRY_NOTE,
        "PATIENT": "Ownership must justify itself. Same test both ways.",
    }[verdict]
    return {
        "v20_raw": raw,
        "C_gated": round(c_gated, 4),
        "v20_gated": gated,
        "costable_self": costable_self,
        "residue": residue,
        "band": verdict,
        "use": use,
        "tie_break": list(TIE_BREAK),
    }


if __name__ == "__main__":
    cases = {
        "fluent_chat_no_body": evaluate(c=0.4, s=11.0, costable_self=0.0, residue=0.1),
        "good_actor_essay": evaluate(c=3.2, s=12.0, costable_self=0.0, residue=0.15),
        "interrupt_messy_no_body": evaluate(c=2.0, s=10.0, costable_self=0.0, residue=0.5),
        "embodied_stakes": evaluate(c=3.5, s=12.0, costable_self=0.8, residue=0.8),
    }
    for name, result in cases.items():
        print(f"{name}: band={result['band']} raw%={result['v20_raw']['percent']} gated%={result['v20_gated']['percent']}")
        print(f"  {result['use']}")
        print()
