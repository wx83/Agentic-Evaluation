# pyramid2 run `p2_hdepicE_1023t_g4_v16_self__44`

dataset hdepic_e · videos 1 · examiner `gcp/google/gemini-3.1-pro-preview` · solver `gcp/google/gemini-4-argon` · n_per_layer 200 · seed 1023 · prompt physical-mental-draft2-hdepic-e+v16sg

**结果为 provisional**:gold = Examiner 的 proposed_reference_answer,未经人工核验;open/plan 题由 Gemini judge 判。

## 每层概览

| layer | stop | turns | scored | correct | raw acc | cluster-dedup acc | follow-up | invalid/unresolved | confirmation |
|---|---|---|---|---|---|---|---|---|---|
| L1 | STAIRCASE_COMPLETE | 14 | 10 | 7 | 0.7 | 0.625 | 0 | 0/4 | - |
| L2 | STAIRCASE_COMPLETE | 38 | 38 | 37 | 0.974 | 0.969 | 0 | 0/0 | - |
| L3 | STAIRCASE_COMPLETE | 8 | 8 | 7 | 0.875 | 0.875 | 0 | 0/0 | - |
| L4 | STAIRCASE_COMPLETE | 2 | 2 | 2 | 1.0 | 1.0 | 0 | 0/0 | - |

## 每层 × skill 诊断结论

| layer | skill | verdict | scored | correct | clusters | first-try correct | supported hypotheses | confirmation |
|---|---|---|---|---|---|---|---|---|
| L1 | spatial_near | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L1 | spatial_side | boundary 2.0 | 1 | 1 | 1 |  | - | - |
| L1 | object_recognition | boundary>=4 | 6 | 6 | 4 |  | - | - |
| L1 | object_location_at_time | not_started | 0 | 0 | 0 |  | - | - |
| L1 | object_grounding | boundary<1 | 3 | 0 | 3 |  | - | - |
| L2 | sound_action_binding | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | object_state_change | boundary>=4 | 6 | 6 | 4 |  | - | - |
| L2 | action_temporal_order | boundary 3.5 | 8 | 7 | 6 |  | - | - |
| L2 | action_recognition | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | event_object_role | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | sound_anchored_spatial_near | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L2 | sound_anchored_spatial_side | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L2 | sound_movement_binding | boundary>=4 | 6 | 6 | 4 |  | - | - |
| L3 | cross_event_integration | boundary 3.5 | 8 | 7 | 8 |  | - | - |
| L3 | hidden_state_inference | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | spatial_state_integration | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | causal_prerequisite_reasoning | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L4 | goal_conditioned_planning | boundary 2.5 | 2 | 2 | 2 |  | - | - |

## L1 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | spatial_side | single_choice | coverage | - | correct | B | B | At the moment when the ingredient is cut open, about 0.5 seconds into the clip, which of the following objects |
| 2 | DIAG | object_recognition | - | request_verification | - | evidence_unresolved | None | None |  |
| 3 | DIAG | object_recognition | single_choice | coverage | - | correct | C | C | During the event where the avocado flesh is scooped into the canister, about 9 seconds into the clip, which of |
| 4 | DIAG | object_recognition | single_choice | same_skill_new_event | - | correct | A | A | During the event where another spoonful of yoghurt is scooped and poured, about 8.5 seconds into the clip, whi |
| 5 | DIAG | object_recognition | single_choice | same_skill_new_event | - | correct | C | C | During the event where the lid is secured onto the canister, about 5 seconds into the clip, which of the follo |
| 6 | DIAG | object_recognition | single_choice | same_skill_new_event | - | correct | B | B | During the event where the canister is placed onto the scale, about 3.5 seconds into the clip, which of the fo |
| 7 | DIAG | object_recognition | short_answer | coverage | - | correct | the plastic bag | plastic packaging | During the event where the last leaves of parsley are pulled out and scooped, about 5.5 seconds into the clip, |
| 8 | DIAG | object_recognition | short_answer | coverage | - | correct | the scale | weighing scales | During the event where the canister is placed onto the scale, about 1 second into the clip, what object does t |
| 9 | DIAG | object_location_at_time | - | request_verification | - | evidence_unresolved | None | None |  |
| 10 | DIAG | object_location_at_time | - | request_verification | - | evidence_unresolved | None | None |  |
| 11 | DIAG | object_location_at_time | - | request_verification | - | evidence_unresolved | None | None |  |
| 12 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.057, 0.795, 0.224, 0.96] | 40.7, 90.4, 60.2, 99.7 | Please provide the bounding box for the blender jar in the first frame of the clip. |
| 13 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.316, 0.486, 0.392, 0.653] | 18.6, 64.4, 32.6, 78.8 | Please provide the bounding box for the blender jar in the first frame of the clip. |
| 14 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.059, 0.439, 0.071, 0.567] | 58.1, 42.9, 81.5, 59.8 | Please provide the bounding box for the bag of parsley in the first frame of the clip. |

## L2 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | sound_action_binding | single_choice | coverage | - | correct | C | C | Which action causes the loud appliance motor sound heard in the clip? |
| 2 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | correct | A | A | Which action causes the sharp tapping or knocking sounds heard in the clip? |
| 3 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | correct | B | B | Which action causes the series of hard clinking or tapping sounds heard in the clip? |
| 4 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | correct | A | A | Which action causes the splashing or running liquid sound heard in the clip? |
| 5 | DIAG | sound_action_binding | short_answer | coverage | - | correct | Cutting off the ends of the ga | slicing the ends off the garli | When the garlic is prepared with a knife, what action causes the chopping sounds? |
| 6 | DIAG | sound_action_binding | short_answer | coverage | - | correct | Inserting the canister into th | Placing the canister into the  | When the blender is turned on to pulse the ingredients, what action causes the plastic collision sound heard r |
| 7 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | After the blender button is pressed to test the appliance, where is the blender jar placed? |
| 8 | DIAG | object_state_change | single_choice | same_skill_new_event | - | correct | A | A | When the spoon is retrieved to scoop the yoghurt, where is it taken from? |
| 9 | DIAG | object_state_change | single_choice | same_skill_new_event | - | correct | A | A | When the garlic is prepared with a knife, where is the knife placed afterwards? |
| 10 | DIAG | object_state_change | single_choice | same_skill_new_event | - | correct | B | B | When the plastic canister is carried away from the counter after the salt is added, where is it placed? |
| 11 | DIAG | object_state_change | short_answer | coverage | - | correct | on the chopping board | On the wooden chopping board | After the blender button is pressed to test the appliance, where is the blender jar placed? |
| 12 | DIAG | object_state_change | short_answer | same_event_new_format | - | correct | The cutlery drawer | the cutlery drawer | When the spoon is retrieved to scoop the yoghurt, where is it taken from? |
| 13 | DIAG | action_temporal_order | single_choice | coverage | - | correct | B | B | What action does the camera wearer perform immediately after testing the blender by pressing the canister into |
| 14 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | A | A | What action does the camera wearer perform immediately after picking up the spoon? |
| 15 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | C | C | What action does the camera wearer perform immediately before scooping the first spoonful of yoghurt into the  |
| 16 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | B | B | What action does the camera wearer perform immediately after allowing water into the plastic canister? |
| 17 | DIAG | action_temporal_order | short_answer | coverage | - | correct | peels the skin off the clove o | pulling the outer skin off | What action does the camera wearer perform immediately after slicing both ends off the clove of garlic? |
| 18 | DIAG | action_temporal_order | short_answer | same_skill_new_event | - | wrong | adding salt into the blender j | places the plastic canister in | What action does the camera wearer perform immediately before turning on the blender? |
| 19 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | A | A | What action does the camera wearer perform immediately before cutting the avocado in half with the serrated kn |
| 20 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | C | C | What action does the camera wearer perform immediately after placing the plastic canister onto the weighing sc |
| 21 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | What action does the camera wearer perform on the whole avocado after placing it on the wooden chopping board? |
| 22 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | C | C | What action does the camera wearer perform with the spoon and the avocado half? |
| 23 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | A | A | What action does the camera wearer perform with the spoon and the greek yoghurt container? |
| 24 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | C | C | What action does the camera wearer perform with the parsley taken from the plastic packet? |
| 25 | DIAG | action_recognition | short_answer | coverage | - | correct | cuts the ends off with the kni | slices both ends off and peels | What actions does the camera wearer perform with the serrated knife and their hands to prepare the single clov |
| 26 | DIAG | action_recognition | short_answer | same_skill_new_event | - | correct | sprinkles it into the plastic  | sprinkles it into the plastic  | What action does the camera wearer perform with the salt taken from the salt pig? |
| 27 | DIAG | event_object_role | single_choice | coverage | - | correct | C | C | When the avocado is cut in half on the wooden chopping board, what tool is used? |
| 28 | DIAG | event_object_role | single_choice | same_skill_new_event | - | correct | A | A | When the avocado flesh is scooped out of its skin and into the plastic canister, what tool is used? |
| 29 | DIAG | event_object_role | single_choice | same_skill_new_event | - | correct | B | B | When the greek yoghurt is scooped out of its container and added to the plastic canister, what tool is used? |
| 30 | DIAG | event_object_role | single_choice | same_skill_new_event | - | correct | B | B | When the handfuls of parsley are taken out of the plastic packet, what container are they dropped into? |
| 31 | DIAG | event_object_role | short_answer | same_skill_new_event | - | correct | a knife | a knife | When the ends are sliced off the single clove of garlic, what tool is used? |
| 32 | DIAG | event_object_role | short_answer | same_skill_new_event | - | correct | the salt pig | a salt pig | When the pinches of salt are sprinkled into the plastic canister, what container are they taken from? |
| 33 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | When the avocado is prepared on the chopping board, which object's movement causes the chopping sounds? |
| 34 | DIAG | sound_movement_binding | single_choice | same_skill_new_event | - | correct | B | B | When the greek yoghurt is scooped into the canister, which object's movement causes the collision sounds? |
| 35 | DIAG | sound_movement_binding | single_choice | same_skill_new_event | - | correct | B | B | When the single clove of garlic is prepared, which object's movement causes the chopping sounds? |
| 36 | DIAG | sound_movement_binding | single_choice | same_skill_new_event | - | correct | A | A | When the blender is turned on to pulse the ingredients, which object's movement causes the plastic collision s |
| 37 | DIAG | sound_movement_binding | short_answer | same_event_new_format | - | correct | the knife | the knife | When the avocado is prepared on the chopping board, which object's movement causes the chopping sounds? |
| 38 | DIAG | sound_movement_binding | short_answer | same_event_new_format | - | correct | A spoon hitting the rim of the | the spoon | When the greek yoghurt is scooped into the canister, which object's movement causes the collision sounds? |

## L3 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | What is being scooped out of its skin and into the canister? |
| 2 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | C | C | What is already in the canister when the yoghurt is added? |
| 3 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | C | C | Which of the following ingredients is already in the canister when the water is poured? |
| 4 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | C | C | Which of the following is already in the canister when the garlic is added? |
| 5 | DIAG | cross_event_integration | short_answer | same_skill_new_event | - | correct | a weighing scale | the weighing scales | Before the Greek yoghurt is scooped into the canister, what is the canister placed onto? |
| 6 | DIAG | cross_event_integration | short_answer | coverage | - | wrong | water | yoghurt | What ingredient is added to the canister just before the parsley is added? |
| 7 | DIAG | cross_event_integration | single_choice | coverage | - | correct | B | B | Before the clove of garlic is thrown into the plastic canister, which of the following ingredients was poured  |
| 8 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | What is the last ingredient added to the canister before its lid is screwed on? |

## L4 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | C | C | For the task the camera wearer is doing, what is the next step after the clip ends? |
| 2 | DIAG | goal_conditioned_planning | single_choice | same_skill_new_event | - | correct | C | C | For the task the camera wearer is doing, what is the next step after the clip ends? |

## Gemini 用量

| role | calls | errors | tok_in | tok_out | tok_think |
|---|---|---|---|---|---|
| examiner | 69 | 1 | 1847296 | 41754 | 212776 |
| judge | 17 | 0 | 4626 | 841 | 2107 |
| scope | 1 | 0 | 1620 | 2894 | 1626 |
| solver | 174 | 0 | 1169400 | 2978 | 0 |
