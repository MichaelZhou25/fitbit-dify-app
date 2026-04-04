# Dify Workflow Blueprint

## Current status

You do not need a deployed Dify workflow to continue backend work.

At this stage you can:

1. keep using `/analyze` with local fallback output
2. export a workflow blueprint from the repo
3. deploy the Dify workflow later and then run a connection check

## Recommended app type

Use a `Workflow` application first.

This project sends a fresh `inputs` payload for every analysis request, so `Workflow` is a better fit than a long-running chat app.

## Input variables

- `user_id`
- `segment_id`
- `profile_prompt_prefix`
- `profile_json`
- `goals_json`
- `thresholds_json`
- `baseline_stats_json`
- `rolling_memory_summary`
- `feature_summary`
- `probability_json`
- `top_label`
- `user_query`

## Expected output fields

- `summary`
- `explanation`
- `personalized_advice`
- `confidence_note`

## Suggested node order

1. `Start`
2. `Template` or `Code`
3. `LLM`
4. `End`

## System prompt template

```text
{{profile_prompt_prefix}}

你会收到四类信息：
1. 用户长期画像与目标
2. 最近滚动窗口的记忆摘要
3. 当前 Fitbit 数据片段的特征摘要
4. 模型输出的类别概率

要求：
- 先解释模型结果，再结合用户画像给出建议
- 不做医学诊断
- 如果证据不足，要明确说明不确定性
- 只输出 JSON，不要输出 Markdown，不要输出额外说明
- JSON 必须包含 summary、explanation、personalized_advice、confidence_note 四个字段
- personalized_advice 可以是字符串，也可以是字符串数组
```

## User message template

```text
用户画像: {{profile_json}}
目标: {{goals_json}}
阈值: {{thresholds_json}}
基线: {{baseline_stats_json}}

近期记忆: {{rolling_memory_summary}}

当前特征: {{feature_summary}}

模型结果:
top_label={{top_label}}
probabilities={{probability_json}}

用户问题:
{{user_query}}
```

## Repo helpers

Export a ready-to-use blueprint JSON:

```powershell
.\backend\.venv\Scripts\python.exe .\backend\scripts\export_dify_blueprint.py `
  --external-user-id fitabase_1503960366
```

This writes a blueprint file to [`dify-workflow-blueprint.json`](/D:/Playground/data/processed/dify-workflow-blueprint.json).

This repo also includes a directly importable Dify DSL YAML:

- [`dify-fitbit-analysis.workflow.yml`](/D:/Playground/data/processed/dify-fitbit-analysis.workflow.yml)

Import path in Dify:

1. Create or open a Workflow app
2. Choose `Import DSL`
3. Select the YAML file above

If your Dify workspace does not have `OpenAI / gpt-4o-mini`, import the workflow first and then change the LLM node model once inside Dify.

After you deploy the workflow and fill `.env`, verify the connection:

```powershell
.\backend\.venv\Scripts\python.exe .\backend\scripts\check_dify_connection.py
```

## Integration note

The backend already tolerates these cases:

- `DIFY_API_KEY` is empty
- Dify returns a non-2xx response
- Dify is reachable but the workflow output shape is not ideal

In those cases the API returns local fallback output instead of breaking the request.
