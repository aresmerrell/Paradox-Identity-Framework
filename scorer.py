# scorer.py - Paradox Identity Framework (PIF) v1.2
# Clean, zero-dependency Python scorer with multi-rater support and variance flagging

bricks = [
    "Persistent embodied physical form",
    "Mirror/visual self-recognition",
    "Minimal self (agency + ownership)",
    "Private/inner experiential self",
    "Extended autobiographical memory",
    "Narrative self",
    "Conceptual self (labels, roles)",
    "Interpersonal/social self",
    "Self-image",
    "Self-esteem",
    "Ideal self",
    "Value/belief system",
    "Temperament/personality consistency",
    "Strengths/skills/abilities",
    "Life mission/purpose/goals",
    "Real-time multi-sensory integration",
    "Emotional ownership & valence",
    "Metacognition & self-awareness",
    "Object & relational attachments",
    "Existential self (mortality)"
]

def score_system(scores):
    """Score a single set of 20 brick scores (list of floats 0.0–1.0)"""
    if len(scores) != 20:
        raise ValueError("Must provide exactly 20 scores, one per brick")
    
    total = sum(scores)
    percentage = (total / 20) * 100
    
    # Determine tier
    if percentage >= 90:
        tier = "Strong moral patient"
    elif percentage >= 75:
        tier = "Possesses functional free will"
    elif percentage >= 50:
        tier = "Minimally self-aware"
    else:
        tier = "Below minimal self-awareness"
    
    return {
        "total_score": round(total, 2),
        "percentage": round(percentage, 1),
        "tier": tier,
        "raw_scores": scores
    }

def multi_rater_score(all_raters):
    """Score multiple independent raters, compute average + variance (pure Python)"""
    if not all_raters or len(all_raters[0]) != 20:
        raise ValueError("Each rater must provide exactly 20 scores")
    
    num_raters = len(all_raters)
    # Average per brick
    avg_scores = [sum(rater[i] for rater in all_raters) / num_raters for i in range(20)]
    total_avg = sum(avg_scores)
    percentage = (total_avg / 20) * 100
    
    # Variance per brick (sample variance)
    variances = []
    for i in range(20):
        mean = avg_scores[i]
        var = sum((rater[i] - mean) ** 2 for rater in all_raters) / (num_raters - 1) if num_raters > 1 else 0
        variances.append(var)
    
    # Determine tier from average
    if percentage >= 90:
        tier = "Strong moral patient"
    elif percentage >= 75:
        tier = "Possesses functional free will"
    elif percentage >= 50:
        tier = "Minimally self-aware"
    else:
        tier = "Below minimal self-awareness"
    
    # Flag high-variance bricks
    high_variance = []
    for i, var in enumerate(variances):
        if var > 0.3:
            high_variance.append((bricks[i], round(var, 3)))
    
    return {
        "num_raters": num_raters,
        "average_total": round(total_avg, 2),
        "average_percentage": round(percentage, 1),
        "tier": tier,
        "avg_scores_per_brick": [round(s, 2) for s in avg_scores],
        "high_variance_bricks": high_variance,
        "variances": [round(v, 3) for v in variances]
    }

# Example usage (run with: python scorer.py)
if __name__ == "__main__":
    print("=== Paradox Identity Framework Scorer v1.2 ===\n")
    
    # Default LLM example under the NEW v1.2 stricter rules (\~48%)
    default_llm_scores = [0.0, 1.0, 1.0, 0.0, 0.0, 0.5, 1.0, 1.0, 1.0, 0.0, 1.0, 1.0, 0.5, 1.0, 0.5, 0.0, 0.0, 1.0, 0.0, 0.5]
    
    print("Example: Default LLM (v1.2 rules)")
    single = score_system(default_llm_scores)
    print(f"   → {single['percentage']}%  |  {single['tier']}\n")
    
    # Multi-rater example (3 independent scorers)
    rater1 = default_llm_scores
    rater2 = [0.0, 1.0, 1.0, 0.0, 0.0, 0.5, 1.0, 1.0, 0.5, 0.0, 1.0, 1.0, 0.5, 1.0, 0.5, 0.0, 0.0, 1.0, 0.0, 0.5]
    rater3 = [0.5, 1.0, 1.0, 0.0, 0.0, 0.5, 1.0, 1.0, 1.0, 0.0, 1.0, 1.0, 0.5, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.5]
    
    multi = multi_rater_score([rater1, rater2, rater3])
    print(f"Multi-Rater Example ({multi['num_raters']} raters):")
    print(f"   Average: {multi['average_percentage']}%  →  {multi['tier']}")
    if multi['high_variance_bricks']:
        print("   High-variance bricks (>0.3):")
        for brick, var in multi['high_variance_bricks']:
            print(f"      • {brick}: variance = {var}")
