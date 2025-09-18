from __future__ import annotations
import random
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from utils.geo import haversine_km

@dataclass
class TravelOffer:
    mode: str
    provider: str
    price: float
    currency: str
    depart: str
    arrive: str
    duration_min: int
    rating: float
    reviews: int
    deeplink: Optional[str] = None

def _time_pair(hours: float) -> (str, str):
    dep_h = 9 + random.randint(-2, 2)
    dur_min = int(max(60, hours * 60))
    arr_h = dep_h + max(1, dur_min // 60)
    return f"{dep_h:02d}:{random.randint(0,59):02d}", f"{arr_h:02d}:{random.randint(0,59):02d}", dur_min

def _mock_price(distance_km: float, base: float, per_km: float) -> float:
    surge = random.uniform(0.9, 1.3)
    return round((base + per_km * distance_km) * surge, 0)

def search_travel(origin: Dict[str, float], dest: Dict[str, float], party_size: int, modes: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    distance = haversine_km(origin["lat"], origin["lon"], dest["lat"], dest["lon"])
    results: Dict[str, List[Dict[str, Any]]] = {m: [] for m in modes}
    if "flight" in modes:
        for carrier in ["IndiGo", "Air India", "Vistara", "Akasa"]:
            hours = max(1.0, distance / 650.0)
            depart, arrive, dur_min = _time_pair(hours)
            price = _mock_price(distance, base=2000, per_km=5.5) * party_size
            rating = random.uniform(3.8, 4.6)
            results["flight"].append(TravelOffer("flight", carrier, price, "INR", depart, arrive, dur_min, round(rating,1), random.randint(500, 5000)).__dict__)
    if "train" in modes:
        for provider in ["Rajdhani", "Shatabdi", "Duronto", "Vande Bharat"]:
            hours = max(3.5, distance / 85.0)
            depart, arrive, dur_min = _time_pair(hours)
            price = _mock_price(distance, base=400, per_km=0.8) * party_size
            rating = random.uniform(3.5, 4.4)
            results["train"].append(TravelOffer("train", provider, price, "INR", depart, arrive, dur_min, round(rating,1), random.randint(200, 4000)).__dict__)
    if "bus" in modes:
        for provider in ["Orange Tours", "VRL", "Kaveri", "KSRTC"]:
            hours = max(4.0, distance / 55.0)
            depart, arrive, dur_min = _time_pair(hours)
            price = _mock_price(distance, base=300, per_km=0.9) * party_size
            rating = random.uniform(3.6, 4.5)
            results["bus"].append(TravelOffer("bus", provider, price, "INR", depart, arrive, dur_min, round(rating,1), random.randint(50, 2000)).__dict__)
    if "cab" in modes:
        for provider in ["Ola Outstation", "Uber Intercity", "Local Taxi Co."]:
            hours = max(1.0, distance / 60.0)
            depart, arrive, dur_min = _time_pair(hours)
            price = _mock_price(distance, base=800, per_km=12.0)  # total group
            rating = random.uniform(3.7, 4.7)
            results["cab"].append(TravelOffer("cab", provider, price, "INR", depart, arrive, dur_min, round(rating,1), random.randint(20, 1200)).__dict__)
    for k in results:
        results[k] = sorted(results[k], key=lambda x: x["price"])
    return results
