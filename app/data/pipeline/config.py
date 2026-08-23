import os

# Ensure outputs directory exists
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

TARGET_ACCOUNTS = [
    "Shell", "Aramco", "Equinor", "BP", "Chevron",
    "ExxonMobil", "TotalEnergies", "ConocoPhillips", "Eni", "Petrobras",
    "Schlumberger", "Halliburton", "Baker Hughes", "Weatherford", "National Oilwell Varco"
]

SENIORITY_LEVELS = ["C-Suite", "VP/Director", "Manager", "IC"]
