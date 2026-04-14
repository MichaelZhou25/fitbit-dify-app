# ECG EDA WESAD 教学项目

这个项目用于演示一条完整的生理信号建模路线：

- 从 `ECG / EDA / 温度 / ACC` 原始信号出发
- 做预处理、质量控制和特征提取
- 在 WESAD 上做多被试机器学习实验
- 比较 `random split` 和 `LOSO`
- 比较不同窗长配置
- 生成适合教学和汇报的结果材料

## 1. 你现在完成了什么

当前项目已经完成了下面这些任务：

1. 搭建了一个可运行的后端原型，能把原始多模态信号处理成特征、风险结果和结构化输出。
2. 基于 WESAD 跑通了多被试实验，而不是只看单个 `S2`。
3. 比较了 4 个传统机器学习模型：
   - `LR`
   - `SVM`
   - `RF`
   - `Boosting`
4. 比较了 4 套特征组合：
   - `ECG-only`
   - `EDA-only`
   - `TEMP-only`
   - `ECG+EDA+TEMP`
5. 比较了两种评估协议：
   - `random split`
   - `LOSO`
6. 比较了三组窗长配置：
   - `60s / 30s`
   - `30s / 15s`
   - `10s / 5s`

## 2. 项目目录怎么理解

建议先把项目分成 5 块来看：

### 数据与原始材料

- `WESAD/`
  - WESAD 原始数据集
- `WESAD/WESAD/S2/S2_quest.csv`
  - S2 的问卷与实验段元数据
- `WESAD.zip`
  - 原始压缩包，保留作数据追溯

### 核心代码

- `src/anxiety_monitor/preprocessing.py`
  - 信号预处理、滤波、切窗
- `src/anxiety_monitor/features.py`
  - ECG / EDA / 温度 / ACC 特征提取
- `src/anxiety_monitor/pipeline.py`
  - 把整条流程串起来
- `src/anxiety_monitor/model.py`
  - 风险模型与推理逻辑
- `src/anxiety_monitor/experiments.py`
  - random split、LOSO、多模型对比
- `src/anxiety_monitor/datasets/wesad.py`
  - WESAD 读取逻辑

### 实验脚本

- `scripts/train_wesad.py`
  - 运行 WESAD 多被试实验
- `scripts/generate_teaching_notebook.py`
  - 生成教学展示 notebook

### 实验结果

- `artifacts/wesad_experiments/`
  - `60s / 30s`
- `artifacts/wesad_experiments_w30_s15/`
  - `30s / 15s`
- `artifacts/wesad_experiments_w10_s5/`
  - `10s / 5s`
- `artifacts/window_comparison/`
  - 三组窗长结果汇总

### 教学与说明材料

- `WESAD_LOSO_window_comparison_teaching.ipynb`
  - 面向同学讲解的主 notebook
- `ECG_EDA_WESAD_emotion_tutorial.ipynb`
  - 早期教学 notebook
- `docs/WESAD_S2_quest_guide.md`
  - `S2_quest.csv` 说明文档

## 3. 如何运行

### 安装依赖

```bash
pip install -e .
```

### 查看训练脚本参数

```bash
python scripts/train_wesad.py --help
```

### 运行 WESAD 多被试实验

```bash
python scripts/train_wesad.py --wesad-root WESAD\WESAD
```

### 生成教学 notebook

```bash
python scripts/generate_teaching_notebook.py
```

## 4. 如何看懂结果

### 重点先看这几个文件

- `artifacts/wesad_experiments/loso_summary.csv`
- `artifacts/wesad_experiments/random_split_summary.csv`
- `artifacts/window_comparison/window_comparison_summary.csv`

### 你应该重点关注什么

- `random split` 往往会高于 `LOSO`
  - 因为 random split 会让同一个人的窗口同时出现在训练和测试中
- `LOSO` 更接近真实跨人泛化能力
- `ECG+EDA+TEMP` 通常比单模态更强
- 窗口变短会增加样本数，但不一定提升 LOSO 效果

## 5. 当前最重要的实验结论

基于当前已经跑完的实验，可以先记住这几条：

1. 多被试 `LOSO` 结果明显低于 `random split`，说明跨人泛化比单人内部分类更难。
2. `ECG+EDA+TEMP` 是当前最稳定的融合方案。
3. `60s / 30s` 仍然是当前更稳的主配置。
4. `10s / 5s` 虽然样本数更多，但并没有明显超过 `60s / 30s` 的 LOSO 泛化表现。

## 6. 关于 S2_quest.csv

`WESAD/WESAD/S2/S2_quest.csv` 是原始问卷和实验段元数据文件，不建议直接修改原文件。

如果你想看懂它，请看：

- `docs/WESAD_S2_quest_guide.md`

这份文档会解释：

- 为什么它是 `;` 分隔
- 为什么每行前面带 `#`
- `ORDER / START / END / PANAS / STAI / DIM / SSSQ` 各是什么意思

## 7. 下一步可以继续做什么

如果你后面继续扩展，这几个方向是自然的：

1. 加入更多 ECG / EDA 特征
2. 引入更正式的问卷标签映射
3. 加入深度学习模型
4. 加入产后女性专门数据
5. 把结构化结果进一步接入 Dify 做后验解释

