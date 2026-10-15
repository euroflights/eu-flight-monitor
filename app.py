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

# Airports located in EU member countries.
# Coordinates are used to estimate route distance.
AIRPORTS = {
    "CDG": (49.0097, 2.5479),  # Paris, France
    "ORY": (48.7262, 2.3652),  # Paris, France
    "FRA": (50.0379, 8.5622),  # Frankfurt, Germany
    "MUC": (48.3538, 11.7861), # Munich, Germany
    "MAD": (40.4983, -3.5676), # Madrid, Spain
    "BCN": (41.2974, 2.0833),  # Barcelona, Spain
    "FCO": (41.8003, 12.2389), # Rome, Italy
    "MXP": (45.6306, 8.7281),  # Milan, Italy
    "AMS": (52.3105, 4.7683),  # Amsterdam, Netherlands
    "BRU": (50.9010, 4.4844),  # Brussels, Belgium
    "LIS": (38.7742, -9.1342), # Lisbon, Portugal
    "ATH": (37.9364, 23.9445), # Athens, Greece
    "VIE": (48.1103, 16.5697), # Vienna, Austria
    "CPH": (55.6181, 12.6560), # Copenhagen, Denmark
    "WAW": (52.1657, 20.9671), # Warsaw, Poland
    "PRG": (50.1008, 14.2600), # Prague, Czechia
    "BUD": (47.4298, 19.2611), # Budapest, Hungary
    "DUB": (53.4213, -6.2701), # Dublin, Ireland
    "HEL": (60.3172, 24.9633), # Helsinki, Finland
    "ARN": (59.6519, 17.9186), # Stockholm, Sweden
    "OTP": (44.5711, 26.0850), # Bucharest, Romania
    "SOF": (42.6967, 23.4114), # Sofia, Bulgaria
    "ZAG": (45.7429, 16.0688), # Zagreb, Croatia
    "LJU": (46.2237, 14.4576), # Ljubljana, Slovenia
    "LUX": (49.6233, 6.2044),  # Luxembourg
    "MLA": (35.8575, 14.4775), # Malta
    "LCA": (34.8751, 33.6249), # Larnaca, Cyprus
    "TLL": (59.4133, 24.8328), # Tallinn, Estonia
    "RIX": (56.9236, 23.9711), # Riga, Latvia
    "VNO": (54.6341, 25.2858), # Vilnius, Lithuania
    "OPO": (41.2481, -8.6814), # Porto, Portugal
    "NAP": (40.8860, 14.2908), # Naples, Italy
    "PMI": (39.5517, 2.7388),  # Palma, Spain
    "AGP": (36.6749, -4.4991), # Malaga, Spain
    "SVQ": (37.4180, -5.8931), # Seville, Spain
    "TLS": (43.6293, 1.3638),  # Toulouse, France
    "NCE": (43.6584, 7.2159),  # Nice, France
    "LYS": (45.7256, 5.0811),  # Lyon, France
    "BER": (52.3667, 13.5033), # Berlin, Germany
    "HAM": (53.6304, 9.9882),  # Hamburg, Germany
    "DUS": (51.2895, 6.7668),  # Dusseldorf, Germany
    "NAP": (40.8860, 14.2908), # Naples, Italy
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

# Only monitor flights between airports in our EU list.
if origin not in AIRPORTS or destination not in AIRPORTS:
    continue

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
