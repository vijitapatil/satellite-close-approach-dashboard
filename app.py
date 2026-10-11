
import streamlit as st
import pandas as pd
import numpy as np

from itertools import combinations
from datetime import datetime, timedelta, timezone
from sgp4.api import Satrec, jday

# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Orbit Guard",
    page_icon="🛰️",
    layout="wide"
)

st.title("🛰️ Orbit Guard")
st.subheader("Satellite Close-Approach Monitoring System")

st.write(
    "Monitor satellite positions and screen for potential "
    "close approaches using orbital data."
)

st.info(
    "Educational prototype only. Results use sampled positions "
    "and are not certified collision predictions."
)

# --------------------------------------------------
# SIDEBAR SETTINGS
# --------------------------------------------------

st.sidebar.header("Simulation Settings")

num_satellites = st.sidebar.selectbox(
    "Number of satellites",
    [5, 10],
    index=0
)

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

step_minutes = 10

# --------------------------------------------------
# LOAD SATELLITES FROM LOCAL TLE FILE
# --------------------------------------------------

def fetch_tle_data():
    satellites = []

    with open("satellites.tle", "r", encoding="utf-8") as f:
        lines = [
            line.strip()
            for line in f
            if line.strip()
        ]

    # TLE format: satellite name, line 1, line 2
    for i in range(0, len(lines) - 2, 3):
        name, line1, line2 = lines[i:i + 3]

        if line1.startswith("1 ") and line2.startswith("2 "):
            try:
                sat = Satrec.twoline2rv(line1, line2)

                satellites.append({
                    "name": name,
                    "catalog_number": line1[2:7].strip(),
                    "satrec": sat
                })

            except Exception:
                continue

    if not satellites:
        raise ValueError(
            "No valid satellites found. Check satellites.tle "
            "contains satellite names, TLE line 1, and TLE line 2."
        )

    return satellites

# --------------------------------------------------
# RISK SCORE CALCULATION
# --------------------------------------------------

def calculate_risk_score(distance):
    if distance < 200:
        score = 10 - (distance / 200)

    elif distance < 300:
        score = 9 - ((distance - 200) / 100)

    elif distance < 400:
        score = 8 - ((distance - 300) / 100)

    elif distance < 500:
        score = 7 - ((distance - 400) / 100)

    elif distance < 600:
        score = 6 - ((distance - 500) / 100)

    elif distance < 700:
        score = 5 - ((distance - 600) / 100)

    elif distance < 800:
        score = 4 - ((distance - 700) / 100)

    elif distance < 900:
        score = 3 - ((distance - 800) / 100)

    elif distance <= 1000:
        score = 2 - ((distance - 900) / 100)

    else:
        score = 1

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

# --------------------------------------------------
# CALCULATE POSITIONS AND SCREEN CLOSE APPROACHES
# --------------------------------------------------

def run_screening(satellites, hours, threshold_km):

    start_time = datetime.now(timezone.utc)

    total_steps = int(hours * 60 / step_minutes) + 1

    times = [
        start_time + timedelta(minutes=step_minutes * i)
        for i in range(total_steps)
    ]

    position_records = []
    errors = []

    # Propagate every satellite at each sample time
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

    # Compare satellite pairs at matching times
    pair_records = []

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

    # Find minimum sampled distance for each satellite pair
    closest_indices = pair_df.groupby(
        ["Satellite 1", "Satellite 2"]
    )["Distance (km)"].idxmin()

    closest = (
        pair_df.loc[closest_indices]
        .sort_values("Distance (km)")
        .reset_index(drop=True)
    )

     # Assign risk score and risk level
    closest["Risk score"] = (
        closest["Distance (km)"].apply(calculate_risk_score)
    )

    closest["Risk level"] = (
        closest["Risk score"].apply(get_risk_level)
    )

# Identify candidate close approaches
    closest["Candidate"] = (
        closest["Distance (km)"] <= threshold_km
    )

    return positions, closest, errors


# --------------------------------------------------
# DASHBOARD OVERVIEW
# --------------------------------------------------

col1, col2, col3 = st.columns(3)

col1.metric("Satellites requested", num_satellites)
col2.metric("Simulation duration", f"{duration_hours} hours")
col3.metric("Screening threshold", f"{threshold} km")

st.divider()

# --------------------------------------------------
# RUN SCREENING BUTTON
# --------------------------------------------------

if st.button("🚀 Run Screening", type="primary"):

    try:
        with st.spinner(
            "Loading TLE data and calculating satellite positions..."
        ):

            all_satellites = fetch_tle_data()

            selected = all_satellites[:num_satellites]

            positions, closest, errors = run_screening(
                selected,
                duration_hours,
                threshold
            )

        st.success("Screening completed successfully!")

        candidate_count = (
            int(closest["Candidate"].sum())
            if not closest.empty
            else 0
        )

        m1, m2, m3 = st.columns(3)

        m1.metric("Satellites loaded", len(selected))
        m2.metric("Position records", len(positions))
        m3.metric("Candidate pairs", candidate_count)

        # ------------------------------------------
        # CLOSEST APPROACH RESULTS
        # ------------------------------------------

        st.subheader("📍 Closest Sampled Approaches")

        if closest.empty:

            st.warning(
                "No pairwise results could be calculated. "
                "Check the TLE file and propagation errors."
            )

        else:

            st.caption(
                "Each row shows one satellite pair's minimum "
                "distance among the sampled times."
            )

            display_df = closest.rename(
                columns={
                    "Time": "Sampled closest time",
                    "Distance (km)": "Minimum sampled distance (km)",
                    "Candidate": "Below threshold"
                }
            )

            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True
            )

            # --------------------------------------
            # DISTANCE CHART
            # --------------------------------------

            st.subheader("📊 Minimum Sampled Distance by Pair")

            chart_df = closest.copy()

            chart_df["Pair"] = (
                chart_df["Satellite 1"]
                + " ↔ "
                + chart_df["Satellite 2"]
            )

            chart_df = chart_df.set_index("Pair")

            st.bar_chart(chart_df["Distance (km)"])

            # --------------------------------------
            # CANDIDATE PAIRS
            # --------------------------------------

            st.subheader("🔎 Candidate Close Approaches")

            candidates = closest[closest["Candidate"]]

            if candidates.empty:

                st.info(
                    "No satellite pairs were within the selected "
                    "threshold at the sampled times. An encounter "
                    "between samples cannot be ruled out."
                )

            else:

                st.warning(
                    f"{len(candidates)} satellite pair(s) "
                    "met the screening threshold."
                )

                st.dataframe(
                    candidates,
                    use_container_width=True,
                    hide_index=True
                )

        # ------------------------------------------
        # PROPAGATION ERRORS
        # ------------------------------------------

        if errors:

            st.warning(
                f"{len(errors)} propagation error(s) occurred. "
                "Some positions may have been skipped."
            )

        # ------------------------------------------
        # DOWNLOAD RESULTS
        # ------------------------------------------

        st.subheader("⬇️ Download Results")

        if not positions.empty:

            st.download_button(
                "Download Satellite Positions (CSV)",
                data=positions.to_csv(
                    index=False
                ).encode("utf-8"),
                file_name="satellite_positions.csv",
                mime="text/csv"
            )

        if not closest.empty:

            st.download_button(
                "Download Screening Results (CSV)",
                data=closest.to_csv(
                    index=False
                ).encode("utf-8"),
                file_name="close_approach_screening.csv",
                mime="text/csv"
            )

    except FileNotFoundError:

        st.error(
            "satellites.tle was not found. Make sure it is in "
            "the same project folder as app.py."
        )

    except Exception as exc:

        st.error(f"Screening failed: {exc}")

        st.caption(
            "Check that satellites.tle contains valid TLE data "
            "and that all required Python packages are installed."
        )

# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.divider()

st.caption(
    "Orbit Guard | Educational prototype | SGP4 orbital propagation"
)
