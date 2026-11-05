# pyramid2 run `p2_hdepicE_1023t_g4_v16_self__07`

dataset hdepic_e · videos 1 · examiner `gcp/google/gemini-3.1-pro-preview` · solver `gcp/google/gemini-4-argon` · n_per_layer 200 · seed 1023 · prompt physical-mental-draft2-hdepic-e+v16sg

**结果为 provisional**:gold = Examiner 的 proposed_reference_answer,未经人工核验;open/plan 题由 Gemini judge 判。

## 每层概览

| layer | stop | turns | scored | correct | raw acc | cluster-dedup acc | follow-up | invalid/unresolved | confirmation |
|---|---|---|---|---|---|---|---|---|---|
| L1 | STAIRCASE_COMPLETE | 29 | 17 | 14 | 0.824 | 0.824 | 0 | 0/12 | - |
| L2 | STAIRCASE_COMPLETE | 40 | 40 | 30 | 0.75 | 0.763 | 0 | 0/0 | - |
| L3 | STAIRCASE_COMPLETE | 12 | 12 | 10 | 0.833 | 0.833 | 0 | 0/0 | - |
| L4 | STAIRCASE_COMPLETE | 7 | 7 | 6 | 0.857 | 0.857 | 0 | 0/0 | - |

## 每层 × skill 诊断结论

| layer | skill | verdict | scored | correct | clusters | first-try correct | supported hypotheses | confirmation |
|---|---|---|---|---|---|---|---|---|
| L1 | spatial_near | boundary 2 | 1 | 1 | 1 |  | - | - |
| L1 | spatial_side | boundary 2.5 | 3 | 3 | 3 |  | - | - |
| L1 | object_recognition | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L1 | object_location_at_time | boundary 2 | 2 | 2 | 2 |  | - | - |
| L1 | object_grounding | boundary 1.5 | 5 | 2 | 5 |  | - | - |
| L2 | sound_action_binding | boundary>=4 | 9 | 8 | 9 |  | - | - |
| L2 | object_state_change | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | action_temporal_order | boundary 2.5 | 5 | 4 | 5 |  | - | - |
| L2 | action_recognition | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | event_object_role | boundary<1 | 4 | 1 | 4 |  | - | - |
| L2 | sound_anchored_spatial_near | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L2 | sound_anchored_spatial_side | boundary 2 | 6 | 4 | 4 |  | - | - |
| L2 | sound_movement_binding | boundary<1 | 4 | 1 | 4 |  | - | - |
| L3 | cross_event_integration | boundary 3.5 | 8 | 7 | 8 |  | - | - |
| L3 | hidden_state_inference | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | spatial_state_integration | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | causal_prerequisite_reasoning | boundary 1.75 | 4 | 3 | 4 |  | - | - |
| L4 | goal_conditioned_planning | boundary 3 | 7 | 6 | 7 |  | - | - |

## L1 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | spatial_near | single_choice | coverage | - | correct | A | A | About 5 seconds into the clip, the person peels an onion. At about 8 seconds into the clip, which of the follo |
| 2 | DIAG | spatial_near | - | request_verification | - | evidence_unresolved | None | None |  |
| 3 | DIAG | spatial_near | - | request_verification | - | evidence_unresolved | None | None |  |
| 4 | DIAG | spatial_near | - | request_verification | - | evidence_unresolved | None | None |  |
| 5 | DIAG | spatial_side | single_choice | coverage | - | correct | B | B | About 5 seconds into the clip, the person peels an onion. At about 3.5 seconds into the clip, from the camera  |
| 6 | DIAG | spatial_side | single_choice | coverage | - | correct | B | B | About 7 seconds into the clip, the chopped pieces are transferred into a bowl. At that moment, from the camera |
| 7 | DIAG | spatial_side | single_choice | coverage | - | correct | C | C | About 4 seconds into the clip, tomatoes are placed on the scale. At that moment, from the camera wearer's own  |
| 8 | DIAG | spatial_side | - | request_verification | - | evidence_unresolved | None | None |  |
| 9 | DIAG | spatial_side | - | request_verification | - | evidence_unresolved | None | None |  |
| 10 | DIAG | spatial_side | - | request_verification | - | evidence_unresolved | None | None |  |
| 11 | DIAG | object_recognition | single_choice | coverage | - | correct | C | C | In this clip, ingredients are placed on the tabletop. Between 4.5 and 5.5 seconds into the clip, the person pl |
| 12 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | About 9.8 seconds into the clip, an object is placed on the counter. Which object is it? |
| 13 | DIAG | object_recognition | - | request_verification | - | evidence_unresolved | None | None |  |
| 14 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | About 4 seconds into the clip, the person peels the additional onions. About 7 seconds into the clip, the pers |
| 15 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | At the start of the clip, a chopping sound is heard as the knife hits the board. At that moment, the person is |
| 16 | DIAG | object_recognition | - | request_verification | - | evidence_unresolved | None | None |  |
| 17 | DIAG | object_recognition | short_answer | coverage | - | correct | a knife | knife | In this clip, more tomatoes are sliced and placed into the mixer jar. About 7.6 seconds into the clip, the per |
| 18 | DIAG | object_recognition | short_answer | coverage | - | correct | cutting board | chopping board | In this clip, more tomatoes are sliced and placed into the mixer jar. About 0.5 seconds into the clip, the per |
| 19 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 2.4 seconds into the clip, the jar of ginger paste is placed down. Where is it placed? |
| 20 | DIAG | object_location_at_time | - | request_verification | - | evidence_unresolved | None | None |  |
| 21 | DIAG | object_location_at_time | single_choice | coverage | - | correct | C | C | About 4.7 seconds into the clip, the person peels an onion. About 3.1 seconds into the clip, a pen is placed d |
| 22 | DIAG | object_location_at_time | - | request_verification | - | evidence_unresolved | None | None |  |
| 23 | DIAG | object_location_at_time | - | request_verification | - | evidence_unresolved | None | None |  |
| 24 | DIAG | object_location_at_time | - | request_verification | - | evidence_unresolved | None | None |  |
| 25 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.424, 0.639, 0.514, 0.774] | 51.1, 69.6, 63.6, 82.7 | Throughout the clip, ingredients are placed on the tabletop. In the first frame of the clip, what is the bound |
| 26 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.472, 0.562, 0.65, 0.887] | 47.4, 59.0, 57.4, 81.2 | In the first frame of the clip, what is the bounding box of the chopping board? |
| 27 | DIAG | object_grounding | bbox | coverage | - | correct | [0.41, 0.667, 0.695, 0.936] | 46.7, 67.2, 77.6, 95.9 | At the start of the clip, a chopping board is placed on the counter. In the first frame of the clip, what is t |
| 28 | DIAG | object_grounding | bbox | coverage | - | correct | [0.55, 0.53, 0.69, 0.73] | 56.8, 55.6, 71.8, 69.9 | In the first frame of the clip, what is the bounding box of the knife? |
| 29 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.604, 0.608, 0.732, 0.754] | 55.9, 58.8, 67.0, 75.2 | Throughout the clip, the person peels an onion. In the first frame of the clip, what is the bounding box of th |

## L2 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | sound_action_binding | single_choice | coverage | - | wrong | C | B | When the ingredients are placed on the tabletop, which action produces the sliding sound? |
| 2 | DIAG | sound_action_binding | single_choice | coverage | - | correct | C | C | During the task the camera wearer is doing, which action produces the ceramic clinking sound? |
| 3 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | When the camera wearer peels the outer layer of the onion, which sound is produced? |
| 4 | DIAG | sound_action_binding | single_choice | coverage | - | correct | C | C | During the task the camera wearer is doing, just before they peel the additional onions, a single hard clackin |
| 5 | DIAG | sound_action_binding | single_choice | coverage | - | correct | B | B | During the task the camera wearer is doing, a series of repeated cutting sounds is heard. Which action produce |
| 6 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, a series of repeated cutting sounds is heard. Which action produce |
| 7 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they place the knife on the chopping board, which sound is pr |
| 8 | DIAG | sound_action_binding | short_answer | coverage | - | correct | placing the bowl on the dish d | placing the bowl on the stove | During the task the camera wearer is doing, when the chopped onions are transferred into a bowl, what action p |
| 9 | DIAG | sound_action_binding | short_answer | coverage | - | correct | Washing tomatoes under the tap | washing the tomatoes | During the task the camera wearer is doing, what action produces the sound of running water? |
| 10 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when the camera wearer places the retrieved items down, where is t |
| 11 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when the chopping board is placed down, where is it placed? |
| 12 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when the camera wearer picks up a piece of onion to peel it, where |
| 13 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, after peeling the outer layer of the onion, where is it placed? |
| 14 | DIAG | object_state_change | short_answer | coverage | - | correct | On the weighing scale | on the weighing balance | During the task the camera wearer is doing, when the tomatoes are picked up from the chopping board for the fi |
| 15 | DIAG | object_state_change | short_answer | coverage | - | correct | In the blender jar | in the jar | During the task the camera wearer is doing, when the camera wearer picks up the sliced tomatoes, where are the |
| 16 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when the ingredients are placed on the tabletop, which action happ |
| 17 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, which action happens immediately after they pick up the knife from |
| 18 | DIAG | action_temporal_order | single_choice | coverage | - | wrong | A | B | During the task the camera wearer is doing, which action happens immediately after they peel the outer layer o |
| 19 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, which action happens immediately after they place the chopped piec |
| 20 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, which action happens immediately after they place the onion peel o |
| 21 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when the camera wearer interacts with the green chillies in the si |
| 22 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, what action do they perform with the knife? |
| 23 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, what action do they perform on the piece of onion immediately afte |
| 24 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, what action do they perform on the onion immediately after placing |
| 25 | DIAG | action_recognition | short_answer | coverage | - | correct | They chop the onion into small | chop the onion | During the task the camera wearer is doing, what action do they perform with the knife immediately after picki |
| 26 | DIAG | action_recognition | short_answer | coverage | - | correct | Chop the piece of onion | chop the onion | During the task the camera wearer is doing, what action do they perform with the knife immediately after placi |
| 27 | DIAG | event_object_role | single_choice | coverage | - | wrong | D | A | During the task the camera wearer is doing, when the ingredients are placed on the tabletop, which of the foll |
| 28 | DIAG | event_object_role | single_choice | coverage | - | wrong | B | A | During the task the camera wearer is doing, which item is placed on the chopping board using the right hand? |
| 29 | DIAG | event_object_role | single_choice | coverage | - | correct | B | B | During the task the camera wearer is doing, when they peel the outer layer of the onion, what is actively used |
| 30 | DIAG | event_object_role | single_choice | coverage | - | wrong | B | A | During the task the camera wearer is doing, when they pick up a piece of onion from the chopping board, which  |
| 31 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | wrong | C | B | During the task the camera wearer is doing, at the moment the second metallic clanking sound is heard while th |
| 32 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | correct | B | B | During the task the camera wearer is doing, when the person peels an onion, a cutting or chopping sound is hea |
| 33 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | correct | C | C | During the task the camera wearer is doing, when the green chillies are sliced and placed into the mixer jar,  |
| 34 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | correct | C | C | During the task the camera wearer is doing, when a sliding sound is heard as the green chillies are placed dow |
| 35 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | correct | C | C | During the task the camera wearer is doing, when the person peels an onion, a cutting or chopping sound is hea |
| 36 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | wrong | D | A | During the task the camera wearer is doing, while a chopping board is being placed on the counter, when the se |
| 37 | DIAG | sound_movement_binding | single_choice | coverage | - | wrong | D | A | During the task the camera wearer is doing, when the person takes ingredients out of the refrigerator, which o |
| 38 | DIAG | sound_movement_binding | single_choice | coverage | - | wrong | D | C | During the task the camera wearer is doing, a sound of metal hitting wood is heard. Which object's movement pr |
| 39 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when the person peels an onion, a cutting or chopping sound is hea |
| 40 | DIAG | sound_movement_binding | single_choice | coverage | - | wrong | B | A | During the task the camera wearer is doing, when the person peels the additional onions, a cutting or chopping |

## L3 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | What was done to the onions before they were chopped? |
| 2 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | What was done to the onions just before they were transferred into a bowl? |
| 3 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | What was done to the tomatoes before they were sliced? |
| 4 | DIAG | cross_event_integration | single_choice | coverage | - | correct | B | B | What was done to the contents of the mixer jar just before the green chillies were sliced into it? |
| 5 | DIAG | cross_event_integration | short_answer | coverage | - | correct | Blended in a blender | They were blended into a puree | What was done to the tomatoes just before they were poured into the bowl? |
| 6 | DIAG | cross_event_integration | short_answer | coverage | - | wrong | One onion was chopped | The first half was chopped | What was done to the onions just before the remaining ones were chopped? |
| 7 | DIAG | cross_event_integration | single_choice | coverage | - | correct | C | C | What was put into the mixer jar just before more sliced tomatoes were placed into it? |
| 8 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | What was done to the tomatoes just before more of them were sliced and placed into the mixer jar? |
| 9 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | wrong | D | A | What was the last ingredient added to the mixer jar before the blender was turned on? |
| 10 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | correct | C | C | What was done to the green chillies before they were chopped? |
| 11 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | correct | C | C | What was the last ingredient added to the mixer jar before the blender was turned on? |
| 12 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | correct | A | A | What was done to the green chillies before they were chopped? |

## L4 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | C | C | What is the next step the person will take to continue the task they are doing? |
| 2 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | A | A | What is the next step the person will take to continue the task they are doing? |
| 3 | DIAG | goal_conditioned_planning | plan | coverage | - | correct | ['Wash and slice the green chi | 1. Fetch, prep, and wash some  | List the remaining stages, in order, to complete the task the camera wearer is doing. |
| 4 | DIAG | goal_conditioned_planning | plan | coverage | - | correct | ['Chop the green chillies and  | 1. Cut the green chillies into | List the remaining stages, in order, to complete the task the camera wearer is doing. |
| 5 | DIAG | goal_conditioned_planning | plan | coverage | - | wrong | ['Chop the other half of the o | 1. Separate the chopped onion  | List the remaining stages, in order, to complete the task the camera wearer is doing. |
| 6 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | C | C | What is the next step the person will take to continue the task they are doing? |
| 7 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | C | C | What is the next step the person will take to continue the task they are doing? |

## Gemini 用量

| role | calls | errors | tok_in | tok_out | tok_think |
|---|---|---|---|---|---|
| examiner | 98 | 0 | 3479586 | 58341 | 349701 |
| judge | 20 | 0 | 9546 | 2510 | 7847 |
| scope | 1 | 0 | 2013 | 6315 | 5391 |
| solver | 228 | 0 | 1232319 | 3990 | 0 |
