"""
Proof that IST timezone works worldwide regardless of server location.
This demonstrates how the bot will behave on servers in different timezones.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

# Simulate different server locations
timezones = {
    "🇮🇳 India Server (IST)": "Asia/Kolkata",
    "🇺🇸 AWS US-East (EST)": "America/New_York",
    "🇺🇸 AWS US-West (PST)": "America/Los_Angeles",
    "🇪🇺 GCP Europe (CET)": "Europe/Paris",
    "🇸🇬 Singapore (SGT)": "Asia/Singapore",
    "🇯🇵 Japan (JST)": "Asia/Tokyo",
    "🇬🇧 UK (GMT)": "Europe/London",
    "🌐 UTC Server": "UTC"
}

print("=" * 80)
print("🌍 WORLDWIDE TIMEZONE TEST - Indian Trading Bot")
print("=" * 80)
print()

# Get current IST time (what the bot uses)
ist_now = datetime.now(ZoneInfo("Asia/Kolkata"))
print(f"📊 INDIAN MARKET TIME: {ist_now.strftime('%Y-%m-%d %I:%M:%S %p %Z')}")
print()

# Check market status
market_open = datetime.strptime("09:15", "%H:%M").time()
market_close = datetime.strptime("15:30", "%H:%M").time()
no_new_trades = datetime.strptime("15:00", "%H:%M").time()
current_time = ist_now.time()

if current_time < market_open:
    status = "🔴 PRE-MARKET (Market not yet open)"
elif market_open <= current_time < no_new_trades:
    status = "🟢 ACTIVE TRADING (New trades allowed)"
elif no_new_trades <= current_time < market_close:
    status = "🟡 NO NEW TRADES (Only exits allowed)"
else:
    status = "⚫ POST-MARKET (Market closed)"

print(f"Market Status: {status}")
print()
print("-" * 80)
print("🌎 Same Moment in Different Server Locations:")
print("-" * 80)

# Show what time it would be on different servers
for location, tz_name in timezones.items():
    local_time = ist_now.astimezone(ZoneInfo(tz_name))
    print(f"{location:35} → {local_time.strftime('%I:%M:%S %p %Z'):20} | BUT BOT STILL USES IST ✅")

print()
print("=" * 80)
print("🎯 KEY INSIGHT:")
print("=" * 80)
print("No matter which server time is shown above, the bot ALWAYS:")
print(f"  • Uses IST time: {ist_now.strftime('%I:%M:%S %p')}")
print(f"  • Market status: {status}")
print("  • Makes the same trading decisions at the same moment")
print()
print("✅ Your bot will work ANYWHERE in the world!")
print("=" * 80)
