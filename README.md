# satellite-close-approach-dashboard
Satellite orbit tracking and close-approach monitoring prototype
# Orbit Guard — upgraded close-approach dashboard

## Features
- Fetches current CelesTrak GP/TLE data for the `active` and `debris` groups; live mode and five-minute dashboard refresh are compulsory in the UI.
- Uses a configurable object cap (up to 16,000) and automatic dashboard refresh every five minutes.
- Propagates objects with SGP4 and uses a SciPy KD-tree to screen nearby pairs instead of testing every possible pair at each timestamp.
- Shows distance-based risk scores and launch-hold review advisories for pairs exceeding a configurable threshold.
- Calculates accuracy, precision, recall, false-outcome rate, false-positive rate, and false-negative rate from an uploaded labeled CSV.
- Exports propagated positions and candidate close approaches.

## Run locally
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Live data and limitations
- Live feed is fetched from CelesTrak GP data using the `active` and `debris` groups. If the live provider fails or returns no valid data, the run stops rather than silently using stale local TLEs. Provider availability, rate limits, and catalog group sizes can change.
- The app uses live orbital elements, but a complete screening run is a sampled prediction over a selected time window, not continuously updated high-fidelity conjunction assessment.
- Results only include pairs within the screening radius at sampled times. A coarse sampling interval can miss close approaches.
- The dashboard defaults to 16,000 objects but the available feed may contain fewer unique valid records; the displayed count is the actual number loaded.
- The distance-based 1–10 score is illustrative and is not a probability of collision.
- A launch-hold message is a decision-support advisory only. This code does not control a launch system or calculate a validated maneuver vector. Operational decisions require authoritative conjunction data, covariance, probability-of-collision assessment, and qualified flight-dynamics review.
- Performance metrics require labeled reference data with columns `actual_collision` and `predicted_collision`, using 1/0, true/false, yes/no, or collision/safe labels. Do not present the sample template as real validation data.

## Evaluation CSV
Download `orbit_guard_evaluation_template.csv` from the dashboard or create a CSV:
```csv
actual_collision,predicted_collision
1,1
0,0
0,1
1,0
```
Replace sample rows with verified historical outcomes and the corresponding system predictions before reporting metrics.
