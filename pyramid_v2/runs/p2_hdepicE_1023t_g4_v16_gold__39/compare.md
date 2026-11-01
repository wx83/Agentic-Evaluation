# self vs gold history:`p2_hdepicE_1023t_g4_v16_self__39` vs `p2_hdepicE_1023t_g4_v16_gold__39`

self = Solver 看到下层题 + 自己的回答;gold = 同一批题,下层答案换成参考答案(L1–L3 的参考答案是 Examiner 的 proposed_reference_answer,未人工核验)。

| layer | n | self 对 | gold 对 | self acc | gold acc | self✗→gold✓ | self✓→gold✗ | history 深度(中位 / 0 条的题) | 剔除同答案 |
|---|---|---|---|---|---|---|---|---|---|
| L1 | 9 | 7 | 8 | 0.78 | 0.89 | 1 | 0 | 0 / 9 | 0 |
| L2 | 36 | 25 | 27 | 0.69 | 0.75 | 2 | 0 | 4 / 0 | 0 |
| L3 | 6 | 5 | 6 | 0.83 | 1.00 | 1 | 0 | 18 / 0 | 0 |
| L4 | 5 | 3 | 2 | 0.60 | 0.40 | 0 | 1 | 14 / 0 | 0 |
| **all** | 56 | 40 | 43 | 0.71 | 0.77 | 4 | 1 | | |

| layer | skill | n | self 对 | gold 对 |
|---|---|---|---|---|
| L1 | object_grounding | 3 | 1 | 2 |
| L1 | object_location_at_time | 3 | 3 | 3 |
| L1 | object_recognition | 2 | 2 | 2 |
| L1 | spatial_near | 1 | 1 | 1 |
| L2 | action_recognition | 6 | 6 | 6 |
| L2 | action_temporal_order | 12 | 9 | 11 |
| L2 | event_object_role | 2 | 2 | 2 |
| L2 | object_state_change | 2 | 2 | 2 |
| L2 | sound_action_binding | 8 | 4 | 4 |
| L2 | sound_anchored_spatial_near | 3 | 1 | 1 |
| L2 | sound_movement_binding | 3 | 1 | 1 |
| L3 | causal_prerequisite_reasoning | 1 | 1 | 1 |
| L3 | cross_event_integration | 5 | 4 | 5 |
| L4 | goal_conditioned_planning | 5 | 3 | 2 |

| layer | 计分题 | 有 scope_id | 有 history(n>0) |
|---|---|---|---|
| L1 | 9 | 0 | 0 |
| L2 | 36 | 0 | 36 |
| L3 | 6 | 0 | 6 |
| L4 | 5 | 0 | 5 |
