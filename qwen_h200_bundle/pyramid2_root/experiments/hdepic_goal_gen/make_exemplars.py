"""Build exemplars.json for method B from official EgoPlan annotations (times converted from frames with official fps; nothing predicted)."""
import json, random, collections
R = "/mnt/work_new/weihanxu/benchmarks_1011/raw"
e1 = [x for x in json.load(open(f"{R}/egoplan1/EgoPlan_validation.json")) if x.get("video_source") == "EpicKitchens"]
e2 = json.load(open(f"{R}/egoplan2/EgoPlan-Bench2.json"))
def fps_epic(vid):  # EPIC-KITCHENS: P01-P31 recorded at 59.94 fps (EPIC-55), P32+ extension at 50 fps
    return 59.94 if int(vid.split("_")[0][1:]) <= 31 else 50.0
def steps(x, fps):
    s = [{"t0": p["start_frame"] / fps, "t1": p["stop_frame"] / fps, "narration": p["narration_text"]} for p in x["task_progress_metadata"]]
    s.append({"t0": x["current_observation_frame"] / fps, "t1": x["current_observation_frame"] / fps, "narration": x["answer"] + " (next action, official answer)"})
    return s
random.seed(1022)
# bucket EPIC samples by size and verb theme; pick a spread of sizes 4..20 and themes
want = [(4, "wash|rinse|scrub"), (5, "cut|chop|slice|peel"), (6, "pour|stir|mix"), (7, "put away|store|return"), (8, "fry|cook|boil|heat"), (10, None), (12, None), (15, None), (19, None), (6, "fridge|open|take")]
pick = []; used = set()
for n, theme in want:
    c = [x for x in e1 if len(x["task_progress_metadata"]) + 1 == n and x["task_goal"] not in used and (theme is None or __import__("re").search(theme, x["task_goal"], flags=2))]
    c = [x for x in c if not x["task_goal"][0].islower()] or c
    if not c: c = [x for x in e1 if abs(len(x["task_progress_metadata"]) + 1 - n) <= 1 and x["task_goal"] not in used]
    x = random.choice(c); used.add(x["task_goal"])
    pick.append({"source": "EgoPlan-Bench (EPIC-KITCHENS)", "video_id": x["video_id"], "goal": x["task_goal"], "steps": steps(x, fps_epic(x["video_id"]))})
for x in random.sample([x for x in e2 if x["domain"] == "Daily life" and 5 <= len(x["task_progress_metadata"]) + 1 <= 9], 2):
    pick.append({"source": "EgoPlan-Bench2 (Ego4D, 30 fps)", "video_id": x["sample_id"].split("_")[0][:8], "goal": x["task_goal"], "steps": steps(x, 30.0)})
json.dump(pick, open(f"{__import__('os').path.dirname(__import__('os').path.abspath(__file__))}/exemplars.json", "w"), indent=1)
for p in pick: print(len(p["steps"]), p["video_id"], p["goal"])
