# pyramid2 run `p2_hdepicE_1023t_g4_v16_self__13`

dataset hdepic_e · videos 1 · examiner `gcp/google/gemini-3.1-pro-preview` · solver `gcp/google/gemini-4-argon` · n_per_layer 200 · seed 1023 · prompt physical-mental-draft2-hdepic-e+v16sg

**结果为 provisional**:gold = Examiner 的 proposed_reference_answer,未经人工核验;open/plan 题由 Gemini judge 判。

## 每层概览

| layer | stop | turns | scored | correct | raw acc | cluster-dedup acc | follow-up | invalid/unresolved | confirmation |
|---|---|---|---|---|---|---|---|---|---|
| L1 | STAIRCASE_COMPLETE | 19 | 17 | 10 | 0.588 | 0.562 | 0 | 0/2 | - |
| L2 | STAIRCASE_COMPLETE | 43 | 26 | 24 | 0.923 | 0.917 | 0 | 0/17 | - |
| L3 | STAIRCASE_COMPLETE | 11 | 11 | 10 | 0.909 | 0.909 | 0 | 0/0 | - |
| L4 | STAIRCASE_COMPLETE | 3 | 3 | 3 | 1.0 | 1.0 | 0 | 0/0 | - |

## 每层 × skill 诊断结论

| layer | skill | verdict | scored | correct | clusters | first-try correct | supported hypotheses | confirmation |
|---|---|---|---|---|---|---|---|---|
| L1 | spatial_near | boundary 2.0 | 1 | 1 | 1 |  | - | - |
| L1 | spatial_side | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L1 | object_recognition | boundary 1.5 | 4 | 2 | 4 |  | - | - |
| L1 | object_location_at_time | boundary 3 | 8 | 6 | 7 |  | - | - |
| L1 | object_grounding | boundary<1 | 4 | 1 | 4 |  | - | - |
| L2 | sound_action_binding | boundary 2 | 5 | 4 | 5 |  | - | - |
| L2 | object_state_change | boundary 3 | 4 | 4 | 4 |  | - | - |
| L2 | action_temporal_order | not_started | 0 | 0 | 0 |  | - | - |
| L2 | action_recognition | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | event_object_role | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | sound_anchored_spatial_near | boundary 1.75 | 4 | 3 | 2 |  | - | - |
| L2 | sound_anchored_spatial_side | not_started | 0 | 0 | 0 |  | - | - |
| L2 | sound_movement_binding | boundary 2 | 1 | 1 | 1 |  | - | - |
| L3 | cross_event_integration | boundary 2.5 | 5 | 4 | 5 |  | - | - |
| L3 | hidden_state_inference | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | spatial_state_integration | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | causal_prerequisite_reasoning | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L4 | goal_conditioned_planning | boundary 3.5 | 3 | 3 | 3 |  | - | - |

## L1 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | spatial_near | single_choice | coverage | - | correct | C | C | At the start of the clip, the biscuit packets are placed on the counter. About 9 seconds into the clip, when t |
| 2 | DIAG | object_recognition | single_choice | coverage | - | wrong | C | A | About 7 seconds into the clip, during the event to place the food processor bowl on the counter, what object d |
| 3 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | About 4 seconds into the clip, the camera wearer attempts to insert a part into the food processor bowl. At th |
| 4 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | At the start of the clip, the camera wearer picks up the center spindle piece. About 3 seconds into the clip,  |
| 5 | DIAG | object_recognition | single_choice | coverage | - | wrong | B | A | About 4.5 seconds into the clip, during the event to plug the power cord into the wall outlet, the camera wear |
| 6 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | At the start of the clip, during the event to place the biscuit packets on the counter, where does the camera  |
| 7 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | At the start of the clip, the camera wearer picks up the center spindle piece. About 4 seconds into the clip,  |
| 8 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 3 seconds into the clip, during the event to remove the lid from the food processor bowl, where does the |
| 9 | DIAG | object_location_at_time | - | request_verification | - | evidence_unresolved | None | None |  |
| 10 | DIAG | object_location_at_time | - | request_verification | - | evidence_unresolved | None | None |  |
| 11 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | At the start of the clip, the camera wearer picks up the center spindle piece. About 9 seconds into the clip,  |
| 12 | DIAG | object_location_at_time | short_answer | coverage | - | wrong | the food processor bowl | shelf | About 4 seconds into the clip, during the event to insert the blade into the food processor bowl, the camera w |
| 13 | DIAG | object_location_at_time | single_choice | coverage | - | wrong | B | A | About 6 seconds into the clip, during the event to plug the power cord into the wall outlet, where does the ca |
| 14 | DIAG | object_location_at_time | single_choice | coverage | - | correct | B | B | About 5 seconds into the clip, during the event to open the biscuit packet, the camera wearer is holding the p |
| 15 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | At the start of the clip, the camera wearer presses the button on the food processor base. About 8 seconds int |
| 16 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.54, 0.64, 0.79, 0.93] | 54.4, 68.2, 68.0, 78.5 | At the start of the clip, during the event to dry the spindle with a towel, what is the bounding box of the to |
| 17 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.52, 0.41, 0.56, 0.46] | 67.4, 77.6, 89.6, 98.5 | At the start of the clip, during the event to place the biscuit packets on the counter, what is the bounding b |
| 18 | DIAG | object_grounding | bbox | coverage | - | correct | [0.39, 0.55, 0.59, 0.73] | 38.6, 56.9, 57.1, 77.4 | At the start of the clip, during the event to place the biscuit packets on the counter, what is the bounding b |
| 19 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.575, 0.55, 0.795, 0.761] | 51.6, 53.5, 69.6, 74.9 | At the start of the clip, during the event to pick up the center spindle piece, what is the bounding box of th |

## L2 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | sound_action_binding | single_choice | coverage | - | wrong | B | A | During the task the camera wearer is doing, when they rotate and remove the cover of the food processor, what  |
| 2 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they attempt to place the blade on the center part of the foo |
| 3 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they pick up the center piece from the cupboard, what kind of |
| 4 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they wash the center piece of the food processor, what kind o |
| 5 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they plug the power cord into the wall outlet, what kind of s |
| 6 | DIAG | sound_action_binding | - | request_verification | - | evidence_unresolved | None | None |  |
| 7 | DIAG | sound_action_binding | - | request_verification | - | evidence_unresolved | None | None |  |
| 8 | DIAG | sound_action_binding | - | request_verification | - | evidence_unresolved | None | None |  |
| 9 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they put down the packet of biscuits, where do they place it? |
| 10 | DIAG | object_state_change | - | request_verification | - | evidence_unresolved | None | None |  |
| 11 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they find and pick up the center plastic piece, where do they |
| 12 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they plug the power cord into the wall outlet, where do they  |
| 13 | DIAG | object_state_change | - | request_verification | - | evidence_unresolved | None | None |  |
| 14 | DIAG | object_state_change | - | request_verification | - | evidence_unresolved | None | None |  |
| 15 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they close the food processor, where do they place the lid? |
| 16 | DIAG | object_state_change | - | request_verification | - | evidence_unresolved | None | None |  |
| 17 | DIAG | object_state_change | - | request_verification | - | evidence_unresolved | None | None |  |
| 18 | DIAG | object_state_change | - | request_verification | - | evidence_unresolved | None | None |  |
| 19 | DIAG | action_temporal_order | - | request_verification | - | evidence_unresolved | None | None |  |
| 20 | DIAG | action_temporal_order | - | request_verification | - | evidence_unresolved | None | None |  |
| 21 | DIAG | action_temporal_order | - | request_verification | - | evidence_unresolved | None | None |  |
| 22 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they handle the packet of biscuits, what exactly do they do? |
| 23 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they bring the blade to the food processor bowl, what exactly |
| 24 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they reach into the open cupboard, what action do they perfor |
| 25 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they open the tap, what exactly do they do with the plastic c |
| 26 | DIAG | action_recognition | short_answer | coverage | - | correct | Place it into the food process | insert it into the food proces | During the task the camera wearer is doing, after successfully fitting the center piece into the blade, what e |
| 27 | DIAG | action_recognition | short_answer | coverage | - | correct | press the button on the food p | Press the dial | During the task the camera wearer is doing, when they first interact with the food processor base in the clip, |
| 28 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they gather an item from the upper shelf, which object do the |
| 29 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they attempt to place an object on the center part of the foo |
| 30 | DIAG | event_object_role | single_choice | coverage | - | correct | B | B | During the task the camera wearer is doing, when they reach into the cupboard and pick up the missing piece, w |
| 31 | DIAG | event_object_role | single_choice | coverage | - | correct | B | B | During the task the camera wearer is doing, when they dry the plastic center piece, which object do they use? |
| 32 | DIAG | event_object_role | short_answer | coverage | - | correct | the food processor bowl | the center tower of the food p | During the task the camera wearer is doing, when they install the assembled blade piece, what exactly do they  |
| 33 | DIAG | event_object_role | short_answer | coverage | - | correct | the button on the food process | the dial | During the task the camera wearer is doing, when they first test the food processor in the clip, what specific |
| 34 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | wrong | D | A | During the task the camera wearer is doing, when the second plastic-only collision sound is heard, which of th |
| 35 | DIAG | sound_anchored_spatial_near | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, when they pour the remaining biscuits from the packet into the bow |
| 36 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when a sound of metal and plastic colliding is heard, which of the |
| 37 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they pour the remaining biscuits from the packet into the bow |
| 38 | DIAG | sound_anchored_spatial_side | - | request_verification | - | evidence_unresolved | None | None |  |
| 39 | DIAG | sound_movement_binding | - | request_verification | - | evidence_unresolved | None | None |  |
| 40 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they make their second attempt to fit the piece onto the cent |
| 41 | DIAG | sound_movement_binding | - | request_verification | - | evidence_unresolved | None | None |  |
| 42 | DIAG | sound_movement_binding | - | request_verification | - | evidence_unresolved | None | None |  |
| 43 | DIAG | sound_movement_binding | - | request_verification | - | evidence_unresolved | None | None |  |

## L3 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | When the button is pressed to run the processor, what is being crushed? |
| 2 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | A | A | Before more biscuits are thrown into the bowl of the food processor, what was done to the biscuits already ins |
| 3 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | wrong | A | B | When the food processor is turned on by rotating the dial, what is being crushed? |
| 4 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | C | C | When the food processor is turned on by rotating the dial for the second time in the clip, what is being crush |
| 5 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | B | B | Before the camera wearer attempts to insert the blade into the food processor bowl, what was removed from the  |
| 6 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | correct | A | A | Before the spindle (center piece) is inserted into the food processor bowl, what was done to it? |
| 7 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | correct | A | A | What earlier action was necessary for the food processor to receive power when the button on its base was pres |
| 8 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | correct | A | A | Before the center piece attached to the blade is inserted into the food processor, what necessary preparation  |
| 9 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | correct | A | A | Which earlier action was a necessary physical prerequisite for the food processor to receive electricity when  |
| 10 | DIAG | causal_prerequisite_reasoning | short_answer | coverage | - | correct | It was rinsed and dried with a | It was dried with a towel. | Before the center piece attached to the blade is inserted into the food processor, what necessary preparation  |
| 11 | DIAG | causal_prerequisite_reasoning | short_answer | coverage | - | correct | plugging the power cord into t | Plugging the power cord into t | What earlier action was a necessary physical prerequisite for the food processor to turn on when the button on |

## L4 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | B | B | Based on the progress shown in the clip, what is the next step the person will take for the task they are doin |
| 2 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | C | C | Based on the progress shown in the clip, what is the next step the person will take for the task they are doin |
| 3 | DIAG | goal_conditioned_planning | plan | coverage | - | correct | ['Open the second packet of bi | 1. Put a second packet of bisc | What are the remaining stages, in order, to complete the task the camera wearer is doing? |

## Gemini 用量

| role | calls | errors | tok_in | tok_out | tok_think |
|---|---|---|---|---|---|
| examiner | 85 | 0 | 2420691 | 47725 | 277957 |
| judge | 7 | 0 | 3094 | 736 | 2253 |
| scope | 1 | 0 | 1767 | 4610 | 2638 |
| solver | 171 | 0 | 919338 | 3000 | 0 |
