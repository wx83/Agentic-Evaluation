# pyramid2 run `p2_hdepicE_1023t_g4_v17_self__05`

dataset hdepic_e · videos 1 · examiner `gcp/google/gemini-3.1-pro-preview` · solver `gcp/google/gemini-4-argon` · n_per_layer 200 · seed 1023 · prompt physical-mental-draft2-hdepic-e+v16sg

**结果为 provisional**:gold = Examiner 的 proposed_reference_answer,未经人工核验;open/plan 题由 Gemini judge 判。

## 每层概览

| layer | stop | turns | scored | correct | raw acc | cluster-dedup acc | follow-up | invalid/unresolved | confirmation |
|---|---|---|---|---|---|---|---|---|---|
| L1 | EVENT_LOOP_COMPLETE | 19 | 19 | 10 | 0.526 | 0.526 | 0 | 0/0 | - |
| L2 | EVENT_LOOP_COMPLETE | 43 | 43 | 39 | 0.907 | 0.907 | 0 | 0/0 | - |
| L3 | EVENT_LOOP_COMPLETE | 9 | 9 | 7 | 0.778 | 0.778 | 0 | 0/0 | - |
| L4 | STAIRCASE_COMPLETE | 3 | 3 | 3 | 1.0 | 1.0 | 0 | 0/0 | - |

## 每层 × skill 诊断结论

| layer | skill | verdict | scored | correct | clusters | first-try correct | supported hypotheses | confirmation |
|---|---|---|---|---|---|---|---|---|
| L1 | spatial_near | boundary 1.0 | 1 | 1 | 1 |  | - | - |
| L1 | spatial_side | boundary 1.0 | 1 | 0 | 1 |  | - | - |
| L1 | object_recognition | boundary 2.5 | 9 | 8 | 9 |  | - | - |
| L1 | object_location_at_time | boundary 1.5 | 2 | 0 | 2 |  | - | - |
| L1 | object_grounding | boundary<1 | 6 | 1 | 6 |  | - | - |
| L2 | sound_action_binding | boundary>=4 | 9 | 9 | 9 |  | - | - |
| L2 | object_state_change | boundary 2.0 | 2 | 2 | 2 |  | - | - |
| L2 | action_temporal_order | boundary 2.5 | 9 | 7 | 9 |  | - | - |
| L2 | action_recognition | boundary>=4 | 9 | 9 | 9 |  | - | - |
| L2 | event_object_role | boundary>=4 | 9 | 8 | 9 |  | - | - |
| L2 | sound_anchored_spatial_near | boundary 1.0 | 1 | 1 | 1 |  | - | - |
| L2 | sound_anchored_spatial_side | boundary 1.0 | 1 | 0 | 1 |  | - | - |
| L2 | sound_movement_binding | boundary 2.5 | 3 | 3 | 3 |  | - | - |
| L3 | cross_event_integration | boundary 3.5 | 7 | 6 | 7 |  | - | - |
| L3 | hidden_state_inference | boundary 1.0 | 1 | 0 | 1 |  | - | - |
| L3 | spatial_state_integration | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | causal_prerequisite_reasoning | boundary 1.0 | 1 | 1 | 1 |  | - | - |
| L4 | goal_conditioned_planning | boundary 3.5 | 3 | 3 | 3 |  | - | - |

## L1 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | spatial_near | single_choice | coverage | - | correct | C | C | At the start of the clip, when the plastic measuring jug is placed on the counter, which of the following obje |
| 2 | DIAG | spatial_side | single_choice | coverage | - | wrong | B | C | At the start of the clip, when the measuring jug is placed on the counter, from the camera wearer's own viewpo |
| 3 | DIAG | object_recognition | single_choice | coverage | - | correct | B | B | About 5 seconds into the clip, when the camera wearer picks up an object from the countertop using the right h |
| 4 | DIAG | object_location_at_time | single_choice | coverage | - | wrong | B | A | About 8 seconds into the clip, when the camera wearer puts down the small metallic tumbler, where is it placed |
| 5 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.8009999999999999, 0.861, 0. | 56.4, 54.7, 65.0, 66.2 | At the start of the clip, when the measuring jug is placed on the counter, what is the bounding box of the pla |
| 6 | DIAG | object_recognition | single_choice | coverage | - | correct | B | B | About 1 second into the clip, when the camera wearer pulls out an object using the right hand to create space, |
| 7 | DIAG | object_location_at_time | single_choice | coverage | - | wrong | B | A | About 5 seconds into the clip, when the camera wearer puts down the water cooler's drip tray, where is it plac |
| 8 | DIAG | object_grounding | bbox | coverage | - | correct | [0.55, 0.53, 0.66, 0.62] | 53.5, 55.6, 65.1, 65.8 | At the start of the clip, when the sound of water running and splashing into the jug is heard, what is the bou |
| 9 | DIAG | object_recognition | single_choice | coverage | - | wrong | B | C | About 6 seconds into the clip, when the camera wearer positions an object under the nozzle to fill it with wat |
| 10 | DIAG | object_recognition | single_choice | coverage | - | correct | B | B | About 1 second into the clip, when the camera wearer tips an object over the pressure cooker to transfer water |
| 11 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.635, 0.562, 0.976, 0.681] | 48.9, 61.7, 71.8, 69.6 | At the start of the clip, when the camera wearer picks up the wooden spatula from the pressure cooker, what is |
| 12 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | About 3 seconds into the clip, when the camera wearer squeezes an object over the spoon, which object is squee |
| 13 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | At the end of the clip, while the liquid and masala in the pressure cooker are stirred with a spatula, which o |
| 14 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | About 6 seconds into the clip, when the stove knob is turned to adjust the heat, which object is pressed using |
| 15 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.604, 0.587, 0.725, 0.652] | 67.4, 67.5, 80.2, 78.3 | At the start of the clip, when the wooden spatula is put down back in the pressure cooker, what is the boundin |
| 16 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | About 4 seconds into the clip, when the camera wearer shakes an object over the pressure cooker, which object  |
| 17 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.448, 0.569, 0.681, 0.747] | 53.0, 57.3, 81.7, 76.2 | At the start of the clip, while the contents of the pressure cooker are stirred with a wooden spatula, what is |
| 18 | DIAG | object_recognition | single_choice | coverage | - | correct | C | C | At the start of the clip, when the rice and masala are gently mixed together, which object is held in the righ |
| 19 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.18, 0.53, 0.3, 0.66] | 16.6, 67.5, 31.0, 83.4 | At the start of the clip, when the rice and masala are gently mixed together, what is the bounding box of the  |

## L2 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | Which action produced the clattering sound of hard materials colliding heard in the clip? |
| 2 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | When the measuring jug is placed down, where is it put? |
| 3 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | In the clip, what does the camera wearer do immediately after picking up the tumbler from the countertop? |
| 4 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | What action involving the measuring jug and the counter is observed in the clip? |
| 5 | DIAG | event_object_role | single_choice | coverage | - | wrong | B | A | Which object is taken out of the cabinet and placed on the counter? |
| 6 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | correct | C | C | When the sound of something opening or closing is heard in the clip, which of the following objects is nearest |
| 7 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | wrong | D | B | When the measuring jug is placed on the counter, a sound of metal and plastic colliding is heard. At the momen |
| 8 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | Which of the following movements produced the sound of metal and plastic colliding heard in the clip? |
| 9 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | correct | A | A | Which action produced the electronic beep sounds heard in the clip? |
| 10 | DIAG | object_state_change | single_choice | same_skill_new_event | - | correct | A | A | When the water cooler's drip tray is removed, where is it put down? |
| 11 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | A | A | In the clip, what does the camera wearer do immediately after pressing the button on the water cooler to stop  |
| 12 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | A | A | When the sound of water is first heard in the clip, what action is the camera wearer performing with the metal |
| 13 | DIAG | event_object_role | single_choice | same_skill_new_event | - | correct | A | A | When the sound of water running is heard in the clip, which object is the camera wearer holding in their right |
| 14 | DIAG | sound_movement_binding | single_choice | same_skill_new_event | - | correct | C | C | Which of the following movements produced the sound of metal and plastic colliding heard in the clip? |
| 15 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | In the clip, the sound of water is heard multiple times. Which action produced the second sound of water heard |
| 16 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | A | A | In the clip, what does the camera wearer do immediately before the first time water is poured from the tumbler |
| 17 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | A | A | In the clip, what action does the camera wearer perform to add water to the measuring jug for the first time? |
| 18 | DIAG | event_object_role | single_choice | coverage | - | correct | B | B | In the clip, when the camera wearer tips the tumbler to pour water, into which object is the water poured? |
| 19 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | In the clip, the sound of water is heard multiple times. Which of the following object movements produced the  |
| 20 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | correct | A | A | In the clip, a distinct sound of water is heard for several seconds. Which action produced this sound? |
| 21 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | wrong | B | A | In the clip, what does the camera wearer do immediately before pouring water from the measuring jug into the p |
| 22 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | A | A | In the clip, what action involving the measuring jug is observed? |
| 23 | DIAG | event_object_role | single_choice | same_skill_new_event | - | correct | A | A | In the clip, when the camera wearer pours water, from which object is the water poured? |
| 24 | DIAG | sound_action_binding | short_answer | coverage | - | correct | taking the spoon from the plat | picking up the spoon from the  | In the clip, lemon juice is squeezed from a lemon half into the pressure cooker. A ceramic collision sound is  |
| 25 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | A | A | In the clip, what does the camera wearer do immediately after squeezing the lemon for the first time? |
| 26 | DIAG | action_recognition | short_answer | coverage | - | correct | Squeezes juice from it | squeezing it | In the clip, what action does the camera wearer perform with the lemon half while holding the spoon below it? |
| 27 | DIAG | event_object_role | single_choice | same_skill_new_event | - | correct | A | A | In the clip, when the camera wearer squeezes the lemon half, into which object is the juice directly squeezed? |
| 28 | DIAG | sound_action_binding | short_answer | coverage | - | correct | Stirring the liquid and masala | stirring the liquid and masala | In the clip, a continuous scraping and mixing sound is heard. What action involving the pressure cooker and a  |
| 29 | DIAG | action_temporal_order | single_choice | coverage | - | correct | B | B | In the clip, what does the camera wearer do immediately after stirring the contents of the pressure cooker for |
| 30 | DIAG | action_recognition | short_answer | same_skill_new_event | - | correct | Stirring the liquid and masala | Stirring the contents of the p | In the clip, what continuous action does the camera wearer perform using the wooden spatula? |
| 31 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | In the clip, when the camera wearer stirs the contents of the pressure cooker, which object is used as the sti |
| 32 | DIAG | sound_action_binding | short_answer | coverage | - | correct | Pressing the buttons on the st | Pressing the buttons on the st | In the clip, electronic beep sounds are heard. What action is performed on the stove to adjust the heat that p |
| 33 | DIAG | action_temporal_order | single_choice | coverage | - | wrong | B | A | In the clip, the stove knob is turned to adjust the heat. What does the camera wearer do immediately after thi |
| 34 | DIAG | action_recognition | short_answer | same_skill_new_event | - | correct | Presses the minus button on th | Pressing the buttons on the el | In the clip, what action does the camera wearer perform to adjust the heat? |
| 35 | DIAG | event_object_role | single_choice | same_skill_new_event | - | correct | A | A | In the clip, the camera wearer adjusts the heat. Which part of the stove do they interact with to do this? |
| 36 | DIAG | sound_action_binding | short_answer | same_skill_new_event | - | correct | pouring the bowl of basmati ri | Pouring basmati rice from a bo | In the clip, a pouring sound is heard. What action produces this sound? |
| 37 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | A | A | In the clip, what does the camera wearer do immediately before pouring the basmati rice into the pressure cook |
| 38 | DIAG | action_recognition | short_answer | same_skill_new_event | - | correct | Pours the rice into the pressu | Pours the rice into the pressu | In the clip, what action does the camera wearer perform with the bowl of basmati rice after picking it up from |
| 39 | DIAG | event_object_role | short_answer | same_skill_new_event | - | correct | pressure cooker | pressure cooker | In the clip, when the camera wearer pours the basmati rice, into which object is it poured? |
| 40 | DIAG | sound_action_binding | short_answer | same_skill_new_event | - | correct | Gently mixing the rice and mas | Stirring the contents of the p | In the clip, continuous stirring and mixing sounds are heard. What action does the camera wearer perform that  |
| 41 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | A | A | In the clip, what does the camera wearer do immediately after stirring the contents of the pressure cooker for |
| 42 | DIAG | action_recognition | short_answer | same_skill_new_event | - | correct | Gently mixes the rice and masa | Stirring the contents of the p | In the clip, what continuous action does the camera wearer perform using the wooden spatula? |
| 43 | DIAG | event_object_role | short_answer | same_skill_new_event | - | correct | wooden spatula | wooden spatula | In the clip, when the camera wearer gently mixes the rice and masala together, which object is used as the mix |

## L3 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | Before water is poured into the measuring jug, what was done to the jug? |
| 2 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | When water is poured from the tumbler, which container is it poured into? |
| 3 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | Before water is poured from the measuring jug into the pressure cooker, how was the jug filled with water? |
| 4 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | correct | B | B | Where did the water being poured into the pressure cooker come from? |
| 5 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | When the lemon is squeezed, what liquid is already in the pressure cooker? |
| 6 | DIAG | cross_event_integration | short_answer | coverage | - | wrong | Rice | lemon juice | Before the contents of the pressure cooker are stirred with the wooden spatula, what was the last ingredient a |
| 7 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | Before the basmati rice is poured into the pressure cooker, what was done to the contents of the cooker? |
| 8 | DIAG | hidden_state_inference | single_choice | coverage | - | wrong | B | A | When the basmati rice is poured into the pressure cooker, what is the heat level of the stove? |
| 9 | DIAG | cross_event_integration | single_choice | coverage | - | correct | B | B | When the contents of the pressure cooker are mixed with the wooden spatula, what ingredient is being coated wi |

## L4 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | C | C | For the task the camera wearer is doing, what is the next step after the clip ends? |
| 2 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | C | C | For the task the camera wearer is doing, what is the next step after the clip ends? |
| 3 | DIAG | goal_conditioned_planning | plan | coverage | - | correct | ['Add the drained basmati rice | 1. Put the basmati rice into t | For the task the camera wearer is doing, what are the remaining stages, in order? |

## Gemini 用量

| role | calls | errors | tok_in | tok_out | tok_think |
|---|---|---|---|---|---|
| examiner | 85 | 0 | 2276867 | 53306 | 273031 |
| judge | 24 | 0 | 7849 | 1481 | 4533 |
| solver | 222 | 0 | 2097897 | 3994 | 0 |
