# Manual Nifty 50 Token Update
# Run this in Python REPL to update nifty50.json with new stocks

import json
from pathlib import Path

# New stocks to add (you need to get tokens from Angel One instrument master)
# Download from: https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json

NEW_STOCKS = [
    # These tokens need to be verified from Angel One instrument master
    {"symbol": "ETERNAL-EQ", "token": "543320", "name": "Eternal (Zomato)"},
    {"symbol": "JIOFIN-EQ", "token": "543940", "name": "Jio Financial Services"},
    {"symbol": "TRENT-EQ", "token": "1964", "name": "Trent"},
    {"symbol": "BEL-EQ", "token": "383", "name": "Bharat Electronics"},
    {"symbol": "INDIGO-EQ", "token": "11194", "name": "InterGlobe Aviation"},
    {"symbol": "MAXHEALTH-EQ", "token": "543220", "name": "Max Healthcare Institute"},
]

# Load existing config
config_path = Path("config/nifty50.json")
with open(config_path) as f:
    config = json.load(f)

existing_symbols = {s['symbol'] for s in config['stocks']}

# Add new stocks
for stock in NEW_STOCKS:
    if stock['symbol'] not in existing_symbols:
        config['stocks'].append(stock)
        print(f"Added: {stock['symbol']}")
    else:
        print(f"Already exists: {stock['symbol']}")

# Save
with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)

print(f"\nTotal stocks: {len(config['stocks'])}")
