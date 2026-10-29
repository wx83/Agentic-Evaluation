# Qwen3-Omni 推理服务器迁移到 H200(pyramid2 的 Solver / Examiner 后端)

这个文件夹是一个独立的 Qwen3-Omni-30B-A3B-Instruct HTTP 服务,pyramid2 通过 `solver_backend: qwen_http` / `examiner_backend: qwen_http` 调它。
pyramid2 本身(代码、证据库、clip、Gemini 调用)**留在原机器**,只把 Qwen 推理搬到 H200;两边用 HTTP 连。

## 1. 文件夹内容

| 文件 | 作用 |
|---|---|
| `qwen_server.py` | HTTP 服务(单线程、每请求新 session)。`GET /` 探活,`POST /ask` 推理。比原版多两样:`media_b64`(远程调用时直接把 mp4 内容发过来,不需要共享文件系统)和 `system`(可选 system prompt,Examiner 用)。 |
| `qwen_agent.py` | 模型加载与推理,从 `agent/bench/agents/qwen_agent.py` 抽出,去掉了对仓库 `config.py` 的依赖;模型路径由环境变量 `QWEN_PATH` 或 `--model` 给。含 librosa 1.0 的 ffmpeg 抽音补丁。 |
| `requirements.txt` | 当前机器实测可用的版本(Python 3.12.13、torch 2.9.1+cu128、transformers 4.57.1、qwen-omni-utils 0.0.9)。 |
| `environment_timechatcap_full.yml` | 当前 conda 环境完整导出,只作参考,不建议整份复现(里面有和 Qwen 无关的包)。 |
| `start_servers.sh` | 两张卡各起一个服务器:GPU0 → 端口 8799,GPU1 → 8800。 |
| `smoke_test.py` | 三个请求:纯文字、本地路径视频、base64 上传视频。 |
| `sample/clip_20s.mp4` | 一段 20 s 的 HD-EPIC clip(带音轨),给 smoke test 用。 |
| `model/`(需要你放) | 模型权重,见第 2 节。 |

**不在文件夹里、需要单独搬的**:模型权重 66 GB(第 2 节)。clip 不用搬(第 5 节用 `media_b64` 直接传)。

## 2. 模型权重(66 GB)

两种方式任选:

```bash
# A. 从原机器 rsync(原目录是指向 HF cache 的符号链接,-L 跟随链接复制真实文件)
rsync -avL --progress weihanxu@<原机器>:/mnt/work_new/weihanxu/agent/Qwen3-Omni/Qwen3-Omni-30B-A3B-Instruct/  ./model/Qwen3-Omni-30B-A3B-Instruct/

# B. 直接从 Hugging Face 下载(同一个模型)
pip install -U huggingface_hub
huggingface-cli download Qwen/Qwen3-Omni-30B-A3B-Instruct --local-dir ./model/Qwen3-Omni-30B-A3B-Instruct
```

权重 bf16 约 60 GB 显存,H200 141 GB 一张卡放得下,剩余给 KV cache(Examiner 输入 5 万 token 约再用 5 GB)。

## 3. 环境

```bash
# 系统依赖:ffmpeg(抽音轨用),CUDA 驱动 ≥ 12.8
sudo apt-get install -y ffmpeg            # 或 conda install -c conda-forge ffmpeg

conda create -n qwen python=3.12 -y
conda activate qwen
pip install -r requirements.txt            # torch 走 cu128 索引,已写在文件里
python -c "import torch, transformers; print(torch.cuda.is_available(), torch.cuda.device_count(), transformers.__version__)"
```

注意:
- transformers 必须是带 `Qwen3OmniMoeForConditionalGeneration` 的版本(4.57.1 实测可用);升到 5.x 没有验证过。
- 不装 flash-attn 也能跑(现在就是默认 attention)。
- `qwen_omni_utils` 对 librosa 1.0 的兼容问题已在 `qwen_agent.py` 里打补丁(先 ffmpeg 抽 wav),不用降级 librosa。

## 4. 启动与自测

```bash
cd qwen_h200_bundle
export QWEN_PATH=$PWD/model/Qwen3-Omni-30B-A3B-Instruct
./start_servers.sh 2 8799             # 2 张卡 → 8799、8800;日志 logs/qwen_server_<port>.log
# 或单张卡手动:
# CUDA_VISIBLE_DEVICES=0 python qwen_server.py --port 8799 --host 0.0.0.0

# 等日志出现 "[qwen_server] listening on ..."(加载约 2–3 分钟),然后
python smoke_test.py --url http://127.0.0.1:8799
```

smoke test 预期输出:`GET /` 返回 `{"ok": true}`;纯文字一两秒返回 `OK`;两次视频请求各 10–40 s,返回一句对画面的描述,`meta` 里有 `n_input_tokens`、`n_output_tokens`、`peak_gpu_mb`。

服务器是**单线程**的:同一端口上的请求排队。要并行就多开端口(每张卡一个;H200 显存够的话同一张卡开第二个进程也行,但两个进程各占 60 GB 权重,141 GB 放不下两份,所以一张卡一个)。

`--host 0.0.0.0` 让原机器能直接连;如果 H200 不开放端口,就用 SSH 隧道(第 5 节)。

## 5. 原机器(pyramid2)怎么连

### 5.1 网络
二选一:
```bash
# 直连:H200 的 8799/8800 对原机器开放
qwen_url = "http://<h200-ip>:8799"

# SSH 隧道:在原机器上开,把远端 8799/8800 映射到本机
ssh -N -L 8799:127.0.0.1:8799 -L 8800:127.0.0.1:8800 <user>@<h200-ip> &
qwen_url = "http://127.0.0.1:8799"
```

### 5.2 合约改三项
```json
"solver_backend": "qwen_http",
"qwen_url": "http://<h200-ip 或 127.0.0.1>:8799",
"qwen_send_media": true
```
`qwen_send_media: true` 让 pyramid2 的 `solver.ask_qwen` 把 clip 文件内容 base64 放进请求(`media_b64`),H200 不需要能读原机器的路径;clip 通常 0.5–1.5 MB,一次请求几 MB,没问题。Examiner 走 `examiner_backend: qwen_http` 时只发文字,不受影响。

两张卡两个端口:把 task 分成两组,一组合约 `qwen_url` 指 8799、另一组指 8800,两个 run 脚本同时跑。

### 5.3 验证
```bash
cd /mnt/work_new/weihanxu/agent/bench/pyramid2
GEMINI_BACKEND=nv python3 cli.py preflight --contract <合约>.json      # qwen_http 的角色改成探活,不查 NVIDIA 模型表
```
然后照常 `./run_smoke.sh <合约> L1 L2 L3 L4`。

## 6. 速度参考(原机器 RTX PRO 6000 96 GB,HF eager,单线程)

| 调用 | 中位 | p90 |
|---|---|---|
| Solver 答题(v16 clip 10–30 s) | 39 s | 274 s(L3 的长 clip) |
| Examiner 出题(输入约 2.4 万 token,输出 ~700 token) | 68 s | 108 s |

H200 显存带宽约是这张卡的 2.6 倍,解码会快,视频编码部分提升有限;估 1.5–2 倍。一个 v16 task(约 65 题,self + gold 各答一次):Qwen 只做 Solver 约 1–1.5 h / 卡;Qwen 同时做 Examiner 约 2–2.5 h / 卡。

## 7. 常见问题

- **端口已被占用**:`ss -ltnp | grep 8799`;换端口或停掉旧进程。服务器不答 GET 时用 `ss` 判断是否在监听(新版 server 已支持 GET)。
- **`TypeError: Invalid file`(librosa)**:说明 `_patch_audio_backend` 没生效,检查 ffmpeg 在 PATH 里。
- **显存不够**:`disable_talker()` 已省约 10 GB;长 clip 的帧数由 `FPS_MAX_FRAMES`(默认 600)限制,可以调低。
- **多个客户端同时打一个端口**:会排队不报错,但每个客户端看到的延迟翻倍;按卡分端口。
- 本文件夹在 H200 上**没有实跑过**(原机器只有一张卡且被占用),第 4 节 smoke test 过了就等于验证通过。

## 8. 在 tillicum 上跑整个 pyramid2(Qwen 相关的全部 case,Gemini 出题)

第 1–7 节只把 Qwen 推理搬过去。这一节把 pyramid2 主流程也搬过去,出题 / scope / judge 仍是 Gemini(走 NVIDIA gateway),答题是本机的 Qwen 服务器。

### 8.1 内容

| 位置 | 内容 | 来源 |
|---|---|---|
| `pyramid2_root/agent/bench/` | `config.py`、`clips.py` 等 + `pyramid/` + `pyramid2/`(去掉 `.bak`) | GitHub(本 repo) |
| `pyramid2_root/gemini/` | `nv_gemini.py`(Gemini NV gateway 客户端,不含 key) | GitHub |
| `pyramid2_root/output/pyramid_v2/contracts/` | 全部合约(223 个 Qwen 合约 + 新加的 `qwen_gx_v16`) | GitHub |
| `pyramid2_root/experiments/daily_report/*prompts*.md` | 合约引用的 prompt 文件 | GitHub |
| `pyramid2_root/experiments/hdepic_goal_gen/out/E/<video>/` | Method E 切好的每个 task 的 sub-goal(`merged.json` + 每个 step 一个 json + `audio_tags.json`),50 个视频;`out/picks/` 与生成代码 `method_e.py` 等 | GitHub |
| `output/pyramid_v2/data/` | 证据库 evidence.jsonl 等、scope/sg 缓存(约 400 MB) | HF private dataset `WitneyWW/pyramid2-qwen-data-1028` |
| `output/pyramid_v2/media/hdepic_e/` | 已切好的 2280 个 clip(2.2 GB) | 同上 |
| `output/pyramid_v2/runs/` | 已有 run(gold / none 重放要读 self run,710 MB) | 同上 |
| `output/_shared/pose/` | HD-EPIC 位姿缓存(代替 318 GB SLAM) | 同上 |
| `hd-epic/annotations/` | HD-EPIC 官方标注(gaze priming 用) | 同上 |
| `hd-epic/video/`(可选) | 49 个原视频 68 GB,只有跑新 task / 新窗口才需要 | 同上(`--with-videos`) |

合约种类:`examiner_backend` 不写 = Gemini 出题(217 个,v5–v12 等)+ `qwen_gx_v16`(Gemini 出题、Qwen 答题,task 55/39/07/13/05,self + gold);`examiner_backend: qwen_http` = Qwen 出题(qwen_v14 / qwen_v16,6 个)。

### 8.2 安装

```bash
git clone -b qwen-h200-bundle git@github.com:wx83/Agentic-Evaluation.git && cd Agentic-Evaluation/qwen_h200_bundle
pip install -r requirements.txt -r requirements_pyramid2.txt      # 与第 3 节同一个 env 即可
HF_TOKEN=<你的 HF token> ./setup_pyramid2.sh                       # 下载数据 + 把原机器路径改成本地路径
export NVIDIA_API_KEY=<Gemini NV gateway key>                      # 只放环境变量,不要写进 repo
```

### 8.3 运行

```bash
./start_servers.sh 1 8799                                          # 合约里 qwen_url = http://127.0.0.1:8799,pyramid2 和服务器在同一个节点上跑
cd pyramid2_root/agent/bench/pyramid2
GEMINI_BACKEND=nv python3 cli.py preflight --contract ../../../output/pyramid_v2/contracts/p2_hdepicE_1023t_qwen_gx_v16_self__55.json
nohup ./run_qwen_gx_v16.sh 55 > ../../../logs/pyramid2/run_qwen_gx_v16.log 2>&1 &
```
单个合约:`./run_smoke.sh <合约> L1 L2 L3 L4`;gold / none 臂:`GEMINI_BACKEND=nv python3 cli.py replay --contract <gold 合约> --from-run <self run_id>`。
pyramid2 和 Qwen 服务器不在同一节点时,把合约里的 `qwen_url` 改成服务器节点地址(`qwen_send_media` 已是 true,clip 随请求发送)。

不包含:HF Space 建站 / 推送步骤(原 run 脚本末尾的 `hf_space_*` 部分),以及 Ego4D / EgoPlan / AEA 的 clip 和原视频。
