# Scope planner(最新版):Method E

把 HD-EPIC 一段录像拆成 **goal → sub-goal**:goal = 官方 recipe step(数据集自带的 ground truth),sub-goal = Gemini 在这个 step 里拆出来的小目标。pyramid2 就用这个结构出题。

## 怎么做

1. 每个官方 recipe step 当成一段,把这个 step 时间段里的官方 narration 按时间排好。
2. 交给 Gemini 3.1 Pro(temperature 0),让它给出:这段的 overall goal、若干 sub-goal(每个引用自己的 narration id,4–20 条为宜)、和这个 step 无关的 narration。
3. 不在任何 step 里的 narration(加上第 2 步判成无关的)按时间每 120 条一组,用同一个 prompt 再分组。
4. 模型只引用 narration id,不写时间;sub-goal 的起止时间由程序从官方 narration 抄。

prompt 原文在 `method_e.py` 开头。做法参照 EgoPlan-Bench2(用 Ego4D 的段落 summary 分段,再在段内提 goal),这里用 HD-EPIC 的 recipe step 代替 summary。

## 用法

```bash
pip install -r requirements.txt
export OPENROUTER_API_KEY=sk-or-...
python3 method_e.py --annot /path/to/hd-epic/annotations/data --video P08-20240617-184909 -o out/P08-20240617-184909
python3 method_e.py --stats out/          # 对一批输出算 metrics
```

输出 `out/<video>/merged.json`:`goals[]` 里每个 sub-goal 有 `description`、`action_ids`、`segment`(官方 step id,或 `nostep_xx`)、`start_s` / `end_s`、`n_actions`、`n_interruptions_gt60s`。

## 例子(`examples/`)

每个文件 = 真实发给 Gemini 的输入 + 它的原始返回 + 最终带时间的 sub-goal。

| 文件 | 官方 step | narration → sub-goal |
|---|---|---|
| `P08-20240617-184909__P08_R07_S06.json` | Slice onion, chili pepper, and bell pepper and place to side | 30 → 3(切洋葱 / 切辣椒 / 去籽切甜椒) |
| `P06-20240510-090328__P06_R01_S01.json` | Mix the uttapam pancake mix into water in a bowl until a smooth batter is prepared and set it aside for 10-15 minutes. | 92 → 8 |
| `P03-20240218-190556__P03_R02_S01.json` | Wash potatoes, peel and cut them into small cubes | 107 → 9 |

## Metrics(50 段录像的输出,`metrics.json`)

| | 官方 step 内 | 不在 step 里 |
|---|---|---|
| sub-goal 数 | 1281 | 1999 |
| 每个 sub-goal 的 narration 数(中位 / p10–p90) | 10 / 4–17 | 10 / 5–18 |
| 每个 sub-goal 时长(中位 / p10–p90) | 29.5 s / 10–122 s | 24.1 s / 8–96 s |
| narration 数在 4–20 内 | 94% | 96% |
| 中间被打断 > 60 s | 9.8% | 8.5% |

259 个官方 step,每个拆成的 sub-goal 数中位 4(1–21)。sub-goal 是模型候选,未人工核验。

## 为什么选 E(10-21 / 10-22 和 A–D 的对比)

同 3 段录像(P08 / P06 / P03)上比了 5 种做法:

| 方法 | 做法 | goal 怎么来 |
|---|---|---|
| A | EgoPlan 式层级 prompt,每 120 条 narration 一窗 | 全部由 Gemini 分 |
| B | A 的分窗 + 12 个官方 EgoPlan 例子做 few-shot | 全部由 Gemini 分 |
| C | task 级 few-shot,出整道菜级的 goal | 全部由 Gemini 分 |
| D | A 的 prompt + 12 个 EgoPlan-Bench2 例子 | 全部由 Gemini 分 |
| **E** | 按官方 recipe step 分段,step 内再拆 | **goal = 官方 step,只有 sub-goal 由 Gemini 分** |

- 选 E 是因为结构:上层 goal 直接是数据集的 ground truth,不用模型猜;下层 sub-goal 颗粒度和 EgoPlan 一致(中位 10 条 narration、约 30 s)。
- Gemini 盲评(每次比两种分法哪个更好,46 段)里 E 输给 A(5 : 41)、B(3 : 43)、D(3 : 43)。主要原因是盲评按时间窗口比,而 E 按 recipe step 分组,一个 step 的时间本来就散在录像各处,所以被判「不连续 / 交错」;盲评也在各方法里都抓到描述里的幻觉。盲评结果只说明 E 的分组不按时间连续,不说明 goal 结构更差。

对比页:Space `WitneyWW/hdepic-goal-gen-ab-1021`(私有,五种方法逐视频并排);E 的说明页:Space `WitneyWW/hdepic-method-e-1022`(私有)。
