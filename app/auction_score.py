import pandas as pd
import numpy as np

def calculate_auction_score(df):
    """
    IPL Player ROI Index — a weighted score combining:
    - Total runs (40%) — volume of scoring
    - Strike rate (40%) — scoring speed
    - Consistency (20%) — balls faced relative to runs
    """
    
    # Normalize each metric to 0-100 scale
    def normalize(series):
        min_val = series.min()
        max_val = series.max()
        return ((series - min_val) / (max_val - min_val) * 100).round(2)
    
    # Filter players with meaningful data
    df = df[df['balls_faced'] >= 200].copy()
    
    # Calculate consistency score — runs per ball faced
    df['runs_per_ball'] = (df['total_runs'] / df['balls_faced']).round(4)
    
    # Normalize each component
    df['runs_score'] = normalize(df['total_runs'])
    df['sr_score'] = normalize(df['strike_rate'])
    df['consistency_score'] = normalize(df['runs_per_ball'])
    
    # Weighted final score
    df['roi_index'] = (
        df['runs_score'] * 0.40 +
        df['sr_score'] * 0.40 +
        df['consistency_score'] * 0.20
    ).round(2)
    
    # Label tiers
    def assign_tier(score):
        if score >= 75:
            return '🔥 Elite'
        elif score >= 55:
            return '⭐ Premium'
        elif score >= 35:
            return '✅ Value'
        else:
            return '⚠️ Risky'
    
    df['tier'] = df['roi_index'].apply(assign_tier)
    
    return df.sort_values('roi_index', ascending=False)