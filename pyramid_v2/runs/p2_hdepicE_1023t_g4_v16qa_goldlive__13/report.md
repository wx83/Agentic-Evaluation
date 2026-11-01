# pyramid2 run `p2_hdepicE_1023t_g4_v16qa_goldlive__13`

dataset hdepic_e · videos 1 · examiner `gcp/google/gemini-3.1-pro-preview` · solver `gcp/google/gemini-4-argon` · n_per_layer 200 · seed 1023 · prompt physical-mental-draft2-hdepic-e+v16sg

**结果为 provisional**:gold = Examiner 的 proposed_reference_answer,未经人工核验;open/plan 题由 Gemini judge 判。

## 每层概览

| layer | stop | turns | scored | correct | raw acc | cluster-dedup acc | follow-up | invalid/unresolved | confirmation |
|---|---|---|---|---|---|---|---|---|---|
| L1 | STAIRCASE_COMPLETE | 19 | 14 | 8 | 0.571 | 0.615 | 0 | 0/5 | - |
| L2 | STAIRCASE_COMPLETE | 54 | 54 | 42 | 0.778 | 0.784 | 0 | 0/0 | - |
| L3 | STAIRCASE_COMPLETE | 12 | 12 | 12 | 1.0 | 1.0 | 0 | 0/0 | - |
| L4 | STAIRCASE_COMPLETE | 5 | 5 | 4 | 0.8 | 0.8 | 0 | 0/0 | - |

## 每层 × skill 诊断结论

| layer | skill | verdict | scored | correct | clusters | first-try correct | supported hypotheses | confirmation |
|---|---|---|---|---|---|---|---|---|
| L1 | spatial_near | boundary 2.0 | 1 | 1 | 1 |  | - | - |
| L1 | spatial_side | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L1 | object_recognition | boundary 1.5 | 4 | 2 | 4 |  | - | - |
| L1 | object_location_at_time | boundary 3 | 4 | 3 | 3 |  | - | - |
| L1 | object_grounding | boundary 1.5 | 5 | 2 | 5 |  | - | - |
| L2 | sound_action_binding | boundary 3.5 | 8 | 7 | 8 |  | - | - |
| L2 | object_state_change | boundary>=4 | 11 | 9 | 11 |  | - | - |
| L2 | action_temporal_order | boundary 3 | 10 | 8 | 10 |  | - | - |
| L2 | action_recognition | boundary 2.5 | 5 | 4 | 5 |  | - | - |
| L2 | event_object_role | boundary 3.5 | 8 | 7 | 8 |  | - | - |
| L2 | sound_anchored_spatial_near | boundary 1.75 | 4 | 3 | 2 |  | - | - |
| L2 | sound_anchored_spatial_side | boundary<1 | 2 | 0 | 1 |  | - | - |
| L2 | sound_movement_binding | boundary 2 | 6 | 4 | 6 |  | - | - |
| L3 | cross_event_integration | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L3 | hidden_state_inference | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | spatial_state_integration | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | causal_prerequisite_reasoning | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L4 | goal_conditioned_planning | boundary 2.5 | 5 | 4 | 5 |  | - | - |

## L1 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | spatial_near | single_choice | coverage | - | correct | C | C | When the biscuit packets are placed on the counter, about 9 seconds into the clip, which of the following obje |
| 2 | DIAG | object_recognition | single_choice | coverage | - | wrong | B | A | When an object is put down on the notepad, about 7 seconds into the clip, which object is it? |
| 3 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | When the camera wearer looks back and forth to figure out what they are doing wrong, about 10 seconds into the |
| 4 | DIAG | object_recognition | single_choice | coverage | - | correct | B | B | When the camera wearer picks up an object from the cupboard, at the start of the clip, which object is it? |
| 5 | DIAG | object_recognition | single_choice | coverage | - | wrong | D | B | When the camera wearer picks up an object from the countertop, about 5 seconds into the clip, which object is  |
| 6 | DIAG | object_location_at_time | single_choice | coverage | - | correct | C | C | When the biscuit packets are placed, about 3 seconds into the clip, where are they put down? |
| 7 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | When the center spindle piece is picked up, at the start of the clip, where is the box of the hand blender put |
| 8 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | When the lid is removed from the food processor bowl, about 3 seconds into the clip, where are the biscuits pu |
| 9 | DIAG | object_location_at_time | - | request_verification | - | evidence_unresolved | None | None |  |
| 10 | DIAG | object_location_at_time | - | request_verification | - | evidence_unresolved | None | None |  |
| 11 | DIAG | object_location_at_time | single_choice | coverage | - | wrong | B | A | When the center spindle piece is picked up, at the start of the clip, where is the blade put down? |
| 12 | DIAG | object_location_at_time | - | request_verification | - | evidence_unresolved | None | None |  |
| 13 | DIAG | object_location_at_time | - | request_verification | - | evidence_unresolved | None | None |  |
| 14 | DIAG | object_location_at_time | - | request_verification | - | evidence_unresolved | None | None |  |
| 15 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.553, 0.646, 0.795, 0.938] | 54.4, 68.2, 68.0, 78.5 | When the spindle is dried with a towel, at the start of the clip, what is the bounding box of the towel in the |
| 16 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.517, 0.456, 0.56, 0.487] | 67.4, 77.6, 89.6, 98.5 | When the biscuit packets are placed on the counter, at the start of the clip, what is the bounding box of the  |
| 17 | DIAG | object_grounding | bbox | coverage | - | correct | [0.39, 0.55, 0.59, 0.73] | 38.6, 56.9, 57.1, 77.4 | When the bowl is picked up, at the start of the clip, what is the bounding box of the bowl in the first frame  |
| 18 | DIAG | object_grounding | bbox | coverage | - | correct | [0.58, 0.55, 0.79, 0.77] | 51.6, 53.5, 69.6, 74.9 | What is the bounding box of the box of the hand blender in the first frame of the clip? |
| 19 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.278, 0.697, 0.745, 0.999] | 58.1, 74.2, 72.3, 99.7 | When the biscuit packet is opened, at the start of the clip, what is the bounding box of the packet of biscuit |

## L2 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | sound_action_binding | single_choice | coverage | - | correct | B | B | When the camera wearer removes the cover of the food processor bowl, which specific movement makes the sound? |
| 2 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | When the camera wearer attempts a second time to place the blade on the center part of the food processor, whi |
| 3 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | When the camera wearer places the center plastic piece into the food processor, which specific movement makes  |
| 4 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they wash the center piece of the food processor, which speci |
| 5 | DIAG | sound_action_binding | short_answer | coverage | - | correct | The wearer connects the plug i | pressing the button on the soc | During the task the camera wearer is doing, when they plug the power cord into the wall outlet, which specific |
| 6 | DIAG | sound_action_binding | short_answer | coverage | - | wrong | twisting the lid into place | rotating the dial | During the task the camera wearer is doing, after they press the button on the food processor base, which spec |
| 7 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they drop biscuits into the food processor bowl, which specif |
| 8 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they interact with the food processor lid, which specific mov |
| 9 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they take the packet of biscuits from the shelf, where do the |
| 10 | DIAG | object_state_change | single_choice | coverage | - | wrong | B | A | During the task the camera wearer is doing, when they attempt a second time to place the blade on the center p |
| 11 | DIAG | object_state_change | single_choice | coverage | - | wrong | B | A | During the task the camera wearer is doing, when they take the centre plastic piece from the cupboard, where d |
| 12 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they plug the power cord into the wall outlet, where do they  |
| 13 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they push the food processor, where do they move it? |
| 14 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they pick the lid of the food processor from the upper shelf, |
| 15 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they place the lid on the food processor bowl, to which fixtu |
| 16 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they lift the lid from the food processor bowl, where do they |
| 17 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they pour the remaining biscuits from the packet into the bow |
| 18 | DIAG | object_state_change | short_answer | coverage | - | correct | Into the food processor bowl | into the food processor bowl | During the task the camera wearer is doing, when they pour biscuits from the second packet, where do they move |
| 19 | DIAG | object_state_change | short_answer | coverage | - | correct | To the counter | To the counter | During the task the camera wearer is doing, when they turn the food processor by rotating the dial, to which f |
| 20 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they handle the packet of biscuits, which of the following se |
| 21 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they attempt to insert the blade into the food processor bowl |
| 22 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they retrieve the center piece of the food processor, which o |
| 23 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they clean the center piece of the food processor, which of t |
| 24 | DIAG | action_temporal_order | short_answer | coverage | - | correct | They turn on the outlet switch | Press the button on the socket | During the task the camera wearer is doing, when they plug the power cord into the wall outlet, what action do |
| 25 | DIAG | action_temporal_order | short_answer | coverage | - | wrong | Put the blade inside the food  | They touch the center tower of | During the task the camera wearer is doing, when they press the dial on the food processor base, what action d |
| 26 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they add the biscuits to the food processor bowl, which of th |
| 27 | DIAG | action_temporal_order | single_choice | coverage | - | wrong | C | A | During the task the camera wearer is doing, when they crush the first batch of biscuits, which of the followin |
| 28 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they add the second handful of biscuits to the food processor |
| 29 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they close the food processor, which of the following sequenc |
| 30 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they handle the packet of biscuits, what action do they perfo |
| 31 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, after they rotate the blade piece, what action do they perform wit |
| 32 | DIAG | action_recognition | single_choice | coverage | - | wrong | B | A | During the task the camera wearer is doing, when they find the centre plastic piece in the cupboard, what acti |
| 33 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they pick up the towel, what action do they perform with it? |
| 34 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, after they place the food processor on the countertop, what action |
| 35 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they reach to the upper shelf and then place the retrieved it |
| 36 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they attempt a second time to place the blade, where do they  |
| 37 | DIAG | event_object_role | single_choice | coverage | - | correct | C | C | During the task the camera wearer is doing, when they reach into the cupboard and retrieve an item that they s |
| 38 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they dry the spindle (center piece) of the food processor, wh |
| 39 | DIAG | event_object_role | short_answer | coverage | - | correct | The wall socket | The wall socket | During the task the camera wearer is doing, when they plug in the food processor, what do they plug it into? |
| 40 | DIAG | event_object_role | short_answer | coverage | - | wrong | Secure the lid of the food pro | Press the dial | During the task the camera wearer is doing, when they try to turn on the food processor but it does not start, |
| 41 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they pull apart the plastic packaging, what do they remove fr |
| 42 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they close the food processor, what object do they place on t |
| 43 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | wrong | D | A | During the task the camera wearer is doing, when they place the biscuit packets on the counter, at the moment  |
| 44 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | correct | C | C | During the task the camera wearer is doing, when the remaining biscuits are poured from the packet into the bo |
| 45 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they place the biscuit packets on the counter, at the moment  |
| 46 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | correct | D | D | During the task the camera wearer is doing, when the remaining biscuits are poured from the packet into the bo |
| 47 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | wrong | B | A | During the task the camera wearer is doing, when they place the biscuit packets on the counter, at the moment  |
| 48 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | wrong | D | A | During the task the camera wearer is doing, when they place the biscuit packets on the counter, at the moment  |
| 49 | DIAG | sound_movement_binding | single_choice | coverage | - | wrong | D | C | During the task the camera wearer is doing, after they place the biscuit packets on the counter, which specifi |
| 50 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they attempt a second time to place the part on the center of |
| 51 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | B | B | During the task the camera wearer is doing, when they retrieve the center plastic piece from the cupboard, whi |
| 52 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they insert the spindle and blade into the food processor bow |
| 53 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when they test the food processor and prepare it for use, the move |
| 54 | DIAG | sound_movement_binding | single_choice | coverage | - | wrong | B | A | During the task the camera wearer is doing, when they open the biscuit packet, the movement of which object ma |

## L3 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | cross_event_integration | single_choice | coverage | - | correct | B | B | When the button is pressed to run the food processor, what is being crushed inside it? |
| 2 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | Before more biscuits are thrown into the bowl of the food processor, what was done to the biscuits already ins |
| 3 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | When the food processor is turned on to crush biscuits for the second time, what ingredient was most recently  |
| 4 | DIAG | cross_event_integration | single_choice | coverage | - | correct | C | C | When the food processor is run for the second time in the clip, what ingredient was most recently added to its |
| 5 | DIAG | cross_event_integration | short_answer | coverage | - | correct | The lid of the food processor | the cover | Before the person attempts to insert the blade into the food processor, what was removed from the food process |
| 6 | DIAG | cross_event_integration | short_answer | coverage | - | correct | Biscuits | biscuits | Before the lid is placed on the food processor bowl, what ingredient was added inside it? |
| 7 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | correct | A | A | What necessary preparation was done to the center piece before it was inserted into the food processor bowl? |
| 8 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | correct | A | A | Before the button on the food processor base is pressed, what necessary preparation was done with its power co |
| 9 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | correct | A | A | Before the center piece is inserted into the food processor bowl, what was done to it? |
| 10 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | correct | A | A | Before the button on the food processor base is pressed, what necessary action was taken to provide it with el |
| 11 | DIAG | causal_prerequisite_reasoning | short_answer | coverage | - | correct | It was washed and dried, and t | It was washed and dried. | Before the center piece is inserted into the food processor bowl, what necessary preparation was done to it? |
| 12 | DIAG | causal_prerequisite_reasoning | short_answer | coverage | - | correct | Plugging its power cord into t | The power cord was plugged int | Before the button on the food processor base is pressed, what necessary action was taken to provide it with el |

## L4 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | C | C | What is the next step for the task the camera wearer is doing? |
| 2 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | C | C | What is the next step for the task the camera wearer is doing? |
| 3 | DIAG | goal_conditioned_planning | plan | coverage | - | wrong | ['Crush the next batch of bisc | 1. Add another packet of biscu | What are the remaining stages, in order, for the task the camera wearer is doing? |
| 4 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | D | D | What is the next step for the task the camera wearer is doing? |
| 5 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | B | B | What is the next step for the task the camera wearer is doing? |

## Gemini 用量

| role | calls | errors | tok_in | tok_out | tok_think |
|---|---|---|---|---|---|
| examiner | 104 | 1 | 2882686 | 63500 | 358510 |
| judge | 21 | 0 | 7224 | 1612 | 5793 |
| solver | 255 | 0 | 1200882 | 4448 | 0 |
