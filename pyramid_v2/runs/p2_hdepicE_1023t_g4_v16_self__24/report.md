# pyramid2 run `p2_hdepicE_1023t_g4_v16_self__24`

dataset hdepic_e · videos 1 · examiner `gcp/google/gemini-3.1-pro-preview` · solver `gcp/google/gemini-4-argon` · n_per_layer 200 · seed 1023 · prompt physical-mental-draft2-hdepic-e+v16sg

**结果为 provisional**:gold = Examiner 的 proposed_reference_answer,未经人工核验;open/plan 题由 Gemini judge 判。

## 每层概览

| layer | stop | turns | scored | correct | raw acc | cluster-dedup acc | follow-up | invalid/unresolved | confirmation |
|---|---|---|---|---|---|---|---|---|---|
| L1 | STAIRCASE_COMPLETE | 26 | 26 | 19 | 0.731 | 0.739 | 0 | 0/0 | - |
| L2 | STAIRCASE_COMPLETE | 54 | 48 | 41 | 0.854 | 0.914 | 0 | 0/6 | - |
| L3 | STAIRCASE_COMPLETE | 10 | 8 | 8 | 1.0 | 1.0 | 0 | 0/2 | - |
| L4 | STAIRCASE_COMPLETE | 6 | 5 | 4 | 0.8 | 0.8 | 0 | 1/0 | - |

## 每层 × skill 诊断结论

| layer | skill | verdict | scored | correct | clusters | first-try correct | supported hypotheses | confirmation |
|---|---|---|---|---|---|---|---|---|
| L1 | spatial_near | boundary 1.5 | 1 | 0 | 1 |  | - | - |
| L1 | spatial_side | boundary 3.5 | 3 | 3 | 2 |  | - | - |
| L1 | object_recognition | boundary 3.5 | 7 | 6 | 7 |  | - | - |
| L1 | object_location_at_time | boundary 3.5 | 7 | 6 | 5 |  | - | - |
| L1 | object_grounding | boundary<1 | 8 | 4 | 8 |  | - | - |
| L2 | sound_action_binding | boundary>=4 | 10 | 9 | 7 |  | - | - |
| L2 | object_state_change | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | action_temporal_order | boundary>=4 | 6 | 6 | 4 |  | - | - |
| L2 | action_recognition | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | event_object_role | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | sound_anchored_spatial_near | boundary<1 | 2 | 0 | 1 |  | - | - |
| L2 | sound_anchored_spatial_side | boundary 2.25 | 8 | 6 | 2 |  | - | - |
| L2 | sound_movement_binding | boundary 1.5 | 4 | 2 | 3 |  | - | - |
| L3 | cross_event_integration | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L3 | hidden_state_inference | boundary 2.0 | 1 | 1 | 1 |  | - | - |
| L3 | spatial_state_integration | not_started | 0 | 0 | 0 |  | - | - |
| L3 | causal_prerequisite_reasoning | boundary 2.0 | 1 | 1 | 1 |  | - | - |
| L4 | goal_conditioned_planning | boundary 3.25 | 5 | 4 | 5 |  | - | - |

## L1 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | spatial_near | single_choice | coverage | - | wrong | A | B | About 6 seconds into the clip, when the packets of mushrooms are placed on the counter, which of the following |
| 2 | DIAG | spatial_side | single_choice | coverage | - | correct | B | B | About 7 seconds into the clip, when the packets of mushrooms are placed on the counter, from the camera wearer |
| 3 | DIAG | spatial_side | single_choice | coverage | - | correct | C | C | About 9 seconds into the clip, when the foil is placed down, from the camera wearer's own viewpoint at that mo |
| 4 | DIAG | spatial_side | single_choice | coverage | - | correct | A | A | About 9 seconds into the clip, when the foil is placed down, from the camera wearer's own viewpoint at that mo |
| 5 | DIAG | object_recognition | single_choice | coverage | - | correct | B | B | At the start of the clip, when the camera wearer grabs an object from the side of the cupboard using their rig |
| 6 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | About 2 seconds into the clip, when the camera wearer smooths out an object into the baking tray, pushing it i |
| 7 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | At the start of the clip, when the camera wearer rinses off an object using both hands, which object is it? |
| 8 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | About 7 seconds into the clip, before the water running sound stops, what object is the camera wearer rinsing  |
| 9 | DIAG | object_recognition | short_answer | coverage | - | wrong | container | mushrooms | About 4 seconds into the clip, before the water running sound stops, what object does the camera wearer pick u |
| 10 | DIAG | object_recognition | single_choice | coverage | - | correct | B | B | At the start of the clip, when the camera wearer picks up an object from the container and places it into thei |
| 11 | DIAG | object_recognition | single_choice | coverage | - | correct | C | C | At the start of the clip, when the camera wearer slices an object using the chef's knife in their right hand w |
| 12 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 5 seconds into the clip, while the water running sound is heard, where is the mushroom picked up from? |
| 13 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 4 seconds into the clip, while the water running sound is heard, where are the mushrooms placed? |
| 14 | DIAG | object_location_at_time | single_choice | coverage | - | correct | B | B | About 9 seconds into the clip, when the washed mushrooms are placed down, where are they placed? |
| 15 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 4 seconds into the clip, while the water running sound is heard, where does the camera wearer place the  |
| 16 | DIAG | object_location_at_time | short_answer | coverage | - | wrong | on the sink drainboard | counter | About 5 seconds into the clip, while the water running sound is heard, where does the camera wearer place the  |
| 17 | DIAG | object_location_at_time | single_choice | coverage | - | correct | C | C | About 8 seconds into the clip, when the packets of mushrooms are placed down, where does the camera wearer pla |
| 18 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 9 seconds into the clip, when the foil is placed down, where does the camera wearer place it? |
| 19 | DIAG | object_grounding | bbox | coverage | - | correct | [0.39, 0.51, 0.61, 0.7] | 41.5, 50.3, 59.5, 65.8 | What is the bounding box of the tupperware in the first frame of the clip? |
| 20 | DIAG | object_grounding | bbox | coverage | - | correct | [0.54, 0.56, 0.71, 0.74] | 53.8, 54.4, 68.4, 73.7 | What is the bounding box of the packet of mushrooms in the first frame of the clip? |
| 21 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.51, 0.44, 0.7, 0.68] | 29.2, 46.2, 47.9, 58.8 | What is the bounding box of the tupperware in the first frame of the clip? |
| 22 | DIAG | object_grounding | bbox | coverage | - | correct | [0.517, 0.569, 0.732, 0.767] | 47.0, 59.1, 71.5, 79.0 | At the start of the clip, when the second packet of mushrooms is opened, what is the bounding box of the packe |
| 23 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.48, 0.56, 0.72, 0.69] | 43.9, 53.0, 75.2, 73.2 | At the start of the clip, when the second packet of mushrooms is opened, what is the bounding box of the packe |
| 24 | DIAG | object_grounding | bbox | coverage | - | correct | [0.37, 0.56, 0.68, 0.84] | 34.2, 57.4, 66.5, 86.2 | What is the bounding box of the washing up bowl in the first frame of the clip? |
| 25 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.565, 0.39, 0.691, 0.56] | 0.9, 32.3, 29.9, 55.2 | At the start of the clip, when the packets of mushrooms are placed on the counter, what is the bounding box of |
| 26 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.649, 0.413, 1.0, 0.774] | 54.2, 51.5, 95.2, 88.7 | What is the bounding box of the sheet of foil in the first frame of the clip? |

## L2 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | When the mushroom packet is placed onto the countertop, what kind of sound is heard? |
| 2 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | wrong | B | A | When the foil is placed and folded onto the baking tray, what kind of sound is heard? |
| 3 | DIAG | sound_action_binding | single_choice | coverage | - | correct | B | B | When the sound of running water starts, which action is the camera wearer performing? |
| 4 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | correct | B | B | When the water running sound stops, which action is the camera wearer performing? |
| 5 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | When the sound of water is first heard in the clip, which action is the camera wearer performing? |
| 6 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | correct | A | A | When the chopping sound is heard, which action is the camera wearer performing? |
| 7 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | When the final mushrooms are sliced, what kind of sound is heard? |
| 8 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | correct | A | A | When the cutting board is placed onto the countertop, what kind of sound is heard? |
| 9 | DIAG | sound_action_binding | short_answer | same_skill_new_event | - | correct | rustling of plastic | plastic-only collision | When the packets of mushrooms are placed on the counter, what kind of sound is heard? |
| 10 | DIAG | sound_action_binding | short_answer | same_event_new_format | - | correct | A crinkling and rustling sound | crinkling of foil | When the camera wearer places and folds the foil onto the baking tray, what kind of sound is heard? |
| 11 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | When the camera wearer places the packet of mushrooms, where does it end up? |
| 12 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | When the camera wearer places the torn-off foil, where does it end up? |
| 13 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | When the camera wearer opens the first packet of mushrooms, where does the punnet of mushrooms end up? |
| 14 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | When the camera wearer places the washed mushrooms down, where do they end up? |
| 15 | DIAG | object_state_change | short_answer | coverage | - | correct | In the sink | in the sink | When the water running sound starts, where does the camera wearer place the mushrooms? |
| 16 | DIAG | object_state_change | short_answer | coverage | - | correct | On the cutting board | On the cutting board | When the camera wearer places the washed mushrooms down, where do they end up? |
| 17 | DIAG | action_temporal_order | - | request_verification | - | evidence_unresolved | None | None |  |
| 18 | DIAG | action_temporal_order | - | request_verification | - | evidence_unresolved | None | None |  |
| 19 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | Which of the following sequences of actions occurs in the clip? |
| 20 | DIAG | action_temporal_order | - | request_verification | - | evidence_unresolved | None | None |  |
| 21 | DIAG | action_temporal_order | - | request_verification | - | evidence_unresolved | None | None |  |
| 22 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | When the water running sound stops, which of the following sequences of actions occurs? |
| 23 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | Immediately after the camera wearer slices the mushrooms for the first time, which action do they perform? |
| 24 | DIAG | action_temporal_order | single_choice | coverage | - | correct | C | C | When the final mushrooms are sliced, which of the following sequences of actions occurs? |
| 25 | DIAG | action_temporal_order | short_answer | same_event_new_format | - | correct | Rinsing them in the sink | wash the mushrooms | After opening the packet of mushrooms, what is the next action the camera wearer performs with the mushrooms? |
| 26 | DIAG | action_temporal_order | short_answer | same_event_new_format | - | correct | shakes off the excess water ov | shake off the mushrooms | Immediately after turning off the tap, what action does the camera wearer perform with the mushrooms in their  |
| 27 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | After picking up the packet of mushrooms from the vegetable drawer, what action does the camera wearer perform |
| 28 | DIAG | action_recognition | single_choice | coverage | - | correct | B | B | What action does the camera wearer perform with the oven in the clip? |
| 29 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | What action does the camera wearer perform to remove the mushrooms from their packaging? |
| 30 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | What action does the camera wearer repeatedly perform with the mushrooms after washing and rinsing them? |
| 31 | DIAG | action_recognition | short_answer | coverage | - | correct | turns on the cold water tap | turns it on | What action does the camera wearer perform with the tap? |
| 32 | DIAG | action_recognition | short_answer | coverage | - | correct | places them on the cutting boa | places them on the cutting boa | After picking up mushrooms from the sink, what action does the camera wearer perform with them? |
| 33 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | When the camera wearer takes an object out of the vegetable drawer and places it onto the countertop, what obj |
| 34 | DIAG | event_object_role | single_choice | coverage | - | correct | B | B | When the camera wearer places and smooths out the foil, what object is it placed into? |
| 35 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | When the camera wearer pulls an item out of the plastic packaging, what object is being handled? |
| 36 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | When the camera wearer places the washed mushrooms down, what object are they placed onto? |
| 37 | DIAG | event_object_role | short_answer | coverage | - | correct | A packet of mushrooms | packet of mushrooms | What object does the camera wearer open by pulling apart its packaging? |
| 38 | DIAG | event_object_role | short_answer | coverage | - | correct | the tap | the tap | When the water running sound stops, what object does the camera wearer turn off? |
| 39 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | wrong | A | B | When the packets of mushrooms are placed on the counter, an open/close sound is heard. At that moment, relativ |
| 40 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | wrong | B | A | When the packets of mushrooms are placed on the counter, an open/close sound is heard. At that moment, relativ |
| 41 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | correct | C | C | When the packets of mushrooms are placed on the counter, a metal/plastic collision sound is heard. At that mom |
| 42 | DIAG | sound_anchored_spatial_side | single_choice | same_skill_new_event | - | correct | C | C | When the oven is turned on, a metal collision sound is heard. At that moment, from the camera wearer's own vie |
| 43 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | correct | C | C | When the packets of mushrooms are placed on the counter, an open/close sound is heard. At that moment, from th |
| 44 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | correct | C | C | When the oven is turned on, a metal collision sound is heard. At that moment, from the camera wearer's own vie |
| 45 | DIAG | sound_anchored_spatial_side | short_answer | coverage | - | correct | the bowl in the sink | washing up bowl | Just before the packets of mushrooms are placed on the counter, a sound of something opening or closing is hea |
| 46 | DIAG | sound_anchored_spatial_side | short_answer | coverage | - | wrong | the sheet of foil | box of foil roll | While the oven is being turned on, a metal collision sound is heard. At that moment, from the camera wearer's  |
| 47 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | wrong | B | C | Just before the packets of mushrooms are placed on the counter, a metal/plastic collision sound is heard. At t |
| 48 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | correct | C | C | When the oven is turned on, a metal-only collision sound is heard. At that moment, from the camera wearer's ow |
| 49 | DIAG | sound_movement_binding | single_choice | coverage | - | wrong | D | B | When the first metal or plastic collision sound is heard in the clip, which object is being moved? |
| 50 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | When the baking tray is being lined, which object is being moved when the metallic collision sound is heard? |
| 51 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | When the sound of running water begins, which of the following objects is being moved? |
| 52 | DIAG | sound_movement_binding | - | request_verification | - | evidence_unresolved | None | None |  |
| 53 | DIAG | sound_movement_binding | - | request_verification | - | evidence_unresolved | None | None |  |
| 54 | DIAG | sound_movement_binding | single_choice | coverage | - | wrong | B | A | During the action of lining the roasting tray, a metal or wood collision sound is heard. Which of the followin |

## L3 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | Before the mushrooms are sliced and placed into the mixing bowl, what was done to them? |
| 2 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | Before the water running sound starts again, what had been done to the tap? |
| 3 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | Before the second batch of mushrooms is washed under the tap, what was done with the first batch? |
| 4 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | Before the second batch of mushrooms is washed under the tap, what had been done to the tap? |
| 5 | DIAG | cross_event_integration | short_answer | coverage | - | correct | They were washed and placed on | They were washed and placed on | Before the chopping sound is heard, what was done to the mushrooms? |
| 6 | DIAG | cross_event_integration | short_answer | coverage | - | correct | On the cutting board | on the cutting board | Before the mushrooms are sliced and placed into the mixing bowl, where were they placed? |
| 7 | DIAG | hidden_state_inference | single_choice | coverage | - | correct | B | B | While the first packet of mushrooms is opened, what is the state of the oven? |
| 8 | DIAG | spatial_state_integration | - | request_verification | - | evidence_unresolved | None | None |  |
| 9 | DIAG | spatial_state_integration | - | request_verification | - | evidence_unresolved | None | None |  |
| 10 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | correct | C | C | Which of the following had to happen to the mushrooms before they could be sliced? |

## L4 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | goal_conditioned_planning | single_choice | coverage | - | item_invalid | None | A | What is the next step the person will take for the task they are doing? |
| 2 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | A | A | What is the next step the person will take for the task they are doing? |
| 3 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | C | C | What is the next step the person will take for the task they are doing? |
| 4 | DIAG | goal_conditioned_planning | plan | coverage | - | wrong | ['Open the second packet of mu | 1. Open the second package of  | What are the remaining stages, in order, for the task the camera wearer is doing? |
| 5 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | A | A | What is the next step the person will take for the task they are doing? |
| 6 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | C | C | What is the next step the person will take for the task they are doing? |

## Gemini 用量

| role | calls | errors | tok_in | tok_out | tok_think |
|---|---|---|---|---|---|
| examiner | 111 | 0 | 4583116 | 67149 | 453279 |
| judge | 17 | 0 | 6177 | 1728 | 3888 |
| scope | 1 | 0 | 1838 | 3952 | 8975 |
| solver | 261 | 0 | 1410081 | 4615 | 0 |
