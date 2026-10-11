
import streamlit as st
import pandas as pd
import numpy as np

from itertools import combinations
from datetime import datetime, timedelta, timezone
from sgp4.api import Satrec, jday


# ==========================================================
# ORBIT GUARD | SPACE DEBRIS & CLOSE-APPROACH MONITOR
# ==========================================================

st.set_page_config(
    page_title="Orbit Guard | Space Surveillance",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ==========================================================
# DARK SPACE THEME
# ==========================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap');

:root {
    --bg: #070B18;
    --panel: #10182B;
    --panel2: #141E35;
    --cyan: #45E5FF;
    --purple: #A78BFA;
    --text: #F1F5FF;
    --muted: #9BAAC5;
    --border: #263654;
}

.stApp {
    background:
        radial-gradient(ellipse at 12% 0%, #14234A 0%, transparent 35%),
        radial-gradient(ellipse at 90% 20%, #201344 0%, transparent 32%),
        linear-gradient(145deg, #070B18 0%, #0A1021 55%, #080B18 100%);
    color: var(--text);
    font-family: 'Inter', sans-serif;
}

[data-testid="stHeader"] {
    background: rgba(7, 11, 24, 0.85);
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0D1529, #080D1C);
    border-right: 1px solid #263654;
}

[data-testid="stSidebar"] * {
    color: #E8F0FF;
}

.block-container {
    padding-top: 1.6rem;
    padding-bottom: 2.5rem;
    max-width: 1600px;
}

h1, h2, h3 {
    font-family: 'Space Grotesk', sans-serif !important;
    color: #F1F5FF !important;
    letter-spacing: -0.5px;
}

p, label, .stMarkdown, [data-testid="stCaptionContainer"] {
    color: #B8C5DE;
}

.hero {
    padding: 30px 32px;
    border: 1px solid #29456B;
    border-radius: 22px;
    background:
        radial-gradient(ellipse at 85% 0%, #263F76 0%, transparent 45%),
        linear-gradient(120deg, #111C35 0%, #11152C 55%, #21163F 100%);
    margin-bottom: 24px;
    box-shadow: 0 15px 45px rgba(0,0,0,0.22);
}

.hero-tag {
    display: inline-block;
    color: #54E9FF;
    background: rgba(69,229,255,0.09);
    border: 1px solid rgba(69,229,255,0.32);
    border-radius: 20px;
    padding: 6px 12px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.8px;
    margin-bottom: 12px;
}

.hero-title {
    color: #FFFFFF;
    font-family: 'Space Grotesk', sans-serif;
    font-size: clamp(32px, 4vw, 48px);
    font-weight: 700;
    line-height: 1.12;
    margin-bottom: 10px;
}

.hero-title span {
    color: #55E5FF;
}

.hero-subtitle {
    font-size: 15px;
    color: #B7C6E2;
    line-height: 1.8;
    max-width: 780px;
}

.section-label {
    color: #55E5FF;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 2px;
    margin: 24px 0 5px 0;
}

.section-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 23px;
    font-weight: 700;
    color: #F1F5FF;
    margin-bottom: 16px;
}

.metric-card {
    background: linear-gradient(145deg, #141F36, #0E172A);
    border: 1px solid #293B5C;
    border-radius: 16px;
    padding: 20px 18px;
    min-height: 125px;
    box-shadow: 0 8px 25px rgba(0,0,0,0.14);
}

.metric-label {
    color: #9EAFCE;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.8px;
    text-transform: uppercase;
}

.metric-value {
    color: #F5F8FF;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 30px;
    font-weight: 700;
    margin-top: 10px;
    line-height: 1.2;
    overflow-wrap: anywhere;
}

.metric-note {
    color: #45E5FF;
    font-size: 11px;
    margin-top: 8px;
}

.panel {
    background: rgba(16,24,43,0.90);
    border: 1px solid #263654;
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 15px;
}

.status-chip {
    display: inline-block;
    padding: 5px 11px;
    border-radius: 20px;
    background: rgba(69,229,255,0.10);
    border: 1px solid rgba(69,229,255,0.25);
    color: #64E9FF;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
}

div.stButton > button {
    width: 100%;
    border: 1px solid #53E7FF;
    border-radius: 11px;
    background: linear-gradient(100deg, #16A7CE, #6752DA);
    color: white;
    font-weight: 800;
    padding: 0.72rem 1rem;
    transition: 0.2s ease;
    box-shadow: 0 5px 22px rgba(54,155,255,0.18);
}

div.stButton > button:hover {
    border-color: #FFFFFF;
    color: white;
    filter: brightness(1.13);
}

div[data-testid="stDownloadButton"] button {
    background: #131F37;
    color: #62E8FF;
    border: 1px solid #31486A;
    border-radius: 9px;
}

div[data-testid="stDownloadButton"] button:hover {
    border-color: #55E5FF;
    color: white;
}

.stSlider [data-baseweb="slider"] {
    margin-top: 10px;
}

[data-testid="stDataFrame"] {
    border: 1px solid #293B5C;
    border-radius: 12px;
    overflow: hidden;
}

[data-testid="stAlert"] {
    border-radius: 12px;
}

hr {
    border-color: #263654 !important;
}

.footer {
    border-top: 1px solid #263654;
    padding-top: 18px;
    margin-top: 35px;
    color: #8495B5;
    font-size: 12px;
    text-align: center;
}

@media (max-width: 768px) {
    .hero {
        padding: 22px 18px;
    }
    .metric-value {
        font-size: 24px;
    }
}
</style>
""", unsafe_allow_html=True)


# ==========================================================
# HEADER
# ==========================================================

st.markdown("""
<div class="hero">
    <div class="hero-tag">ORBITAL INTELLIGENCE · MISSION CONTROL</div>
    <div class="hero-title">🛰️ ORBIT <span>GUARD</span></div>
    <div class="hero-subtitle">
        Space debris and satellite close-approach monitoring.
        Propagate orbital data, compare satellite positions,
        identify candidate close approaches, and visualize
        potential proximity risks in one unified dashboard.
    </div>
    <br>
    <span class="status-chip">● SIMULATION PLATFORM</span>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div style="background:rgba(255,190,75,0.07);
border:1px solid rgba(255,190,75,0.25);
border-radius:12px;padding:13px 16px;margin-bottom:20px;
color:#F4D8A1;font-size:13px;">
⚠️ <b>Research prototype:</b> Results are based on sampled
orbital positions and simplified distance-based risk scores.
They are not certified collision predictions. A pair below
the screening threshold is a candidate for further analysis,
not proof of an impending collision.
</div>
""", unsafe_allow_html=True)


# ==========================================================
# SIDEBAR | SIMULATION CONTROLS
# ==========================================================

st.sidebar.markdown("""
<div style="padding:10px 0 18px 0;">
    <div style="font-size:11px;color:#55E5FF;
    letter-spacing:2px;font-weight:800;">MISSION CONTROL</div>
    <div style="font-size:24px;font-weight:800;
    color:#FFFFFF;font-family:'Space Grotesk',sans-serif;">
    Configuration
    </div>
    <div style="font-size:12px;color:#9BAAC5;">
    Set up your orbital screening run.
    </div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("### 🛰️ Satellite Selection")

num_satellites = st.sidebar.selectbox(
    "Number of satellites",
    [5, 10],
    index=0
)

st.sidebar.markdown("### 🎯 Screening Parameters")

threshold = st.sidebar.slider(
    "Screening threshold (km)",
    min_value=1,
    max_value=1000,
    value=1000,
    step=10
)

duration_hours = st.sidebar.selectbox(
    "Simulation duration",
    [1, 3, 6],
    index=2
)

step_minutes = st.sidebar.selectbox(
    "Sampling interval (minutes)",
    [1, 5, 10, 15],
    index=2
)

st.sidebar.markdown("---")

st.sidebar.markdown("""
<div style="font-size:12px;color:#9BAAC5;line-height:1.8;">
<b style="color:#55E5FF;">ENGINE</b><br>
SGP4 orbital propagation<br>
<b style="color:#55E5FF;">INPUT</b><br>
Local TLE catalog<br>
<b style="color:#55E5FF;">OUTPUT</b><br>
Closest sampled approaches<br>
Risk screening and CSV exports
</div>
""", unsafe_allow_html=True)


# ==========================================================
# TLE DATA LOADING
# ==========================================================

def fetch_tle_data():
    satellites = []

    with open("satellites.tle", "r", encoding="utf-8-sig") as f:
        lines = [
            line.strip()
            for line in f
            if line.strip()
        ]

    i = 0

    while i < len(lines):
        # Expected format:
        # Satellite name
        # TLE line 1
        # TLE line 2

        if i + 2 >= len(lines):
            break

        name = lines[i]
        line1 = lines[i + 1]
        line2 = lines[i + 2]

        if line1.startswith("1 ") and line2.startswith("2 "):
            try:
                sat = Satrec.twoline2rv(line1, line2)

                satellites.append({
                    "name": name,
                    "catalog_number": line1[2:7].strip(),
                    "satrec": sat
                })

                i += 3

            except Exception:
                i += 3

        else:
            i += 1

    if not satellites:
        raise ValueError(
            "No valid satellites found in satellites.tle. "
            "Check that the file contains satellite names, "
            "TLE line 1, and TLE line 2 in the expected format."
        )

    return satellites


# ==========================================================
# RISK SCORING
# ==========================================================

def calculate_risk_score(distance):
    """
    Illustrative proximity score from 1 to 10.
    This is not a physical collision probability.
    """

    score = 10 - (float(distance) / 100)

    return round(max(1, min(10, score)), 2)


def get_risk_level(score):
    if score >= 9:
        return "Very High"
    elif score >= 8:
        return "High"
    elif score >= 6:
        return "Moderate-High"
    elif score >= 4:
        return "Moderate"
    elif score >= 2:
        return "Low"
    else:
        return "Very Low"


# ==========================================================
# ORBITAL PROPAGATION AND PROXIMITY SCREENING
# ==========================================================

def run_screening(satellites, hours, threshold_km, interval_minutes):

    start_time = datetime.now(timezone.utc)

    total_steps = int(hours * 60 / interval_minutes) + 1

    times = [
        start_time + timedelta(minutes=interval_minutes * i)
        for i in range(total_steps)
    ]

    position_records = []
    errors = []

    # Propagate each satellite at each sample time.
    for sat in satellites:

        for current_time in times:

            jd, fr = jday(
                current_time.year,
                current_time.month,
                current_time.day,
                current_time.hour,
                current_time.minute,
                current_time.second
                + current_time.microsecond / 1_000_000
            )

            error_code, position, velocity = sat["satrec"].sgp4(
                jd, fr
            )

            if error_code != 0:
                errors.append({
                    "Satellite": sat["name"],
                    "Error code": error_code
                })
                continue

            position_records.append({
                "Satellite": sat["name"],
                "Catalog number": sat["catalog_number"],
                "Time": current_time,
                "X (km)": position[0],
                "Y (km)": position[1],
                "Z (km)": position[2]
            })

    positions = pd.DataFrame(position_records)

    if positions.empty:
        return positions, pd.DataFrame(), errors

    pair_records = []

    # Compare satellite pairs at matching timestamps.
    for current_time, frame in positions.groupby("Time"):

        rows = frame.to_dict("records")

        for a, b in combinations(rows, 2):

            dx = a["X (km)"] - b["X (km)"]
            dy = a["Y (km)"] - b["Y (km)"]
            dz = a["Z (km)"] - b["Z (km)"]

            distance = float(
                np.sqrt(dx**2 + dy**2 + dz**2)
            )

            pair_records.append({
                "Satellite 1": a["Satellite"],
                "Satellite 2": b["Satellite"],
                "Time": current_time,
                "Distance (km)": distance
            })

    pair_df = pd.DataFrame(pair_records)

    if pair_df.empty:
        return positions, pd.DataFrame(), errors

    # Find the minimum sampled distance for each pair.
    closest_indices = pair_df.groupby(
        ["Satellite 1", "Satellite 2"]
    )["Distance (km)"].idxmin()

    closest = (
        pair_df.loc[closest_indices]
        .sort_values("Distance (km)")
        .reset_index(drop=True)
    )

    closest["Distance (km)"] = closest["Distance (km)"].round(3)

    closest["Risk score"] = (
        closest["Distance (km)"].apply(calculate_risk_score)
    )

    closest["Risk level"] = (
        closest["Risk score"].apply(get_risk_level)
    )

    closest["Candidate"] = (
        closest["Distance (km)"] <= threshold_km
    )

    return positions, closest, errors


# ==========================================================
# REUSABLE DASHBOARD METRIC CARD
# ==========================================================

def metric_card(label, value, note):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


# ==========================================================
# OVERVIEW METRICS
# ==========================================================

st.markdown('<div class="section-label">01 / OVERVIEW</div>',
            unsafe_allow_html=True)

st.markdown('<div class="section-title">Mission Snapshot</div>',
            unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)

with c1:
    metric_card(
        "SATELLITES REQUESTED",
        str(num_satellites),
        "Selected for screening"
    )

with c2:
    metric_card(
        "SIMULATION WINDOW",
        f"{duration_hours} HRS",
        f"Sample interval: {step_minutes} min"
    )

with c3:
    metric_card(
        "DISTANCE THRESHOLD",
        f"{threshold} KM",
        "Candidate identification limit"
    )

st.markdown("")


# ==========================================================
# RUN SCREENING
# ==========================================================

st.markdown('<div class="section-label">02 / EXECUTION</div>',
            unsafe_allow_html=True)

st.markdown('<div class="section-title">Orbital Analysis</div>',
            unsafe_allow_html=True)

st.markdown("""
<div class="panel">
    <div style="color:#EAF2FF;font-weight:600;margin-bottom:7px;">
    Ready to initialize screening?
    </div>
    <div style="color:#9BAAC5;font-size:13px;line-height:1.7;">
    The system will load the local TLE catalog, propagate satellite
    positions using SGP4, and compare pairwise distances at matching
    sample times.
    </div>
</div>
""", unsafe_allow_html=True)

if st.button("🚀  INITIALIZE ORBITAL SCREENING", type="primary"):

    try:
        with st.spinner(
            "Initializing orbital engine and propagating satellite positions..."
        ):

            all_satellites = fetch_tle_data()

            selected = all_satellites[:num_satellites]

            if len(selected) < num_satellites:
                st.warning(
                    f"The TLE file contains only {len(selected)} "
                    f"valid satellite(s), fewer than the "
                    f"{num_satellites} requested."
                )

            positions, closest, errors = run_screening(
                selected,
                duration_hours,
                threshold,
                step_minutes
            )

            st.session_state["og_result"] = {
                "positions": positions,
                "closest": closest,
                "errors": errors,
                "selected_count": len(selected),
                "requested_count": num_satellites,
                "duration": duration_hours,
                "threshold": threshold,
                "step": step_minutes,
                "start_time": datetime.now(timezone.utc)
            }

        st.success("Orbital screening completed.")

    except FileNotFoundError:
        st.error(
            "satellites.tle was not found. Place it in the same "
            "folder as app.py."
        )

    except Exception as exc:
        st.error(f"Screening failed: {exc}")

        st.caption(
            "Verify the TLE file format and confirm that all "
            "required Python packages are installed."
        )


# ==========================================================
# RESULTS DASHBOARD
# ==========================================================

if "og_result" in st.session_state:

    result = st.session_state["og_result"]

    positions = result["positions"]
    closest = result["closest"]
    errors = result["errors"]

    # Avoid presenting results from an earlier configuration
    # as if they were calculated with the current settings.
    current_config = (
        result["requested_count"] == num_satellites
        and result["duration"] == duration_hours
        and result["threshold"] == threshold
        and result["step"] == step_minutes
    )

    if not current_config:
        st.warning(
            "Settings have changed since the last run. "
            "Initialize screening again to update these results."
        )

    st.markdown("---")

    st.markdown(
        '<div class="section-label">03 / LIVE RESULTS</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="section-title">Screening Intelligence</div>',
        unsafe_allow_html=True
    )

    candidate_count = (
        int(closest["Candidate"].sum())
        if not closest.empty
        else 0
    )

    highest_risk = (
        float(closest["Risk score"].max())
        if not closest.empty
        else 0
    )

    r1, r2, r3, r4 = st.columns(4)

    with r1:
        metric_card(
            "SATELLITES LOADED",
            str(result["selected_count"]),
            "Valid TLE records"
        )

    with r2:
        metric_card(
            "POSITION RECORDS",
            f"{len(positions):,}",
            "Successful propagation samples"
        )

    with r3:
        metric_card(
            "CANDIDATE PAIRS",
            str(candidate_count),
            f"Threshold: {result['threshold']} km"
        )

    with r4:
        metric_card(
            "HIGHEST RISK SCORE",
            f"{highest_risk:.2f}/10",
            "Illustrative proximity score"
        )

    # ------------------------------------------------------
    # CLOSEST APPROACH TABLE
    # ------------------------------------------------------

    st.markdown(
        '<div class="section-label">04 / PROXIMITY ANALYSIS</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="section-title">Closest Sampled Approaches</div>',
        unsafe_allow_html=True
    )

    st.caption(
        "Each row represents one satellite pair's minimum "
        "distance among the sampled timestamps."
    )

    if closest.empty:

        st.warning(
            "No pairwise results could be calculated. "
            "Check the TLE data and propagation errors."
        )

    else:

        display_df = closest.rename(
            columns={
                "Time": "Closest sampled time (UTC)",
                "Distance (km)": "Minimum distance (km)",
                "Candidate": "Below threshold"
            }
        ).copy()

        display_df["Closest sampled time (UTC)"] = (
            display_df["Closest sampled time (UTC)"]
            .dt.strftime("%Y-%m-%d %H:%M:%S")
        )

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            height=350,
            column_config={
                "Risk score": st.column_config.ProgressColumn(
                    "Risk score / 10",
                    min_value=0,
                    max_value=10,
                    format="%.2f"
                ),
                "Below threshold": st.column_config.CheckboxColumn(
                    "Below threshold"
                ),
                "Minimum distance (km)": st.column_config.NumberColumn(
                    "Minimum distance (km)",
                    format="%.3f"
                )
            }
        )

        # --------------------------------------------------
        # DISTANCE CHART
        # --------------------------------------------------

        st.markdown(
            '<div class="section-label">05 / VISUAL ANALYTICS</div>',
            unsafe_allow_html=True
        )

        st.markdown(
            '<div class="section-title">Satellite Proximity Map</div>',
            unsafe_allow_html=True
        )

        chart_df = closest.copy()

        chart_df["Pair"] = (
            chart_df["Satellite 1"]
            + " ↔ "
            + chart_df["Satellite 2"]
        )

        chart_df = chart_df.sort_values(
            "Distance (km)",
            ascending=True
        ).set_index("Pair")

        st.bar_chart(
            chart_df[["Distance (km)"]],
            horizontal=True,
            height=max(300, min(650, len(chart_df) * 35)),
            color="#45E5FF"
        )

        st.caption(
            "The chart displays minimum sampled separation in km. "
            "Shorter bars indicate closer sampled positions."
        )

        # --------------------------------------------------
        # CANDIDATE CLOSE APPROACHES
        # --------------------------------------------------

        st.markdown(
            '<div class="section-label">06 / ALERT CENTER</div>',
            unsafe_allow_html=True
        )

        st.markdown(
            '<div class="section-title">Candidate Close Approaches</div>',
            unsafe_allow_html=True
        )

        candidates = closest[closest["Candidate"]].copy()

        if candidates.empty:

            st.success(
                "No satellite pairs were within the selected "
                "threshold at the sampled timestamps."
            )

            st.info(
                "This does not rule out a close approach between "
                "samples or establish that all orbits are safe."
            )

        else:

            st.warning(
                f"{len(candidates)} satellite pair(s) met the "
                "screening threshold. Further orbital analysis "
                "is recommended."
            )

            for _, row in candidates.iterrows():

                if row["Risk level"] in ["Very High", "High"]:
                    color = "#FF6B83"
                elif row["Risk level"] in ["Moderate-High", "Moderate"]:
                    color = "#FFC66D"
                else:
                    color = "#55E5FF"

                time_text = row["Time"].strftime(
                    "%d %b %Y · %H:%M:%S UTC"
                )

                st.markdown(
                    f"""
                    <div style="
                        background:linear-gradient(110deg,#151F36,#10172A);
                        border:1px solid #2B3B5B;
                        border-left:4px solid {color};
                        border-radius:12px;
                        padding:17px 19px;
                        margin-bottom:12px;
                    ">
                        <div style="font-size:15px;font-weight:700;
                        color:#F1F5FF;">
                            {row['Satellite 1']}
                            <span style="color:#55E5FF;"> ↔ </span>
                            {row['Satellite 2']}
                        </div>
                        <div style="display:flex;flex-wrap:wrap;
                        gap:22px;margin-top:13px;">
                            <div>
                                <div style="font-size:10px;
                                color:#9BAAC5;">MINIMUM DISTANCE</div>
                                <div style="font-size:20px;
                                font-weight:700;color:{color};">
                                    {row['Distance (km)']:.3f} km
                                </div>
                            </div>
                            <div>
                                <div style="font-size:10px;
                                color:#9BAAC5;">RISK LEVEL</div>
                                <div style="font-size:15px;
                                font-weight:700;color:{color};">
                                    {row['Risk level']}
                                </div>
                            </div>
                            <div>
                                <div style="font-size:10px;
                                color:#9BAAC5;">RISK SCORE</div>
                                <div style="font-size:15px;
                                font-weight:700;color:#F1F5FF;">
                                    {row['Risk score']:.2f}/10
                                </div>
                            </div>
                        </div>
                        <div style="font-size:11px;color:#9BAAC5;
                        margin-top:12px;">
                            Closest sampled time: {time_text}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        # --------------------------------------------------
        # PROPAGATION ERRORS
        # --------------------------------------------------

        if errors:

            st.markdown(
                '<div class="section-title">Propagation Diagnostics</div>',
                unsafe_allow_html=True
            )

            st.warning(
                f"{len(errors)} propagation error(s) occurred. "
                "Some satellite positions were skipped."
            )

            st.dataframe(
                pd.DataFrame(errors),
                use_container_width=True,
                hide_index=True
            )

        # --------------------------------------------------
        # CSV DOWNLOADS
        # --------------------------------------------------

        st.markdown(
            '<div class="section-label">07 / DATA EXPORT</div>',
            unsafe_allow_html=True
        )

        st.markdown(
            '<div class="section-title">Export Mission Data</div>',
            unsafe_allow_html=True
        )

        d1, d2 = st.columns(2)

        with d1:

            if not positions.empty:

                st.download_button(
                    label="⬇️ Download Satellite Positions",
                    data=positions.to_csv(
                        index=False
                    ).encode("utf-8"),
                    file_name="orbit_guard_positions.csv",
                    mime="text/csv",
                    key="download_positions"
                )

        with d2:

            if not closest.empty:

                st.download_button(
                    label="⬇️ Download Screening Results",
                    data=closest.to_csv(
                        index=False
                    ).encode("utf-8"),
                    file_name="orbit_guard_screening.csv",
                    mime="text/csv",
                    key="download_screening"
                )


# ==========================================================
# FOOTER
# ==========================================================

st.markdown("""
<div class="footer">
    <div style="color:#55E5FF;font-weight:800;
    letter-spacing:2px;margin-bottom:8px;">
        🛰️ ORBIT GUARD
    </div>
    SPACE DEBRIS & SATELLITE PROXIMITY MONITORING<br>
    <span style="font-size:11px;">
        Built with Python · Streamlit · NumPy · Pandas · SGP4
    </span>
    <br><br>
    <span style="font-size:10px;">
        Educational simulation only · Not an operational collision
        avoidance or conjunction assessment system
    </span>
</div>
""", unsafe_allow_html=True)
