# pyramid2 run `p2_hdepicE_1023t_g4_v16_goldlive__39`

dataset hdepic_e · videos 1 · examiner `gcp/google/gemini-3.1-pro-preview` · solver `gcp/google/gemini-4-argon` · n_per_layer 200 · seed 1023 · prompt physical-mental-draft2-hdepic-e+v16sg

**结果为 provisional**:gold = Examiner 的 proposed_reference_answer,未经人工核验;open/plan 题由 Gemini judge 判。

## 每层概览

| layer | stop | turns | scored | correct | raw acc | cluster-dedup acc | follow-up | invalid/unresolved | confirmation |
|---|---|---|---|---|---|---|---|---|---|
| L1 | STAIRCASE_COMPLETE | 14 | 8 | 7 | 0.875 | 0.8 | 0 | 0/6 | - |
| L2 | STAIRCASE_COMPLETE | 30 | 23 | 21 | 0.913 | 0.895 | 0 | 0/7 | - |
| L3 | STAIRCASE_COMPLETE | 3 | 3 | 3 | 1.0 | 1.0 | 0 | 0/0 | - |
| L4 | STAIRCASE_COMPLETE | 6 | 6 | 5 | 0.833 | 0.833 | 0 | 0/0 | - |

## 每层 × skill 诊断结论

| layer | skill | verdict | scored | correct | clusters | first-try correct | supported hypotheses | confirmation |
|---|---|---|---|---|---|---|---|---|
| L1 | spatial_near | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L1 | spatial_side | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L1 | object_recognition | boundary>=4 | 4 | 4 | 2 |  | - | - |
| L1 | object_location_at_time | not_started | 0 | 0 | 0 |  | - | - |
| L1 | object_grounding | boundary 1.5 | 4 | 3 | 3 |  | - | - |
| L2 | sound_action_binding | boundary 3.5 | 5 | 5 | 3 |  | - | - |
| L2 | object_state_change | boundary>=4 | 2 | 2 | 2 |  | - | - |
| L2 | action_temporal_order | boundary>=4 | 7 | 6 | 6 |  | - | - |
| L2 | action_recognition | boundary>=4 | 4 | 4 | 4 |  | - | - |
| L2 | event_object_role | boundary>=4 | 2 | 2 | 2 |  | - | - |
| L2 | sound_anchored_spatial_near | boundary<1 | 3 | 2 | 2 |  | - | - |
| L2 | sound_anchored_spatial_side | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L2 | sound_movement_binding | not_started | 0 | 0 | 0 |  | - | - |
| L3 | cross_event_integration | boundary>=4 | 2 | 2 | 2 |  | - | - |
| L3 | hidden_state_inference | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | spatial_state_integration | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | causal_prerequisite_reasoning | boundary 2.0 | 1 | 1 | 1 |  | - | - |
| L4 | goal_conditioned_planning | boundary 2.25 | 6 | 5 | 6 |  | - | - |

## L1 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | About 4.5 seconds into the clip, the camera wearer shakes an object slightly and empties water into the sink.  |
| 2 | DIAG | object_recognition | - | request_verification | - | evidence_unresolved | None | None |  |
| 3 | DIAG | object_recognition | - | request_verification | - | evidence_unresolved | None | None |  |
| 4 | DIAG | object_recognition | single_choice | coverage | - | correct | C | C | About 1.5 seconds into the clip, the camera wearer uses their left hand to scoop something into a neat pile. W |
| 5 | DIAG | object_recognition | - | request_verification | - | evidence_unresolved | None | None |  |
| 6 | DIAG | object_recognition | - | request_verification | - | evidence_unresolved | None | None |  |
| 7 | DIAG | object_recognition | short_answer | coverage | - | correct | a tin can | can | About 4 seconds into the clip, the camera wearer tips an object so that the chickpeas go into the colander and |
| 8 | DIAG | object_recognition | short_answer | coverage | - | correct | another chickpea | a chickpea | About 8.5 seconds into the clip, as the person discards the removed skins into a pile or a waste bin, what obj |
| 9 | DIAG | object_location_at_time | - | request_verification | - | evidence_unresolved | None | None |  |
| 10 | DIAG | object_location_at_time | - | request_verification | - | evidence_unresolved | None | None |  |
| 11 | DIAG | object_grounding | bbox | coverage | - | correct | [0.58, 0.45, 0.84, 0.71] | 47.4, 64.8, 69.4, 88.5 | What is the bounding box of the colander in the first frame of the clip? |
| 12 | DIAG | object_grounding | bbox | coverage | - | correct | [0.472, 0.75, 0.701, 0.989] | 47.2, 78.8, 69.7, 100.2 | What is the bounding box of the colander in the first frame of the clip? |
| 13 | DIAG | object_grounding | bbox | coverage | - | correct | [0.47, 0.74, 0.69, 0.98] | 47.2, 78.8, 69.7, 100.2 | What is the bounding box of the colander in the first frame of the clip? |
| 14 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.16, 0.49, 0.29, 0.73] | 20.9, 46.3, 35.2, 68.2 | What is the bounding box of the kitchen roll in the first frame of the clip? |

## L2 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | sound_action_binding | single_choice | coverage | - | correct | B | B | During the clip, which action produces a cutting or chopping sound? |
| 2 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | correct | A | A | During the clip, which action produces the sound of running water splashing into the metal can? |
| 3 | DIAG | sound_action_binding | - | request_verification | - | evidence_unresolved | None | None |  |
| 4 | DIAG | sound_action_binding | - | request_verification | - | evidence_unresolved | None | None |  |
| 5 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | During the clip, which action produces a metallic collision sound? |
| 6 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | During the clip, what sound is produced when the person turns the blade of the can opener to open the top of t |
| 7 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | During the clip, which of the following actions produces a cutting or chopping sound? |
| 8 | DIAG | sound_action_binding | - | request_verification | - | evidence_unresolved | None | None |  |
| 9 | DIAG | sound_action_binding | - | request_verification | - | evidence_unresolved | None | None |  |
| 10 | DIAG | object_state_change | short_answer | coverage | - | correct | on the left side of the kitche | in the sink | While the sound of running water splashing into the metal can is heard, where does the person put down the can |
| 11 | DIAG | object_state_change | short_answer | same_skill_new_event | - | correct | On the paper towel | on the kitchen paper | When the person empties the chickpeas from the colander, where are they placed? |
| 12 | DIAG | action_temporal_order | single_choice | coverage | - | wrong | B | A | When the person opens the can of chickpeas, which of the following actions happens first? |
| 13 | DIAG | action_temporal_order | single_choice | coverage | - | correct | C | C | During the clip, which of the following actions happens first? |
| 14 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | A | A | After the person runs water over the chickpeas in the colander, which of the following actions happens first? |
| 15 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | C | C | During the clip, which of the following actions happens first? |
| 16 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | B | B | After the person scoops the loose skin into a neat pile, which of the following actions happens first? |
| 17 | DIAG | action_temporal_order | short_answer | coverage | - | correct | Pick off the loose skins from  | pick off loose skins | During the clip, after the person moves the dried chickpeas from the paper towels onto the baking tray, what a |
| 18 | DIAG | action_temporal_order | short_answer | same_event_new_format | - | correct | Pick up the can opener | pick up the can opener | When the person opens the can of chickpeas, what action do they perform immediately after opening the cutlery  |
| 19 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | After placing the can of chickpeas on the counter, what action does the person perform on it? |
| 20 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | C | C | After peeling back the metal lid of the can to look inside, what action does the person perform with the can? |
| 21 | DIAG | action_recognition | short_answer | same_skill_new_event | - | correct | shakes the colander | Swirl and shake the colander | While rinsing the chickpeas under the running water, what action does the person perform to ensure they are th |
| 22 | DIAG | action_recognition | short_answer | same_skill_new_event | - | correct | pours the chickpeas onto the p | tips the chickpeas out onto th | During the clip, immediately after picking up the colander of chickpeas, what action does the person perform w |
| 23 | DIAG | event_object_role | short_answer | coverage | - | correct | Can opener | can opener | When the person opens the top of the can, what tool do they use? |
| 24 | DIAG | event_object_role | short_answer | same_skill_new_event | - | correct | colander | colander | During the clip, what object does the person pour the chickpeas into? |
| 25 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | correct | B | B | When the person opens the container of chickpeas, which of the following objects is nearest to the can opener  |
| 26 | DIAG | sound_anchored_spatial_near | single_choice | same_skill_new_event | - | wrong | C | B | When the person tips the can to pour the liquid down the sink drain, which of the following objects is nearest |
| 27 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | correct | A | A | When the person opens the metal container, among the listed candidates, which object is nearest to the can ope |
| 28 | DIAG | sound_anchored_spatial_near | - | request_verification | - | evidence_unresolved | None | None |  |
| 29 | DIAG | sound_movement_binding | - | request_verification | - | evidence_unresolved | None | None |  |
| 30 | DIAG | sound_movement_binding | - | request_verification | - | evidence_unresolved | None | None |  |

## L3 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | cross_event_integration | short_answer | coverage | - | correct | Rinsed it and put it down in t | Rinsed it out with water. | Before the person rinses the chickpeas in the colander, what did they do with the empty can? |
| 2 | DIAG | cross_event_integration | short_answer | same_skill_new_event | - | correct | Rinsed in a colander under run | They were rinsed and drained i | What was done to the chickpeas before they were dumped onto the paper towels? |
| 3 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | correct | B | B | Which earlier action made it possible to pour liquid out of the can? |

## L4 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | B | B | What is the next step the person should take to continue the task they are doing? |
| 2 | DIAG | goal_conditioned_planning | single_choice | same_skill_new_event | - | correct | B | B | What is the next step the person should take to continue the task they are doing? |
| 3 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | B | B | What is the next step the person should take to continue the task they are doing? |
| 4 | DIAG | goal_conditioned_planning | single_choice | same_skill_new_event | - | correct | C | C | What is the next step the person should take to continue the task they are doing? |
| 5 | DIAG | goal_conditioned_planning | plan | coverage | - | wrong | ['Pat the chickpeas dry using  | 1. Move the chickpeas to a bak | What are the remaining stages, in order, to complete the task the camera wearer is doing? |
| 6 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | A | A | What is the next step the person should take to continue the task they are doing? |

## Gemini 用量

| role | calls | errors | tok_in | tok_out | tok_think |
|---|---|---|---|---|---|
| examiner | 58 | 0 | 1455332 | 32206 | 208875 |
| judge | 10 | 0 | 3840 | 846 | 2793 |
| solver | 120 | 0 | 444441 | 2204 | 0 |
