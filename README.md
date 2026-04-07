# Fitbit Dify App

Minimal scaffold for a Fitbit segment analysis service:

- ingest Fitbit-like segment data
- store raw segments, features, predictions, and user memory
- compute simple feature vectors
- generate class probabilities through a replaceable predictor
- pass personalized context to Dify for explanation

## Quick start

1. Create a virtual environment and install dependencies:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Copy the environment template:

```powershell
Copy-Item ..\.env.example .env
```

If you want to use Supabase instead of the local SQLite file, set `DATABASE_URL`
to your Supabase Postgres Session Pooler connection string in `backend/.env`.
Use the `postgresql://...` form so SQLAlchemy can parse it correctly.

3. Run the API:

```powershell
uvicorn app.main:app --reload
```

4. Open the docs:

`http://127.0.0.1:8000/docs`

5. Open the dashboard:

`http://127.0.0.1:8000/dashboard`

## Flutter frontend

A Flutter MVP frontend now lives in [`frontend/`](frontend). It is a single-user, analysis-first client that supports:

- latest analysis home screen
- segment timeline and detail pages
- read-only profile view
- zip upload import flow through backend APIs

Run it with:

```powershell
cd frontend
flutter pub get --offline
flutter run --dart-define=API_BASE_URL=http://127.0.0.1:8000 --dart-define=FITBIT_EXTERNAL_USER_ID=fitbit_u001
```

The app uses these new backend endpoints:

- `GET /api/v1/users/by-external-id/{external_user_id}`
- `POST /api/v1/users/{user_id}/bootstrap-profile`
- `POST /api/v1/imports/fitbit`

The frontend does not need any database-specific configuration. As long as the
backend can reach Supabase, the existing Flutter flows continue to work.

## Import Fitbit export data

1. Export your Fitbit data from the Fitbit app and unzip it into `data/raw/fitbit-export/`.
2. Run the importer:

```powershell
.\backend\.venv\Scripts\python.exe .\backend\scripts\import_fitbit_export.py `
  --external-user-id fitbit_u001 `
  --name Alice `
  --timezone Asia/Shanghai
```

Use `--dry-run` first if you want to preview the generated hourly payloads without writing to the database.

If the directory contains Fitabase-style merged CSV files, the script auto-detects multi-user mode and creates one backend user per source `Id`.

More details: [docs/fitbit-import.md](docs/fitbit-import.md)

Project handover guide: [docs/project-handover-guide.md](docs/project-handover-guide.md)

## Backfill features and predictions

Once you have imported many raw segments, you can materialize missing feature vectors and model predictions in bulk:

```powershell
.\backend\.venv\Scripts\python.exe .\backend\scripts\backfill_features_predictions.py `
  --external-user-id fitabase_1503960366 `
  --limit 500
```

Run without `--external-user-id` to process every matching segment that is still missing features or predictions.

## Current scope

- The database defaults to SQLite for local setup. For shared or deployed usage,
  set `DATABASE_URL` to a Supabase Postgres Session Pooler connection string.
- The predictor falls back to a deterministic heuristic when no trained XGBoost model artifact is present.
- Dify calls are skipped when `DIFY_API_KEY` is empty. The API still returns the assembled payload so you can inspect it.

## Supabase setup

1. Create a Supabase project and open `Project Settings -> Database`.
2. Copy the `Session Pooler` connection string.
3. Set `DATABASE_URL=postgresql://...` in `backend/.env`.
4. Start the backend once so `Base.metadata.create_all()` can create the tables in Supabase.
5. Re-import your Fitbit/Fitabase zip data into the empty Supabase database.
6. Run profile bootstrap and segment analysis as usual.

This project does not migrate existing local SQLite data into Supabase. The
recommended workflow is to start with an empty Supabase database and re-import
raw zip data through the existing import flow.

## Suggested next steps

- Replace the heuristic predictor with a trained XGBoost artifact.
- Add Alembic migrations.
- Add a frontend timeline page.
- Add async jobs for batch feature extraction and prediction.
