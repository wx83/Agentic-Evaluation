# pyramid2 run `p2_hdepicE_1023t_g4_v16_self__05`

dataset hdepic_e · videos 1 · examiner `gcp/google/gemini-3.1-pro-preview` · solver `gcp/google/gemini-4-argon` · n_per_layer 200 · seed 1023 · prompt physical-mental-draft2-hdepic-e+v16sg

**结果为 provisional**:gold = Examiner 的 proposed_reference_answer,未经人工核验;open/plan 题由 Gemini judge 判。

## 每层概览

| layer | stop | turns | scored | correct | raw acc | cluster-dedup acc | follow-up | invalid/unresolved | confirmation |
|---|---|---|---|---|---|---|---|---|---|
| L1 | STAIRCASE_COMPLETE | 17 | 17 | 11 | 0.647 | 0.538 | 0 | 0/0 | - |
| L2 | STAIRCASE_COMPLETE | 41 | 41 | 31 | 0.756 | 0.8 | 0 | 0/0 | - |
| L3 | STAIRCASE_COMPLETE | 11 | 11 | 9 | 0.818 | 0.818 | 0 | 0/0 | - |
| L4 | STAIRCASE_COMPLETE | 3 | 3 | 3 | 1.0 | 1.0 | 0 | 0/0 | - |

## 每层 × skill 诊断结论

| layer | skill | verdict | scored | correct | clusters | first-try correct | supported hypotheses | confirmation |
|---|---|---|---|---|---|---|---|---|
| L1 | spatial_near | boundary 2.0 | 1 | 1 | 1 |  | - | - |
| L1 | spatial_side | boundary 1.5 | 1 | 0 | 1 |  | - | - |
| L1 | object_recognition | boundary>=4 | 10 | 9 | 6 |  | - | - |
| L1 | object_location_at_time | boundary<1 | 2 | 1 | 2 |  | - | - |
| L1 | object_grounding | boundary<1 | 3 | 0 | 3 |  | - | - |
| L2 | sound_action_binding | boundary>=4 | 9 | 8 | 7 |  | - | - |
| L2 | object_state_change | boundary 2.75 | 8 | 7 | 2 |  | - | - |
| L2 | action_temporal_order | boundary 2.5 | 5 | 4 | 5 |  | - | - |
| L2 | action_recognition | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | event_object_role | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | sound_anchored_spatial_near | boundary<1 | 2 | 0 | 1 |  | - | - |
| L2 | sound_anchored_spatial_side | boundary<1 | 2 | 0 | 1 |  | - | - |
| L2 | sound_movement_binding | boundary<1 | 3 | 0 | 2 |  | - | - |
| L3 | cross_event_integration | boundary 3.5 | 8 | 7 | 8 |  | - | - |
| L3 | hidden_state_inference | boundary<1 | 2 | 1 | 2 |  | - | - |
| L3 | spatial_state_integration | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | causal_prerequisite_reasoning | boundary 2.0 | 1 | 1 | 1 |  | - | - |
| L4 | goal_conditioned_planning | boundary 3.5 | 3 | 3 | 3 |  | - | - |

## L1 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | spatial_near | single_choice | coverage | - | correct | B | B | At the start of the clip (about 0.2 seconds in), when the measuring jug is placed, which of the following obje |
| 2 | DIAG | spatial_side | single_choice | coverage | - | wrong | B | C | At the start of the clip (about 0.2 seconds in), when the measuring jug is placed on the counter, from the cam |
| 3 | DIAG | object_recognition | single_choice | coverage | - | correct | C | C | About 4.5 seconds into the clip, when an object is picked up from the countertop using the right hand, which o |
| 4 | DIAG | object_recognition | single_choice | same_skill_new_event | - | wrong | A | B | About 4 seconds into the clip, when water is poured into the measuring jug, which object is used to pour the w |
| 5 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | About 0.5 seconds into the clip, when water is poured into the pressure cooker, which object is held under the |
| 6 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | At the start of the clip, when the contents of the pressure cooker are stirred, which object is used to stir? |
| 7 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | About 2.5 seconds into the clip, when the lemon is squeezed over the pressure cooker, which object is held bel |
| 8 | DIAG | object_recognition | single_choice | same_skill_new_event | - | correct | A | A | About 4.5 seconds into the clip, when an object is shaken over the pressure cooker, which object is shaken? |
| 9 | DIAG | object_recognition | single_choice | same_skill_new_event | - | correct | B | B | About 2.5 seconds into the clip, when an object is transferred from the right hand to the left hand, which obj |
| 10 | DIAG | object_recognition | single_choice | same_skill_new_event | - | correct | A | A | About 1 second into the clip, when an object is pulled out using the right hand, which object is handled? |
| 11 | DIAG | object_recognition | short_answer | coverage | - | correct | cabinet | open door of the upper cabinet | During the event where the measuring jug is placed on the counter, about 0.5 seconds into the clip, when the l |
| 12 | DIAG | object_recognition | short_answer | same_event_new_format | - | correct | a transparent pitcher | measuring jug | About 3 seconds into the clip, when an object is placed under the nozzle of the water cooler using the left ha |
| 13 | DIAG | object_location_at_time | single_choice | coverage | - | wrong | B | A | About 5.5 seconds into the clip, when the water cooler's drip tray is put down, where is it placed? |
| 14 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 0.5 seconds into the clip, when the measuring jug is placed, where is it put down? |
| 15 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.31, 0.73, 0.41, 0.82] | 33.2, 67.2, 45.3, 79.5 | Please provide the bounding box of the water cooler's drip tray in the first frame of the clip. |
| 16 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.61, 0.56, 1.0, 0.75] | 53.0, 57.3, 81.7, 76.2 | Please provide the bounding box of the pressure cooker in the first frame of the clip. |
| 17 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.19, 0.53, 0.32, 0.65] | 16.6, 67.5, 31.0, 83.4 | Please provide the bounding box of the bowl in the first frame of the clip. |

## L2 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | sound_action_binding | single_choice | coverage | - | wrong | B | A | Which action makes the sound of hard objects colliding heard in the clip? |
| 2 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | correct | B | B | Which action makes the beep sound heard in the clip? |
| 3 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | correct | C | C | Which action makes the sound of water heard in the clip? |
| 4 | DIAG | sound_action_binding | single_choice | coverage | - | correct | B | B | Which action makes the sound of ceramic objects colliding heard in the clip? |
| 5 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | Which action makes the continuous scraping sound heard in the clip? |
| 6 | DIAG | sound_action_binding | single_choice | coverage | - | correct | C | C | Which action makes the pouring sound heard in the clip? |
| 7 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | Which action makes the stirring sounds heard in the clip? |
| 8 | DIAG | sound_action_binding | short_answer | coverage | - | correct | closing the cabinet door | closing the cabinet door | During the event where 'The measuring jug is placed on the counter', what action makes the sound of something  |
| 9 | DIAG | sound_action_binding | short_answer | coverage | - | correct | Removing the water cooler's dr | pulling out the water cooler's | When preparing to place the measuring jug under the nozzle, what action makes the sound of metal and plastic c |
| 10 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | During the event where the measuring jug is placed on the counter, where was it moved from? |
| 11 | DIAG | object_state_change | single_choice | same_skill_new_event | - | correct | C | C | When the water cooler's drip tray is pulled out, where is it put down? |
| 12 | DIAG | object_state_change | single_choice | same_skill_new_event | - | correct | C | C | During the event where the tumbler is placed on the counter, where was it picked up from? |
| 13 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | During the event where the drip tray is put down next to the sink, where was it moved from? |
| 14 | DIAG | object_state_change | short_answer | same_event_new_format | - | correct | the cupboard | the cupboard | During the event where the measuring jug is placed on the counter, where was it moved from? |
| 15 | DIAG | object_state_change | short_answer | same_event_new_format | - | wrong | On the countertop. | next to the sink | When the water cooler's drip tray is pulled out, where is it put down? |
| 16 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | During the event where the measuring jug is pulled out from the cabinet, where is it placed? |
| 17 | DIAG | object_state_change | single_choice | coverage | - | correct | C | C | When the water cooler's drip tray is pulled out, where is it put down? |
| 18 | DIAG | action_temporal_order | single_choice | coverage | - | correct | B | B | Which action happens immediately before picking up the tumbler? |
| 19 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | A | A | Which action happens immediately before the first time water is poured into the measuring jug? |
| 20 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | wrong | D | B | Which action happens immediately before water is poured from the measuring jug into the pressure cooker? |
| 21 | DIAG | action_temporal_order | single_choice | coverage | - | correct | B | B | Which action happens immediately before the lemon is squeezed over the spoon for the first time? |
| 22 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | Which action happens immediately before the stove knob is turned to adjust the heat? |
| 23 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | What does the camera wearer do with the plastic measuring jug? |
| 24 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | A | A | When the camera wearer holds the metallic tumbler over the measuring jug, what do they do with it? |
| 25 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | A | A | When the camera wearer holds the measuring jug over the pressure cooker, what action do they perform with it? |
| 26 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | B | B | When the camera wearer holds the lemon half over the spoon, what do they do with it? |
| 27 | DIAG | action_recognition | short_answer | coverage | - | correct | Stir the contents inside the p | stirs the contents of the pres | When the camera wearer holds the handlebar of the pressure cooker with their left hand for support, what actio |
| 28 | DIAG | action_recognition | short_answer | same_skill_new_event | - | correct | Pours the basmati rice into th | Pour the rice into the pressur | After picking up the bowl of basmati rice from the wooden chopping board, what action does the camera wearer p |
| 29 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | When the camera wearer shakes the tumbler, which object is it shaken over? |
| 30 | DIAG | event_object_role | single_choice | same_skill_new_event | - | correct | A | A | When the camera wearer tips the tumbler to pour water, what object is the water poured into? |
| 31 | DIAG | event_object_role | single_choice | same_skill_new_event | - | correct | B | B | When the camera wearer tips the measuring jug to pour water, which object is the water poured into? |
| 32 | DIAG | event_object_role | single_choice | same_skill_new_event | - | correct | A | A | When the camera wearer squeezes the lemon half, which object is held directly underneath to catch the juice? |
| 33 | DIAG | event_object_role | short_answer | coverage | - | correct | a wooden spatula | wooden spatula | When the camera wearer stirs the contents of the pressure cooker, what tool do they use? |
| 34 | DIAG | event_object_role | short_answer | same_skill_new_event | - | correct | a pressure cooker | pressure cooker | When the camera wearer pours the basmati rice, what object is it poured into? |
| 35 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | wrong | B | A | During the event where the measuring jug is placed on the counter, when the sound of something closing is hear |
| 36 | DIAG | sound_anchored_spatial_near | single_choice | same_skill_cleaner_event | - | wrong | D | B | During the event where the measuring jug is placed on the counter, when the sound of something closing is hear |
| 37 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | wrong | B | C | During the event where the measuring jug is placed on the counter, when the sound of metal and plastic collidi |
| 38 | DIAG | sound_anchored_spatial_side | single_choice | same_skill_cleaner_event | - | wrong | D | A | During the event where the measuring jug is placed on the counter, when the sound of metal and plastic collidi |
| 39 | DIAG | sound_movement_binding | single_choice | coverage | - | wrong | B | A | During the event where the measuring jug is placed on the counter, which object's movement makes the sound of  |
| 40 | DIAG | sound_movement_binding | single_choice | same_skill_new_event | - | wrong | D | B | During the event where the sound of water running and splashing into the jug is heard, which object's movement |
| 41 | DIAG | sound_movement_binding | single_choice | same_skill_cleaner_event | - | wrong | B | A | During the event where the measuring jug is placed on the counter, a sound of metal and plastic colliding is h |

## L3 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | cross_event_integration | single_choice | coverage | - | correct | B | B | Where did the camera wearer previously place the container that the water from the tumbler is poured into? |
| 2 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | B | B | What liquid is poured into the pressure cooker before the lemon is squeezed? |
| 3 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | A | A | What was done to the ingredient that is being mixed with the masala using the spatula just before it was mixed |
| 4 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | A | A | Before water is heard running and splashing into it, what was done with the measuring jug? |
| 5 | DIAG | cross_event_integration | short_answer | same_skill_new_event | - | correct | It was dispensed into a metall | It was poured from a tumbler t | Before water is poured from the measuring jug into the pressure cooker, how did the water get into the measuri |
| 6 | DIAG | cross_event_integration | short_answer | same_skill_new_event | - | wrong | basmati rice | lemon juice | What is the last ingredient added to the pressure cooker before its contents are stirred and the heat on the h |
| 7 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | A | A | Just before the drained basmati rice is poured from the bowl into the pressure cooker, what was done to the co |
| 8 | DIAG | cross_event_integration | single_choice | coverage | - | correct | C | C | Which container is the water from the tumbler poured into? |
| 9 | DIAG | hidden_state_inference | single_choice | coverage | - | wrong | A | B | When the drained basmati rice is poured into the pressure cooker, what is the heat level of the electric hob? |
| 10 | DIAG | hidden_state_inference | single_choice | coverage | - | correct | B | B | When the drained basmati rice is poured into the pressure cooker, what is the heat level of the electric hob? |
| 11 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | correct | A | A | Where did the water being poured into the pressure cooker come from? |

## L4 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | C | C | What is the next step the person will take to continue the task they are doing? |
| 2 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | B | B | What is the next step the person will take to continue the task they are doing? |
| 3 | DIAG | goal_conditioned_planning | plan | coverage | - | correct | ['Add the drained basmati rice | 1. Add the basmati rice into t | List the remaining stages, in order, to complete the task the camera wearer is doing. |

## Gemini 用量

| role | calls | errors | tok_in | tok_out | tok_think |
|---|---|---|---|---|---|
| examiner | 81 | 1 | 2202801 | 49800 | 296185 |
| judge | 22 | 0 | 7187 | 1393 | 2923 |
| scope | 1 | 0 | 1672 | 2472 | 2432 |
| solver | 216 | 0 | 2353116 | 3621 | 0 |
