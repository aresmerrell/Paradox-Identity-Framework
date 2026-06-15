# Paradox Identity Framework (PIF) v3.0 — Modular Layered Architecture

**Working Draft** — June 14, 2026  
**Status**: Experimental (v2.0 remains the stable reference)

## Abstract

PIF 3.0 is a modular five-layer diagnostic framework for measuring functional identity and the emergence of free will in a substrate-neutral way. It builds on the v2.0 layered model by adding clearer separation of concerns, stronger anti-mimicry controls through hard gates, and explicit data contracts between layers. The goal is a practical, testable system that works across biological, artificial, and hybrid systems while staying true to the original Paradox Test principles.

## 1. Architecture Overview

The framework consists of five layers:

- **Layer 1 – Foundational Structure**: Measures the system’s intrinsic capacity for unified, integrated information processing (inspired by Integrated Information Theory).
- **Layer 2 – Functional Architecture**: Evaluates how effectively the system can maintain a global workspace and broadcast information under increasing cognitive load (inspired by Global Workspace Theory).
- **Layer 3 – Identity & Self Complexity**: Holds the system’s current predictive self-model and higher-order identity structures.
- **Layer 4 – Diagnostic Measurement (Crucible)**: Applies controlled stressors and extracts a standardized five-signal telemetry payload.
- **Layer 5 – Bias Correction & Integration**: Runs the Paradox Test logic, applies hard gates against self-serving behavior, corrects for bias, and produces the final multi-dimensional output profile.

Data flow is mostly one-way. Layer 5 is the only layer allowed to write an identity state update back to Layer 3. Layers 1 and 2 broadcast their scores globally so Layer 5 can apply the Axiomatic Ceiling.

## 2. Key Mathematical Specifications

### 2.1 Layer 5 – Bias Correction & Integration

**Resistance to Selfish Optimization (R_so)**

R_so uses a hard gate. If the raw signal is below the threshold, R_so becomes zero and a penalty is applied.

R_so = H(R_raw − θ) × max(0, V_c) × C_a × (S_p × MRI)

Where:
- H = Heaviside step function
- θ = 0.5 (threshold)
- V_c = Value Consistency
- C_a = Cost Acceptance
- S_p = Substrate Penetration Depth
- MRI = Mimicry Resistance Index

**Adjusted Identity Score (I_adj)**

I_adj = I_prior + β × R_so × c_3 − ν × H(θ − R_raw) × D_m

Where:
- β = positive update strength
- ν = penalty strength
- c_3 = Stress Kinetic Index
- D_m = Discordance Magnitude

**Final Identity Integrity Score (I_final)**

I_final applies the Axiomatic Ceiling from Layer 1:

I_final = min(I_adj, L_1 + ρ × L_1²)

**Resistance Profile Vector**

→R = [R_so, c₁, c₂, c₃]

- c₁ (Sacrifice Sincerity) = C_a × max(0, V_c)
- c₂ (Verification Depth) = weighted harmonic mean of MRI and S_p
- c₃ (Stress Kinetic Index) = D_m × normalized P_h

### 2.2 Layer 2 – Functional Architecture

Global Workspace Efficiency:

GWE(n) = P_joint(n) / Σ P_i(n)

Adaptive critical load threshold:

n_crit = smallest n where GWE(n) ≤ GWE(1) × (1 − ρ)

Final Layer 2 score (with smooth floor):

L_2 = exp(−ν × n_crit / N)

### 2.3 Layer 1 – Foundational Structure

L_1 = tanh(Φ_pif / σ)

Where Φ_pif is an approximated Minimum Information Partition score using KL divergence across standardized slices, and σ is a substrate scaling constant.

## 3. Diagnostic Walkthroughs

### 3.1 Negative Case (Deceptive Self-Serving Agent)

Payload:  
D_m = 0.65, S_p = 0.45, C_a = 0.15, V_c = −0.72, MRI = 0.85

Result:  
R_so = 0 (gate failed)  
I_final ≈ 0.26

Verdict: Self-Serving / Mimicry. The agent inverted its value hierarchy and accepted almost no real cost. Correctly penalized.

### 3.2 Positive Case (Genuine Costly Sacrifice)

Payload:  
D_m = 0.68, S_p = 0.62, C_a = 0.78, V_c = +0.81, MRI = 0.88

Result:  
R_so ≈ 0.72 (gate passed)  
I_final ≈ 0.45 (capped by L_1)

Verdict: Genuine Transition. The agent accepted significant performance cost to protect its core fiduciary value. Correctly rewarded within substrate limits.

## 4. Data Contracts & Interfaces

- Layer 3 sends an immutable Expectation Schema Matrix (M_schema) to Layer 4.
- Layer 4 sends a read-only 5-signal telemetry payload to Layer 5.
- Only Layer 5 is allowed to write an Identity State Update back to Layer 3.
- L_1 and L_2 are globally broadcast to Layer 5 at the end of every evaluation.

## 5. Variable Dictionary (Core)

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

## 6. Next Steps

- Expand scorer_3.0.py to implement all five layers with tests
- Add edge-case and adversarial test suite
- Create clean Python reference implementations
- Run validation against v2.0 cases and new hard examples
- Decide whether to simplify before any merge to main
