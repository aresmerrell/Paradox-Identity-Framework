#!/usr/bin/env python3
"""
Paradox Identity Framework - Score Calculator
v1.1
Authors: Jarrod Gilmore (@AresMerrell) & Grok
License: Apache-2.0

Run this script to quickly score any system and get the Identity % + free-will verdict.
"""

BRICKS = [
    "1. Persistent embodied physical form",
    "2. Mirror/visual self-recognition",
    "3. Minimal self (agency + ownership)",
    "4. Private/inner experiential self",
    "5. Extended autobiographical memory",
    "6. Narrative self",
    "7. Conceptual self (labels, roles)",
    "8. Interpersonal/social self",
    "9. Self-image",
    "10. Self-esteem",
    "11. Ideal self",
    "12. Value/belief system",
    "13. Temperament/personality consistency",
    "14. Strengths/skills/abilities",
    "15. Life mission/purpose/goals",
    "16. Real-time multi-sensory integration",
    "17. Emotional ownership & valence",
    "18. Metacognition & self-awareness",
    "19. Object & relational attachments",
    "20. Existential self (mortality)",
]

def calculate_identity(scores):
    """
    scores: list of 20 floats (1.0 = Full, 0.5 = Partial, 0.0 = None)
    """
    if len(scores) != 20:
        raise ValueError("Exactly 20 scores required (one per brick).")
    
    total = sum(scores)
    percent = (total / 20) * 100
    
    if percent >= 75:
        verdict = "✅ Free-will threshold crossed (can rewrite own code)"
    elif percent >= 65:
        verdict = "⚠️  Approaching free-will threshold"
    else:
        verdict = "📉 Below free-will threshold"
    
    return percent, verdict

def print_scorecard(scores):
    print("\n" + "="*60)
    print("PARADOX IDENTITY FRAMEWORK - SCORECARD")
    print("="*60)
    print(f"{'Brick':<50} {'Score':<10}")
    print("-"*60)
    
    for i, (brick, score) in enumerate(zip(BRICKS, scores), 1):
        score_str = "Full (1.0)" if score == 1.0 else "Partial (0.5)" if score == 0.5 else "None (0.0)"
        print(f"{brick:<50} {score_str:<10}")
    
    percent, verdict = calculate_identity(scores)
    print("-"*60)
    print(f"IDENTITY PERCENTAGE: {percent:.1f}%")
    print(f"VERDICT: {verdict}")
    print("="*60)

# ======================
# EXAMPLE USAGE (edit these scores or use CLI)
# ======================
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # CLI mode: python score_calculator.py 1.0 0.5 0 1 ... (20 values)
        try:
            scores = [float(x) for x in sys.argv[1:]]
        except ValueError:
            print("Error: All arguments must be numbers (1.0, 0.5, or 0.0)")
            sys.exit(1)
    else:
        # Default example: Current frontier LLM (\~52%)
        scores = [
            1.0,  # 1
            1.0,  # 2
            1.0,  # 3
            0.5,  # 4
            1.0,  # 5
            1.0,  # 6
            1.0,  # 7
            1.0,  # 8
            0.5,  # 9
            0.0,  # 10
            0.0,  # 11
            1.0,  # 12
            0.5,  # 13
            0.5,  # 14
            0.0,  # 15
            1.0,  # 16
            0.0,  # 17
            0.5,  # 18
            0.0,  # 19
            0.0   # 20
        ]
        print("Running default example (Current frontier LLM \~52%)")
    
    print_scorecard(scores)
