import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="EU Flight Delay Monitor",
    page_icon="✈️",
    layout="wide",
)

st.title("✈️ EU Flight Delay & Compensation Monitor")
st.write("Your flight monitoring dashboard")

st.info(
    "Demo mode: these are example flights, not live flight data."
)

distance = st.slider(
    "Minimum flight distance (km)",
    min_value=1500,
    max_value=4000,
    value=1500,
    step=100,
)

threshold = st.slider(
    "Arrival delay warning threshold (minutes)",
    min_value=60,
    max_value=240,
    value=180,
    step=30,
)

col1, col2 = st.columns(2)
col1.metric("Minimum route distance", f"{distance:,} km")
col2.metric("Delay warning threshold", f"{threshold} minutes")

flights = pd.DataFrame([
    {
        "Flight": "AB123",
        "Route": "Paris → Madrid",
        "Distance (km)": 1050,
        "Arrival delay (min)": 210,
    },
    {
        "Flight": "CD456",
        "Route": "Frankfurt → Rome",
        "Distance (km)": 960,
        "Arrival delay (min)": 45,
    },
    {
        "Flight": "EF789",
        "Route": "Amsterdam → Athens",
        "Distance (km)": 2160,
        "Arrival delay (min)": 195,
    },
])

st.subheader("Flight monitor")

filtered = flights[
    (flights["Distance (km)"] >= distance)
    & (flights["Arrival delay (min)"] >= threshold)
]

if filtered.empty:
    st.success("No example flights match your selected filters.")
else:
    st.warning(f"{len(filtered)} example flight(s) need attention.")
    st.dataframe(filtered, use_container_width=True)

st.caption(
    "Demo data only. A delay warning does not guarantee "
    "compensation. EU261 eligibility depends on the actual "
    "arrival delay, route, airline, and circumstances."
)
