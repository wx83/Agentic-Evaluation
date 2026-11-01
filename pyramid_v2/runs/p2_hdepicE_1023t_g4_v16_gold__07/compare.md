# self vs gold history:`p2_hdepicE_1023t_g4_v16_self__07` vs `p2_hdepicE_1023t_g4_v16_gold__07`

self = Solver 看到下层题 + 自己的回答;gold = 同一批题,下层答案换成参考答案(L1–L3 的参考答案是 Examiner 的 proposed_reference_answer,未人工核验)。

| layer | n | self 对 | gold 对 | self acc | gold acc | self✗→gold✓ | self✓→gold✗ | history 深度(中位 / 0 条的题) | 剔除同答案 |
|---|---|---|---|---|---|---|---|---|---|
| L1 | 17 | 14 | 14 | 0.82 | 0.82 | 0 | 0 | 0 / 17 | 0 |
| L2 | 40 | 30 | 30 | 0.75 | 0.75 | 1 | 1 | 6 / 0 | 1 |
| L3 | 12 | 10 | 10 | 0.83 | 0.83 | 0 | 0 | 31 / 0 | 0 |
| L4 | 7 | 6 | 5 | 0.86 | 0.71 | 0 | 1 | 24 / 0 | 0 |
| **all** | 76 | 60 | 59 | 0.79 | 0.78 | 1 | 2 | | |

| layer | skill | n | self 对 | gold 对 |
|---|---|---|---|---|
| L1 | object_grounding | 5 | 2 | 2 |
| L1 | object_location_at_time | 2 | 2 | 2 |
| L1 | object_recognition | 6 | 6 | 6 |
| L1 | spatial_near | 1 | 1 | 1 |
| L1 | spatial_side | 3 | 3 | 3 |
| L2 | action_recognition | 6 | 6 | 6 |
| L2 | action_temporal_order | 5 | 4 | 4 |
| L2 | event_object_role | 4 | 1 | 1 |
| L2 | object_state_change | 6 | 6 | 6 |
| L2 | sound_action_binding | 9 | 8 | 7 |
| L2 | sound_anchored_spatial_side | 6 | 4 | 4 |
| L2 | sound_movement_binding | 4 | 1 | 2 |
| L3 | causal_prerequisite_reasoning | 4 | 3 | 3 |
| L3 | cross_event_integration | 8 | 7 | 7 |
| L4 | goal_conditioned_planning | 7 | 6 | 5 |

| layer | 计分题 | 有 scope_id | 有 history(n>0) |
|---|---|---|---|
| L1 | 17 | 0 | 0 |
| L2 | 40 | 0 | 40 |
| L3 | 12 | 0 | 12 |
| L4 | 7 | 0 | 7 |
