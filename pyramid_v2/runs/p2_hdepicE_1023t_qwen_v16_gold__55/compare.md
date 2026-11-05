# self vs gold history:`p2_hdepicE_1023t_qwen_v16_self__55` vs `p2_hdepicE_1023t_qwen_v16_gold__55`

self = Solver 看到下层题 + 自己的回答;gold = 同一批题,下层答案换成参考答案(L1–L3 的参考答案是 Examiner 的 proposed_reference_answer,未人工核验)。

| layer | n | self 对 | gold 对 | self acc | gold acc | self✗→gold✓ | self✓→gold✗ | history 深度(中位 / 0 条的题) | 剔除同答案 |
|---|---|---|---|---|---|---|---|---|---|
| L1 | 8 | 2 | 2 | 0.25 | 0.25 | 0 | 0 | 0 / 8 | 0 |
| L2 | 20 | 13 | 15 | 0.65 | 0.75 | 2 | 0 | 4 / 0 | 0 |
| L3 | 9 | 7 | 8 | 0.78 | 0.89 | 1 | 0 | 14 / 0 | 0 |
| L4 | 2 | 1 | 1 | 0.50 | 0.50 | 0 | 0 | 9 / 0 | 0 |
| **all** | 39 | 23 | 26 | 0.59 | 0.67 | 3 | 0 | | |

| layer | skill | n | self 对 | gold 对 |
|---|---|---|---|---|
| L1 | object_location_at_time | 4 | 1 | 1 |
| L1 | object_recognition | 4 | 1 | 1 |
| L2 | action_recognition | 8 | 6 | 6 |
| L2 | action_temporal_order | 4 | 4 | 4 |
| L2 | event_object_role | 3 | 2 | 3 |
| L2 | sound_action_binding | 4 | 1 | 2 |
| L2 | sound_movement_binding | 1 | 0 | 0 |
| L3 | causal_prerequisite_reasoning | 3 | 2 | 3 |
| L3 | cross_event_integration | 6 | 5 | 5 |
| L4 | goal_conditioned_planning | 2 | 1 | 1 |

| layer | 计分题 | 有 scope_id | 有 history(n>0) |
|---|---|---|---|
| L1 | 8 | 0 | 0 |
| L2 | 20 | 0 | 20 |
| L3 | 9 | 0 | 9 |
| L4 | 2 | 0 | 2 |
