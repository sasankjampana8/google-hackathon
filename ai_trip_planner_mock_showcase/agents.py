from __future__ import annotations
from typing import List, Dict, Tuple
import datetime as dt
from utils.scoring import score_activity

class BudgetAgent:
    def propose(self, candidates: List[dict], daily_budget: float) -> List[dict]:
        plan, total = [], 0.0
        for a in sorted(candidates, key=lambda x: x.get("cost", 0)):
            c = a.get("cost", 0) or 0
            if total + c <= daily_budget * 1.2:
                plan.append(a); total += c
        if not plan and candidates:
            plan = [sorted(candidates, key=lambda x: x.get("cost", 0))[0]]
        return plan

class InterestAgent:
    def shortlist(self, all_poi: List[dict], preferences: List[str], mood: float) -> List[Tuple[dict, float]]:
        scored = [(p, score_activity(p, preferences, mood)) for p in all_poi]
        return sorted(scored, key=lambda x: x[1], reverse=True)[:20]

class LogisticsAgent:
    def sequence(self, day_candidates: List[dict]) -> List[dict]:
        return day_candidates

class TimeScheduler:
    def schedule_day(self, day_candidates: List[dict], start_hour: int = 9, end_hour: int = 21) -> List[dict]:
        cur = dt.datetime.combine(dt.date.today(), dt.time(hour=start_hour, minute=0))
        end = dt.datetime.combine(dt.date.today(), dt.time(hour=end_hour, minute=0))
        timeline = []
        for a in day_candidates:
            dur_min = int(a.get("duration_min", 90) or 90)
            travel_pad = 30
            start_time = cur
            end_time = cur + dt.timedelta(minutes=dur_min)
            if end_time > end:
                break
            block = dict(a)
            block["start_time"] = start_time.strftime("%H:%M")
            block["end_time"] = end_time.strftime("%H:%M")
            timeline.append(block)
            cur = end_time + dt.timedelta(minutes=travel_pad)
        return timeline

class BookingAgent:
    def quote(self, items: List[dict]) -> Dict[str, float]:
        base = sum(a.get("cost", 0) for a in items)
        tax = round(base * 0.12, 2)
        return {"subtotal": round(base, 2), "tax": tax, "total": round(base + tax, 2)}
