# self vs gold history:`p2_hdepicE_1023t_g4_v16_self__13` vs `p2_hdepicE_1023t_g4_v16_gold__13`

self = Solver 看到下层题 + 自己的回答;gold = 同一批题,下层答案换成参考答案(L1–L3 的参考答案是 Examiner 的 proposed_reference_answer,未人工核验)。

| layer | n | self 对 | gold 对 | self acc | gold acc | self✗→gold✓ | self✓→gold✗ | history 深度(中位 / 0 条的题) | 剔除同答案 |
|---|---|---|---|---|---|---|---|---|---|
| L1 | 17 | 10 | 11 | 0.59 | 0.65 | 1 | 0 | 0 / 17 | 0 |
| L2 | 26 | 24 | 24 | 0.92 | 0.92 | 0 | 0 | 6 / 0 | 5 |
| L3 | 11 | 10 | 11 | 0.91 | 1.00 | 1 | 0 | 25 / 0 | 0 |
| L4 | 3 | 3 | 2 | 1.00 | 0.67 | 0 | 1 | 13 / 0 | 0 |
| **all** | 57 | 47 | 48 | 0.82 | 0.84 | 2 | 1 | | |

| layer | skill | n | self 对 | gold 对 |
|---|---|---|---|---|
| L1 | object_grounding | 4 | 1 | 1 |
| L1 | object_location_at_time | 8 | 6 | 6 |
| L1 | object_recognition | 4 | 2 | 3 |
| L1 | spatial_near | 1 | 1 | 1 |
| L2 | action_recognition | 6 | 6 | 6 |
| L2 | event_object_role | 6 | 6 | 6 |
| L2 | object_state_change | 4 | 4 | 4 |
| L2 | sound_action_binding | 5 | 4 | 4 |
| L2 | sound_anchored_spatial_near | 4 | 3 | 3 |
| L2 | sound_movement_binding | 1 | 1 | 1 |
| L3 | causal_prerequisite_reasoning | 6 | 6 | 6 |
| L3 | cross_event_integration | 5 | 4 | 5 |
| L4 | goal_conditioned_planning | 3 | 3 | 2 |

| layer | 计分题 | 有 scope_id | 有 history(n>0) |
|---|---|---|---|
| L1 | 17 | 0 | 0 |
| L2 | 26 | 0 | 26 |
| L3 | 11 | 0 | 11 |
| L4 | 3 | 0 | 3 |
