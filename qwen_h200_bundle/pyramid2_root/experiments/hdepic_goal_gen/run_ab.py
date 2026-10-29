#!/usr/bin/env python3
"""Usage: python -I run_ab.py <A|B> <video_id> ...   -> out/<method>/<video>/{input_actions,wXX,merged}.json"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import common
m = sys.argv[1].upper(); P = __import__({"A": "prompts_a", "B": "prompts_b", "C": "prompts_c", "D": "prompts_d"}[m])
if m == "C": common.WIN, common.CTX = 250, 30
for vid in sys.argv[2:]:
    print(f"== {m} {vid}", flush=True)
    common.run_method(vid, m, P.SYSTEM, P.build_prompt, f"{HERE}/out/{m}/{vid}")
