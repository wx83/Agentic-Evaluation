# self vs gold history:`p2_hdepicE_1023t_g4_v16_self__55` vs `p2_hdepicE_1023t_g4_v16_gold__55`

self = Solver 看到下层题 + 自己的回答;gold = 同一批题,下层答案换成参考答案(L1–L3 的参考答案是 Examiner 的 proposed_reference_answer,未人工核验)。

| layer | n | self 对 | gold 对 | self acc | gold acc | self✗→gold✓ | self✓→gold✗ | history 深度(中位 / 0 条的题) | 剔除同答案 |
|---|---|---|---|---|---|---|---|---|---|
| L1 | 17 | 11 | 11 | 0.65 | 0.65 | 1 | 1 | 0 / 17 | 0 |
| L2 | 33 | 25 | 23 | 0.76 | 0.70 | 0 | 2 | 7 / 0 | 0 |
| L3 | 12 | 10 | 11 | 0.83 | 0.92 | 1 | 0 | 15 / 0 | 0 |
| L4 | 3 | 3 | 3 | 1.00 | 1.00 | 0 | 0 | 10 / 0 | 0 |
| **all** | 65 | 49 | 48 | 0.75 | 0.74 | 2 | 3 | | |

| layer | skill | n | self 对 | gold 对 |
|---|---|---|---|---|
| L1 | object_grounding | 4 | 1 | 2 |
| L1 | object_location_at_time | 5 | 3 | 3 |
| L1 | object_recognition | 8 | 7 | 6 |
| L2 | action_recognition | 5 | 4 | 4 |
| L2 | action_temporal_order | 6 | 4 | 4 |
| L2 | event_object_role | 6 | 6 | 5 |
| L2 | object_state_change | 6 | 6 | 6 |
| L2 | sound_action_binding | 5 | 3 | 3 |
| L2 | sound_movement_binding | 5 | 2 | 1 |
| L3 | causal_prerequisite_reasoning | 6 | 4 | 5 |
| L3 | cross_event_integration | 6 | 6 | 6 |
| L4 | goal_conditioned_planning | 3 | 3 | 3 |

| layer | 计分题 | 有 scope_id | 有 history(n>0) |
|---|---|---|---|
| L1 | 17 | 0 | 0 |
| L2 | 33 | 0 | 33 |
| L3 | 12 | 0 | 12 |
| L4 | 3 | 0 | 3 |
