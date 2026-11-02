"""evidence / media / item / candidate 的字段词表与校验(1012.md §8-§10)。"""
EPISTEMIC = {"observation", "measurement", "participant_report", "interpretation", "stipulated_condition"}
SOLVER_ACCESS = {"observed", "answer_only", "stipulated"}
TIME_BASES = {"source_video_seconds", "clip_local_seconds", "precut_clip_seconds"}
VERIFICATION = {"verified", "needs_verification", "rejected"}
COMPLETENESS = {"complete", "partial", "window_only", "unknown", "absent"}
ID_SPACES = {"hdepic_assoc", "hdepic_mask", "om_chunk_local", "ego4d_person", "name_only", "ego4d_uid", "task",
             "geo3d_track", "geo3d_fixture"}      # geo3d_fixture: Gemini fixture candidate geo3d:<sid>:fixture:<slug>;geo3d_track: SAM3 文字跟踪实例 geo3d:<sid>:<slug>#<obj_id>(只在该 clip 内唯一)
DOMAINS = {"physical.objects_properties", "physical.spatial", "physical.dynamics", "physical.causality",
           "human.goals_preferences", "human.affect", "human.social", "human.communication", "human.attention",
           "task.structure"}
KINDS = {"sound_source_direction", "gaze_sample",   # 10-27 晚 AEA(adapters/aea_p_spatial.py)
    
    # HD-EPIC
    "sound_event", "action_narration", "object_move", "object_location_transition", "object_visible_track",
    "object_mask_anchor", "recipe_step", "task_recipe", "gaze_fixation",
    # task timeline
    "task_segment", "task_step",
    # Ego4D
    "hand_object_interaction", "action_scene_graph", "object_parts_attributes", "object_state_change",
    "next_active_object", "future_action_sequence", "activity_moment", "visual_query_track",
    "utterance", "person_talking", "person_looking",
    # hdepic_annot / tactile / object_memory(后置)
    "object_name", "object_position_anchor", "object_mask", "object_3d_box", "task_segment_candidate",
    "action_with_roles", "hand_object_role", "spatial_relation", "object_description", "camera_pose",
    "object_position_interval", "object_observation", "fixture_alias", "object_identity", "object_reference_point",
    "tactile_property_episode", "object_instance", "object_state", "object_state_transition",
    "sound_object_binding_candidate", "contact_rich_action",
    # geo3d(10-15 spec §4-§7):每 clip 一条 frame / calibration;fixture 为 Gemini candidate
    "spatial_frame", "camera_calibration", "fixture_candidate",
}
FORMATS = {"single_choice", "multi_select", "short_answer", "plan", "gap_steps", "bbox"}   # bbox(10-27):object_grounding,作答 = 框
ACTIONS_DIAG = {"PROPOSE_DIAGNOSTIC", "REQUEST_VERIFICATION", "BEGIN_CONFIRMATION", "INCONCLUSIVE"}
ACTIONS_CONF = {"PROPOSE_CONFIRMATION", "REQUEST_VERIFICATION", "INCONCLUSIVE"}
STRATEGIES = {"coverage", "same_skill_new_event", "same_skill_cleaner_event", "same_event_new_format",
              "request_verification"}

EVIDENCE_REQUIRED = ("evidence_id", "version", "video_id", "media_id", "kind", "domain", "time", "entities", "value",
                     "epistemic_type", "modalities_supporting_fact", "solver_access", "provenance", "verification",
                     "coverage", "quality_flags")


def validate_evidence(r):
    e = []
    for k in EVIDENCE_REQUIRED:
        if k not in r:
            e.append(f"missing {k}")
    if e:
        return e
    if r["kind"] not in KINDS: e.append(f"kind {r['kind']}")
    if r["domain"] not in DOMAINS: e.append(f"domain {r['domain']}")
    if r["epistemic_type"] not in EPISTEMIC: e.append(f"epistemic {r['epistemic_type']}")
    if r["solver_access"] not in SOLVER_ACCESS: e.append(f"solver_access {r['solver_access']}")
    t = r["time"]
    if t is None:
        e.append("time None")
    else:
        if t.get("time_base") not in TIME_BASES: e.append(f"time_base {t.get('time_base')}")
        if t.get("start_sec") is None or t.get("end_sec") is None: e.append("time missing")
        elif t["start_sec"] > t["end_sec"] + 1e-6: e.append("start>end")
    if r["verification"].get("status") not in VERIFICATION: e.append("verification.status")
    if r["coverage"].get("completeness") not in COMPLETENESS: e.append("coverage.completeness")
    for ent in r["entities"]:
        if ent.get("id_space") not in ID_SPACES: e.append(f"entity id_space {ent.get('id_space')}")
    if not isinstance(r["version"], int) or r["version"] < 1: e.append("version")
    ch = r.get("checks")                       # 可选:模型 / 人工的旁路核验,不改 verification.status(build 会重刷 verification,checks 不会)
    if ch is not None:
        if not isinstance(ch, list): e.append("checks not list")
        else:
            for c in ch:
                if not isinstance(c, dict) or not all(k in c for k in ("method", "verdict", "confidence")): e.append("checks item needs method/verdict/confidence"); break
    return e


def validate_media(m):
    e = []
    for k in ("media_id", "dataset", "video_id", "kind", "path", "time_base", "annotation_sources"):
        if k not in m: e.append(f"missing {k}")
    if m.get("kind") not in ("source_video", "precut_clip"): e.append("kind")
    if m.get("time_base") not in TIME_BASES: e.append("time_base")
    return e


def validate_candidate(out, phase):
    """Examiner 输出(§10)结构校验;语义校验在 examiner.check_output。"""
    e = []
    if not isinstance(out, dict):
        return ["not an object"]
    act = out.get("action")
    allowed = ACTIONS_DIAG if phase == "DIAGNOSIS" else ACTIONS_CONF
    if act not in allowed: e.append(f"action {act!r} not in {sorted(allowed)}")
    if act in ("PROPOSE_DIAGNOSTIC", "PROPOSE_CONFIRMATION"):
        pub, pri = out.get("public"), out.get("private")
        if not isinstance(pub, dict): e.append("public missing"); return e
        if not isinstance(pri, dict): e.append("private missing"); return e
        if pub.get("format") not in FORMATS: e.append(f"format {pub.get('format')}")
        if not pub.get("question"): e.append("question empty")
        if not pub.get("media_refs"): e.append("media_refs empty")
        if pub.get("format") == "single_choice":
            o = pub.get("options")
            if not (isinstance(o, list) and len(o) == 4): e.append("single_choice needs 4 options")
        if pub.get("format") == "multi_select":
            o = pub.get("options")
            if not (isinstance(o, list) and 3 <= len(o) <= 5): e.append("multi_select needs 3-5 statements")
        if pri.get("gold_answer") is not None: e.append("gold_answer must be null")
        if pri.get("gold_verification_status") != "needs_verification": e.append("gold_verification_status")
        if pri.get("validation_status") != "PENDING_VALIDATION": e.append("validation_status")
        if pri.get("proposed_reference_answer") in (None, ""): e.append("proposed_reference_answer empty")
        if not pri.get("evidence_refs"): e.append("evidence_refs empty")
        if out.get("strategy") not in STRATEGIES: e.append(f"strategy {out.get('strategy')}")
        if not out.get("selection_reason"): e.append("selection_reason empty")
    else:
        if act == "REQUEST_VERIFICATION" and not out.get("verification_request"):
            e.append("verification_request empty")
    return e
