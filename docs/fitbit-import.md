# Fitbit Import

This project can now import Fitbit export files into hourly `raw_segments` for the backend.

## What you still need to do manually

Fitbit export is account-private, so you still need to export your own data from the Fitbit app first.

As of April 4, 2026, the export path in the Fitbit app is:

1. Profile picture
2. Fitbit settings
3. Manage data and privacy
4. Export your data

After downloading the export, unzip it into [`data/raw/fitbit-export`](/D:/Playground/data/raw/fitbit-export).

## Supported input shapes

The importer supports:

- JSON or CSV files
- A directory tree or a single `.zip` archive
- Intraday steps, calories, and heart rate files with timestamps
- Sleep logs with `startTime` and `endTime`
- Sleep stage payloads with `levels.data`
- Fitabase merged CSV directories such as `hourlySteps_merged.csv` and `minuteSleep_merged.csv`

Daily summary files without intraday timestamps are skipped because the backend stores hourly segments.

If the directory contains Fitabase merged CSV files with an `Id` column, the importer switches to multi-user mode and creates one backend user per source `Id`. The default external id format is `fitabase_<Id>`.

## Run the importer

From [`/D:/Playground`](/D:/Playground):

```powershell
.\backend\.venv\Scripts\python.exe .\backend\scripts\import_fitbit_export.py `
  --external-user-id fitbit_u001 `
  --name Alice `
  --timezone Asia/Shanghai
```

Dry run first if you want to inspect the generated payloads:

```powershell
.\backend\.venv\Scripts\python.exe .\backend\scripts\import_fitbit_export.py `
  --external-user-id fitbit_u001 `
  --timezone Asia/Shanghai `
  --dry-run
```

For Fitabase merged exports, `--external-user-id` is not used. The script auto-detects that layout and creates users like `fitabase_1503960366`.

## Output mapping

Each imported hour becomes one `raw_segments` row with this payload shape:

```json
{
  "steps": 623,
  "calories": 132.4,
  "heart_rate_series": [78, 82, 85, 88],
  "sleep_minutes": 0,
  "sedentary_minutes": 35,
  "active_minutes": 12
}
```

Notes:

- `active_minutes` and `sedentary_minutes` are taken directly from timestamped export data when present.
- If those files are missing, the importer falls back to deriving them from hourly steps.
- If calorie files are missing, calories fall back to `steps * 0.04`.
