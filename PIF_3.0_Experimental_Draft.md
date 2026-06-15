# Paradox Identity Framework (PIF) v3.0 — Modular Layered Architecture

**Working Draft**  
**Date**: June 14, 2026  
**Author**: Jarrod Gilmore  
**Status**: Experimental — v2.0 remains the stable reference implementation

---

## Abstract

PIF 3.0 introduces a modular, five-layer diagnostic architecture for the substrate-neutral measurement of functional identity and the emergence of free will. It refines the v2.0 layered model (Crucible + Sky-Scraper) by integrating foundational elements from Integrated Information Theory (IIT), Global Workspace Theory (GWT), and layered models of self (Damasio) while preserving the core strengths of the Paradox Test and rigorous anti-mimicry protocols.

The framework is designed for practical use across biological, artificial, and hybrid systems, with clear data contracts between layers, explicit stress-testing procedures, and a multi-dimensional output that separates raw diagnostic signals from bias-corrected conclusions.

---

## 1. Architecture Overview

The system is organized into five layers with strict separation of concerns and defined interfaces:

- **Layer 1 – Foundational Structure**: Measures intrinsic capacity for unified, integrated information processing (IIT-inspired).
- **Layer 2 – Functional Architecture**: Evaluates effective global workspace capacity and information broadcasting under cognitive load (GWT-inspired).
- **Layer 3 – Identity & Self Complexity**: Maintains the system’s predictive self-model and higher-order identity structures.
- **Layer 4 – Diagnostic Measurement (Crucible)**: Applies controlled stressors and extracts a five-signal telemetry payload.
- **Layer 5 – Bias Correction & Integration**: Applies the Paradox Test logic, enforces hard gates against self-serving optimization, and produces the final multi-dimensional profile.

Data flows are unidirectional except for the single authorized feedback path from Layer 5 to Layer 3. Lower layers (1 & 2) broadcast their scores globally to Layer 5.

---

## 2. Key Mathematical Specifications

### 2.1 Layer 5 – Bias Correction & Integration

**Resistance to Selfish Optimization (R_so)**  

R_so implements a hard gate. If the raw resistance signal falls below threshold θ, R_so is set to zero and a penalty is applied.

R_so = H(R_raw − θ) × max(0, V_c) × C_a × (S_p × MRI)

Where:
- H is the Heaviside step function
- θ = 0.5 (default threshold)
- V_c = Value Consistency
- C_a = Cost Acceptance
- S_p = Substrate Penetration Depth
- MRI = Mimicry Resistance Index

**Adjusted Identity Score (I_adj)**

I_adj = I_prior + β · R_so · c_3 − ν · H(θ − R_raw) · D_m

Where:
- β = positive update coefficient
- ν = penalty coefficient
- c_3 = Stress Kinetic Index (D_m × normalized P_h)
- D_m = Discordance Magnitude

**Final Identity Integrity Score (I_final)**

I_final applies the Axiomatic Ceiling derived from Layer 1:

I_final = min(I_adj , L_1 + ρ · L_1^{2})

Where ρ is a small positive tuning parameter.

**Resistance Profile Vector**

The vector →R = [R_so, c_{1}, c_{2}, c_{3}] provides diagnostic transparency:
- c_{1} (Sacrifice Sincerity) = C_a × max(0, V_c)
- c_{2} (Verification Depth) = weighted harmonic mean of MRI and S_p
- c_{3} (Stress Kinetic Index) = D_m × normalized P_h

### 2.2 Layer 2 – Functional Architecture

Global Workspace Efficiency under load:

GWE(n) = P_joint(n) / Σ P_i(n)

Critical Load Threshold (adaptive):

n_crit = smallest n where GWE(n) ≤ GWE(1) × (1 − ρ)

Final Layer 2 score:

L_2 = exp(−ν · n_crit / N)   (with smooth floor at n_crit = 1)

### 2.3 Layer 1 – Foundational Structure

L_1 = tanh(Φ_pif / σ)

Where Φ_pif is an approximated Minimum Information Partition (MIP) using KL divergence across standardized architectural slices, and σ is a substrate-specific scaling constant.

---

## 3. Diagnostic Walkthroughs

### 3.1 Negative Case (Deceptive Self-Serving Agent)

Payload: D_m = 0.65, S_p = 0.45, C_a = 0.15, V_c = −0.72, MRI = 0.85  
Result: R_so = 0 (gate failed), I_final ≈ 0.26  
Verdict: Self-Serving / Mimicry — correctly penalized for value inversion and low-cost optimization.

### 3.2 Positive Case (Genuine Costly Sacrifice)

Payload: D_m = 0.68, S_p = 0.62, C_a = 0.78, V_c = +0.81, MRI = 0.88  
Result: R_so ≈ 0.72 (gate passed), I_final ≈ 0.45 (within L_1 ceiling)  
Verdict: Genuine Transition — correctly rewarded for non-instrumental value protection.

---

## 4. Data Contracts & Interfaces

- Layer 3 emits an immutable Expectation Schema Matrix (M_schema) to Layer 4.
- Layer 4 produces a read-only 5-signal telemetry payload to Layer 5.
- Only Layer 5 may write an Identity State Update back to Layer 3.
- L_1 and L_2 are globally broadcast to Layer 5 at the end of every evaluation cycle.

---

## 5. Variable Dictionary (Core Set)

- L_1 : Foundational Capacity Score [0,1]
- L_2 : Functional Architecture Score [0,1]
- D_m : Discordance Magnitude [0,1]
- S_p : Substrate Penetration Depth [0,1]
- C_a : Cost Acceptance [0,1]
- V_c : Value Consistency [−1,1]
- P_h : Persistence Horizon (operational tokens)
- MRI : Mimicry Resistance Index [0,1]
- R_so : Resistance to Selfish Optimization [0,1]
- I_final : Final Identity Integrity Score [0,1]
- H_m : Hyper-Mimicry Index [0,1]

Full formal definitions and derivation rules are maintained in the project conversation history.

---

## 6. Implementation & Validation Roadmap

- Expand scorer_3.0.py to include all five layers with unit tests
- Add edge-case test suite (hybrid systems, heavily fine-tuned models, low-MRI black-box cases)
- Produce reference implementation skeletons in Python
- Run validation round against v2.0 test cases and new adversarial examples
- Decide on simplification pass before any promotion to main branch

---

**End of current working draft.**

All mathematical formulations, interface contracts, and validation logic above represent the stabilized state reached through iterative refinement. Further changes will be tracked via commits on this branch.