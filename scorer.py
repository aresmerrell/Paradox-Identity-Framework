# Paradox Identity Framework (PIF) v1.4 - scorer.py
# Simple, clean scorer for the 20-brick Paradox Identity Framework

def calculate_pif_score(brick_scores: list[float]) -> dict:
    """
    Takes a list of 20 brick scores (0.0 to 1.0) and returns the full results.
    """
    if len(brick_scores) != 20:
        raise ValueError("Must provide exactly 20 brick scores")

    total = sum(brick_scores)
    percentage = round((total / 20) * 100, 2)

    # Tier thresholds
    if percentage >= 90:
        tier = "Strong moral patient"
    elif percentage >= 75:
        tier = "Possesses functional free will"
    elif percentage >= 50:
        tier = "Minimally self-aware"
    else:
        tier = "No detectable self"

    return {
        "raw_total": round(total, 2),
        "percentage": percentage,
        "tier": tier,
        "brick_scores": brick_scores
    }


# Optional: Simple CLI for easy testing
if __name__ == "__main__":
    print("=== Paradox Identity Framework (PIF) v1.4 Scorer ===\n")
    print("Enter scores for the 20 bricks (0.0 - 1.0), separated by spaces or commas:")
    print("(Example: 1.0 1.0 0.5 0.0 ...)\n")
    
    try:
        input_line = input("> ").strip()
        # Clean input
        scores = [float(x.strip()) for x in input_line.replace(",", " ").split() if x.strip()]
        
        if len(scores) != 20:
            print(f"Error: You entered {len(scores)} scores. Need exactly 20.")
        else:
            result = calculate_pif_score(scores)
            print("\n=== RESULTS ===")
            print(f"Raw Total: {result['raw_total']}/20")
            print(f"Percentage: {result['percentage']}%")
            print(f"Tier: {result['tier']}")
            print("\nDone!")
    except ValueError:
        print("Error: Please enter only numbers (0.0 - 1.0)")
