# pyramid2 run `p2_hdepicE_1023t_g4_v16_goldlive__13`

dataset hdepic_e · videos 1 · examiner `gcp/google/gemini-3.1-pro-preview` · solver `gcp/google/gemini-4-argon` · n_per_layer 200 · seed 1023 · prompt physical-mental-draft2-hdepic-e+v16sg

**结果为 provisional**:gold = Examiner 的 proposed_reference_answer,未经人工核验;open/plan 题由 Gemini judge 判。

## 每层概览

| layer | stop | turns | scored | correct | raw acc | cluster-dedup acc | follow-up | invalid/unresolved | confirmation |
|---|---|---|---|---|---|---|---|---|---|
| L1 | STAIRCASE_COMPLETE | 24 | 22 | 16 | 0.727 | 0.762 | 0 | 0/2 | - |
| L2 | STAIRCASE_COMPLETE | 46 | 44 | 33 | 0.75 | 0.775 | 0 | 0/2 | - |
| L3 | STAIRCASE_COMPLETE | 14 | 14 | 13 | 0.929 | 0.929 | 0 | 0/0 | - |
| L4 | STAIRCASE_COMPLETE | 3 | 3 | 3 | 1.0 | 1.0 | 0 | 0/0 | - |

## 每层 × skill 诊断结论

| layer | skill | verdict | scored | correct | clusters | first-try correct | supported hypotheses | confirmation |
|---|---|---|---|---|---|---|---|---|
| L1 | spatial_near | boundary 2.0 | 1 | 1 | 1 |  | - | - |
| L1 | spatial_side | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L1 | object_recognition | boundary>=4 | 9 | 8 | 9 |  | - | - |
| L1 | object_location_at_time | boundary 2 | 8 | 6 | 7 |  | - | - |
| L1 | object_grounding | boundary<1 | 4 | 1 | 4 |  | - | - |
| L2 | sound_action_binding | boundary>=4 | 9 | 8 | 9 |  | - | - |
| L2 | object_state_change | boundary 2.5 | 5 | 4 | 5 |  | - | - |
| L2 | action_temporal_order | boundary<1 | 5 | 2 | 5 |  | - | - |
| L2 | action_recognition | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | event_object_role | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | sound_anchored_spatial_near | boundary 1.75 | 5 | 3 | 2 |  | - | - |
| L2 | sound_anchored_spatial_side | boundary<1 | 2 | 0 | 1 |  | - | - |
| L2 | sound_movement_binding | boundary 2 | 6 | 4 | 6 |  | - | - |
| L3 | cross_event_integration | boundary 3.5 | 8 | 7 | 8 |  | - | - |
| L3 | hidden_state_inference | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | spatial_state_integration | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | causal_prerequisite_reasoning | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L4 | goal_conditioned_planning | boundary 3.5 | 3 | 3 | 3 |  | - | - |

## L1 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | spatial_near | single_choice | coverage | - | correct | C | C | About 9 seconds into the clip, after the biscuit packets are placed on the counter at the start of the clip, w |
| 2 | DIAG | object_recognition | single_choice | coverage | - | wrong | D | B | About 7 seconds into the clip, when the food processor bowl is placed on the counter, which object does the ca |
| 3 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | About 4 seconds into the clip, when the camera wearer attempts to insert an object into the food processor bow |
| 4 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | At the start of the clip, when the camera wearer picks up a piece from the top shelf of the cupboard with thei |
| 5 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | About 5 seconds into the clip, during the action to plug the power cord into the wall outlet, the camera weare |
| 6 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | About 7 seconds into the clip, when the camera wearer picks up an object from the upper shelf, which object is |
| 7 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | About 8 seconds into the clip, during the sound of running water from the tap, which object does the camera we |
| 8 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | At the start of the clip, when the camera wearer presses a control to check if the appliance works, which obje |
| 9 | DIAG | object_recognition | short_answer | coverage | - | correct | the biscuit packet | packaging | About 4 seconds into the clip, the camera wearer starts to pour the remaining biscuits from the packet into th |
| 10 | DIAG | object_recognition | short_answer | coverage | - | correct | a biscuit | a biscuit | About 6 seconds into the clip, when the camera wearer picks up an object that has fallen on the counter top us |
| 11 | DIAG | object_location_at_time | single_choice | coverage | - | correct | C | C | At the start of the clip, when the camera wearer places the biscuit packets on the counter, where exactly are  |
| 12 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 4 seconds into the clip, after the camera wearer picks up the center spindle piece at the start of the c |
| 13 | DIAG | object_location_at_time | single_choice | coverage | - | correct | B | B | About 5 seconds into the clip, when the camera wearer removes the lid from the food processor bowl, where are  |
| 14 | DIAG | object_location_at_time | - | request_verification | - | evidence_unresolved | None | None |  |
| 15 | DIAG | object_location_at_time | - | request_verification | - | evidence_unresolved | None | None |  |
| 16 | DIAG | object_location_at_time | single_choice | coverage | - | wrong | B | A | About 9 seconds into the clip, after the camera wearer picks up the center spindle piece at the start of the c |
| 17 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 3 seconds into the clip, when the camera wearer picks up the plastic tube of biscuits to open it, where  |
| 18 | DIAG | object_location_at_time | single_choice | coverage | - | wrong | A | B | About 4 seconds into the clip, when the camera wearer attempts to insert the blade into the food processor bow |
| 19 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 9 seconds into the clip, during the action to plug the power cord into the wall outlet, where is the foo |
| 20 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 8 seconds into the clip, after the camera wearer presses the button on the food processor base at the st |
| 21 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.547, 0.639, 0.804, 0.933] | 54.4, 68.2, 68.0, 78.5 | At the start of the clip, during the action to dry the spindle with a towel, what is the bounding box of the t |
| 22 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.486, 0.476, 0.514, 0.514] | 67.4, 77.6, 89.6, 98.5 | At the start of the clip, when the biscuit packets are placed on the counter, what is the bounding box of the  |
| 23 | DIAG | object_grounding | bbox | coverage | - | correct | [0.4, 0.56, 0.59, 0.73] | 38.6, 56.9, 57.1, 77.4 | At the start of the clip, when the camera wearer picks up a bowl from the drainer, what is the bounding box of |
| 24 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.58, 0.549, 0.788, 0.767] | 51.6, 53.5, 69.6, 74.9 | At the start of the clip, when the camera wearer closes the cupboard, what is the bounding box of the box of t |

## L2 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | sound_action_binding | single_choice | coverage | - | wrong | D | A | When the camera wearer removes the cover of the food processor, what kind of sound is heard? |
| 2 | DIAG | sound_action_binding | single_choice | coverage | - | correct | B | B | When the camera wearer attempts to insert the blade into the food processor bowl, what kind of sound is heard? |
| 3 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | When the camera wearer picks up the center spindle piece, what kind of sound is heard? |
| 4 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | When the camera wearer washes the plastic center piece, what kind of sound is heard? |
| 5 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | When the camera wearer inserts the spindle and blade into the food processor bowl, what kind of sound is heard |
| 6 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | When the camera wearer successfully starts the food processor, what kind of sound is heard? |
| 7 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | When the camera wearer drops the biscuits into the food processor bowl, what kind of sound is heard? |
| 8 | DIAG | sound_action_binding | short_answer | coverage | - | correct | A plastic clanking sound as th | plastic-only collision | When the camera wearer places the lid on the food processor bowl, what kind of sound is heard? |
| 9 | DIAG | sound_action_binding | short_answer | coverage | - | correct | A plastic clanking sound as th | plastic collision | When the camera wearer removes the lid from the food processor bowl, what kind of sound is heard? |
| 10 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | When the camera wearer puts down the packet of biscuits, where is it placed? |
| 11 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | When the camera wearer attempts a second time to place the blade, where do they try to put it? |
| 12 | DIAG | object_state_change | single_choice | coverage | - | wrong | B | A | When the camera wearer takes the center plastic piece out of the cupboard, where is it moved to? |
| 13 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | When the camera wearer plugs the power cord into the wall outlet, where is the food processor placed? |
| 14 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | When the camera wearer moves the food processor after switching it off, where is it moved to? |
| 15 | DIAG | action_temporal_order | single_choice | coverage | - | wrong | D | C | When the camera wearer retrieves an item from the upper shelf and places it on the countertop, what object is  |
| 16 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | When the camera wearer attempts for a second time to place the blade on the center part of the food processor, |
| 17 | DIAG | action_temporal_order | single_choice | coverage | - | wrong | C | A | When the camera wearer picks up the center plastic piece from the cupboard, what action do they perform immedi |
| 18 | DIAG | action_temporal_order | single_choice | coverage | - | correct | C | C | When the camera wearer closes the tap after rinsing the plastic piece, what action do they perform immediately |
| 19 | DIAG | action_temporal_order | single_choice | coverage | - | wrong | B | A | When the camera wearer inserts the spindle and blade into the food processor bowl and checks its fit, what act |
| 20 | DIAG | action_recognition | single_choice | coverage | - | correct | C | C | When the camera wearer handles the packet of biscuits, what action do they perform? |
| 21 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | When the camera wearer handles the blade and the center part of the food processor, what action do they perfor |
| 22 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | When the camera wearer locates the center spindle piece on the top shelf of the cupboard, what action do they  |
| 23 | DIAG | action_recognition | single_choice | coverage | - | correct | B | B | When the camera wearer handles the towel, what action do they perform? |
| 24 | DIAG | action_recognition | short_answer | coverage | - | correct | Plug it into the wall socket | Plug it into the wall socket. | When the camera wearer handles the plug of the food processor, what action do they perform with it? |
| 25 | DIAG | action_recognition | short_answer | coverage | - | correct | Press the dial on the food pro | Press the button | When the camera wearer interacts with the controls of the food processor while the lid is still off, what acti |
| 26 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | When the camera wearer places an item on the countertop next to the condensed milk, butter, and cocoa, what ob |
| 27 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | When the camera wearer attempts for a second time to place the blade, what object do they try to place it onto |
| 28 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | When the camera wearer reaches into the cupboard and picks up an item, what object is being retrieved? |
| 29 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | When the camera wearer dries the center piece of the food processor, what object do they use? |
| 30 | DIAG | event_object_role | short_answer | coverage | - | correct | the wall socket | the wall socket | When the camera wearer connects the food processor to the power supply, what object do they plug it into? |
| 31 | DIAG | event_object_role | short_answer | coverage | - | correct | The dial of the food processor | the dial | When the camera wearer tests the food processor while the lid is still off, what specific part of the applianc |
| 32 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | correct | C | C | At the moment the plastic clattering sound is heard as the bowl is placed on the countertop, among the listed  |
| 33 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | wrong | B | A | When the remaining biscuits are poured from the packet into the bowl and a metal/plastic collision sound is he |
| 34 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | correct | B | B | When the metal and plastic collision sound is heard as the bowl is picked up from the drainer, among the follo |
| 35 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | correct | A | A | When the remaining biscuits are poured from the packet into the bowl and a metal/plastic collision sound is he |
| 36 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | wrong | B | A | When the plastic-only collision sound is heard just before the bowl is picked up from the drainer, among the l |
| 37 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | wrong | B | A | When the metal and plastic collision sound is heard as the bowl is picked up from the drainer, from the camera |
| 38 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | wrong | D | C | When the metal and plastic collision sound is heard as the bowl is picked up from the drainer, from the camera |
| 39 | DIAG | sound_movement_binding | - | request_verification | - | evidence_unresolved | None | None |  |
| 40 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | B | B | When the camera wearer attempts a second time to place an object on the center part of the food processor and  |
| 41 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | When the camera wearer picks up the center spindle piece from the cupboard and an open/close sound is heard, w |
| 42 | DIAG | sound_movement_binding | single_choice | coverage | - | wrong | B | A | When the camera wearer plugs the power cord into the wall outlet and a metal/plastic collision sound is heard, |
| 43 | DIAG | sound_movement_binding | - | request_verification | - | evidence_unresolved | None | None |  |
| 44 | DIAG | sound_movement_binding | single_choice | coverage | - | wrong | B | A | When the camera wearer opens the biscuit packet and a metal/plastic collision sound is heard, which movement p |
| 45 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | When the camera wearer interacts with the food processor and a plastic-only collision sound is heard, which sp |
| 46 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | When the camera wearer removes the lid from the food processor bowl and a plastic-only collision sound is hear |

## L3 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | When the food processor is started, what is being crushed inside it? |
| 2 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | A | A | Before more biscuits are thrown into the bowl of the food processor, what happened to the biscuits that were a |
| 3 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | A | A | When the food processor is turned on by rotating the dial, what is being crushed inside it? |
| 4 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | A | A | When the food processor is run for the second time in the clip, what is being crushed inside it? |
| 5 | DIAG | cross_event_integration | short_answer | coverage | - | correct | the cover of the food processo | the cover | Before the camera wearer attempts to insert the blade into the food processor bowl, what part was removed from |
| 6 | DIAG | cross_event_integration | short_answer | same_skill_new_event | - | wrong | No ingredients; the bowl was e | biscuits | Just before the lid is placed on the food processor bowl for the first time in the clip, what ingredient was a |
| 7 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | C | C | When the lid is removed from the food processor bowl, what had just been done with the food processor? |
| 8 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | A | A | Before more biscuits are thrown into the bowl of the food processor, what had been done with the lid of the fo |
| 9 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | correct | C | C | Before the center piece is inserted into the food processor bowl, what necessary preparation was done to it? |
| 10 | DIAG | causal_prerequisite_reasoning | single_choice | same_skill_new_event | - | correct | A | A | Before the button on the food processor base is pressed, what necessary preparation was done to the appliance? |
| 11 | DIAG | causal_prerequisite_reasoning | single_choice | same_skill_new_event | - | correct | C | C | Before the center piece attached to the blade is inserted into the food processor bowl, what was done to prepa |
| 12 | DIAG | causal_prerequisite_reasoning | single_choice | same_skill_new_event | - | correct | A | A | Before the dial of the food processor is pressed to check if it works, what necessary preparation was done to  |
| 13 | DIAG | causal_prerequisite_reasoning | short_answer | same_skill_new_event | - | correct | It was washed and dried with a | It was dried with a towel. | Before the center piece attached to the blade is inserted into the food processor, what necessary preparation  |
| 14 | DIAG | causal_prerequisite_reasoning | short_answer | same_skill_new_event | - | correct | Plugging the power cord into t | The power cord was plugged int | Before the button on the food processor base is pressed, what necessary preparation was done to provide the ap |

## L4 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | A | A | Based on the clip, what is the next step the camera wearer will take for the task they are doing? |
| 2 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | C | C | Based on the clip, what is the next step the camera wearer will take for the task they are doing? |
| 3 | DIAG | goal_conditioned_planning | plan | coverage | - | correct | ['Add biscuits from the next p | 1. Add another packet of biscu | What are the remaining stages, in order, for the task the camera wearer is doing? |

## Gemini 用量

| role | calls | errors | tok_in | tok_out | tok_think |
|---|---|---|---|---|---|
| examiner | 101 | 0 | 2840723 | 60933 | 352524 |
| judge | 16 | 0 | 5632 | 1302 | 3702 |
| solver | 249 | 0 | 1320651 | 4328 | 0 |
