"""NFL home venues, adapted from the user-provided 32-team coordinate CSV.

Historical entries for the Raiders (Oakland), Rams (St Louis), Chargers
(San Diego) and 49ers (old San Francisco site) have been corrected.
Coordinates are approximate venue locations, not geocoded street addresses.
Weather is deliberately suppressed for indoor/roofed venues.
"""
from __future__ import annotations

# Keyed by the nickname at the end of the full team name.
# lat, lon, venue name, weather applicable outdoors
NFL_VENUES = {
    "Titans": (36.166461, -86.771289, "Nissan Stadium", True),
    "Giants": (40.812194, -74.076983, "MetLife Stadium", True),
    "Steelers": (40.446786, -80.015761, "Acrisure Stadium", True),
    "Panthers": (35.225808, -80.852861, "Bank of America Stadium", True),
    "Ravens": (39.277969, -76.622767, "M&T Bank Stadium", True),
    "Buccaneers": (27.975967, -82.50335, "Raymond James Stadium", True),
    "Colts": (39.760056, -86.163806, "Lucas Oil Stadium", False),
    "Vikings": (44.973881, -93.258094, "U.S. Bank Stadium", False),
    "Cardinals": (33.5277, -112.262608, "State Farm Stadium", False),
    "Cowboys": (32.747778, -97.092778, "AT&T Stadium", False),
    "Falcons": (33.757614, -84.400972, "Mercedes-Benz Stadium", False),
    "Jets": (40.812194, -74.076983, "MetLife Stadium", True),
    "Broncos": (39.743936, -105.020097, "Empower Field at Mile High", True),
    "Dolphins": (25.957919, -80.238842, "Hard Rock Stadium", True),
    "Eagles": (39.900775, -75.167453, "Lincoln Financial Field", True),
    "Bears": (41.862306, -87.616672, "Soldier Field", True),
    "Patriots": (42.090925, -71.26435, "Gillette Stadium", True),
    "Commanders": (38.907697, -76.864517, "Northwest Stadium", True),
    "Packers": (44.501306, -88.062167, "Lambeau Field", True),
    "Chargers": (33.9535, -118.3392, "SoFi Stadium", False),
    "Saints": (29.950931, -90.081364, "Caesars Superdome", False),
    "Texans": (29.684781, -95.410956, "NRG Stadium", False),
    "Bills": (42.773739, -78.786978, "Buffalo home stadium", True),
    "49ers": (37.403, -121.97, "Levi's Stadium", True),
    "Jaguars": (30.323925, -81.637356, "EverBank Stadium", True),
    "Browns": (41.506022, -81.699564, "Huntington Bank Field", True),
    "Raiders": (36.0909, -115.1833, "Allegiant Stadium", False),
    "Chiefs": (39.048914, -94.484039, "GEHA Field at Arrowhead Stadium", True),
    "Rams": (33.9535, -118.3392, "SoFi Stadium", False),
    "Seahawks": (47.595153, -122.331625, "Lumen Field", True),
    "Bengals": (39.095442, -84.516039, "Paycor Stadium", True),
    "Lions": (42.340156, -83.045808, "Ford Field", False),
}

def nfl_home_venue(team: str) -> dict | None:
    nickname = (team or "").strip().split(" ")[-1]
    if nickname in ("Redskins", "Football Team"):
        nickname = "Commanders"
    if nickname in ("Forty-Niners", "Niners"):
        nickname = "49ers"
    venue = NFL_VENUES.get(nickname)
    if not venue:
        return None
    lat, lon, name, outdoor = venue
    return {"name": name, "latitude": lat, "longitude": lon,
            "outdoor": outdoor, "source": "nfl_venue_lookup"}
