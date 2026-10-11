import io
import time
from datetime import datetime, timedelta, timezone
from itertools import combinations

import numpy as np
import pandas as pd
import requests
import streamlit as st
from scipy.spatial import cKDTree
from sgp4.api import Satrec, jday
from streamlit_autorefresh import st_autorefresh

# ==========================================================
# ORBIT GUARD | LIVE SPACE DEBRIS & CLOSE-APPROACH MONITOR
# ==========================================================
st.set_page_config(
    page_title="Orbit Guard | Space Surveillance",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap');
:root { --bg:#070B18; --panel:#10182B; --cyan:#45E5FF; --text:#F1F5FF; --muted:#9BAAC5; }
.stApp { background:radial-gradient(ellipse at 12% 0%,#14234A 0%,transparent 35%),radial-gradient(ellipse at 90% 20%,#201344 0%,transparent 32%),linear-gradient(145deg,#070B18 0%,#0A1021 55%,#080B18 100%); color:var(--text); font-family:'Inter',sans-serif; }
[data-testid="stHeader"] { background:rgba(7,11,24,.85); }
[data-testid="stSidebar"] { background:linear-gradient(180deg,#0D1529,#080D1C); border-right:1px solid #263654; }
[data-testid="stSidebar"] * { color:#E8F0FF; }
.block-container { padding-top:1.6rem; padding-bottom:2.5rem; max-width:1600px; }
h1,h2,h3 { font-family:'Space Grotesk',sans-serif !important; color:#F1F5FF !important; }
p,label,.stMarkdown,[data-testid="stCaptionContainer"] { color:#B8C5DE; }
.hero { padding:28px 30px; border:1px solid #29456B; border-radius:22px; background:radial-gradient(ellipse at 85% 0%,#263F76 0%,transparent 45%),linear-gradient(120deg,#111C35 0%,#11152C 55%,#21163F 100%); margin-bottom:20px; }
.hero-tag { display:inline-block; color:#54E9FF; background:rgba(69,229,255,.09); border:1px solid rgba(69,229,255,.32); border-radius:20px; padding:6px 12px; font-size:11px; font-weight:700; letter-spacing:1.8px; margin-bottom:12px; }
.hero-title { color:#FFF; font-family:'Space Grotesk',sans-serif; font-size:clamp(32px,4vw,48px); font-weight:700; line-height:1.12; }
.hero-title span { color:#55E5FF; }
.metric-card { background:linear-gradient(145deg,#141F36,#0E172A); border:1px solid #293B5C; border-radius:16px; padding:18px; min-height:115px; }
.metric-label { color:#9EAFCE; font-size:12px; font-weight:600; letter-spacing:.8px; text-transform:uppercase; }
.metric-value { color:#F5F8FF; font-family:'Space Grotesk',sans-serif; font-size:28px; font-weight:700; margin-top:10px; overflow-wrap:anywhere; }
.metric-note { color:#45E5FF; font-size:11px; margin-top:8px; }
.section-label { color:#55E5FF; font-size:11px; font-weight:800; letter-spacing:2px; margin:24px 0 5px; }
.section-title { font-family:'Space Grotesk',sans-serif; font-size:23px; font-weight:700; color:#F1F5FF; margin-bottom:14px; }
div.stButton > button { width:100%; border:1px solid #53E7FF; border-radius:11px; background:linear-gradient(100deg,#16A7CE,#6752DA); color:white; font-weight:800; padding:.72rem 1rem; }
[data-testid="stDataFrame"] { border:1px solid #293B5C; border-radius:12px; overflow:hidden; }
.footer { border-top:1px solid #263654; padding-top:18px; margin-top:35px; color:#8495B5; font-size:12px; text-align:center; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <div class="hero-tag">ORBITAL INTELLIGENCE · MISSION CONTROL</div>
  <div class="hero-title">🛰️ ORBIT <span>GUARD</span></div>
  <p>Live catalog ingestion, SGP4 propagation, scalable close-approach screening,
  risk-based launch-hold advisories, and measurable model evaluation.</p>
</div>
""", unsafe_allow_html=True)

st.warning(
    "Research prototype, not a certified conjunction assessment system. "
    "Distance-based scores are screening indicators, not collision probabilities. "
    "Launch holds and maneuver suggestions are advisory only; no spacecraft or launch "
    "system is controlled by this dashboard."
)

CELESTRAK_BASE = "https://celestrak.org/NORAD/elements/gp.php"
DEFAULT_LOCAL_TLE = "satellites.tle"
MAX_OBJECTS_DEFAULT = 16000


def parse_tle_text(text):
    """Parse 3-line TLE records and validate them with SGP4."""
    lines = [line.strip() for line in text.replace("\r", "").split("\n") if line.strip()]
    sats, seen = [], set()
    i = 0
    while i + 2 < len(lines):
        name, line1, line2 = lines[i:i + 3]
        if line1.startswith("1 ") and line2.startswith("2 "):
            catalog = line1[2:7].strip()
            if catalog and catalog not in seen:
                try:
                    sat = Satrec.twoline2rv(line1, line2)
                    sats.append({
                        "name": name[:80],
                        "catalog_number": catalog,
                        "satrec": sat,
                        "source": "CelesTrak/live" if "celestrak" in text[:200].lower() else "TLE catalog",
                    })
                    seen.add(catalog)
                except Exception:
                    pass
            i += 3
        else:
            i += 1
    return sats


@st.cache_data(ttl=300, show_spinner=False)
def fetch_live_tle_text():
    """Fetch live GP TLEs; combine active and debris groups and de-duplicate."""
    headers = {"User-Agent": "OrbitGuard-Research-Dashboard/1.0"}
    all_lines, seen = [], set()
    group_counts = {}
    errors = []
    # CelesTrak publishes these catalog groups as current GP/TLE data.
    for group in ("active", "debris"):
        try:
            response = requests.get(
                CELESTRAK_BASE,
                params={"GROUP": group, "FORMAT": "tle"},
                headers=headers,
                timeout=(8, 45),
            )
            response.raise_for_status()
            body = response.text.strip()
            if not body or "error" in body[:100].lower():
                raise ValueError("Provider returned an empty/error response")
            parsed_lines = [x.strip() for x in body.splitlines() if x.strip()]
            before = len(seen)
            for j in range(0, len(parsed_lines) - 2, 3):
                name, line1, line2 = parsed_lines[j:j + 3]
                if line1.startswith("1 ") and line2.startswith("2 "):
                    catalog = line1[2:7].strip()
                    if catalog and catalog not in seen:
                        all_lines.extend([name, line1, line2])
                        seen.add(catalog)
            group_counts[group] = len(seen) - before
        except Exception as exc:
            errors.append(f"{group}: {exc}")
    return "\n".join(all_lines), group_counts, errors, datetime.now(timezone.utc).isoformat()


def load_local_tle():
    with open(DEFAULT_LOCAL_TLE, "r", encoding="utf-8-sig") as f:
        return parse_tle_text(f.read())


def get_catalog(use_live, max_objects):
    # Live data is compulsory: fail closed instead of presenting stale local TLEs as real-time.
    text, group_counts, errors, fetched_at = fetch_live_tle_text()
    sats = parse_tle_text(text)
    if not sats:
        detail = "; ".join(errors) if errors else "Provider returned no valid orbital elements."
        raise RuntimeError(
            "The live CelesTrak feed is unavailable or returned no valid records. "
            "Screening was stopped so stale local data cannot be mislabeled as real-time. "
            f"Provider details: {detail}"
        )
    return sats[:max_objects], "LIVE CelesTrak (active + debris)", group_counts, errors, fetched_at


def calculate_risk_score(distance_km):
    # Illustrative proximity score only. This is not a collision probability.
    return round(float(np.clip(10.0 - float(distance_km) / 100.0, 1.0, 10.0)), 2)


def get_risk_level(score):
    if score >= 9.5:
        return "Critical"
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


def propagate_positions(satellites, times):
    """Propagate all objects at each sample time and return ECI/TEME position rows."""
    records, errors = [], []
    for sat in satellites:
        satrec = sat["satrec"]
        for current_time in times:
            jd, fr = jday(
                current_time.year, current_time.month, current_time.day,
                current_time.hour, current_time.minute,
                current_time.second + current_time.microsecond / 1_000_000,
            )
            code, position, _velocity = satrec.sgp4(jd, fr)
            if code != 0:
                if len(errors) < 500:
                    errors.append({"Satellite": sat["name"], "Catalog number": sat["catalog_number"], "Error code": code})
                continue
            records.append((
                current_time, sat["name"], sat["catalog_number"],
                float(position[0]), float(position[1]), float(position[2]),
            ))
    return records, errors


def run_screening(satellites, hours, threshold_km, interval_minutes, max_pairs=50000):
    """
    Use a spatial KD-tree at each timestamp to avoid the O(N^2) all-pairs scan.
    Only pairs within the configured screening distance are retained.
    """
    start_time = datetime.now(timezone.utc).replace(microsecond=0)
    total_steps = int(hours * 60 / interval_minutes) + 1
    times = [start_time + timedelta(minutes=interval_minutes * i) for i in range(total_steps)]
    records, errors = propagate_positions(satellites, times)
    if not records:
        return pd.DataFrame(), pd.DataFrame(), errors, start_time, len(times)

    positions = pd.DataFrame(records, columns=[
        "Time", "Satellite", "Catalog number", "X (km)", "Y (km)", "Z (km)"
    ])
    # Keep only the minimum sampled distance for each catalog-number pair.
    best = {}
    truncated = False
    for current_time, frame in positions.groupby("Time", sort=False):
        xyz = frame[["X (km)", "Y (km)", "Z (km)"]].to_numpy(dtype=float)
        if len(xyz) < 2:
            continue
        tree = cKDTree(xyz)
        pair_indices = tree.query_pairs(r=float(threshold_km), output_type="ndarray")
        if pair_indices.size == 0:
            continue
        # A high threshold can produce many candidates; cap retained candidates for UI safety.
        for ia, ib in pair_indices:
            a, b = frame.iloc[int(ia)], frame.iloc[int(ib)]
            distance = float(np.linalg.norm(xyz[int(ia)] - xyz[int(ib)]))
            id_a, id_b = str(a["Catalog number"]), str(b["Catalog number"])
            key = tuple(sorted((id_a, id_b)))
            old = best.get(key)
            if old is None or distance < old["Distance (km)"]:
                best[key] = {
                    "Satellite 1": a["Satellite"] if id_a <= id_b else b["Satellite"],
                    "Catalog 1": key[0],
                    "Satellite 2": b["Satellite"] if id_a <= id_b else a["Satellite"],
                    "Catalog 2": key[1],
                    "Time": current_time,
                    "Distance (km)": distance,
                }
            if len(best) >= max_pairs:
                truncated = True
                break
        if truncated:
            break
    closest = pd.DataFrame(list(best.values()))
    if not closest.empty:
        closest["Distance (km)"] = closest["Distance (km)"].round(3)
        closest["Risk score"] = closest["Distance (km)"].apply(calculate_risk_score)
        closest["Risk level"] = closest["Risk score"].apply(get_risk_level)
        closest["Candidate"] = True
        closest = closest.sort_values("Distance (km)").reset_index(drop=True)
    if truncated:
        errors.append({"Satellite": "SYSTEM", "Catalog number": "-", "Error code": f"Candidate list capped at {max_pairs:,} pairs; increase filtering or use a smaller threshold."})
    return positions, closest, errors, start_time, len(times)


def metric_card(label, value, note):
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div><div class="metric-note">{note}</div></div>',
        unsafe_allow_html=True,
    )


def truthy(value):
    if pd.isna(value):
        return np.nan
    if isinstance(value, (bool, np.bool_)):
        return int(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "collision", "positive"}:
        return 1
    if text in {"0", "false", "no", "n", "no collision", "negative", "safe"}:
        return 0
    return np.nan


# -------------------- Sidebar controls --------------------
st.sidebar.markdown("## Mission Control")
st.sidebar.caption("Live orbital data and screening settings")
# Live data and automatic refresh are compulsory for this version.
use_live = True
auto_refresh = True
st.sidebar.success("LIVE DATA REQUIRED · auto-refresh every 5 minutes")
st_autorefresh(interval=300_000, key="orbit_guard_refresh")
if st.sidebar.button("↻ Force fresh catalog download"):
    fetch_live_tle_text.clear()
    st.rerun()

max_objects = st.sidebar.select_slider(
    "Objects to process",
    options=[100, 500, 1000, 2500, 5000, 10000, 16000],
    value=16000,
    help="Live catalog is capped at this many unique objects for manageable runtime.",
)
duration_hours = st.sidebar.selectbox("Prediction window", [1, 3, 6, 12, 24], index=0)
step_minutes = st.sidebar.selectbox("Sampling interval", [1, 2, 5, 10, 15], index=2)
threshold = st.sidebar.slider("Close-approach screening distance (km)", 1, 1000, 50, 1)
risk_threshold = st.sidebar.slider("High-risk score threshold", 1.0, 10.0, 9.5, 0.1)
st.sidebar.caption("Screening is sampled at the selected interval; a coarse interval may miss an encounter.")

# -------------------- Catalog status --------------------
st.markdown('<div class="section-label">01 / LIVE CATALOG</div>', unsafe_allow_html=True)
st.markdown('<div class="section-title">Orbital Data Feed</div>', unsafe_allow_html=True)

if st.button("🚀 LOAD CATALOG & RUN CLOSE-APPROACH SCREENING", type="primary"):
    try:
        with st.spinner("Loading orbital catalog and propagating selected objects..."):
            satellites, source_label, group_counts, source_errors, fetched_at = get_catalog(use_live, max_objects)
            positions, closest, errors, start_time, n_steps = run_screening(
                satellites, duration_hours, threshold, step_minutes
            )
            st.session_state["og_result"] = {
                "positions": positions, "closest": closest, "errors": errors,
                "selected_count": len(satellites), "source": source_label,
                "group_counts": group_counts, "source_errors": source_errors,
                "fetched_at": fetched_at, "start_time": start_time,
                "duration": duration_hours, "threshold": threshold,
                "step": step_minutes, "risk_threshold": risk_threshold,
                "max_objects": max_objects, "n_steps": n_steps,
                "auto_refresh": auto_refresh, "use_live": use_live,
            }
        st.success("Screening run completed.")
    except Exception as exc:
        st.error(f"Screening failed: {exc}")

if "og_result" in st.session_state:
    result = st.session_state["og_result"]
    positions, closest, errors = result["positions"], result["closest"], result["errors"]
    if result["source"].startswith("LIVE"):
        st.success(f"Data source: {result['source']} · Objects loaded: {result['selected_count']:,}")
    else:
        st.error("Non-live data source. Do not treat these results as real-time.")
    fetched_at = result.get("fetched_at")
    if fetched_at:
        st.caption(f"Catalog fetch timestamp (UTC): {fetched_at}")
    st.caption(
        f"Screening run started: {result['start_time'].strftime('%Y-%m-%d %H:%M:%S UTC')} · "
        f"{result['n_steps']} sampled times · {result['step']} minute interval · "
        f"screening radius {result['threshold']} km"
    )
    if result["group_counts"]:
        st.caption("New unique records by group: " + " · ".join(f"{k}: {v:,}" for k, v in result["group_counts"].items()))
    for err in result["source_errors"]:
        st.info(f"Catalog note: {err}")

    config_matches = (
        result["duration"] == duration_hours and result["threshold"] == threshold
        and result["step"] == step_minutes and result["risk_threshold"] == risk_threshold
        and result["max_objects"] == max_objects
    )
    if not config_matches:
        st.warning("Settings changed since the last run. Run screening again to apply the new settings.")

    candidate_count = len(closest)
    highest_risk = float(closest["Risk score"].max()) if not closest.empty else 0.0
    hold_candidates = closest[closest["Risk score"] >= result["risk_threshold"]] if not closest.empty else closest
    if not hold_candidates.empty:
        st.error(
            f"⛔ LAUNCH-HOLD ADVISORY: {len(hold_candidates):,} candidate pair(s) meet or exceed "
            f"the configured risk-score threshold ({result['risk_threshold']:.1f}/10). "
            "Pause the simulated launch decision pending qualified conjunction review."
        )
    else:
        st.success("No sampled candidate pair exceeded the configured launch-hold advisory threshold.")
    st.caption("This is an advisory rule based on the prototype's distance score, not a certified launch decision.")

    st.markdown('<div class="section-label">02 / MISSION SNAPSHOT</div>', unsafe_allow_html=True)
    cols = st.columns(4)
    metrics = [
        ("OBJECTS LOADED", f"{result['selected_count']:,}", "Satellites + cataloged debris"),
        ("POSITION SAMPLES", f"{len(positions):,}", "Successful SGP4 propagation records"),
        ("CLOSE-APPROACH PAIRS", f"{candidate_count:,}", f"Within {result['threshold']} km at a sampled time"),
        ("HIGHEST RISK SCORE", f"{highest_risk:.2f}/10", "Illustrative distance score"),
    ]
    for col, (label, value, note) in zip(cols, metrics):
        with col:
            metric_card(label, value, note)

    st.markdown('<div class="section-label">03 / CLOSE-APPROACH ANALYSIS</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Closest Sampled Approaches</div>', unsafe_allow_html=True)
    st.caption("Only pairs observed within the screening radius at a sampled timestamp are retained. Encounters between samples may be missed.")
    if closest.empty:
        st.info("No pairs were found inside the configured screening radius at the sampled timestamps. This does not prove that all objects are safe.")
    else:
        display = closest.copy()
        display["Time"] = display["Time"].dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        display = display.rename(columns={"Time": "Closest sampled time (UTC)", "Distance (km)": "Minimum sampled distance (km)"})
        st.dataframe(display, use_container_width=True, hide_index=True, height=380)
        chart = closest.head(50).copy()
        chart["Pair"] = chart["Satellite 1"] + " ↔ " + chart["Satellite 2"]
        st.markdown("#### 50 closest candidate pairs")
        st.bar_chart(chart.set_index("Pair")[["Distance (km)"]], horizontal=True, height=550)

        st.markdown('<div class="section-label">04 / MANEUVER & LAUNCH ADVISORY</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Risk-Based Review Queue</div>', unsafe_allow_html=True)
        for _, row in hold_candidates.head(25).iterrows():
            st.error(
                f"LAUNCH HOLD REVIEW · {row['Satellite 1']} ({row['Catalog 1']}) ↔ "
                f"{row['Satellite 2']} ({row['Catalog 2']}) · "
                f"{row['Distance (km)']:.3f} km · score {row['Risk score']:.2f}/10 · "
                f"closest sampled time {row['Time'].strftime('%Y-%m-%d %H:%M:%S UTC')}"
            )
            st.write(
                "Recommended next step: obtain an authoritative conjunction assessment, review covariance and "
                "probability-of-collision data, and have qualified flight-dynamics personnel evaluate a maneuver. "
                "This prototype does not calculate a safe burn vector or execute a maneuver."
            )
        if hold_candidates.empty:
            st.info("No pairs exceeded the configured risk threshold. Continue monitoring and use authoritative conjunction data for launch decisions.")

    if errors:
        st.markdown("#### Propagation and screening diagnostics")
        st.warning(f"{len(errors):,} diagnostic item(s) were recorded (display capped at 500 propagation errors plus system notes).")
        st.dataframe(pd.DataFrame(errors), use_container_width=True, hide_index=True)

    st.markdown('<div class="section-label">05 / EXPORT</div>', unsafe_allow_html=True)
    e1, e2 = st.columns(2)
    with e1:
        if not positions.empty:
            st.download_button(
                "⬇️ Download propagated positions CSV",
                positions.to_csv(index=False).encode("utf-8"),
                "orbit_guard_positions.csv", "text/csv",
            )
    with e2:
        if not closest.empty:
            st.download_button(
                "⬇️ Download close-approach results CSV",
                closest.to_csv(index=False).encode("utf-8"),
                "orbit_guard_close_approaches.csv", "text/csv",
            )
else:
    st.info("Choose live data and screening settings, then run the analysis. Live catalog refresh is enabled by default; calculations run when you press the button.")

# -------------------- Evaluation metrics --------------------
st.markdown("---")
st.markdown('<div class="section-label">06 / MODEL PERFORMANCE</div>', unsafe_allow_html=True)
st.markdown('<div class="section-title">Accuracy & False-Outcome Evaluation</div>', unsafe_allow_html=True)
st.write(
    "Upload a labeled CSV containing both predictions and verified outcomes. "
    "The dashboard will calculate metrics from those labels; it does not invent an accuracy score from orbital predictions alone."
)
template = pd.DataFrame({
    "actual_collision": [1, 0, 0, 1],
    "predicted_collision": [1, 0, 1, 0],
})
st.download_button(
    "Download evaluation CSV template",
    template.to_csv(index=False).encode("utf-8"),
    "orbit_guard_evaluation_template.csv",
    "text/csv",
)
uploaded = st.file_uploader("Upload labeled evaluation CSV", type=["csv"], key="evaluation_upload")
if uploaded is not None:
    try:
        eval_df = pd.read_csv(uploaded)
        required = {"actual_collision", "predicted_collision"}
        if not required.issubset(eval_df.columns):
            st.error("CSV must contain columns named actual_collision and predicted_collision, using 1/0 or true/false labels.")
        else:
            actual = eval_df["actual_collision"].map(truthy)
            predicted = eval_df["predicted_collision"].map(truthy)
            valid = actual.notna() & predicted.notna()
            actual = actual[valid].astype(int).to_numpy()
            predicted = predicted[valid].astype(int).to_numpy()
            if len(actual) == 0:
                st.error("No valid labeled rows found. Use 1/0, true/false, yes/no, collision/safe.")
            else:
                tp = int(((actual == 1) & (predicted == 1)).sum())
                tn = int(((actual == 0) & (predicted == 0)).sum())
                fp = int(((actual == 0) & (predicted == 1)).sum())
                fn = int(((actual == 1) & (predicted == 0)).sum())
                total = len(actual)
                accuracy = (tp + tn) / total
                precision = tp / (tp + fp) if tp + fp else np.nan
                recall = tp / (tp + fn) if tp + fn else np.nan
                fpr = fp / (fp + tn) if fp + tn else np.nan
                fnr = fn / (fn + tp) if fn + tp else np.nan
                false_outcome = (fp + fn) / total
                st.caption(f"Evaluated {total:,} valid labeled rows; ignored {len(eval_df) - total:,} invalid/incomplete rows.")
                metric_cols = st.columns(4)
                for col, (label, val, note) in zip(metric_cols, [
                    ("ACCURACY", accuracy, "(TP + TN) / all cases"),
                    ("FALSE OUTCOME RATE", false_outcome, "(FP + FN) / all cases"),
                    ("PRECISION", precision, "Positive predictions that were correct"),
                    ("RECALL", recall, "Actual positives detected"),
                ]):
                    with col:
                        metric_card(label, "N/A" if pd.isna(val) else f"{val * 100:.2f}%", note)
                st.write("#### Confusion matrix")
                cm = pd.DataFrame(
                    [[tn, fp], [fn, tp]],
                    index=["Actual: no collision", "Actual: collision"],
                    columns=["Predicted: no collision", "Predicted: collision"],
                )
                st.dataframe(cm, use_container_width=True)
                extra_cols = st.columns(2)
                with extra_cols[0]:
                    st.metric("False-positive rate", "N/A" if pd.isna(fpr) else f"{fpr * 100:.2f}%")
                with extra_cols[1]:
                    st.metric("False-negative rate", "N/A" if pd.isna(fnr) else f"{fnr * 100:.2f}%")
                st.caption("TP = true positive, TN = true negative, FP = false positive, FN = false negative. Metrics are only as trustworthy as the uploaded labels and the evaluation design.")
    except Exception as exc:
        st.error(f"Could not evaluate the uploaded CSV: {exc}")

st.markdown("""
<div class="footer">
  <div style="color:#55E5FF;font-weight:800;letter-spacing:2px;margin-bottom:8px;">🛰️ ORBIT GUARD</div>
  SPACE DEBRIS & SATELLITE PROXIMITY MONITORING<br>
  <span>Python · Streamlit · NumPy · Pandas · SciPy KD-tree · SGP4 · CelesTrak GP data</span><br><br>
  <span>Educational decision-support prototype · Not certified for operational collision avoidance</span>
</div>
""", unsafe_allow_html=True)
