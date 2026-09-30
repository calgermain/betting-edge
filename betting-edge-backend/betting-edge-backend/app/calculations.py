def implied_probability(american_odds):
    odds = float(american_odds)
    return (-odds) / ((-odds) + 100) if odds < 0 else 100 / (odds + 100)

def american_odds(probability):
    p = max(0.0001, min(0.9999, float(probability)))
    return round(-100 * p / (1 - p)) if p >= 0.5 else round(100 * (1 - p) / p)

def edge(estimated_probability, american_odds_value):
    return float(estimated_probability) - implied_probability(american_odds_value)
