# pyramid2 run `p2_hdepicE_1023t_g4_v16_goldlive__24`

dataset hdepic_e · videos 1 · examiner `gcp/google/gemini-3.1-pro-preview` · solver `gcp/google/gemini-4-argon` · n_per_layer 200 · seed 1023 · prompt physical-mental-draft2-hdepic-e+v16sg

**结果为 provisional**:gold = Examiner 的 proposed_reference_answer,未经人工核验;open/plan 题由 Gemini judge 判。

## 每层概览

| layer | stop | turns | scored | correct | raw acc | cluster-dedup acc | follow-up | invalid/unresolved | confirmation |
|---|---|---|---|---|---|---|---|---|---|
| L1 | STAIRCASE_COMPLETE | 26 | 25 | 17 | 0.68 | 0.667 | 0 | 1/0 | - |
| L2 | STAIRCASE_COMPLETE | 45 | 42 | 34 | 0.81 | 0.872 | 0 | 0/3 | - |
| L3 | STAIRCASE_COMPLETE | 10 | 8 | 8 | 1.0 | 1.0 | 0 | 0/2 | - |
| L4 | STAIRCASE_COMPLETE | 5 | 5 | 4 | 0.8 | 0.8 | 0 | 0/0 | - |

## 每层 × skill 诊断结论

| layer | skill | verdict | scored | correct | clusters | first-try correct | supported hypotheses | confirmation |
|---|---|---|---|---|---|---|---|---|
| L1 | spatial_near | boundary 1.5 | 1 | 0 | 1 |  | - | - |
| L1 | spatial_side | boundary 3.5 | 2 | 2 | 2 |  | - | - |
| L1 | object_recognition | boundary>=4 | 9 | 8 | 8 |  | - | - |
| L1 | object_location_at_time | boundary 1.5 | 5 | 3 | 5 |  | - | - |
| L1 | object_grounding | boundary<1 | 8 | 4 | 8 |  | - | - |
| L2 | sound_action_binding | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | object_state_change | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | action_temporal_order | boundary 3.5 | 7 | 6 | 7 |  | - | - |
| L2 | action_recognition | boundary 3.5 | 8 | 7 | 8 |  | - | - |
| L2 | event_object_role | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | sound_anchored_spatial_near | boundary<1 | 2 | 0 | 1 |  | - | - |
| L2 | sound_anchored_spatial_side | boundary<1 | 4 | 1 | 2 |  | - | - |
| L2 | sound_movement_binding | boundary 1.5 | 3 | 2 | 3 |  | - | - |
| L3 | cross_event_integration | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L3 | hidden_state_inference | boundary 2.0 | 1 | 1 | 1 |  | - | - |
| L3 | spatial_state_integration | not_started | 0 | 0 | 0 |  | - | - |
| L3 | causal_prerequisite_reasoning | boundary 2.0 | 1 | 1 | 1 |  | - | - |
| L4 | goal_conditioned_planning | boundary 3.25 | 5 | 4 | 5 |  | - | - |

## L1 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | spatial_near | single_choice | coverage | - | wrong | A | B | About 6 seconds into the clip, when the packets of mushrooms are placed on the counter, which of the following |
| 2 | DIAG | spatial_side | single_choice | coverage | - | correct | B | B | About 8 seconds into the clip, when the packets of mushrooms are placed on the counter, from the camera wearer |
| 3 | DIAG | spatial_side | single_choice | coverage | - | correct | C | C | About 9 seconds into the clip, when the edges of the foil are folded using both hands, from the camera wearer' |
| 4 | DIAG | spatial_side | single_choice | coverage | - | item_invalid | None | C | About 9 seconds into the clip, when the foil is placed onto the baking tray, from the camera wearer's own view |
| 5 | DIAG | object_recognition | single_choice | coverage | - | wrong | D | A | At the start of the clip, when an object is grabbed from the side of the cupboard using the right hand, which  |
| 6 | DIAG | object_recognition | single_choice | coverage | - | correct | C | C | About 4 seconds into the clip, when the oven is turned on and set to the correct temperature using the right h |
| 7 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | About 2 seconds into the clip, when an object is placed down onto the countertop using the right hand, which o |
| 8 | DIAG | object_recognition | single_choice | coverage | - | correct | B | B | About 4 seconds into the clip, before the water running sound stops, when an object is picked up from the punn |
| 9 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | About 7 seconds into the clip, when an object is picked out from the punnet using the left hand, which object  |
| 10 | DIAG | object_recognition | single_choice | coverage | - | correct | C | C | About 4 seconds into the clip, before the water running sound stops, when an object is placed in the draining  |
| 11 | DIAG | object_recognition | single_choice | coverage | - | correct | B | B | At the start of the clip, when the mushrooms are sliced, which object is held in the right hand? |
| 12 | DIAG | object_recognition | short_answer | coverage | - | correct | the knife | chef's knife | About 9 seconds into the clip, when the mushroom is sliced, which object is held in the right hand? |
| 13 | DIAG | object_recognition | short_answer | coverage | - | correct | container | Tupperware box | About 6 seconds into the clip, when an object is placed back in the fridge using the left hand, which object i |
| 14 | DIAG | object_location_at_time | single_choice | coverage | - | wrong | B | A | About 5 seconds into the clip, when the water running sound is heard, where is the mushroom placed? |
| 15 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 8 seconds into the clip, when the packet of mushrooms is placed down using the left hand, where is it pl |
| 16 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 9 seconds into the clip, when the foil is placed down, where is it placed? |
| 17 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 4 seconds into the clip, after the water running sound starts, where is the mushroom placed? |
| 18 | DIAG | object_location_at_time | single_choice | coverage | - | wrong | B | A | About 3 seconds into the clip, when the washed mushroom is placed down, where is it placed? |
| 19 | DIAG | object_grounding | bbox | coverage | - | correct | [0.406, 0.513, 0.621, 0.704] | 41.5, 50.3, 59.5, 65.8 | In the first frame of the clip, what is the bounding box of the tupperware? |
| 20 | DIAG | object_grounding | bbox | coverage | - | correct | [0.547, 0.565, 0.697, 0.745] | 53.8, 54.4, 68.4, 73.7 | In the first frame of the clip, when the first packet of mushrooms is opened, what is the bounding box of the  |
| 21 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.517, 0.452, 0.681, 0.65] | 29.2, 46.2, 47.9, 58.8 | In the first frame of the clip, before the packets of mushrooms are placed on the counter near the end of the  |
| 22 | DIAG | object_grounding | bbox | coverage | - | correct | [0.517, 0.569, 0.736, 0.774] | 47.0, 59.1, 71.5, 79.0 | In the first frame of the clip, just before the second packet of mushrooms is opened, what is the bounding box |
| 23 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.47, 0.56, 0.71, 0.69] | 43.9, 53.0, 75.2, 73.2 | In the first frame of the clip, when the second packet of mushrooms is opened, what is the bounding box of the |
| 24 | DIAG | object_grounding | bbox | coverage | - | correct | [0.4, 0.56, 0.65, 0.83] | 34.2, 57.4, 66.5, 86.2 | In the first frame of the clip, what is the bounding box of the washing up bowl? |
| 25 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.48, 0.39, 0.71, 0.61] | 0.9, 32.3, 29.9, 55.2 | In the first frame of the clip, when the packets of mushrooms are placed on the counter, what is the bounding  |
| 26 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.681, 0.396, 1.0, 0.747] | 54.2, 51.5, 95.2, 88.7 | In the first frame of the clip, what is the bounding box of the sheet of foil? |

## L2 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | sound_action_binding | single_choice | coverage | - | correct | B | B | When the cutting board is retrieved and placed on the counter, which action produces a mixed metallic and plas |
| 2 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when the foil is placed onto the baking tray and adjusted, which a |
| 3 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, which action initiates the continuous sound of running water? |
| 4 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, which action causes the continuous sound of running water to stop? |
| 5 | DIAG | sound_action_binding | short_answer | coverage | - | correct | Turning on the tap | turning on the tap | During the task the camera wearer is doing, when the water running sound starts, what action is the camera wea |
| 6 | DIAG | sound_action_binding | short_answer | coverage | - | correct | Slicing the mushrooms | slicing the mushrooms | During the task the camera wearer is doing, what action produces the chopping sound? |
| 7 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when the packets of mushrooms are taken out of the fridge, where a |
| 8 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when the foil is placed onto the baking tray, where was the packet |
| 9 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when the first packet of mushrooms is opened, where is the punnet  |
| 10 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when the washed mushrooms are placed down, where are they placed? |
| 11 | DIAG | object_state_change | short_answer | coverage | - | correct | The punnet in the sink | sink | During the task the camera wearer is doing, when the water running sound starts, where are the mushrooms moved |
| 12 | DIAG | object_state_change | short_answer | coverage | - | correct | On the cutting board | On the cutting board | During the task the camera wearer is doing, when the washed mushrooms are placed down, where are they placed? |
| 13 | DIAG | action_temporal_order | single_choice | coverage | - | correct | C | C | During the task the camera wearer is doing, when the packet of mushrooms is retrieved from the vegetable drawe |
| 14 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when the foil is handled and the oven is turned on, in what order  |
| 15 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when the first packet of mushrooms is opened and the tap is turned |
| 16 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, in what order do the following actions occur? |
| 17 | DIAG | action_temporal_order | short_answer | coverage | - | wrong | moves the mushrooms on the cut | Adjust the cutting board | During the task the camera wearer is doing, what action does the camera wearer perform immediately before the  |
| 18 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, in what order do the following actions occur? |
| 19 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when the first mushroom shown in the clip is processed, in what or |
| 20 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, what does the camera wearer do with the packet of mushrooms after  |
| 21 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, what does the camera wearer do with the piece of foil after tearin |
| 22 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, what does the camera wearer do with the plastic packaging immediat |
| 23 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when the water running sound stops, what action does the camera we |
| 24 | DIAG | action_recognition | short_answer | coverage | - | correct | rips open the plastic packagin | Opens it | During the task the camera wearer is doing, what action does the camera wearer perform on the packet of mushro |
| 25 | DIAG | action_recognition | short_answer | coverage | - | wrong | transfers the mushrooms to the | shakes the mushrooms | During the task the camera wearer is doing, immediately after turning off the tap, what action does the camera |
| 26 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, what action does the camera wearer perform on the mushrooms on the |
| 27 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, what action does the camera wearer perform to empty the large mixi |
| 28 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when the cutting board is placed down, what surface is it placed o |
| 29 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when the torn-off piece of foil is placed down and smoothed out, w |
| 30 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when the first packet of mushrooms is opened, what is pulled out o |
| 31 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when the washed mushrooms are placed down, what surface are they p |
| 32 | DIAG | event_object_role | short_answer | coverage | - | correct | The mushroom punnet | the punnet | During the task the camera wearer is doing, when the packet of mushrooms is opened, what is the packaging pull |
| 33 | DIAG | event_object_role | short_answer | coverage | - | correct | cutting board | The cutting board | During the task the camera wearer is doing, when the washed mushrooms are placed down, what surface are they p |
| 34 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | wrong | B | A | During the task the camera wearer is doing, when the packets of mushrooms are placed on the counter, at the mo |
| 35 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | wrong | D | B | During the task the camera wearer is doing, when the packets of mushrooms are placed on the counter, at the mo |
| 36 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when the packets of mushrooms are placed on the counter, at the mo |
| 37 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | wrong | D | A | During the task the camera wearer is doing, when the oven is turned on, at the moment a metallic collision sou |
| 38 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | wrong | C | B | During the task the camera wearer is doing, when the packets of mushrooms are placed on the counter, at the mo |
| 39 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | wrong | D | A | During the task the camera wearer is doing, when the oven is turned on, at the moment a metal-only collision s |
| 40 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when the packets of mushrooms are retrieved and placed on the coun |
| 41 | DIAG | sound_movement_binding | single_choice | coverage | - | wrong | C | A | During the task the camera wearer is doing, when the baking tray is lined, which object's movement produces th |
| 42 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when the mushrooms are washed under the tap, which object's moveme |
| 43 | DIAG | sound_movement_binding | - | request_verification | - | evidence_unresolved | None | None |  |
| 44 | DIAG | sound_movement_binding | - | request_verification | - | evidence_unresolved | None | None |  |
| 45 | DIAG | sound_movement_binding | - | request_verification | - | evidence_unresolved | None | None |  |

## L3 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | cross_event_integration | single_choice | coverage | - | correct | B | B | Before the mushrooms are sliced and placed into the mixing bowl, what was done to them? |
| 2 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | A | A | When the water is turned on to wash the second batch of mushrooms, what had the camera wearer done to the tap  |
| 3 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | When the camera wearer washes mushrooms under the tap for the second time, what had they done with the first b |
| 4 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | A | A | When the camera wearer washes the second batch of mushrooms under the tap, what had they done to the tap earli |
| 5 | DIAG | cross_event_integration | short_answer | coverage | - | correct | On the cutting board | on the cutting board | Before the mushrooms are sliced, where had the camera wearer placed them? |
| 6 | DIAG | cross_event_integration | short_answer | same_skill_new_event | - | correct | On the cutting board | on the cutting board | Before the mushrooms are sliced and placed into the mixing bowl, where had the camera wearer placed them? |
| 7 | DIAG | hidden_state_inference | single_choice | coverage | - | correct | A | A | While the first packet of mushrooms is opened, what is the state of the oven? |
| 8 | DIAG | spatial_state_integration | - | request_verification | - | evidence_unresolved | None | None |  |
| 9 | DIAG | spatial_state_integration | - | request_verification | - | evidence_unresolved | None | None |  |
| 10 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | correct | A | A | What had to happen to the mushrooms before they could be sliced? |

## L4 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | B | B | What will the camera wearer do next to continue the task they are doing? |
| 2 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | B | B | What will the camera wearer do next to continue the task they are doing? |
| 3 | DIAG | goal_conditioned_planning | plan | coverage | - | wrong | ['Open the second packet of mu | 1. Open the second packet of m | What are the remaining stages, in order, for the task the camera wearer is doing? |
| 4 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | B | B | What will the camera wearer do next to continue the task they are doing? |
| 5 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | B | B | What will the camera wearer do next to continue the task they are doing? |

## Gemini 用量

| role | calls | errors | tok_in | tok_out | tok_think |
|---|---|---|---|---|---|
| examiner | 97 | 1 | 3859493 | 58895 | 389774 |
| judge | 15 | 0 | 5594 | 1675 | 4943 |
| solver | 240 | 0 | 1357656 | 4232 | 0 |
