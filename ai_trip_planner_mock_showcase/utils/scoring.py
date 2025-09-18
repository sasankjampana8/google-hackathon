from __future__ import annotations
from typing import List

def score_activity(activity: dict, prefs: List[str], mood: float) -> float:
    base = 1.0 if activity.get("theme") in prefs else 0.2
    mood_bonus = 0.5 * (mood / 10.0)
    cost = activity.get("cost", 0) or 0
    cost_penalty = 0.4 if cost > 1500 else (0.2 if cost > 800 else 0.0)
    rating = activity.get("rating") or 4.0
    rating_bonus = (rating - 4.0) * 0.15
    return max(0.0, base + mood_bonus + rating_bonus - cost_penalty)
