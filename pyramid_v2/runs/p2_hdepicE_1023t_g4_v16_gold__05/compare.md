# self vs gold history:`p2_hdepicE_1023t_g4_v16_self__05` vs `p2_hdepicE_1023t_g4_v16_gold__05`

self = Solver 看到下层题 + 自己的回答;gold = 同一批题,下层答案换成参考答案(L1–L3 的参考答案是 Examiner 的 proposed_reference_answer,未人工核验)。

| layer | n | self 对 | gold 对 | self acc | gold acc | self✗→gold✓ | self✓→gold✗ | history 深度(中位 / 0 条的题) | 剔除同答案 |
|---|---|---|---|---|---|---|---|---|---|
| L1 | 17 | 11 | 10 | 0.65 | 0.59 | 0 | 1 | 0 / 17 | 0 |
| L2 | 41 | 31 | 30 | 0.76 | 0.73 | 0 | 1 | 4 / 0 | 1 |
| L3 | 11 | 9 | 9 | 0.82 | 0.82 | 0 | 0 | 17 / 0 | 0 |
| L4 | 3 | 3 | 3 | 1.00 | 1.00 | 0 | 0 | 10 / 0 | 0 |
| **all** | 72 | 54 | 52 | 0.75 | 0.72 | 0 | 2 | | |

| layer | skill | n | self 对 | gold 对 |
|---|---|---|---|---|
| L1 | object_grounding | 3 | 0 | 0 |
| L1 | object_location_at_time | 2 | 1 | 1 |
| L1 | object_recognition | 10 | 9 | 8 |
| L1 | spatial_near | 1 | 1 | 1 |
| L1 | spatial_side | 1 | 0 | 0 |
| L2 | action_recognition | 6 | 6 | 6 |
| L2 | action_temporal_order | 5 | 4 | 3 |
| L2 | event_object_role | 6 | 6 | 6 |
| L2 | object_state_change | 8 | 7 | 7 |
| L2 | sound_action_binding | 9 | 8 | 8 |
| L2 | sound_anchored_spatial_near | 2 | 0 | 0 |
| L2 | sound_anchored_spatial_side | 2 | 0 | 0 |
| L2 | sound_movement_binding | 3 | 0 | 0 |
| L3 | causal_prerequisite_reasoning | 1 | 1 | 1 |
| L3 | cross_event_integration | 8 | 7 | 7 |
| L3 | hidden_state_inference | 2 | 1 | 1 |
| L4 | goal_conditioned_planning | 3 | 3 | 3 |

| layer | 计分题 | 有 scope_id | 有 history(n>0) |
|---|---|---|---|
| L1 | 17 | 0 | 0 |
| L2 | 41 | 0 | 41 |
| L3 | 11 | 0 | 11 |
| L4 | 3 | 0 | 3 |
