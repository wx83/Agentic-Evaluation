# 自适应金字塔评测(experiment 0907)

memory 文本输入 × 固定 4 层(Easy/Low/Medium/High)× 每层 100 题 × 80% 晋级闸门。
Gemini 是独立出题器:程序挖 gold(`facts.py` 包装 `../primitives.py`),Gemini 只写措辞;
从 L2 起,出题以被评测 agent 上一层的作答摘要为条件(选材权重 + 措辞风格,绝不碰 gold)。
计分:第 k 层答对一题得 k 分;某层 100 题对不满 80 就止步。

三个自适应臂(全都要跑):
- `shared_l1`:L1 一套共享题;L2+ 各 agent 用自己的错误画像单独出题。
- `per_agent`:每层都按 agent 单独出题。
- `pooled`  :一座金字塔全体共用,以合并作答为条件;有同步屏障。

产物在 `/mnt/work_new/weihanxu/output/pyramid/`;`PYRAMID_SMOKE=1` 时走
`output/pyramid_smoke/`(冒烟测试不污染正式题库与事实复用登记)。

## Gemini 后端(2026-10-10)

`GEMINI_BACKEND=nv`(**默认**)走 NVIDIA 网关 `inference-api.nvidia.com` 的 Gemini 原生透传
(`gemini/nv_gemini.py`,key 由它解析:env `NVIDIA_API_KEY` → `holi/.secrets/nvidia_key` → `weihanxu/gemini_api_key`);
`GEMINI_BACKEND=google` 是原来的直连(`GEMINI_API_KEY`)。

- 题库 / 缓存 / 事实复用两个后端共用;**结果分目录**:google 仍写 `results/`(历史结果都在这里),nv 写 `results_nv/`。
- nv 没有 Files API,`agent_gemini.upload` 自动改内联 bytes;模型名自动加 `gcp/google/` 前缀(结果行 `model` 字段带前缀)。
- `logs/*/gemini_calls.jsonl` 每行多了 `backend` 字段,`key_id` 按后端取(nv 的 key 指纹 3948af16)。
- **2026-10-11 实测**:NV(Vertex 后端)对 seed43 L2 的答案与 9 月 29 日 Google 直连结果 96/100 一致;
  而 Google AI Studio 直连**今天**的答案只与 9 月 29 日 51% 一致,spatial 题 12 道只对 1 道(答案集中在 C),
  三把 key、upload / inline 都一样 —— generativelanguage 端点的 gemini-3.5-flash 已变。要和历史结果可比,用 nv。
  `modality_probe.py report` 末尾有逐题一致率表。

## L2 模态探针(`modality_probe.py`,2026-10-10)

同一道题四种输入:`av` 原 clip / `v_only` 静音 / `a_only` 黑屏保留音轨 / `a_swap` 原画面+另一题音轨(音画冲突)。
逐题判 V-sufficient / A-sufficient / needs-both,以及 a_swap 时答案跟画面还是跟声音。
结果 `results/modality_probe/{nv,google}/gemini/<cond>.jsonl`,报告 `report/modality_probe.md`。
```bash
PYRAMID_SEED=43 GEMINI_BACKEND=nv     $GEM modality_probe.py run
PYRAMID_SEED=43 GEMINI_BACKEND=google $GEM modality_probe.py run
PYRAMID_SEED=43 python3 modality_probe.py report
```

## 跑法

```bash
cd /mnt/work_new/weihanxu/agent/bench/pyramid
GEM=/home/weihanxu/miniconda3/envs/gemini/bin/python

# 0) 供给表(已验证:Easy 1453 / Low 359 / Medium 1272 / High 909,均 >=150)
python3 facts.py --stats

# 1) 离线冒烟(无 key,mock 全流程;已通过:oracle 全 4 层 100%,random 止步 L1)
PYRAMID_SMOKE=1 python3 orchestrate.py --arm shared_l1 --agents mock_oracle,mock --offline --limit 8

# 2) 在线措辞抽查:每层 10 道,人工通读全部 40 道再放行全量
export GEMINI_API_KEY=...           # 只在 shell 里,不落盘
PYRAMID_SMOKE=1 $GEM orchestrate.py --arm shared_l1 --agents mock_oracle --limit 10
#   读 output/pyramid_smoke/sets/*/*/L*.json 里的 question 字段与 *_rejected.json

# 3) 正式跑(顺序:先 shared_l1 看报告,再 per_agent,最后 pooled)
$GEM orchestrate.py --arm shared_l1 --agents gemini,qwen
$GEM orchestrate.py --arm per_agent --agents gemini,qwen
$GEM orchestrate.py --arm pooled    --agents gemini,qwen

# 4) 报告
python3 report.py                    # -> output/pyramid/report/report.json
```

一切可续跑:题套幂等(存在即复用)、结果 jsonl 按 question_id 跳过已答、措辞有磁盘缓存。
orchestrate 用 `pconfig.AGENT_INTERPRETER` 把 qwen 的评测 subprocess 分发到 timechatcap
环境(30B 权重每次 evaluate 调用加载一次,约 5–10 分钟)。

## 校准与可信度

- 每套题组好后自动跑 mock_oracle(必须 100%,否则断言停下)与 mock random(应落在
  25% 二项带内 —— 跨层难度漂移探测器),记入 `state/<arm>.json`。
- gold 位置精确 25/25/25/25;干扰项与 gold 全由程序挖出并在固定窗口上重推
  (`verify.py`),Gemini 措辞被拒只丢弃或回退模板(标 `phrasing:"template"`,上限 20%)。
- 可比性:per_agent 臂与 shared_l1 的 L2+ 中不同 agent 答不同题,跨 agent 只能定性;
  pooled 臂与共享 L1 是跨 agent 锚点;主分析是同一 agent 的跨臂差值。

## 文件

pconfig(常量)→ facts(挖事实)→ phrase(Gemini/模板措辞)→ verify(校验闸门)→
assemble(组卷)→ evaluate(单套评测)→ adapt(作答摘要)→ orchestrate(臂驱动)→
report(汇总);gemini_io 是确定性 JSON 生成(temp 0、seed 42、4 模型回退)。
