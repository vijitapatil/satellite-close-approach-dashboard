import streamlit as st
import pandas as pd
import numpy as np
from itertools import combinations
from datetime import datetime, timedelta, timezone
from sgp4.api import Satrec, jday

st.set_page_config(
    page_title="Orbit Guard | Space Safety",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Visual system ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');
:root { --bg:#08111f; --panel:#101d30; --panel2:#14243a; --line:#243650; --muted:#91a5c2; --text:#edf4ff; --cyan:#56e0d0; --blue:#70a7ff; }
html, body, [class*="css"] { font-family:'DM Sans',sans-serif; }
.stApp { background: radial-gradient(ellipse at 15% 0%, #142d4c 0%, #08111f 45%, #070d18 100%); color:var(--text); }
[data-testid="stHeader"] { background:rgba(8,17,31,.65); }
.block-container { max-width:1450px; padding-top:2rem; padding-bottom:3rem; }
h1,h2,h3 { font-family:'Space Grotesk',sans-serif !important; color:var(--text) !important; letter-spacing:-.03em; }
p, label, .stMarkdown, [data-testid="stCaptionContainer"] { color:#c4d2e5; }
.hero { padding:1.6rem 1.8rem; border:1px solid #29415f; border-radius:24px; background:linear-gradient(120deg,rgba(24,49,78,.95),rgba(13,27,45,.94)); position:relative; overflow:hidden; margin-bottom:1.2rem; }
.hero:after { content:'✦'; position:absolute; right:7%; top:-30px; font-size:180px; color:rgba(86,224,208,.09); }
.eyebrow { text-transform:uppercase; letter-spacing:.18em; font-size:.72rem; color:var(--cyan); font-weight:700; }
.hero h1 { font-size:2.55rem; margin:.3rem 0 .35rem 0; }
.hero p { max-width:720px; margin:0; color:#b7c9df; }
.pill { display:inline-block; border:1px solid #31536d; background:#102d3a; color:#8ff2df; border-radius:999px; padding:.35rem .7rem; font-size:.75rem; font-weight:600; margin-bottom:.65rem; }
.metric-card { background:linear-gradient(145deg,#13243a,#0d192a); border:1px solid #263b56; border-radius:18px; padding:1rem 1.1rem; min-height:125px; }
.metric-label { color:#91a5c2; font-size:.78rem; text-transform:uppercase; letter-spacing:.09em; font-weight:700; }
.metric-value { font-family:'Space Grotesk',sans-serif; color:#f3f7ff; font-size:1.8rem; font-weight:700; margin-top:.35rem; }
.metric-note { color:#8da6c3; font-size:.78rem; margin-top:.2rem; }
.section-card { background:rgba(16,29,48,.78); border:1px solid #243650; border-radius:18px; padding:1rem 1.2rem; }
div[data-testid="stSidebar"] { background:#0a1423; border-right:1px solid #20324a; }
div[data-testid="stSidebar"] h2, div[data-testid="stSidebar"] h3 { color:#edf4ff !important; }
.stButton > button, .stDownloadButton > button { border-radius:12px; border:1px solid #3b6a7d; font-weight:700; min-height:2.8rem; }
.stButton > button[kind="primary"] { background:linear-gradient(90deg,#26bcae,#4b9df4); color:#071522; border:0; }
[data-testid="stDataFrame"] { border:1px solid #263b56; border-radius:12px; overflow:hidden; }
hr { border-color:#243650; }
div[data-testid="stAlert"] { border-radius:12px; }
.small-muted { color:#91a5c2; font-size:.82rem; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <div class="pill">● ORBITAL SAFETY CONSOLE</div>
  <div class="eyebrow">Space situational awareness</div>
  <h1>Orbit Guard</h1>
  <p>Screen satellite trajectories for potential close approaches using TLE orbital data and SGP4 propagation. Review the closest sampled separations, inspect candidates, and export your results.</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## ⚙️ Simulation setup")
    st.caption("Configure a screening run")
    num_satellites = st.selectbox("Satellites to analyze", [5, 10], index=0)
    threshold = st.slider("Screening threshold", min_value=1, max_value=1000, value=1000, step=10, format="%d km")
    duration_hours = st.selectbox("Simulation window", [1, 3, 6], index=2, format_func=lambda x: f"{x} hours")
    st.markdown("---")
    st.markdown("### Data source")
    st.markdown("`satellites.tle`")
    st.caption("Place a local TLE file beside app.py. Each satellite must have a name line followed by TLE line 1 and line 2.")
    run_clicked = st.button("🚀  Run screening", type="primary", use_container_width=True)
    st.markdown("---")
    st.caption("Orbit Guard · Educational prototype")

step_minutes = 10

def fetch_tle_data():
    satellites = []
    with open("satellites.tle", "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip() and not line.lstrip().startswith("#")]
    for i in range(0, len(lines) - 2, 3):
        name, line1, line2 = lines[i:i + 3]
        if line1.startswith("1 ") and line2.startswith("2 "):
            try:
                sat = Satrec.twoline2rv(line1, line2)
                satellites.append({
                    "name": name,
                    "catalog_number": line1[2:7].strip(),
                    "satrec": sat,
                })
            except Exception:
                continue
    if not satellites:
        raise ValueError("No valid satellites found. Check that satellites.tle contains satellite names, TLE line 1, and TLE line 2.")
    return satellites

def calculate_risk_score(distance):
    if distance < 200:
        score = 10 - distance / 200
    elif distance < 300:
        score = 9 - (distance - 200) / 100
    elif distance < 400:
        score = 8 - (distance - 300) / 100
    elif distance < 500:
        score = 7 - (distance - 400) / 100
    elif distance < 600:
        score = 6 - (distance - 500) / 100
    elif distance < 700:
        score = 5 - (distance - 600) / 100
    elif distance < 800:
        score = 4 - (distance - 700) / 100
    elif distance < 900:
        score = 3 - (distance - 800) / 100
    elif distance <= 1000:
        score = 2 - (distance - 900) / 100
    else:
        score = 1
    return round(max(1, min(10, score)), 2)

def get_risk_level(score):
    if score >= 9:
        return "Very High"
    if score >= 8:
        return "High"
    if score >= 6:
        return "Moderate-High"
    if score >= 4:
        return "Moderate"
    if score >= 2:
        return "Low"
    return "Very Low"

def run_screening(satellites, hours, threshold_km):
    start_time = datetime.now(timezone.utc).replace(microsecond=0)
    total_steps = int(hours * 60 / step_minutes) + 1
    times = [start_time + timedelta(minutes=step_minutes * i) for i in range(total_steps)]
    position_records, errors = [], []

    progress = st.progress(0, text="Propagating satellite positions…")
    total_work = max(1, len(satellites) * len(times))
    completed = 0
    for sat in satellites:
        for current_time in times:
            jd, fr = jday(
                current_time.year, current_time.month, current_time.day,
                current_time.hour, current_time.minute,
                current_time.second + current_time.microsecond / 1_000_000,
            )
            error_code, position, velocity = sat["satrec"].sgp4(jd, fr)
            if error_code != 0:
                errors.append({"Satellite": sat["name"], "Error code": error_code})
            else:
                position_records.append({
                    "Satellite": sat["name"],
                    "Catalog number": sat["catalog_number"],
                    "Time": current_time,
                    "X (km)": position[0], "Y (km)": position[1], "Z (km)": position[2],
                })
            completed += 1
            if completed % max(1, total_work // 30) == 0 or completed == total_work:
                progress.progress(min(completed / total_work, 1.0), text="Propagating satellite positions…")
    progress.empty()

    positions = pd.DataFrame(position_records)
    if positions.empty:
        return positions, pd.DataFrame(), errors

    pair_records = []
    for current_time, frame in positions.groupby("Time"):
        rows = frame.to_dict("records")
        for a, b in combinations(rows, 2):
            dx = a["X (km)"] - b["X (km)"]
            dy = a["Y (km)"] - b["Y (km)"]
            dz = a["Z (km)"] - b["Z (km)"]
            distance = float(np.sqrt(dx**2 + dy**2 + dz**2))
            pair_records.append({
                "Satellite 1": a["Satellite"], "Satellite 2": b["Satellite"],
                "Time": current_time, "Distance (km)": distance,
            })
    pair_df = pd.DataFrame(pair_records)
    if pair_df.empty:
        return positions, pd.DataFrame(), errors

    closest_indices = pair_df.groupby(["Satellite 1", "Satellite 2"])["Distance (km)"].idxmin()
    closest = pair_df.loc[closest_indices].sort_values("Distance (km)").reset_index(drop=True)
    closest["Risk score"] = closest["Distance (km)"].apply(calculate_risk_score)
    closest["Risk level"] = closest["Risk score"].apply(get_risk_level)
    closest["Candidate"] = closest["Distance (km)"] <= threshold_km
    return positions, closest, errors

# Top-line cards
a, b, c = st.columns(3)
for col, label, value, note in [
    (a, "SATELLITES", str(num_satellites), "Selected for this run"),
    (b, "TIME WINDOW", f"{duration_hours} hr", f"Samples every {step_minutes} minutes"),
    (c, "THRESHOLD", f"{threshold:,} km", "Candidate screening limit"),
]:
    with col:
        st.markdown(f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="metric-note">{note}</div></div>', unsafe_allow_html=True)

st.markdown("")
st.info("Educational prototype only. This tool compares sampled positions and does not provide certified collision predictions. Encounters between sample times may be missed.")

if run_clicked:
    try:
        with st.spinner("Loading TLE data and preparing the screening…"):
            all_satellites = fetch_tle_data()
            selected = all_satellites[:num_satellites]
            positions, closest, errors = run_screening(selected, duration_hours, threshold)
        st.session_state["screening_result"] = {
            "positions": positions, "closest": closest, "errors": errors,
            "selected_count": len(selected), "threshold": threshold,
            "duration_hours": duration_hours, "run_time": datetime.now().astimezone().strftime("%d %b %Y, %H:%M:%S %Z"),
        }
        st.success("Screening run completed.")
    except FileNotFoundError:
        st.error("Could not find `satellites.tle`. Add your TLE data file to the same folder as `app.py`, then run screening again.")
    except Exception as exc:
        st.error(f"Screening failed: {exc}")
        st.caption("Check your TLE file format and make sure all required packages are installed.")

result = st.session_state.get("screening_result")
if result:
    positions, closest, errors = result["positions"], result["closest"], result["errors"]
    candidate_count = int(closest["Candidate"].sum()) if not closest.empty else 0
    st.markdown("## Screening summary")
    st.caption(f"Last run: {result['run_time']} · {result['selected_count']} satellites analyzed")
    m1, m2, m3 = st.columns(3)
    for col, label, value, note in [
        (m1, "LOADED", str(result["selected_count"]), "Satellites used"),
        (m2, "POSITION SAMPLES", f"{len(positions):,}", "Valid propagated positions"),
        (m3, "CANDIDATE PAIRS", str(candidate_count), f"At or below {result['threshold']:,} km"),
    ]:
        with col:
            st.markdown(f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="metric-note">{note}</div></div>', unsafe_allow_html=True)

    tab_overview, tab_pairs, tab_data, tab_exports = st.tabs(["📊 Overview", "🔎 Close approaches", "🛰️ Position data", "⬇️ Export"])
    with tab_overview:
        if closest.empty:
            st.warning("No pairwise results could be calculated. Check the TLE data and propagation errors.")
        else:
            chart = closest.copy()
            chart["Satellite pair"] = chart["Satellite 1"] + " ↔ " + chart["Satellite 2"]
            chart = chart.sort_values("Distance (km)").set_index("Satellite pair")
            st.markdown("### Minimum sampled separation")
            st.bar_chart(chart["Distance (km)"], color="#56e0d0", height=350)
            st.caption("Each bar represents the minimum distance observed between a satellite pair at the sampled times.")
            st.markdown("### Run details")
            st.markdown(f"- **Simulation duration:** {result['duration_hours']} hours")
            st.markdown(f"- **Sampling interval:** {step_minutes} minutes")
            st.markdown(f"- **Screening threshold:** {result['threshold']:,} km")
            st.markdown("- **Propagation method:** SGP4 using local TLE data")
    with tab_pairs:
        if closest.empty:
            st.warning("No pairwise results available.")
        else:
            candidates = closest[closest["Candidate"]].copy()
            if candidates.empty:
                st.success("No pairs fell within the selected threshold at sampled times.")
                st.caption("This does not rule out an encounter between sample points.")
            else:
                st.warning(f"{len(candidates)} candidate pair(s) met the selected threshold.")
                st.dataframe(candidates, use_container_width=True, hide_index=True)
            with st.expander("View all satellite pairs"):
                st.dataframe(closest, use_container_width=True, hide_index=True)
    with tab_data:
        if positions.empty:
            st.warning("No position data available.")
        else:
            st.dataframe(positions, use_container_width=True, hide_index=True)
            st.caption(f"{len(positions):,} valid position records.")
    with tab_exports:
        st.markdown("### Download your data")
        st.caption("Export the raw position samples or the minimum-distance screening table as CSV files.")
        d1, d2 = st.columns(2)
        with d1:
            if not positions.empty:
                st.download_button("⬇️  Satellite positions CSV", positions.to_csv(index=False).encode("utf-8"), "satellite_positions.csv", "text/csv", use_container_width=True)
        with d2:
            if not closest.empty:
                st.download_button("⬇️  Screening results CSV", closest.to_csv(index=False).encode("utf-8"), "close_approach_screening.csv", "text/csv", use_container_width=True)
    if errors:
        with st.expander(f"⚠️ Propagation warnings ({len(errors)})"):
            st.warning("Some satellite positions were skipped due to propagation errors.")
            st.dataframe(pd.DataFrame(errors), use_container_width=True, hide_index=True)
else:
    st.markdown("## Ready for screening")
    left, right = st.columns([1.15, 1])
    with left:
        st.markdown('<div class="section-card"><div class="eyebrow">HOW IT WORKS</div><h3>From orbital data to insights</h3><p>01 · Load satellite TLE records</p><p>02 · Propagate positions with SGP4</p><p>03 · Compare pairwise distances at matching sample times</p><p>04 · Flag pairs inside your threshold and export results</p></div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="section-card"><div class="eyebrow">BEFORE YOU START</div><h3>Check your data file</h3><p>Keep <code>satellites.tle</code> in the same folder as this app. Every satellite needs three lines: its name, TLE line 1, and TLE line 2.</p><p class="small-muted">Use current, valid TLE data for meaningful educational screening.</p></div>', unsafe_allow_html=True)

st.markdown("---")
st.markdown('<p class="small-muted" style="text-align:center">ORBIT GUARD · SGP4 ORBITAL PROPAGATION · EDUCATIONAL USE ONLY</p>', unsafe_allow_html=True)

