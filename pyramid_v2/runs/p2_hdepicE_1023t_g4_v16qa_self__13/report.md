# pyramid2 run `p2_hdepicE_1023t_g4_v16qa_self__13`

dataset hdepic_e · videos 1 · examiner `gcp/google/gemini-3.1-pro-preview` · solver `gcp/google/gemini-4-argon` · n_per_layer 200 · seed 1023 · prompt physical-mental-draft2-hdepic-e+v16sg

**结果为 provisional**:gold = Examiner 的 proposed_reference_answer,未经人工核验;open/plan 题由 Gemini judge 判。

## 每层概览

| layer | stop | turns | scored | correct | raw acc | cluster-dedup acc | follow-up | invalid/unresolved | confirmation |
|---|---|---|---|---|---|---|---|---|---|
| L1 | STAIRCASE_COMPLETE | 21 | 19 | 13 | 0.684 | 0.722 | 0 | 0/2 | - |
| L2 | STAIRCASE_COMPLETE | 54 | 54 | 41 | 0.759 | 0.776 | 0 | 0/0 | - |
| L3 | STAIRCASE_COMPLETE | 12 | 12 | 12 | 1.0 | 1.0 | 0 | 0/0 | - |
| L4 | STAIRCASE_COMPLETE | 7 | 7 | 5 | 0.714 | 0.714 | 0 | 0/0 | - |

## 每层 × skill 诊断结论

| layer | skill | verdict | scored | correct | clusters | first-try correct | supported hypotheses | confirmation |
|---|---|---|---|---|---|---|---|---|
| L1 | spatial_near | boundary 2.0 | 1 | 1 | 1 |  | - | - |
| L1 | spatial_side | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L1 | object_recognition | boundary 2 | 7 | 5 | 7 |  | - | - |
| L1 | object_location_at_time | boundary 2.5 | 6 | 5 | 5 |  | - | - |
| L1 | object_grounding | boundary 1.5 | 5 | 2 | 5 |  | - | - |
| L2 | sound_action_binding | boundary 1.5 | 5 | 3 | 5 |  | - | - |
| L2 | object_state_change | boundary 1.5 | 6 | 4 | 6 |  | - | - |
| L2 | action_temporal_order | boundary 2.5 | 11 | 8 | 11 |  | - | - |
| L2 | action_recognition | boundary 3.5 | 8 | 7 | 8 |  | - | - |
| L2 | event_object_role | boundary 3.5 | 8 | 7 | 8 |  | - | - |
| L2 | sound_anchored_spatial_near | boundary 2 | 6 | 5 | 2 |  | - | - |
| L2 | sound_anchored_spatial_side | boundary<1 | 2 | 0 | 1 |  | - | - |
| L2 | sound_movement_binding | boundary 3.5 | 8 | 7 | 8 |  | - | - |
| L3 | cross_event_integration | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L3 | hidden_state_inference | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | spatial_state_integration | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | causal_prerequisite_reasoning | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L4 | goal_conditioned_planning | boundary 2.25 | 7 | 5 | 7 |  | - | - |

## L1 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | spatial_near | single_choice | coverage | - | correct | B | B | At the start of the clip, the camera wearer places the biscuit packets on the counter. About 9 seconds into th |
| 2 | DIAG | object_recognition | single_choice | coverage | - | wrong | B | A | About 7 seconds into the clip, the camera wearer puts down an object on the notepad. Which object is put down? |
| 3 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | At the end of the clip, the camera wearer looks back and forth between the food processor and another object.  |
| 4 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | At the start of the clip, the camera wearer picks up an object from the cupboard. Which object is picked up? |
| 5 | DIAG | object_recognition | single_choice | coverage | - | correct | B | B | About 4.5 seconds into the clip, the camera wearer picks up an object from the countertop. Which object is pic |
| 6 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | While dropping biscuits into the food processor bowl, about 8.5 seconds into the clip, the camera wearer puts  |
| 7 | DIAG | object_recognition | single_choice | coverage | - | correct | B | B | About 4.5 seconds into the clip, the camera wearer places an object inside the edge of the towel to dry it. Wh |
| 8 | DIAG | object_recognition | single_choice | coverage | - | wrong | A | B | At the start of the clip, the camera wearer presses a part of the food processor to check if it works. Which p |
| 9 | DIAG | object_location_at_time | single_choice | coverage | - | correct | C | C | About 3 seconds into the clip, the camera wearer puts down the biscuit packets. Where are they placed? |
| 10 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | At the start of the clip, the camera wearer picks up the center spindle piece. About 4 seconds into the clip,  |
| 11 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 3 seconds into the clip, the camera wearer removes the lid from the food processor bowl. Where are the b |
| 12 | DIAG | object_location_at_time | - | request_verification | - | evidence_unresolved | None | None |  |
| 13 | DIAG | object_location_at_time | - | request_verification | - | evidence_unresolved | None | None |  |
| 14 | DIAG | object_location_at_time | single_choice | coverage | - | wrong | B | A | At the start of the clip, the camera wearer picks up the center spindle piece. About 9 seconds into the clip,  |
| 15 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 4.5 seconds into the clip, the camera wearer opens the biscuit packet. Where was this packet picked up f |
| 16 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 6 seconds into the clip, after attempting to insert the blade, the camera wearer picks it up again. Wher |
| 17 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.54, 0.65, 0.79, 0.93] | 54.4, 68.2, 68.0, 78.5 | At the start of the clip, the camera wearer dries the spindle with a towel. What is the bounding box of the to |
| 18 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.808, 0.36, 0.845, 0.421] | 67.4, 77.6, 89.6, 98.5 | At the start of the clip, the camera wearer places the biscuit packets on the counter. What is the bounding bo |
| 19 | DIAG | object_grounding | bbox | coverage | - | correct | [0.4, 0.56, 0.58, 0.72] | 38.6, 56.9, 57.1, 77.4 | At the start of the clip, the camera wearer picks up a bowl from the drainer. What is the bounding box of the  |
| 20 | DIAG | object_grounding | bbox | coverage | - | correct | [0.575, 0.55, 0.795, 0.766] | 51.6, 53.5, 69.6, 74.9 | At the start of the clip, the camera wearer closes the cupboard. What is the bounding box of the box of the ha |
| 21 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.292, 0.697, 0.744, 1.0] | 58.1, 74.2, 72.3, 99.7 | About 0.4 seconds into the clip, the camera wearer opens the biscuit packet. What is the bounding box of the p |

## L2 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | sound_action_binding | single_choice | coverage | - | wrong | B | A | During the clip, which of the following actions produces a clanking sound of metal and plastic parts colliding |
| 2 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | When the camera wearer attempts to place the blade on the center part of the food processor, which of the foll |
| 3 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | When the camera wearer picks up the center plastic piece from the cupboard, which of the following sounds is h |
| 4 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | During the clip, which of the following actions produces the sound of running water? |
| 5 | DIAG | sound_action_binding | single_choice | coverage | - | wrong | B | A | During the clip, which of the following actions produces a plastic-only collision sound? |
| 6 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | When the camera wearer puts down the packet of biscuits, where do they place it? |
| 7 | DIAG | object_state_change | single_choice | coverage | - | wrong | D | A | When the camera wearer attempts to fit the blade for the second time, where do they place it? |
| 8 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | When the camera wearer retrieves the center plastic piece, where do they take it from? |
| 9 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | When the camera wearer moves the food processor to plug it into the socket, where do they place it? |
| 10 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | When the camera wearer pushes the food processor, where do they move it? |
| 11 | DIAG | object_state_change | single_choice | coverage | - | wrong | D | A | When the camera wearer picks up the lid of the food processor, where do they take it from? |
| 12 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | During the clip, which action does the camera wearer perform immediately after putting down the blade on the n |
| 13 | DIAG | action_temporal_order | single_choice | coverage | - | wrong | B | C | During the clip, which action does the camera wearer perform immediately after attempting for the second time  |
| 14 | DIAG | action_temporal_order | single_choice | coverage | - | wrong | B | A | During the clip, which action does the camera wearer perform immediately after picking up the center plastic p |
| 15 | DIAG | action_temporal_order | single_choice | coverage | - | correct | B | B | During the clip, which action does the camera wearer perform immediately after rinsing the plastic piece? |
| 16 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | During the clip, which action does the camera wearer perform immediately after turning the dial of the food pr |
| 17 | DIAG | action_temporal_order | single_choice | coverage | - | correct | B | B | During the clip, which action does the camera wearer perform immediately after pressing the dial of the open f |
| 18 | DIAG | action_temporal_order | single_choice | coverage | - | correct | B | B | During the clip, which action does the camera wearer perform immediately after dropping the biscuits from the  |
| 19 | DIAG | action_temporal_order | single_choice | coverage | - | correct | B | B | During the clip, which action does the camera wearer perform immediately after placing the lid on the food pro |
| 20 | DIAG | action_temporal_order | single_choice | coverage | - | correct | B | B | During the clip, which action does the camera wearer perform immediately after opening the food processor by t |
| 21 | DIAG | action_temporal_order | short_answer | coverage | - | correct | turns on the food processor | Turn the food processor on. | During the clip, what action does the camera wearer perform immediately after placing the lid back on the food |
| 22 | DIAG | action_temporal_order | short_answer | coverage | - | wrong | puts the food processor lid on | picks up the lid of the food p | During the clip, what action does the camera wearer perform immediately after shaking the packaging to help th |
| 23 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the clip, what action does the camera wearer perform with the packet of biscuits? |
| 24 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the clip, what action does the camera wearer perform with the blade and the food processor? |
| 25 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the clip, what action does the camera wearer perform to retrieve the center plastic piece from the cupb |
| 26 | DIAG | action_recognition | single_choice | coverage | - | correct | B | B | During the clip, what action does the camera wearer perform with the towel? |
| 27 | DIAG | action_recognition | short_answer | coverage | - | correct | Plugs it into the wall socket | plugs it into the socket | During the clip, what action does the camera wearer perform with the plug of the food processor? |
| 28 | DIAG | action_recognition | short_answer | coverage | - | wrong | Turning the dial | presses the dial | When the camera wearer first interacts with the dial of the food processor during the clip, what action do the |
| 29 | DIAG | action_recognition | single_choice | coverage | - | correct | B | B | During the clip, what action does the camera wearer perform with the biscuits that have fallen into the food p |
| 30 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the clip, what action does the camera wearer perform to close the food processor? |
| 31 | DIAG | event_object_role | single_choice | coverage | - | correct | B | B | During the clip, the camera wearer retrieves an item from the upper shelf and places it on the countertop. Whi |
| 32 | DIAG | event_object_role | single_choice | coverage | - | correct | C | C | During the clip, the camera wearer attempts for the second time to place an object on the center part of the f |
| 33 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | During the clip, the camera wearer retrieves an item from the cupboard. Which object do they handle in this ac |
| 34 | DIAG | event_object_role | single_choice | coverage | - | correct | C | C | During the clip, the camera wearer dries the plastic piece. Which object do they use to dry it? |
| 35 | DIAG | event_object_role | short_answer | coverage | - | correct | The food processor | food processor | During the clip, the camera wearer plugs the power cord into the wall outlet. Which appliance does this power  |
| 36 | DIAG | event_object_role | short_answer | coverage | - | wrong | The center plastic piece | the dial | During the clip, the camera wearer tries to operate the food processor before attaching the lid. Which part of |
| 37 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | During the clip, the camera wearer drops biscuits from the packaging. Which object do the biscuits fall into? |
| 38 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | During the clip, the camera wearer closes the food processor. Which object do they place on top of the bowl? |
| 39 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | correct | A | A | During the clip, when the sound of the plastic bowl being placed on the countertop is heard, which of the foll |
| 40 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | correct | A | A | During the clip, when the sound of metal and plastic colliding is heard as the remaining biscuits are poured f |
| 41 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | correct | A | A | During the clip, when the sound of metal and plastic colliding is heard as the bowl is picked up from the drai |
| 42 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | wrong | D | A | During the clip, when the sound of metal and plastic colliding is heard as the remaining biscuits are poured f |
| 43 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | correct | A | A | During the clip, when the sound of a plastic-only collision is heard as the bowl is placed on the countertop,  |
| 44 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | correct | A | A | During the clip, when the sound of metal and plastic colliding is heard as the remaining biscuits are poured f |
| 45 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | wrong | B | A | During the clip, when the sound of metal and plastic colliding is heard as the bowl is picked up from the drai |
| 46 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | wrong | C | A | During the clip, when the sound of metal and plastic colliding is heard as the bowl is picked up from the drai |
| 47 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | During the clip, when the camera wearer holds the food processor bowl by its handle and rotates its top part,  |
| 48 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | During the clip, when the camera wearer attempts a second time to place a part onto the center of the food pro |
| 49 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | During the clip, when the camera wearer slides a part into the center of the food processor, which object's mo |
| 50 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | During the clip, when the camera wearer plugs the power cord into the wall outlet, which object's movement pro |
| 51 | DIAG | sound_movement_binding | short_answer | coverage | - | correct | Locking the food processor lid | attaching the lid to the food  | During the clip, after the camera wearer is seen to press the button on the food processor base, what action p |
| 52 | DIAG | sound_movement_binding | short_answer | coverage | - | wrong | The camera wearer places the l | Dropping the biscuits into the | During the clip, when the camera wearer empties the packaging into the food processor, what movement produces  |
| 53 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | During the clip, when the camera wearer closes the food processor, which of the following movements produces t |
| 54 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | During the clip, when the camera wearer removes the lid from the food processor bowl, which object's movement  |

## L3 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | What is being crushed when the food processor is turned on? |
| 2 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | A | A | Before more biscuits are thrown into the bowl, what was done to the biscuits already inside? |
| 3 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | A | A | When the food processor is turned on after the camera wearer struggles to lock the lid in place, what is insid |
| 4 | DIAG | cross_event_integration | single_choice | coverage | - | correct | C | C | What newly added ingredient is being crushed the second time the food processor is run in the clip? |
| 5 | DIAG | cross_event_integration | short_answer | same_skill_new_event | - | correct | The lid of the food processor | the cover | What was removed from the food processor bowl before the camera wearer attempts to insert the blade into it? |
| 6 | DIAG | cross_event_integration | short_answer | coverage | - | correct | Biscuits | biscuits | Before the lid is placed on the food processor bowl to close it, what ingredient was added to the bowl? |
| 7 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | correct | A | A | What was done to the center piece before it is inserted into the food processor bowl? |
| 8 | DIAG | causal_prerequisite_reasoning | single_choice | same_skill_new_event | - | correct | A | A | What was done to provide power to the food processor before its dial is pressed to check if it works? |
| 9 | DIAG | causal_prerequisite_reasoning | single_choice | same_skill_new_event | - | correct | A | A | What was done to the center piece before it is inserted into the food processor bowl? |
| 10 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | correct | A | A | Which of the following earlier steps was necessary for the food processor to receive power when its dial is pr |
| 11 | DIAG | causal_prerequisite_reasoning | short_answer | same_skill_new_event | - | correct | Rinsed with water, dried with  | It was dried with a towel. | What was done to the center piece before it is inserted into the food processor? |
| 12 | DIAG | causal_prerequisite_reasoning | short_answer | coverage | - | correct | The plug was plugged into the  | Its power cord was plugged int | What was done to provide power to the food processor before its dial is pressed to check if it works? |

## L4 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | goal_conditioned_planning | single_choice | coverage | - | wrong | B | C | Based on the clip, what is the next step the camera wearer will take for the task they are doing? |
| 2 | DIAG | goal_conditioned_planning | single_choice | coverage | - | wrong | B | C | Based on the clip, what is the next step the camera wearer will take for the task they are doing? |
| 3 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | A | A | Based on the clip, what is the next step the camera wearer will take for the task they are doing? |
| 4 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | B | B | Based on the clip, what is the next step the camera wearer will take for the task they are doing? |
| 5 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | B | B | Based on the clip, what is the next step the camera wearer will take for the task they are doing? |
| 6 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | B | B | Based on the clip, what is the next step the camera wearer will take for the task they are doing? |
| 7 | DIAG | goal_conditioned_planning | plan | coverage | - | correct | ['Crush more biscuits in the f | 1. Add another packet of biscu | What are the remaining stages, in order, for the task the camera wearer is doing? |

## Gemini 用量

| role | calls | errors | tok_in | tok_out | tok_think |
|---|---|---|---|---|---|
| examiner | 106 | 0 | 2976049 | 65480 | 364591 |
| judge | 21 | 0 | 7119 | 1536 | 4316 |
| solver | 276 | 0 | 1252383 | 4704 | 0 |
