import math
import requests
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="EU Flight Delay Monitor",
    page_icon="✈️",
    layout="wide",
)

st.title("✈️ EU Flight Delay & Compensation Monitor")
st.write("Live flight status for long-distance European routes")

# Coordinates for selected European airports.
# We can expand this list later.
AIRPORTS = {
    "LHR": (51.4700, -0.4543),
    "CDG": (49.0097, 2.5479),
    "FRA": (50.0379, 8.5622),
    "AMS": (52.3105, 4.7683),
    "MAD": (40.4983, -3.5676),
    "FCO": (41.8003, 12.2389),
    "MUC": (48.3538, 11.7861),
    "BCN": (41.2974, 2.0833),
    "LIS": (38.7742, -9.1342),
    "ATH": (37.9364, 23.9445),
    "VIE": (48.1103, 16.5697),
    "ZRH": (47.4581, 8.5555),
    "CPH": (55.6181, 12.6560),
    "OSL": (60.1976, 11.1004),
    "ARN": (59.6519, 17.9186),
    "HEL": (60.3172, 24.9633),
    "DUB": (53.4213, -6.2701),
    "BRU": (50.9010, 4.4844),
    "WAW": (52.1657, 20.9671),
    "PRG": (50.1008, 14.2600),
    "BUD": (47.4298, 19.2611),
    "IST": (41.2753, 28.7519),
    "JFK": (40.6413, -73.7781),
    "DXB": (25.2532, 55.3657),
}

def distance_km(origin, destination):
    if origin not in AIRPORTS or destination not in AIRPORTS:
        return None

    lat1, lon1 = AIRPORTS[origin]
    lat2, lon2 = AIRPORTS[destination]

    lat1, lat2 = math.radians(lat1), math.radians(lat2)
    dlat = lat2 - lat1
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    return round(
        6371 * 2 * math.atan2(
            math.sqrt(a), math.sqrt(1 - a)
        )
    )

@st.cache_data(ttl=3600)
def load_flights(api_key):
    response = requests.get(
        "https://api.aviationstack.com/v1/flights",
        params={
            "access_key": api_key,
            "limit": 100,
            "dep_iata": "LHR",
        },
        timeout=30,
    )
    response.raise_for_status()
    result = response.json()

    if "error" in result:
        message = result["error"].get(
            "info", "The flight API returned an error."
        )
        raise ValueError(message)

    return result.get("data", [])

with st.sidebar:
    st.header("Monitor settings")

    min_distance = st.slider(
        "Minimum flight distance (km)",
        1500, 4000, 1500, 100,
    )

    delay_threshold = st.slider(
        "Arrival delay warning (minutes)",
        60, 240, 180, 30,
    )

    st.caption("Data refresh is limited to protect your free API allowance.")

if st.button("Refresh flight data"):
    load_flights.clear()

try:
    api_key = st.secrets["AVIATIONSTACK_API_KEY"]
    flights = load_flights(api_key)

    rows = []

    for flight in flights:
        departure = flight.get("departure") or {}
        arrival = flight.get("arrival") or {}
        airline = flight.get("airline") or {}
        details = flight.get("flight") or {}

        origin = departure.get("iata")
        destination = arrival.get("iata")
        km = distance_km(origin, destination)

        # Only show routes whose airport coordinates are known.
        if km is None or km < min_distance:
            continue

        delay = arrival.get("delay")

        rows.append({
            "Flight": details.get("iata") or "Unknown",
            "Airline": airline.get("name") or "Unknown",
            "Route": f"{origin} → {destination}",
            "Distance (km)": km,
            "Status": flight.get("flight_status") or "Unknown",
            "Arrival delay (min)": delay,
            "Scheduled arrival": arrival.get("scheduled"),
            "Warning": (
                "Check delay"
                if isinstance(delay, (int, float))
                and delay >= delay_threshold
                else "No confirmed warning"
                if isinstance(delay, (int, float))
                else "Delay unavailable"
            ),
        })

    st.caption(
        f"API flights received: {len(flights)}. "
        "Results are limited to routes with known airport coordinates."
    )

    if rows:
        df = pd.DataFrame(rows)
        df = df.sort_values(
            "Arrival delay (min)",
            ascending=False,
            na_position="last",
        )

        warnings = df[
            df["Arrival delay (min)"].apply(
                lambda x: isinstance(x, (int, float))
                and x >= delay_threshold
            )
        ]

        col1, col2, col3 = st.columns(3)
        col1.metric("Long-distance flights", len(df))
        col2.metric("Delay warnings", len(warnings))
        col3.metric("Distance filter", f"{min_distance:,} km")

        st.subheader("Flights to monitor")
        st.dataframe(df, use_container_width=True, hide_index=True)

        if not warnings.empty:
            st.warning(
                "Some flights have reported arrival delays "
                "above your selected threshold."
            )

        st.download_button(
            "Download flight results (CSV)",
            df.to_csv(index=False),
            file_name="flight_monitor.csv",
            mime="text/csv",
        )
    else:
        st.info(
            "No matching flights were returned. This does not "
            "mean no long-distance flights are delayed. Try "
            "refreshing later."
        )

except KeyError:
    st.error(
        "API key not found. Check your Streamlit app Secrets "
        "settings and the key name."
    )
except (requests.RequestException, ValueError) as error:
    st.error(f"Could not load flight data: {error}")
except Exception as error:
    st.error(f"Something went wrong: {error}")

st.caption(
    "Live flight status depends on API coverage. Flight distance "
    "uses airport coordinates and is approximate. A delay warning "
    "does not establish EU261 compensation eligibility."
)
