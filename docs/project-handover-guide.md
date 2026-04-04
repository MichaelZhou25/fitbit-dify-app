# 项目交接指南

## 1. 项目是什么

这是一个 Fitbit 片段分析原型项目，目标是把 Fitbit / Fitabase 的原始健康数据整理成结构化的“小时级 segment”，再基于这些 segment 做简单疲劳分类，并把模型结果、用户画像和最近状态交给 Dify 生成自然语言解释与建议。

一句话概括：

`原始 Fitbit 数据 -> 小时级结构化片段 -> 特征提取 -> 疲劳分类 -> Dify 解释 -> 前端展示`

当前仓库更接近“可演示的 MVP”，不是完整上线产品。

## 2. 当前项目状态

当前已经完成的部分：

- 支持导入 Fitbit 导出或 Fitabase merged CSV 数据
- 支持把原始数据落到本地数据库
- 支持批量回填特征和预测结果
- 支持为 `fitabase_*` 用户自动生成一版基础画像、目标和基线
- 支持调用 Dify workflow 生成分析结果
- 支持通过最小 dashboard 查看用户、时间线、segment 详情和分析结果

当前仍然是原型性质的部分：

- 默认数据库是本地 SQLite，不是生产数据库
- 预测器在没有训练好的模型 artifact 时会走 heuristic fallback
- 前端是单文件静态 dashboard，不是正式产品界面
- 旧历史数据里个别分析结果可能有编码遗留问题，重新分析即可刷新

## 3. 仓库结构

### 根目录

- `backend/`: FastAPI 后端、数据库、脚本、测试
- `data/raw/`: 原始数据目录
- `docs/`: 项目说明文档
- `README.md`: 快速启动说明

### 后端目录

- `backend/app/main.py`: FastAPI 入口
- `backend/app/api/`: 路由层
- `backend/app/services/`: 业务逻辑
- `backend/app/importers/`: Fitbit / Fitabase 导入器
- `backend/app/ml/`: 特征工程和预测器
- `backend/app/dify/`: Dify payload、client、workflow 规格
- `backend/app/models/`: SQLAlchemy 数据表模型
- `backend/app/schemas/`: Pydantic 请求/响应模型
- `backend/app/static/dashboard.html`: 最小可视化页面
- `backend/app.db`: 当前主 SQLite 数据库

### 常用脚本

- `backend/scripts/import_fitbit_export.py`: 导入 Fitbit / Fitabase 数据
- `backend/scripts/backfill_features_predictions.py`: 批量补特征和预测
- `backend/scripts/bootstrap_fitabase_profiles.py`: 批量生成用户画像、目标、基线
- `backend/scripts/check_dify_connection.py`: 检查 Dify 联通性
- `backend/scripts/export_dify_blueprint.py`: 导出 Dify workflow 蓝图

## 4. 数据从哪里来

当前本地数据主要来自：

- `data/raw/fitbit-export/mturkfitbit_export_3.12.16-4.11.16`
- `data/raw/fitbit-export/mturkfitbit_export_4.12.16-5.12.16`

这两批数据是典型的 Fitabase merged CSV 结构，特点是：

- 一个 CSV 里包含多个用户
- 通过 `Id` 字段区分用户
- 不同指标分散在不同文件里

常见原始文件有：

- `hourlySteps_merged.csv`
- `hourlyCalories_merged.csv`
- `hourlyIntensities_merged.csv`
- `heartrate_seconds_merged.csv`
- `minuteSleep_merged.csv`
- `minuteIntensitiesNarrow_merged.csv`

## 5. 数据是怎么预处理的

### 5.1 导入入口

统一入口是：

- `backend/scripts/import_fitbit_export.py`

如果目录中识别到 Fitabase merged CSV，脚本会自动切换到多用户导入模式。

### 5.2 Fitabase 数据预处理逻辑

核心逻辑在：

- `backend/app/importers/fitabase_merged.py`

它会做这些事情：

1. 按文件名识别数据类型  
   例如 `steps / calories / heart_rate / sleep / intensity`

2. 按 `Id` 拆用户  
   每个源用户会在本项目里变成一个 backend user，外部 ID 形如 `fitabase_1503960366`

3. 按小时聚合  
   项目内部的核心分析单位不是单条心率点，而是“1 小时一个 segment”

4. 合并多来源指标  
   最终每个小时段会聚合成一个 `raw_payload`

5. 对部分缺失值做推断  
   如果 `active_minutes` 或 `sedentary_minutes` 缺失，会根据 intensity、sleep、steps 做合理补全

### 5.3 预处理后的原始片段长什么样

每个小时段的 `raw_payload` 大致包含：

```json
{
  "steps": 1332,
  "calories": 141.0,
  "heart_rate_series": [78, 80, 83],
  "sleep_minutes": 0,
  "sedentary_minutes": 27,
  "active_minutes": 33
}
```

这些结构化后的小时片段会写入 `raw_segments` 表。

## 6. 数据流和各表关系

项目的主数据流是：

`users -> user_profiles -> raw_segments -> feature_vectors -> model_predictions -> dify_runs`

各表用途如下：

- `users`: 用户主表
- `user_profiles`: 用户画像、目标、阈值、基线、prompt 前缀
- `raw_segments`: 小时级原始片段
- `feature_vectors`: 从片段提取的数值特征
- `model_predictions`: 模型输出的疲劳分类概率
- `memory_snapshots`: 每次分析时计算的最近窗口记忆
- `dify_runs`: 每次发送给 Dify 的输入、输出和状态审计

## 7. 特征是怎么提取的

特征工程代码在：

- `backend/app/ml/feature_engineering.py`

输入：

- 单个 segment 的 `raw_payload_json`

输出：

- `steps_sum`
- `calories_sum`
- `sleep_minutes`
- `sedentary_minutes`
- `active_minutes`
- `hr_mean`
- `hr_std`
- `hr_min`
- `hr_max`
- `hr_range`

这一层的目标很简单：把一个小时内比较原始的行为和心率数据压缩成稳定的数值特征，方便预测器消费。

## 8. 预测器吃什么、吐什么

预测器代码在：

- `backend/app/ml/predictor.py`

输入：

- 一条 feature vector

输出：

- `top_label`
- `probabilities`

标签空间目前是三分类：

- `fatigue_low`
- `fatigue_medium`
- `fatigue_high`

示例输出：

```json
{
  "top_label": "fatigue_high",
  "probabilities": {
    "fatigue_low": 0.05,
    "fatigue_medium": 0.15,
    "fatigue_high": 0.80
  }
}
```

说明：

- 如果配置了训练好的 XGBoost artifact，则优先使用训练模型
- 如果没有 artifact，则使用 heuristic fallback

fallback 大致依据：

- 睡眠不足
- 久坐过久
- 心率波动较大
- 步数偏低

## 9. 用户画像和滚动记忆做了什么

### 9.1 用户画像

用户画像和目标存储在：

- `user_profiles`

批量 bootstrap 脚本：

- `backend/scripts/bootstrap_fitabase_profiles.py`

生成逻辑：

- `backend/app/services/profile_bootstrap_service.py`

它会根据用户历史数据推导出：

- `primary_goal`
- `activity_level`
- `sleep_tracking_quality`
- `heart_rate_coverage`
- `peak_activity_window`
- `daily_steps_goal`
- `sleep_goal_hours`
- `active_minutes_goal`
- 以及一组 `thresholds` 和 `baseline_stats`

### 9.2 滚动记忆

滚动记忆逻辑在：

- `backend/app/services/memory_service.py`

当前做法是：

- 每次分析某个 segment 时，取最近若干条 segment
- 计算最近窗口的平均步数、平均睡眠、平均心率
- 结果写入 `memory_snapshots`

这一步的作用是给 Dify 提供“最近状态”，而不只是孤立地看当前一个小时。

## 10. Dify 在项目中的职责

Dify 不是分类器，分类器已经在后端完成了。  
Dify 的职责是：根据结构化输入，生成自然语言解释和建议。

相关代码：

- `backend/app/dify/prompt_builder.py`
- `backend/app/dify/client.py`
- `backend/app/dify/workflow_spec.py`

发送给 Dify 的关键输入包括：

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

Dify 期望输出这些字段：

- `summary`
- `explanation`
- `personalized_advice`
- `confidence_note`

注意：

- `personalized_advice` 理想上应返回字符串数组
- 当前 dashboard 已兼容“数组”或“多行字符串”两种返回格式

## 11. 前端最终拿到什么

当前前端是一个静态 dashboard：

- `backend/app/static/dashboard.html`

它主要调用这些接口：

- `GET /api/v1/users`
- `GET /api/v1/users/{user_id}/profile`
- `GET /api/v1/users/{user_id}/timeline`
- `GET /api/v1/segments/{segment_id}`
- `GET /api/v1/segments/{segment_id}/latest-analysis`
- `POST /api/v1/segments/{segment_id}/analyze`

前端展示重点：

- 用户列表
- 用户画像摘要
- segment 时间线
- 单个 segment 的原始数据和预测结果
- 最近一次 Dify 分析结果

`/latest-analysis` 会优先读取数据库里最近一次已保存的分析，只有没有历史结果时，才需要手动重新调用 `/analyze`。

## 12. 本地启动方式

### 12.1 安装依赖

```powershell
cd backend
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 12.2 启动服务

推荐用下面这条，而不是直接用 `uvicorn.exe`：

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

打开：

- Dashboard: `http://127.0.0.1:8000/dashboard`
- Swagger: `http://127.0.0.1:8000/docs`

说明：

- 某些旧虚拟环境里的 `uvicorn.exe` 可能带着历史路径，`python -m uvicorn` 更稳

## 13. 常用操作命令

### 13.1 导入原始数据

```powershell
.\backend\.venv\Scripts\python.exe .\backend\scripts\import_fitbit_export.py
```

如果是单用户 Fitbit 导出，可以传：

```powershell
.\backend\.venv\Scripts\python.exe .\backend\scripts\import_fitbit_export.py `
  --external-user-id fitbit_u001 `
  --name Alice `
  --timezone Asia/Shanghai
```

### 13.2 批量回填特征和预测

```powershell
.\backend\.venv\Scripts\python.exe .\backend\scripts\backfill_features_predictions.py --batch-size 2000
```

### 13.3 批量生成用户画像

```powershell
.\backend\.venv\Scripts\python.exe .\backend\scripts\bootstrap_fitabase_profiles.py
```

### 13.4 检查 Dify 连接

```powershell
cd backend
.\.venv\Scripts\python.exe .\scripts\check_dify_connection.py --show-raw
```

### 13.5 运行测试

```powershell
cd backend
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

## 14. Dify 配置要点

需要在 `backend/.env` 中配置：

- `DIFY_BASE_URL`
- `DIFY_API_KEY`
- `DIFY_WORKFLOW_ENDPOINT`
- `DIFY_RESPONSE_MODE`

联调前确认：

1. Workflow 已发布
2. API Key 来自对应 Workflow 的 Backend Service API
3. `/parameters` 能取到 workflow 输入变量

如果 key 缺失或 Dify 不可用：

- 后端不会崩
- `/analyze` 会走 fallback 输出

## 15. 交接时最应该知道的坑

### 15.1 主数据库位置

当前主数据库是：

- `backend/app.db`

不要把根目录下可能存在的其他 `app.db` 当成主库。

### 15.2 dashboard 的目标是“演示”，不是正式前端

它适合：

- 浏览数据
- 查一条 segment
- 触发一次分析

不适合：

- 正式产品交互
- 大规模筛选和报表

### 15.3 旧分析结果可能有乱码

历史上个别 `dify_runs` 记录是在 prompt 编码未完全修正前写入的。  
如果看到某些旧结果乱码，重新触发该 segment 的 `/analyze` 即可刷新。

### 15.4 Dify 输出格式最好保持稳定

当前前端已经兼容 `personalized_advice` 的两种格式，但长期建议统一为：

```json
["建议 1", "建议 2", "建议 3"]
```

## 16. 新同学建议先做什么

建议接手后先按这个顺序熟悉项目：

1. 跑通本地服务，打开 dashboard 和 Swagger
2. 看 `docs/architecture.md` 和本指南
3. 在 dashboard 里点开一个 `fitabase_*` 用户和一条 segment
4. 对照数据库表理解 `raw_segments -> feature_vectors -> model_predictions -> dify_runs`
5. 查看 `backend/app/services/analysis_service.py`
6. 再决定后续是继续做模型、继续做前端，还是继续优化 Dify

## 17. 建议的后续工作

接手后优先级较高的工作：

- 用真正训练好的模型 artifact 替换 heuristic fallback
- 引入 Alembic migration
- 把 dashboard 升级成更完整的前端
- 增加批量分析能力，把 Dify 结果也批量补齐
- 进一步清理少量遗留文案和编码问题

## 18. 相关文档

- `README.md`
- `docs/architecture.md`
- `docs/api.md`
- `docs/fitbit-import.md`
- `docs/dify-workflow.md`

