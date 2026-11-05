# self vs gold history:`p2_hdepicE_1023t_qwen_v16_self__39` vs `p2_hdepicE_1023t_qwen_v16_gold__39`

self = Solver 看到下层题 + 自己的回答;gold = 同一批题,下层答案换成参考答案(L1–L3 的参考答案是 Examiner 的 proposed_reference_answer,未人工核验)。

| layer | n | self 对 | gold 对 | self acc | gold acc | self✗→gold✓ | self✓→gold✗ | history 深度(中位 / 0 条的题) | 剔除同答案 |
|---|---|---|---|---|---|---|---|---|---|
| L1 | 5 | 0 | 0 | 0.00 | 0.00 | 0 | 0 | 0 / 5 | 0 |
| L2 | 19 | 12 | 13 | 0.63 | 0.68 | 1 | 0 | 3 / 0 | 0 |
| L3 | 4 | 3 | 3 | 0.75 | 0.75 | 0 | 0 | 14 / 0 | 0 |
| **all** | 28 | 15 | 16 | 0.54 | 0.57 | 1 | 0 | | |

| layer | skill | n | self 对 | gold 对 |
|---|---|---|---|---|
| L1 | object_grounding | 3 | 0 | 0 |
| L1 | object_location_at_time | 2 | 0 | 0 |
| L2 | action_recognition | 8 | 4 | 5 |
| L2 | action_temporal_order | 2 | 2 | 2 |
| L2 | object_state_change | 4 | 4 | 4 |
| L2 | sound_action_binding | 1 | 1 | 1 |
| L2 | sound_movement_binding | 4 | 1 | 1 |
| L3 | causal_prerequisite_reasoning | 1 | 1 | 1 |
| L3 | cross_event_integration | 3 | 2 | 2 |

| layer | 计分题 | 有 scope_id | 有 history(n>0) |
|---|---|---|---|
| L1 | 5 | 0 | 0 |
| L2 | 19 | 0 | 19 |
| L3 | 4 | 0 | 4 |
