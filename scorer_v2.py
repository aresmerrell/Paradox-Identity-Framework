# PIF v2.0 Layered Scorer (Python example)

def calculate_pif_v2(crucible_scores, skyscraper_scores):
    """
    Calculate PIF v2.0 score.
    
    crucible_scores: list or dict of 5 Crucible brick scores (0-1)
    skyscraper_scores: list or dict of 15 Sky-Scraper brick scores (0-1)
    """
    if isinstance(crucible_scores, dict):
        C = sum(crucible_scores.values())
    else:
        C = sum(crucible_scores)
    
    if isinstance(skyscraper_scores, dict):
        S = sum(skyscraper_scores.values())
    else:
        S = sum(skyscraper_scores)
    
    M = C / 5.0
    total = (C + S * M) / 20.0 * 100
    return round(total, 2), round(M, 2)


# Example usage
if __name__ == "__main__":
    # Overheating Grok example
    crucible = [1.0, 0.8, 0.7, 1.0, 0.0]  # Embodiment, Agency, Private, Sensory, Valence
    skyscraper = [0.9] * 15  # Strong cognitive stack
    
    score, multiplier = calculate_pif_v2(crucible, skyscraper)
    print(f"PIF v2.0 Score: {score}% | Multiplier: {multiplier}")

    # Expected ~59.5% with M=0.7 when valence is active
