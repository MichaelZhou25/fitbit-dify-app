# Dify Workflow Blueprint

这个 Workflow 用来接收后端输出的 `ConsultPacket`，然后生成：

- 用户版解释
- 医生版摘要
- 下一步建议

## 推荐应用类型

- `Workflow`

## Start 节点

输入变量：

- `consult_packet_json`：完整 JSON 字符串

## Code / Template 节点

任务：

- 解析 JSON
- 取出关键字段：
  - `risk.risk_level`
  - `risk.risk_score`
  - `risk.uncertainty`
  - `risk.top_features`
  - `quality.overall_quality`
  - `quality.is_usable`
  - `rule_triggers`
  - `questionnaire`

输出字段建议：

- `risk_level`
- `risk_score`
- `uncertainty`
- `quality_score`
- `is_usable`
- `top_features_text`
- `trigger_text`
- `questionnaire_text`

## IF / ELSE 节点

### 分支 1：低质量优先

条件：

```text
is_usable == false OR quality_score < 0.45
```

### 分支 2：高风险

条件：

```text
risk_level == "high" AND uncertainty <= 0.35
```

### 分支 3：其他

输出中低风险说明，建议继续观察或补信息。

## LLM 节点 Prompt

系统提示词建议：

```text
你是产后情绪监测系统中的后验会诊助手。
你不会直接查看原始波形，只能根据结构化生理结果做解释。

任务：
1. 生成用户版简明解释，语言温和，不制造恐慌。
2. 生成医生版摘要，保留风险等级、证据强弱、主驱动特征和质量信息。
3. 如果数据质量不足，优先说明证据不足，不做高置信判断。
4. 如果风险较高且证据充分，提出下一步建议，包括补充问卷、继续观察、联系医生或支持者。

输出必须是 JSON，包含：
user_summary
clinician_summary
evidence_sufficiency
next_actions
follow_up_questions
```

用户消息模板建议：

```text
risk_level={{risk_level}}
risk_score={{risk_score}}
uncertainty={{uncertainty}}
quality_score={{quality_score}}
is_usable={{is_usable}}
top_features={{top_features_text}}
triggers={{trigger_text}}
questionnaire={{questionnaire_text}}
```

## End 节点

直接输出 LLM 的 JSON 结果。

