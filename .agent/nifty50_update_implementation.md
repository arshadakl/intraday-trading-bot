# Nifty 50 Auto-Update Implementation

## Overview
The trading bot now automatically updates the Nifty 50 stock list from NSE's pre-open API at two key times:
1. **On Bot Startup** - Checks if data is stale and updates if needed
2. **Daily at 9:10 AM IST** - Scheduled automatic update when pre-open data becomes final

## Implementation Details

### 1. Data Storage (`config/nifty50.json`)
The JSON file now includes metadata fields:
- `stocks`: Array of stock objects with `symbol`, `token`, and `name`
- `_updated`: ISO timestamp of last update (e.g., "2026-02-08T21:06:10.388685")
- `_source`: Data source identifier (e.g., "NSE Pre-Open API")
- `index`: Nifty index information

### 2. Update on Startup (`src/core/bot.py`)

#### Method: `_update_nifty50_on_startup()`
- **Location**: Lines 1046-1092
- **Called from**: `initialize()` method after successful initialization
- **Logic**:
  1. Checks if `config/nifty50.json` exists
  2. Reads the `_updated` timestamp
  3. Compares with today's date
  4. If data is from a previous day, triggers update
  5. If file is missing or has no timestamp, triggers update
  6. If data is fresh (updated today), skips update

**Example Log Output**:
```
📊 Checking Nifty 50 data freshness...
✅ Nifty 50 data is fresh (updated: 2026-02-08T21:06:10.388685)
```

### 3. Scheduled Daily Update

#### Method: `_update_nifty50_from_nse()`
- **Location**: Lines 1094-1127
- **Scheduled**: Daily at 9:10 AM IST (configured in `timing.preopen_data_ready`)
- **Process**:
  1. Calls `update_nifty50_at_market_open()` from `src/utils/nifty50_updater.py`
  2. Fetches latest Nifty 50 constituents from NSE API
  3. Updates `config/nifty50.json` with new stock list
  4. Fetches missing instrument tokens from Angel One API
  5. Reloads bot configuration to use updated data
  6. Logs success/failure status

**Scheduled Task** (Lines 997-1002):
```python
self.scheduler.schedule_task(
    "nifty50_update",
    timing.get("preopen_data_ready", "09:10"),
    self._update_nifty50_from_nse
)
```

### 4. Update Function (`src/utils/nifty50_updater.py`)

#### Function: `update_nifty50_at_market_open()`
- **Location**: Lines 343-358
- **Returns**: Boolean (success/failure)
- **Process**:
  1. Creates `Nifty50Updater` instance
  2. Fetches NSE pre-open data
  3. Parses stock symbols
  4. Updates `nifty50.json`
  5. Calls `AngelTokenFetcher().update_nifty50_tokens()` to fill missing tokens
  6. Returns success status

### 5. API Endpoint (`src/api/server.py`)

#### Endpoint: `/api/nifty50/preopen`
- **Method**: GET
- **Authentication**: Required (`@require_auth`)
- **Response**:
```json
{
  "success": true,
  "timestamp": "2026-02-08T21:06:10.388685",
  "data": {
    "stocks": [
      {
        "symbol": "RELIANCE-EQ",
        "token": "2885",
        "name": "Reliance Industries"
      },
      ...
    ],
    "metadata": {
      "total_stocks": 56,
      "last_updated": "2026-02-08T21:06:10.388685",
      "source": "NSE Pre-Open API",
      "update_time": "09:10 AM IST (Daily)"
    }
  }
}
```

### 6. Dashboard Display (`dashboard/index.html` & `dashboard/app.js`)

#### New Tab: "📈 Nifty 50"
- **Location**: Between Dashboard and Logs tabs
- **Features**:
  - Metadata cards showing total stocks, last update, source, and update schedule
  - Table displaying all stocks with symbol, name, token, and status
  - Refresh button for manual updates
  - Auto-loads when tab is selected

#### JavaScript Function: `refreshNifty50Data()`
- **Location**: `dashboard/app.js` lines 1129-1186
- **Triggered by**:
  - Tab selection
  - Manual refresh button click
- **Updates**:
  - Metadata displays
  - Stock table with color-coded status (✅ Active / ⚠️ Missing Token)

## Data Flow

### On Bot Startup
```
Bot Initialize
    ↓
_update_nifty50_on_startup()
    ↓
Check nifty50.json timestamp
    ↓
If stale → _update_nifty50_from_nse()
    ↓
update_nifty50_at_market_open()
    ↓
Fetch from NSE API
    ↓
Update nifty50.json
    ↓
Fetch missing tokens from Angel One
    ↓
Reload config
```

### Daily at 9:10 AM
```
Scheduler triggers at 9:10 AM
    ↓
_update_nifty50_from_nse()
    ↓
update_nifty50_at_market_open()
    ↓
Fetch from NSE API
    ↓
Update nifty50.json
    ↓
Fetch missing tokens from Angel One
    ↓
Reload config
    ↓
Log update status
```

### Dashboard View
```
User clicks "Nifty 50" tab
    ↓
refreshNifty50Data()
    ↓
GET /api/nifty50/preopen
    ↓
Read nifty50.json
    ↓
Return stocks + metadata
    ↓
Update UI table
```

## Configuration

### Timing Configuration (`config/timing`)
```python
"preopen_data_ready": "09:10"  # When NSE pre-open data becomes final
```

### NSE API Endpoint
```
https://www.nseindia.com/api/market-data-pre-open?key=NIFTY
```

## Error Handling

1. **Startup Update Failure**: Bot continues with existing data, logs warning
2. **Scheduled Update Failure**: Logged as error, retries next day
3. **API Endpoint Error**: Returns error response to dashboard
4. **Missing File**: Triggers immediate update

## Testing

### Verify Startup Update
```bash
# Delete timestamp to force update
python -c "import json; from pathlib import Path; p = Path('config/nifty50.json'); data = json.load(open(p)); del data['_updated']; json.dump(data, open(p, 'w'), indent=2)"

# Restart bot and check logs
python run.py
# Should see: "📊 Nifty 50 file has no update timestamp - will update"
```

### Verify Scheduled Update
```bash
# Check scheduler logs at 9:10 AM
# Should see: "📊 UPDATING NIFTY 50 FROM NSE (9:10 AM)"
```

### Verify Dashboard
1. Open dashboard: http://127.0.0.1:5000
2. Click "📈 Nifty 50" tab
3. Verify data displays correctly
4. Click "🔄 Refresh" button
5. Verify data reloads

## Benefits

1. **Always Fresh Data**: Bot uses latest Nifty 50 constituents
2. **Automatic Token Updates**: Missing tokens are fetched automatically
3. **No Manual Intervention**: Fully automated daily updates
4. **Dashboard Visibility**: Easy monitoring of stock list status
5. **Startup Safety**: Ensures fresh data even if bot was offline
6. **Efficient**: Only updates when needed (not already updated today)

## Files Modified

1. `src/core/bot.py` - Added startup and scheduled update methods
2. `src/api/server.py` - Added `/api/nifty50/preopen` endpoint
3. `src/utils/nifty50_updater.py` - Enhanced with `update_nifty50_at_market_open()`
4. `dashboard/index.html` - Added Nifty 50 tab
5. `dashboard/app.js` - Added data fetching and display functions
6. `config/nifty50.json` - Added `_updated` and `_source` metadata fields
