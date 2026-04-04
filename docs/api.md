# API Notes

## Create a user

`POST /api/v1/users`

```json
{
  "external_user_id": "u_001",
  "name": "Alice",
  "timezone": "Asia/Shanghai"
}
```

## List users

`GET /api/v1/users?q=fitabase&limit=50&offset=0`

## Update personalized profile

`PATCH /api/v1/users/{user_id}/profile`

```json
{
  "profile": {
    "age": 29,
    "goal": "sleep_improvement"
  },
  "goals": {
    "sleep_goal_hours": 8
  },
  "thresholds": {
    "fatigue_high_threshold": 0.7
  },
  "baseline_stats": {
    "resting_hr": 61,
    "avg_sleep_minutes": 420
  },
  "system_prompt_prefix": "你正在为一名以改善睡眠为目标的用户提供分析。避免诊断性措辞，回答要谨慎、简洁。"
}
```

## Ingest a segment

`POST /api/v1/segments/ingest`

```json
{
  "user_id": "USER_UUID_HERE",
  "segment_start": "2026-04-04T08:00:00+08:00",
  "segment_end": "2026-04-04T09:00:00+08:00",
  "granularity": "1h",
  "source_type": "fitbit_csv",
  "raw_payload": {
    "steps": 623,
    "calories": 132.4,
    "heart_rate_series": [78, 82, 85, 88],
    "sleep_minutes": 0,
    "sedentary_minutes": 35,
    "active_minutes": 12
  }
}
```

## Analyze a segment

`POST /api/v1/segments/{segment_id}/analyze`

```json
{
  "user_query": "请解释这一段 Fitbit 数据，并给出个性化建议。"
}
```

## Read the latest saved analysis

`GET /api/v1/segments/{segment_id}/latest-analysis`

This returns the newest stored `dify_runs` record for that segment, including:

- `status`
- `created_at`
- `workflow_run_id`
- `model_output`
- `dify_payload`
- `llm_output`
