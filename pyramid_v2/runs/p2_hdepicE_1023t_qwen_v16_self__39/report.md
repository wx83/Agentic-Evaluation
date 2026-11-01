# pyramid2 run `p2_hdepicE_1023t_qwen_v16_self__39`

dataset hdepic_e · videos 1 · examiner `qwen3-omni-30b-a3b-instruct` · solver `qwen3-omni-30b-a3b-instruct` · n_per_layer 200 · seed 1023 · prompt physical-mental-draft2-hdepic-e+v16sg

**结果为 provisional**:gold = Examiner 的 proposed_reference_answer,未经人工核验;open/plan 题由 Gemini judge 判。

## 每层概览

| layer | stop | turns | scored | correct | raw acc | cluster-dedup acc | follow-up | invalid/unresolved | confirmation |
|---|---|---|---|---|---|---|---|---|---|
| L1 | STAIRCASE_COMPLETE | 10 | 5 | 0 | 0.0 | 0.0 | 0 | 5/0 | - |
| L2 | STAIRCASE_COMPLETE | 42 | 19 | 12 | 0.632 | 0.615 | 0 | 23/0 | - |
| L3 | STAIRCASE_COMPLETE | 7 | 4 | 3 | 0.75 | 0.75 | 0 | 2/0 | - |
| L4 | STAIRCASE_COMPLETE | 3 | 0 | 0 | None | None | 0 | 3/0 | - |

## 每层 × skill 诊断结论

| layer | skill | verdict | scored | correct | clusters | first-try correct | supported hypotheses | confirmation |
|---|---|---|---|---|---|---|---|---|
| L1 | spatial_near | not_started | 0 | 0 | 0 |  | - | - |
| L1 | spatial_side | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L1 | object_recognition | not_started | 0 | 0 | 0 |  | - | - |
| L1 | object_location_at_time | boundary<1 | 2 | 0 | 2 |  | - | - |
| L1 | object_grounding | boundary<1 | 3 | 0 | 3 |  | - | - |
| L2 | sound_action_binding | boundary 1 | 1 | 1 | 1 |  | - | - |
| L2 | object_state_change | boundary 3 | 4 | 4 | 2 |  | - | - |
| L2 | action_temporal_order | boundary 3 | 2 | 2 | 2 |  | - | - |
| L2 | action_recognition | boundary 2.5 | 8 | 4 | 6 |  | - | - |
| L2 | event_object_role | not_started | 0 | 0 | 0 |  | - | - |
| L2 | sound_anchored_spatial_near | not_started | 0 | 0 | 0 |  | - | - |
| L2 | sound_anchored_spatial_side | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L2 | sound_movement_binding | boundary<1 | 4 | 1 | 2 |  | - | - |
| L3 | cross_event_integration | boundary 2.5 | 3 | 2 | 3 |  | - | - |
| L3 | hidden_state_inference | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | spatial_state_integration | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | causal_prerequisite_reasoning | boundary 1.0 | 1 | 1 | 1 |  | - | - |
| L4 | goal_conditioned_planning | not_started | 0 | 0 | 0 |  | - | - |

## L1 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | spatial_near | single_choice | coverage | - | item_invalid | None | A | At the moment the camera wearer adjusts the phone on the counter, which object is closest to the phone? |
| 2 | DIAG | spatial_near | single_choice | coverage | - | item_invalid | None | A | At the moment the can opener is used to open the can of chickpeas, which object is closest to the can opener? |
| 3 | DIAG | object_recognition | single_choice | coverage | - | item_invalid | None | B | At the moment the person is turning the blade of the can opener to open the top of the can, what object is bei |
| 4 | DIAG | object_recognition | single_choice | coverage | - | item_invalid | None | B | At the moment the person is turning the blade of the can opener to open the top of the can, what object is bei |
| 5 | DIAG | object_recognition | single_choice | coverage | - | item_invalid | None | B | At about 4 seconds into the clip, the person is running water over the chickpeas in the colander. What object  |
| 6 | DIAG | object_location_at_time | single_choice | coverage | - | wrong | A | B | At about 4 seconds into the clip, when the chickpeas are being tipped out of the colander, where are the chick |
| 7 | DIAG | object_location_at_time | single_choice | coverage | - | wrong | B | A | At about 10 seconds into the clip, when the person is opening the can of chickpeas, where is the can located? |
| 8 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.01, 0.227, 0.187, 0.447] | 20.9, 46.3, 35.2, 68.2 | In the first frame of the clip, what are the bounding box coordinates (x_min, y_min, x_max, y_max) for the kit |
| 9 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.458, 0.643, 0.677, 0.877] | 47.2, 78.8, 69.7, 100.2 | In the first frame of the clip, what are the bounding box coordinates (x_min, y_min, x_max, y_max) for the col |
| 10 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.425, 0.317, 0.681, 0.645] | 47.4, 64.8, 69.4, 88.5 | In the first frame of the clip, what are the bounding box coordinates (x_min, y_min, x_max, y_max) for the col |

## L2 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | correct | B | B | In the event where the can of chickpeas is being opened, which action is producing the sound of cutting or cho |
| 2 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | item_invalid | None | A | In the event where the can of chickpeas is being rinsed under the running water, which action is producing the |
| 3 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | item_invalid | None | A | In the event where the can of chickpeas is being rinsed under the running water, which action is producing the |
| 4 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | item_invalid | None | B | In the event where the colander is being shaken up and down to drain the excess water, which action is produci |
| 5 | DIAG | object_state_change | single_choice | same_skill_new_event | - | correct | B | B | In the event where the can of chickpeas is being opened, where is the can of chickpeas placed at the end of th |
| 6 | DIAG | object_state_change | single_choice | same_skill_new_event | - | correct | A | A | In the event where the can of chickpeas is being rinsed under the running water, where is the can of chickpeas |
| 7 | DIAG | object_state_change | single_choice | same_skill_new_event | - | item_invalid | None | C | In the event where the chickpeas are tipped out of the colander onto the paper towels, where are the chickpeas |
| 8 | DIAG | object_state_change | single_choice | same_skill_new_event | - | item_invalid | None | B | In the event where the chickpeas are tipped out of the colander onto the paper towels, where are the chickpeas |
| 9 | DIAG | object_state_change | single_choice | same_skill_new_event | - | correct | C | C | In the event where the sound of a seal breaking is heard, what is the state of the can of chickpeas? |
| 10 | DIAG | object_state_change | single_choice | same_skill_new_event | - | correct | A | A | In the event where the can of chickpeas is being held under the running water to rinse it, where is the can of |
| 11 | DIAG | object_state_change | single_choice | same_skill_new_event | - | item_invalid | None | A | In the event where the can of chickpeas is being opened, what is the state of the can of chickpeas at the end  |
| 12 | DIAG | object_state_change | single_choice | same_skill_new_event | - | item_invalid | None | A | In the event where the can of chickpeas is being held under the running water to rinse it, where is the can of |
| 13 | DIAG | object_state_change | short_answer | same_skill_new_event | - | item_invalid | None | The chickpeas are on the paper | In the event where the chickpeas are being rubbed or patted with a paper towel, what is the state of the chick |
| 14 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | item_invalid | None | A | In the event where the can of chickpeas is being opened, which action happened first? |
| 15 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | C | C | In the event where the can of chickpeas is being opened, which of the following actions occurred first? |
| 16 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | A | A | In the event where the can of chickpeas is being rinsed under the running water, which of the following action |
| 17 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | item_invalid | None | A | In the event where the chickpeas are being rinsed under the running water, which of the following actions occu |
| 18 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | item_invalid | None | D | In the event where the chickpeas are being rinsed under the running water, which of the following actions occu |
| 19 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | item_invalid | None | A | In the event where the chickpeas are being dried on the paper towels, which of the following actions occurred  |
| 20 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | C | C | In the event where the can of chickpeas is being opened, what is the action being performed? |
| 21 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | A | A | In the event where the can of chickpeas is being rinsed under the running water, what is the action being perf |
| 22 | DIAG | action_recognition | single_choice | same_skill_new_event | - | item_invalid | None | B | In the event where the chickpeas are being rinsed under the running water, what is the action being performed? |
| 23 | DIAG | action_recognition | short_answer | same_skill_new_event | - | wrong | Drying chickpeas on paper towe | toss the chickpeas back and fo | In the event where the chickpeas are being dried on the paper towels, what is the action being performed? |
| 24 | DIAG | action_recognition | single_choice | same_skill_new_event | - | wrong | C | B | In the event where the chickpeas are being dried on the paper towels, what is the action being performed? |
| 25 | DIAG | action_recognition | single_choice | same_skill_new_event | - | wrong | B | C | In the event where the person is pinching individual chickpeas to slide off their translucent skins, what is t |
| 26 | DIAG | action_recognition | single_choice | same_skill_new_event | - | wrong | D | A | In the event where the person is sorting through the chickpeas on the baking tray and picking up a piece of lo |
| 27 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | C | C | In the event where the sound of a seal breaking is heard, what is the action being performed? |
| 28 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | A | A | In the event where the can of chickpeas is being held under the running water to rinse it, what is the action  |
| 29 | DIAG | event_object_role | single_choice | same_skill_new_event | - | item_invalid | None | B | In the event where the can opener is being used to open the can of chickpeas, what is the object that is being |
| 30 | DIAG | event_object_role | single_choice | same_skill_new_event | - | item_invalid | None | D | In the event where the blade of the can opener is being turned to open the top of the can, what is the object  |
| 31 | DIAG | event_object_role | single_choice | same_skill_new_event | - | item_invalid | None | B | In the event where the person tips the can to pour the aquafaba liquid down the sink drain, what is the object |
| 32 | DIAG | sound_anchored_spatial_near | single_choice | same_skill_new_event | - | item_invalid | None | B | In the event where the can of chickpeas is being opened, which object is the sound of cutting or chopping comi |
| 33 | DIAG | sound_anchored_spatial_near | single_choice | same_skill_new_event | - | item_invalid | None | B | In the event where the can of chickpeas is being opened, which object is the sound of cutting or chopping comi |
| 34 | DIAG | sound_anchored_spatial_near | single_choice | same_skill_new_event | - | item_invalid | None | B | In the event where the can of chickpeas is being rinsed under the running water, which object is the sound of  |
| 35 | DIAG | sound_movement_binding | single_choice | same_skill_new_event | - | item_invalid | None | C | In the event where the can of chickpeas is being opened, which action is producing the sound of cutting or cho |
| 36 | DIAG | sound_movement_binding | single_choice | same_skill_new_event | - | item_invalid | None | B | In the event where the can of chickpeas is being opened, which action is producing the sound of cutting or cho |
| 37 | DIAG | sound_movement_binding | single_choice | same_skill_new_event | - | correct | B | B | In the event where the can of chickpeas is being held under the running water to rinse it, which action is pro |
| 38 | DIAG | sound_movement_binding | single_choice | same_skill_new_event | - | item_invalid | None | B | In the event where the can of chickpeas is being held under the running water to rinse it, which action is pro |
| 39 | DIAG | sound_movement_binding | single_choice | same_skill_new_event | - | wrong | C | B | In the event where the chickpeas are being tipped out of the colander onto the paper towels, which action is p |
| 40 | DIAG | sound_movement_binding | single_choice | same_skill_new_event | - | item_invalid | None | B | In the event where the can of chickpeas is being opened, which action is producing the sound of cutting or cho |
| 41 | DIAG | sound_movement_binding | single_choice | same_skill_new_event | - | wrong | B | C | In the event where the chickpeas are tipped out of the can into the colander and the aquafaba drains out, whic |
| 42 | DIAG | sound_movement_binding | single_choice | same_skill_new_event | - | wrong | C | B | In the event where the chickpeas are being gently rubbed or patted with a paper towel, which action is produci |

## L3 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | A | A | What is being poured into the colander? |
| 2 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | wrong | A | B | What was done to the chickpeas before they were placed on the paper towels? |
| 3 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | A | A | What was done to the chickpeas before they were placed on the paper towels? |
| 4 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | item_invalid | None | A | What was done to the chickpeas before they were placed on the paper towels? |
| 5 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | item_invalid | None | A | What was done to the chickpeas before they were placed on the paper towels? |
| 6 | DIAG | cross_event_integration | - | - | - | env_failure | None | None |  |
| 7 | DIAG | causal_prerequisite_reasoning | single_choice | same_skill_new_event | - | correct | A | A | Why was the person able to pour liquid out of the can? |

## L4 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | goal_conditioned_planning | single_choice | same_skill_new_event | - | item_invalid | None | A | At the end of the clip, what is the next sub-goal the camera wearer should perform? |
| 2 | DIAG | goal_conditioned_planning | single_choice | same_skill_new_event | - | item_invalid | None | D | At the end of the clip, what is the next sub-goal the camera wearer should perform? |
| 3 | DIAG | goal_conditioned_planning | single_choice | same_skill_new_event | - | item_invalid | None | A | At the end of the clip, what is the next sub-goal the camera wearer should perform? |

## Gemini 用量

| role | calls | errors | tok_in | tok_out | tok_think |
|---|---|---|---|---|---|
| examiner | 62 | 0 | 1583955 | 0 | 0 |
| judge | 1 | 0 | 323 | 63 | 217 |
| solver | 28 | 0 | 161524 | 0 | 0 |
