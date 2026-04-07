# fitbit_frontend

Flutter MVP client for `fitbit-dify-app`.

## Features

- latest-analysis home screen
- history timeline and segment detail flow
- read-only profile page
- zip upload import page
- responsive shell for mobile and wide layouts

## Run

```powershell
flutter pub get --offline
flutter run --dart-define=API_BASE_URL=http://127.0.0.1:8000 --dart-define=FITBIT_EXTERNAL_USER_ID=fitbit_u001
```

Optional dart defines:

- `FITBIT_DEFAULT_TIMEZONE=Asia/Shanghai`

## Verify

```powershell
flutter analyze --no-pub
flutter test --no-pub
```
