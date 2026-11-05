# pyramid2 run `p2_hdepicE_1023t_g4_v16_goldlive__44`

dataset hdepic_e · videos 1 · examiner `gcp/google/gemini-3.1-pro-preview` · solver `gcp/google/gemini-4-argon` · n_per_layer 200 · seed 1023 · prompt physical-mental-draft2-hdepic-e+v16sg

**结果为 provisional**:gold = Examiner 的 proposed_reference_answer,未经人工核验;open/plan 题由 Gemini judge 判。

## 每层概览

| layer | stop | turns | scored | correct | raw acc | cluster-dedup acc | follow-up | invalid/unresolved | confirmation |
|---|---|---|---|---|---|---|---|---|---|
| L1 | STAIRCASE_COMPLETE | 15 | 15 | 9 | 0.6 | 0.538 | 0 | 0/0 | - |
| L2 | STAIRCASE_COMPLETE | 41 | 41 | 38 | 0.927 | 0.938 | 0 | 0/0 | - |
| L3 | STAIRCASE_COMPLETE | 6 | 6 | 6 | 1.0 | 1.0 | 0 | 0/0 | - |
| L4 | STAIRCASE_COMPLETE | 2 | 2 | 2 | 1.0 | 1.0 | 0 | 0/0 | - |

## 每层 × skill 诊断结论

| layer | skill | verdict | scored | correct | clusters | first-try correct | supported hypotheses | confirmation |
|---|---|---|---|---|---|---|---|---|
| L1 | spatial_near | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L1 | spatial_side | boundary 1.5 | 1 | 0 | 1 |  | - | - |
| L1 | object_recognition | boundary>=4 | 6 | 6 | 5 |  | - | - |
| L1 | object_location_at_time | boundary 1.25 | 5 | 3 | 4 |  | - | - |
| L1 | object_grounding | boundary<1 | 3 | 0 | 3 |  | - | - |
| L2 | sound_action_binding | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | object_state_change | boundary>=4 | 6 | 6 | 4 |  | - | - |
| L2 | action_temporal_order | boundary 3.5 | 8 | 7 | 6 |  | - | - |
| L2 | action_recognition | boundary 3 | 9 | 7 | 6 |  | - | - |
| L2 | event_object_role | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | sound_anchored_spatial_near | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L2 | sound_anchored_spatial_side | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L2 | sound_movement_binding | boundary>=4 | 6 | 6 | 4 |  | - | - |
| L3 | cross_event_integration | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L3 | hidden_state_inference | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | spatial_state_integration | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | causal_prerequisite_reasoning | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L4 | goal_conditioned_planning | boundary 2.5 | 2 | 2 | 2 |  | - | - |

## L1 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | spatial_side | single_choice | coverage | - | wrong | A | C | At the start of the clip, when the ingredient is sliced open, from the camera wearer's own viewpoint at that m |
| 2 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | About 1 second into the clip, when thin vertical cuts are made into the avocado half, which tool is being used |
| 3 | DIAG | object_recognition | single_choice | same_skill_new_event | - | correct | A | A | About 9 seconds into the clip, when the remaining avocado is scooped out from the skin, which tool is being us |
| 4 | DIAG | object_recognition | single_choice | same_skill_new_event | - | correct | B | B | About 3 seconds into the clip, when Greek yoghurt is scooped into the canister, which tool is being used? |
| 5 | DIAG | object_recognition | single_choice | same_skill_new_event | - | correct | B | B | About 8 seconds into the clip, after the event where the lid is secured onto the canister, the camera wearer o |
| 6 | DIAG | object_recognition | short_answer | same_skill_new_event | - | correct | Flat leaf parsley | parsley | About 6 seconds into the clip, when an ingredient is added to the canister by scooping its last leaves out of  |
| 7 | DIAG | object_recognition | short_answer | coverage | - | correct | the lid of the jar | lid | About 4 seconds into the clip, during the event where the blender button is pressed to test the appliance, wha |
| 8 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 2 seconds into the clip, during the event where the blender is turned on to pulse the ingredients, where |
| 9 | DIAG | object_location_at_time | single_choice | same_skill_new_event | - | wrong | B | A | About 8 seconds into the clip, after the event where the blender button is pressed to test the appliance, wher |
| 10 | DIAG | object_location_at_time | single_choice | same_skill_new_event | - | correct | A | A | About 4 seconds into the clip, during the event where the garlic is prepared with a knife, where was the knife |
| 11 | DIAG | object_location_at_time | single_choice | same_skill_cleaner_event | - | correct | A | A | About 9 seconds into the clip, after the event where the blender button is pressed to test the appliance, wher |
| 12 | DIAG | object_location_at_time | single_choice | same_skill_new_event | - | wrong | B | A | About 3 seconds into the clip, when Greek yoghurt is scooped into the canister, where was the spoon picked up  |
| 13 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.047700000000000006, 0.7489, | 40.7, 90.4, 60.2, 99.7 | Please provide the bounding box of the blender jar in the first frame of the clip. |
| 14 | DIAG | object_grounding | bbox | same_skill_new_event | - | wrong | [0.32, 0.49, 0.41, 0.67] | 18.6, 64.4, 32.6, 78.8 | Please provide the bounding box of the blender jar in the first frame of the clip. |
| 15 | DIAG | object_grounding | bbox | same_skill_new_event | - | wrong | [0.78, 0.56, 0.94, 0.65] | 58.1, 42.9, 81.5, 59.8 | At the start of the clip, when parsley is added to the canister, please provide the bounding box of the bag of |

## L2 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | Which action produces the loud appliance motor sound heard in the clip? |
| 2 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | correct | C | C | Which action produces the sharp tapping sounds heard in the clip? |
| 3 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | correct | A | A | Which action produces the repeated metallic tapping sounds heard in the clip? |
| 4 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | correct | A | A | Which action produces the sound of running water heard in the clip? |
| 5 | DIAG | sound_action_binding | short_answer | coverage | - | correct | cutting the ends off the garli | slicing the garlic | When the garlic is prepared with a knife, what specific action produces the repeated chopping sounds? |
| 6 | DIAG | sound_action_binding | short_answer | coverage | - | correct | placing and locking the canist | placing the canister into the  | When the blender is turned on to pulse the ingredients, what specific action by the camera wearer produces the |
| 7 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | After testing the blender, the camera wearer carries the blender jar and the bag of avocados. Where are they p |
| 8 | DIAG | object_state_change | single_choice | same_skill_new_event | - | correct | B | B | When the camera wearer scoops the Greek yoghurt into the canister, where was the spoon they use taken from? |
| 9 | DIAG | object_state_change | single_choice | same_skill_new_event | - | correct | A | A | When the prepared garlic is added to the canister, where is it taken from? |
| 10 | DIAG | object_state_change | single_choice | same_skill_new_event | - | correct | A | A | When the camera wearer carries the plastic canister to blend the ingredients, where is it placed? |
| 11 | DIAG | object_state_change | short_answer | same_event_new_format | - | correct | on the cutting board | on the wooden chopping board | After testing the blender, the camera wearer carries the blender jar and the bag of avocados. Where are they p |
| 12 | DIAG | object_state_change | short_answer | same_event_new_format | - | correct | A drawer | the cutlery drawer | When the camera wearer scoops the Greek yoghurt into the canister, where was the spoon they use taken from? |
| 13 | DIAG | action_temporal_order | single_choice | coverage | - | correct | B | B | When the camera wearer cuts the avocado in half, which of the following actions do they perform immediately af |
| 14 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | B | B | When the camera wearer places the canister onto the scales, which of the following actions do they perform imm |
| 15 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | A | A | When the camera wearer scoops the first spoonful of Greek yoghurt into the canister, which of the following ac |
| 16 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | B | B | When the camera wearer taps the side of the plastic packet so that the parsley falls into the canister, which  |
| 17 | DIAG | action_temporal_order | short_answer | same_skill_new_event | - | correct | Peels the garlic | pull the outer skin off the cl | When the camera wearer slices the second end off the clove of garlic, what action do they perform immediately  |
| 18 | DIAG | action_temporal_order | short_answer | same_skill_new_event | - | wrong | Blend the ingredients | Twists the canister to turn on | When the camera wearer places the plastic canister face down into the blender base, what action do they perfor |
| 19 | DIAG | action_temporal_order | single_choice | coverage | - | correct | B | B | When the camera wearer presses the plastic canister into the blender base to test it, which of the following a |
| 20 | DIAG | action_temporal_order | single_choice | coverage | - | correct | B | B | When the camera wearer scoops the avocado flesh into the canister, which of the following actions do they perf |
| 21 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | When the camera wearer places the whole avocado down on the wooden chopping board, what action do they perform |
| 22 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | A | A | When the camera wearer holds the half chopped avocado in their left hand and the spoon in their right hand, wh |
| 23 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | B | B | When the camera wearer transfers the Greek yoghurt into the plastic canister, what action do they perform to e |
| 24 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | A | A | After scooping parsley out of the plastic packet by hand, what action does the camera wearer perform on the pa |
| 25 | DIAG | action_recognition | short_answer | coverage | - | correct | Cuts off the root end of the g | slice the ends off the garlic  | After moving debris off the chopping board with the knife, what action does the camera wearer perform? |
| 26 | DIAG | action_recognition | short_answer | coverage | - | wrong | pushing down on the canister | Twists the canister | After placing the plastic canister face down into the blender base, what action does the camera wearer perform |
| 27 | DIAG | action_recognition | single_choice | same_event_new_format | - | wrong | B | C | When the camera wearer places the plastic canister into the blender base to test it, what action do they perfo |
| 28 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | When the camera wearer adds the Greek yoghurt to the plastic canister, how do they transfer it from its origin |
| 29 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | B | B | When the camera wearer adds water to the plastic canister, what action do they perform to dispense the water? |
| 30 | DIAG | event_object_role | single_choice | coverage | - | correct | C | C | When the camera wearer cuts the avocado in half, what surface is the avocado resting on? |
| 31 | DIAG | event_object_role | single_choice | same_skill_new_event | - | correct | A | A | When the camera wearer scoops the avocado flesh into the canister, what tool do they use? |
| 32 | DIAG | event_object_role | single_choice | same_skill_new_event | - | correct | B | B | When the camera wearer scoops the Greek yoghurt out of its container, what object do they transfer it into? |
| 33 | DIAG | event_object_role | single_choice | same_skill_new_event | - | correct | A | A | When the camera wearer adds the parsley to the plastic canister, what type of container do they take the parsl |
| 34 | DIAG | event_object_role | short_answer | same_skill_new_event | - | correct | A knife | A knife | When the camera wearer slices the ends off the clove of garlic, what tool do they use? |
| 35 | DIAG | event_object_role | short_answer | coverage | - | correct | blender jar | The plastic canister | When the camera wearer sprinkles the salt, what container do they sprinkle it into? |
| 36 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | When the camera wearer cuts the avocado in half, which object's movement produces the chopping sounds? |
| 37 | DIAG | sound_movement_binding | single_choice | same_skill_new_event | - | correct | A | A | When the camera wearer scoops the Greek yoghurt into the canister, which object's movement produces the collis |
| 38 | DIAG | sound_movement_binding | single_choice | same_skill_new_event | - | correct | B | B | When the camera wearer prepares the garlic, which object's movement produces the chopping sounds? |
| 39 | DIAG | sound_movement_binding | single_choice | same_skill_new_event | - | correct | A | A | When the blender is turned on to pulse the ingredients, which object's movement produces the plastic collision |
| 40 | DIAG | sound_movement_binding | short_answer | same_event_new_format | - | correct | The serrated knife | the knife | When the camera wearer cuts the avocado in half, which object's movement produces the chopping sounds? |
| 41 | DIAG | sound_movement_binding | short_answer | same_event_new_format | - | correct | the spoon | The spoon | When the camera wearer scoops the Greek yoghurt into the canister, which object's movement produces the collis |

## L3 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | When the avocado is scooped into the canister, what was done to it earlier? |
| 2 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | B | B | When the yoghurt is scooped into the canister, what is already inside it? |
| 3 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | A | A | When the water is poured into the canister, which of these ingredients are already inside it? |
| 4 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | A | A | When the garlic is added to the canister, which of these ingredients is already inside it? |
| 5 | DIAG | cross_event_integration | short_answer | coverage | - | correct | a digital scale | the weighing scales | When the Greek yoghurt is scooped into the canister, what was the canister placed onto earlier? |
| 6 | DIAG | cross_event_integration | short_answer | same_skill_new_event | - | correct | Greek yoghurt | yoghurt | When the parsley is added to the canister, what ingredient was added to it immediately after the avocado? |

## L4 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | B | B | What is the next step the person should take to complete the task the camera wearer is doing? |
| 2 | DIAG | goal_conditioned_planning | single_choice | same_skill_new_event | - | correct | C | C | What is the next step the person should take to complete the task the camera wearer is doing? |

## Gemini 用量

| role | calls | errors | tok_in | tok_out | tok_think |
|---|---|---|---|---|---|
| examiner | 70 | 0 | 1948786 | 43887 | 256030 |
| judge | 15 | 0 | 4028 | 764 | 2073 |
| solver | 192 | 0 | 1083642 | 3182 | 0 |
