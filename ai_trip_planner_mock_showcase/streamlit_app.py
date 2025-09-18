from __future__ import annotations
import json, datetime as dt, copy, random
from typing import List, Dict
import streamlit as st
from pydantic import BaseModel, Field
import pandas as pd
import pydeck as pdk

from agents import BudgetAgent, InterestAgent, LogisticsAgent, TimeScheduler, BookingAgent
from travel.providers import search_travel

# ---------- Helpers ----------
def safe_rerun():
    try:
        if hasattr(st, "rerun"):
            st.rerun()
        elif hasattr(st, "experimental_rerun"):
            st.experimental_rerun()
    except Exception:
        pass

@st.cache_data
def load_sample(city: str) -> Dict:
    with open("data/sample_places.json","r") as f:
        data = json.load(f)
    return data.get(city) or {}

def center_of(city: str):
    blob = load_sample(city)
    c = blob.get("center")
    if isinstance(c, (list, tuple)) and len(c)==2:
        return {"lat": c[0], "lon": c[1]}
    return {"lat": 17.3850, "lon": 78.4867}

def catalog(city: str) -> List[Dict]:
    return load_sample(city).get("poi", [])

def schedule_list(acts: List[Dict], start_h: int, end_h: int) -> List[Dict]:
    # wrap TimeScheduler over a predefined list (already ordered)
    ts = TimeScheduler()
    return ts.schedule_day(acts, start_hour=start_h, end_hour=end_h)

def compute_costs(day_plans: List[Dict]) -> Dict[str, int]:
    per_day = [{"date": d["date"], "subtotal": sum(a.get("cost",0) for a in d["activities"])} for d in day_plans]
    total = sum(x["subtotal"] for x in per_day)
    return {"per_day": per_day, "activities_total": int(total)}

# ---------- Models ----------
st.set_page_config(page_title="AI Trip Planner — Mock Showcase (Multi-Itinerary + Editing)", page_icon="🧭", layout="wide")

class UserInput(BaseModel):
    origin_city: str
    destination_city: str
    start_date: dt.date
    end_date: dt.date
    budget_total: int = Field(default=30000)
    party_size: int = Field(default=2)
    themes: List[str] = Field(default_factory=lambda: ["heritage","leisure"])
    mood: float = Field(default=7.0)
    language: str = Field(default="English")
    modes: List[str] = Field(default_factory=lambda: ["flight","train"])
    day_start_hour: int = 9
    day_end_hour: int = 21
    variants: int = 3

# ---------- Sidebar ----------
with st.sidebar:
    st.header("Trip Inputs")
    cities = ["Hyderabad","Goa","Mumbai","Delhi","Bengaluru","Chennai"]
    origin = st.selectbox("Origin city", cities, index=0)
    dest = st.selectbox("Destination city", cities, index=1)
    col1, col2 = st.columns(2)
    with col1:
        start = st.date_input("Start", dt.date.today() + dt.timedelta(days=7))
    with col2:
        end = st.date_input("End", dt.date.today() + dt.timedelta(days=9))
    budget = st.slider("Total budget (₹)", 5000, 300000, 50000, step=5000)
    party = st.number_input("Travellers", 1, 10, 2)
    mood = st.slider("Mood / Energy", 0.0, 10.0, 7.0, step=0.5)
    themes = st.multiselect("Themes", ["heritage","nightlife","adventure","leisure","family","shopping"], default=["heritage","leisure"])
    modes = st.multiselect("Travel modes", ["flight","train","bus","cab"], default=["flight","train"])
    lang = st.selectbox("Language", ["English","हिंदी","తెలుగు"])
    day_start = st.slider("Day start hour", 6, 12, 9)
    day_end = st.slider("Day end hour", 17, 23, 21)
    variants = st.slider("Number of itinerary variants", 1, 5, 3)

    if st.button("Generate / Refresh"):
        ui = UserInput(
            origin_city=origin,
            destination_city=dest,
            start_date=start,
            end_date=end,
            budget_total=budget,
            party_size=party,
            themes=themes,
            mood=mood,
            language=lang,
            modes=modes,
            day_start_hour=day_start,
            day_end_hour=day_end,
            variants=variants,
        )
        st.session_state["user_input"] = ui.model_dump()
        st.session_state.pop("travel_offers", None)
        st.session_state.pop("chosen_travel", None)
        st.session_state.pop("itineraries", None)
        st.session_state["current_idx"] = 0
        safe_rerun()

ui_dict = st.session_state.get("user_input")
if not ui_dict:
    st.title("🧭 AI Trip Planner — Advanced Mock Showcase")
    st.caption("No external APIs. Mock providers, local POIs, **multiple itineraries**, and **in-app editing**.")
    st.info("Use the left panel to configure the trip and click **Generate / Refresh**.")
    st.stop()

ui = UserInput(**ui_dict)
st.title("🧭 AI Trip Planner — Advanced Mock Showcase")
st.caption("Multiple itinerary variants + editing (swap / add / delete).")

budget_agent = BudgetAgent()
interest_agent = InterestAgent()
log_agent = LogisticsAgent()
time_sched = TimeScheduler()
booking_agent = BookingAgent()

# ---------- Data ----------
dest_blob = load_sample(ui.destination_city)
all_poi = dest_blob.get("poi", [])
center = dest_blob.get("center", [17.3850,78.4867])

def center_xy(city: str):
    c = load_sample(city).get("center", [17.3850,78.4867])
    return {"lat": c[0], "lon": c[1]}
origin_xy = center_xy(ui.origin_city)
dest_xy = center_xy(ui.destination_city)

# ---------- Travel (mock) ----------
if "travel_offers" not in st.session_state:
    st.session_state["travel_offers"] = search_travel(origin_xy, dest_xy, ui.party_size, ui.modes)
offers = st.session_state["travel_offers"]

# ---------- Build multiple itineraries ----------
def build_itinerary(seed:int) -> List[Dict]:
    random.seed(seed)
    days = (ui.end_date - ui.start_date).days + 1
    days = max(1, days)
    daily_budget = ui.budget_total / max(1, days)
    # shortlist + shuffle some variation
    shortlist = [p for p,_ in InterestAgent().shortlist(all_poi, ui.themes, ui.mood)]
    random.shuffle(shortlist)
    day_plans = []
    ptr = 0
    for i in range(days):
        date = ui.start_date + dt.timedelta(days=i)
        take = random.randint(4,6)
        chunk = shortlist[ptr:ptr+take] or shortlist[:take]
        ptr += take
        plan = BudgetAgent().propose(chunk, daily_budget)
        plan = LogisticsAgent().sequence(plan)
        plan = TimeScheduler().schedule_day(plan, start_hour=ui.day_start_hour, end_hour=ui.day_end_hour)
        day_plans.append({"date": date, "activities": plan})
    return day_plans

if "itineraries" not in st.session_state:
    itins = []
    base_seed = random.randint(1, 10_000)
    for i in range(ui.variants):
        itins.append(build_itinerary(base_seed + i))
    st.session_state["itineraries"] = itins
    st.session_state["current_idx"] = 0

itins: List[List[Dict]] = st.session_state["itineraries"]
current_idx: int = st.session_state.get("current_idx", 0)

# ---------- Controls for selecting & duplicating variants ----------
st.subheader("Itinerary Variants")
colA, colB, colC = st.columns([3,2,2])
with colA:
    idx = st.selectbox("Choose itinerary", list(range(len(itins))), index=current_idx, format_func=lambda i: f"Variant #{i+1}")
with colB:
    if st.button("Duplicate current as new variant"):
        clone = copy.deepcopy(itins[current_idx])
        itins.append(clone)
        st.session_state["current_idx"] = len(itins)-1
        safe_rerun()
with colC:
    if st.button("Delete current variant") and len(itins) > 1:
        itins.pop(current_idx)
        st.session_state["current_idx"] = max(0, current_idx-1)
        safe_rerun()

if idx != current_idx:
    st.session_state["current_idx"] = idx
    current_idx = idx

current_itin = itins[current_idx]

tab_travel, tab_itin, tab_edit, tab_map, tab_cost, tab_checkout = st.tabs(["Travel Options", "Itinerary", "Edit Itinerary", "Map", "Costs", "Checkout & Tickets"])

# ---------- Travel Options ----------
with tab_travel:
    st.subheader("Compare & Select Travel")
    chosen = st.session_state.get("chosen_travel", {})
    for mode in ui.modes:
        st.markdown(f"### {mode.title()}")
        rows = offers.get(mode, [])
        if not rows:
            st.info("No offers found.")
            continue
        df = pd.DataFrame(rows)
        show = df[["provider","price","currency","depart","arrive","duration_min","rating","reviews"]]
        st.dataframe(show, use_container_width=True, hide_index=True)
        options = [f"{r['provider']} — ₹{int(r['price'])} ({r['depart']}→{r['arrive']})" for r in rows]
        pick = st.radio(f"Select {mode} option", options, key=f"pick_{mode}")
        idx_choice = options.index(pick)
        chosen[mode] = rows[idx_choice]
    st.session_state["chosen_travel"] = chosen
    st.success("Selections saved.")

# ---------- Read-only Itinerary View ----------
with tab_itin:
    st.subheader(f"Variant #{current_idx+1}: {ui.destination_city}")
    for d in current_itin:
        with st.expander(f"{d['date'].strftime('%a, %d %b %Y')}"):
            if not d["activities"]:
                st.write("No activities scheduled.")
            for a in d["activities"]:
                line = f"**{a['name']}** ({a.get('start_time','?')}–{a.get('end_time','?')}) — *{a.get('theme','?')}*, ₹{a.get('cost',0)}"
                if a.get('rating'): line += f", ⭐ {a['rating']} ({a.get('reviews','?')} reviews)"
                st.markdown("• " + line)

# ---------- Editable Itinerary ----------
with tab_edit:
    st.subheader("Edit Itinerary")
    # Choose day to edit
    day_options = [f"{i+1}: {d['date'].strftime('%a, %d %b')}" for i,d in enumerate(current_itin)]
    day_idx = st.selectbox("Choose day", list(range(len(current_itin))), format_func=lambda i: day_options[i])
    day = current_itin[day_idx]
    day_acts = day["activities"]

    # Current activities list
    st.markdown("**Current activities**")
    if not day_acts:
        st.info("No activities on this day yet.")
    else:
        for i, a in enumerate(day_acts):
            cols = st.columns([4,2,2,2])
            with cols[0]:
                st.write(f"{i+1}. **{a['name']}** — *{a.get('theme','?')}*")
            with cols[1]:
                st.write(f"₹{a.get('cost',0)}")
            with cols[2]:
                st.write(f"{a.get('start_time','?')}–{a.get('end_time','?')}")
            with cols[3]:
                st.checkbox("Remove", key=f"rm_{current_idx}_{day_idx}_{i}", value=False)

    st.markdown("---")

    # Swap: pick one activity and swap with catalog item not already present
    all_names_today = {a["name"] for a in day_acts}
    available_for_add = [p for p in catalog(ui.destination_city) if p["name"] not in all_names_today]

    if day_acts:
        st.markdown("**Swap an activity**")
        left_names = [a["name"] for a in day_acts]
        swap_out = st.selectbox("Swap out", ["(select)"] + left_names, index=0)
        swap_in = st.selectbox("Swap in (from catalog)", ["(select)"] + [p["name"] for p in available_for_add], index=0)
        if st.button("Apply swap"):
            if swap_out != "(select)" and swap_in != "(select)":
                # replace activity dict
                repl = next(p for p in available_for_add if p["name"] == swap_in)
                # keep schedule order: replace first match
                for i,a in enumerate(day_acts):
                    if a["name"] == swap_out:
                        day_acts[i] = repl
                        break
                # re-schedule
                day["activities"] = schedule_list(day_acts, ui.day_start_hour, ui.day_end_hour)
                st.success(f"Swapped **{swap_out}** → **{swap_in}**")
                safe_rerun()

    st.markdown("**Add an activity**")
    add_name = st.selectbox("Add from catalog", ["(select)"] + [p["name"] for p in available_for_add], index=0, key=f"add_{current_idx}_{day_idx}")
    if st.button("Add activity"):
        if add_name != "(select)":
            item = next(p for p in available_for_add if p["name"] == add_name)
            day_acts.append(item)
            day["activities"] = schedule_list(day_acts, ui.day_start_hour, ui.day_end_hour)
            st.success(f"Added **{add_name}**")
            safe_rerun()

    if st.button("Apply removals"):
        # collect removals by checkbox keys
        keep = []
        for i,a in enumerate(day_acts):
            key = f"rm_{current_idx}_{day_idx}_{i}"
            if not st.session_state.get(key, False):
                keep.append(a)
        day["activities"] = schedule_list(keep, ui.day_start_hour, ui.day_end_hour)
        st.success("Removed selected activities and re-scheduled.")
        # clear the checkboxes
        for i,_ in enumerate(day_acts):
            k = f"rm_{current_idx}_{day_idx}_{i}"
            if k in st.session_state: del st.session_state[k]
        safe_rerun()

# ---------- Map ----------
with tab_map:
    st.subheader("Map (current itinerary)")
    df = []
    for d in current_itin:
        for a in d["activities"]:
            df.append({"lat": a["lat"], "lon": a["lon"], "name": a["name"], "date": d["date"].isoformat()})
    if df:
        df = pd.DataFrame(df)
        layer = pdk.Layer("ScatterplotLayer", data=df, get_position='[lon, lat]', get_radius=100, pickable=True)
        view_state = pdk.ViewState(latitude=center[0], longitude=center[1], zoom=10)
        st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip={"text":"{name}\\n{date}"}))
    else:
        st.info("No activities to map.")

# ---------- Costs ----------
with tab_cost:
    st.subheader("Costs")
    travel_sel = st.session_state.get("chosen_travel", {})
    travel_total = sum(v["price"] for v in travel_sel.values()) if travel_sel else 0

    costs = compute_costs(current_itin)
    per_day = costs["per_day"]
    df = pd.DataFrame(per_day)
    st.bar_chart(df.set_index("date"))
    activity_total = costs["activities_total"]

    st.write(f"**Travel total (selected)**: ₹{int(travel_total)}")
    st.write(f"**Activities total (est.)**: ₹{int(activity_total)}")
    st.write(f"**Grand total (est.)**: ₹{int(travel_total + activity_total)}")

st.divider()
st.caption("Mock-only showcase. Generate multiple variants; edit by swapping, adding, or removing activities. All changes are kept per-variant in session state.")

# ---------- Unified Checkout & Tickets ----------
with tab_checkout:
    st.subheader("Unified Payment Portal")
    st.caption("One payment → backend (simulated) executes individual bookings and returns your tickets.")

    # Build bill of materials
    travel_sel = st.session_state.get("chosen_travel", {})
    travel_items = []
    travel_total = 0
    for mode, offer in travel_sel.items():
        travel_items.append({
            "item": f"{mode.title()} — {offer['provider']} ({offer['depart']}→{offer['arrive']})",
            "qty": 1,
            "unit_price": int(offer["price"]),
            "total": int(offer["price"]),
        })
        travel_total += offer["price"]

    # Current itinerary selection
    current_itin = itins[current_idx]
    per_day = [{"date": d["date"], "subtotal": sum(a.get("cost",0) for a in d["activities"])} for d in current_itin]
    activities_total = int(sum(x["subtotal"] for x in per_day))

    # Totals & fees
    subtotal = int(travel_total + activities_total)
    tax = int(round(subtotal * 0.12))  # GST placeholder
    platform_fee = int(round(subtotal * 0.015))  # 1.5% platform/conv fee
    grand_total = int(subtotal + tax + platform_fee)

    st.markdown("### Bill of Materials")
    bill_rows = travel_items + [
        {"item": f"Activities — Day {i+1}", "qty": 1, "unit_price": int(x["subtotal"]), "total": int(x["subtotal"])}
        for i, x in enumerate(per_day)
    ]
    bill_df = pd.DataFrame(bill_rows)
    if not bill_df.empty:
        st.dataframe(bill_df, use_container_width=True, hide_index=True)
    st.write(f"**Subtotal**: ₹{subtotal}")
    st.write(f"**GST (12%)**: ₹{tax}")
    st.write(f"**Platform fee (1.5%)**: ₹{platform_fee}")
    st.write(f"### **Amount to Pay**: ₹{grand_total}")

    # Checkout form
    st.markdown("### Payment Details")
    with st.form("checkout_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input("Full name", value="Test User")
            email = st.text_input("Email", value="test@example.com")
            phone = st.text_input("Phone", value="9999999999")
        with col2:
            method = st.selectbox("Payment method", ["UPI", "Card", "NetBanking", "Wallet"], index=0)
            notes = st.text_area("Notes (optional)", value="")
        agree = st.checkbox("I agree to the Terms & Conditions")
        submit = st.form_submit_button(f"Pay ₹{grand_total}")

    if submit:
        if not agree:
            st.error("Please accept the Terms & Conditions to proceed.")
        elif grand_total <= 0:
            st.error("Nothing to pay. Please select travel and/or add activities.")
        else:
            # Simulate payment processing + backend orchestration
            import time, io, zipfile, random
            ts = int(time.time())
            order_id = f"ORD-{ts}"
            st.session_state["order"] = {
                "id": order_id,
                "status": "PAID",
                "paid_amount": grand_total,
                "method": method,
                "name": full_name,
                "email": email,
                "phone": phone,
            }
            st.success(f"Payment received. Order **{order_id}** confirmed.")

            # Generate mock tickets (one per travel mode selected) + day pass for activities
            tickets = []
            for mode, offer in travel_sel.items():
                code = f"{mode[:2].upper()}-{random.randint(100000,999999)}"
                t = {
                    "type": mode,
                    "provider": offer["provider"],
                    "pnr": code,
                    "route": f"{offer['depart']}→{offer['arrive']}",
                    "amount": int(offer['price']),
                }
                tickets.append(t)
            for i, x in enumerate(per_day):
                tickets.append({"type":"day-pass","day": i+1, "activities_value": int(x["subtotal"]), "pass_id": f"D{i+1}-{random.randint(1000,9999)}"})

            # Prepare invoice text
            invoice_txt = io.StringIO()
            invoice_txt.write(f"AI Trip Planner — Invoice\nOrder ID: {order_id}\nName: {full_name}\nPhone: {phone}\nEmail: {email}\n\n")
            invoice_txt.write("Items:\n")
            for r in bill_rows:
                invoice_txt.write(f"- {r['item']}: ₹{r['total']}\n")
            invoice_txt.write(f"\nSubtotal: ₹{subtotal}\nGST (12%): ₹{tax}\nPlatform fee (1.5%): ₹{platform_fee}\nTotal paid: ₹{grand_total}\n")
            invoice_bytes = invoice_txt.getvalue().encode("utf-8")

            # Prepare tickets ZIP
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as z:
                # add a tickets.json
                z.writestr("tickets.json", json.dumps(tickets, indent=2))
                # add simple text stubs per ticket
                for t in tickets:
                    if t["type"] == "day-pass":
                        name = f"day_pass_D{t['day']}.txt"
                        body = f"Order: {order_id}\nDay: {t['day']}\nPass ID: {t['pass_id']}\nValue: ₹{t['activities_value']}"
                    else:
                        name = f"{t['type']}_{t['provider']}_{t['pnr']}.txt".replace(" ", "_")
                        body = f"Order: {order_id}\nProvider: {t['provider']}\nPNR: {t['pnr']}\nRoute: {t['route']}\nPaid: ₹{t['amount']}"
                    z.writestr(name, body)
            zip_buf.seek(0)

            st.markdown("### Downloads")
            st.download_button("⬇️ Download Invoice (TXT)", data=invoice_bytes, file_name=f"invoice_{order_id}.txt", mime="text/plain")
            st.download_button("⬇️ Download Tickets (ZIP)", data=zip_buf, file_name=f"tickets_{order_id}.zip", mime="application/zip")

            # Show a quick summary table
            st.markdown("### Your Tickets")
            tdf = pd.DataFrame(tickets)
            st.dataframe(tdf, use_container_width=True, hide_index=True)
