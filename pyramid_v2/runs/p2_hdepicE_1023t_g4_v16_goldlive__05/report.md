# pyramid2 run `p2_hdepicE_1023t_g4_v16_goldlive__05`

dataset hdepic_e · videos 1 · examiner `gcp/google/gemini-3.1-pro-preview` · solver `gcp/google/gemini-4-argon` · n_per_layer 200 · seed 1023 · prompt physical-mental-draft2-hdepic-e+v16sg

**结果为 provisional**:gold = Examiner 的 proposed_reference_answer,未经人工核验;open/plan 题由 Gemini judge 判。

## 每层概览

| layer | stop | turns | scored | correct | raw acc | cluster-dedup acc | follow-up | invalid/unresolved | confirmation |
|---|---|---|---|---|---|---|---|---|---|
| L1 | STAIRCASE_COMPLETE | 18 | 18 | 13 | 0.722 | 0.615 | 0 | 0/0 | - |
| L2 | STAIRCASE_COMPLETE | 39 | 38 | 35 | 0.921 | 0.9 | 0 | 0/1 | - |
| L3 | STAIRCASE_COMPLETE | 9 | 9 | 6 | 0.667 | 0.667 | 0 | 0/0 | - |
| L4 | STAIRCASE_COMPLETE | 3 | 3 | 3 | 1.0 | 1.0 | 0 | 0/0 | - |

## 每层 × skill 诊断结论

| layer | skill | verdict | scored | correct | clusters | first-try correct | supported hypotheses | confirmation |
|---|---|---|---|---|---|---|---|---|
| L1 | spatial_near | boundary 2.0 | 1 | 1 | 1 |  | - | - |
| L1 | spatial_side | boundary 1.5 | 1 | 0 | 1 |  | - | - |
| L1 | object_recognition | boundary>=4 | 10 | 9 | 6 |  | - | - |
| L1 | object_location_at_time | boundary 3.5 | 3 | 3 | 2 |  | - | - |
| L1 | object_grounding | boundary<1 | 3 | 0 | 3 |  | - | - |
| L2 | sound_action_binding | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | object_state_change | boundary>=4 | 8 | 7 | 2 |  | - | - |
| L2 | action_temporal_order | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | action_recognition | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | event_object_role | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | sound_anchored_spatial_near | boundary 2.0 | 1 | 1 | 1 |  | - | - |
| L2 | sound_anchored_spatial_side | boundary<1 | 2 | 1 | 1 |  | - | - |
| L2 | sound_movement_binding | boundary 1.75 | 3 | 2 | 2 |  | - | - |
| L3 | cross_event_integration | boundary 2.5 | 6 | 5 | 6 |  | - | - |
| L3 | hidden_state_inference | boundary<1 | 2 | 0 | 2 |  | - | - |
| L3 | spatial_state_integration | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | causal_prerequisite_reasoning | boundary 2.0 | 1 | 1 | 1 |  | - | - |
| L4 | goal_conditioned_planning | boundary 3.5 | 3 | 3 | 3 |  | - | - |

## L1 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | spatial_near | single_choice | coverage | - | correct | C | C | At the start of the clip, when the measuring jug is placed on the counter, which of the following objects is n |
| 2 | DIAG | spatial_side | single_choice | coverage | - | wrong | D | C | At the start of the clip, when the measuring jug is placed on the counter, from the camera wearer's own viewpo |
| 3 | DIAG | object_recognition | single_choice | coverage | - | correct | B | B | About 5 seconds into the clip, when an object is picked up from the countertop using the right hand, which obj |
| 4 | DIAG | object_recognition | single_choice | coverage | - | wrong | B | A | About 4 seconds into the clip, when water is poured into the measuring jug, which object is tipped over the ju |
| 5 | DIAG | object_recognition | single_choice | coverage | - | correct | B | B | At the start of the clip, when water is poured from the measuring jug into the pressure cooker, which object i |
| 6 | DIAG | object_recognition | single_choice | coverage | - | correct | B | B | At the start of the clip, when the contents of the pressure cooker are stirred, which object is held in the ri |
| 7 | DIAG | object_recognition | single_choice | coverage | - | correct | C | C | About 2.5 seconds into the clip, when the lemon is squeezed, which object is held below it? |
| 8 | DIAG | object_recognition | single_choice | coverage | - | correct | C | C | About 4.5 seconds into the clip, when an object is shaken over the pressure cooker, which object is it? |
| 9 | DIAG | object_recognition | single_choice | coverage | - | correct | B | B | About 2.5 seconds into the clip, when an object is transferred from the right hand to the left hand, which obj |
| 10 | DIAG | object_recognition | single_choice | coverage | - | correct | B | B | About 4.5 seconds into the clip, when an object is put down next to the sink using both hands, which object is |
| 11 | DIAG | object_recognition | short_answer | coverage | - | correct | the cupboard door | open door of the upper cabinet | About 0.5 seconds into the clip, during the event where the measuring jug is placed on the counter, what is cl |
| 12 | DIAG | object_recognition | short_answer | coverage | - | correct | a glass jug | measuring jug | About 3 seconds into the clip, when an object is placed under the nozzle of the water cooler using the left ha |
| 13 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 5 seconds into the clip, when the water cooler's drip tray is put down, where is it placed? |
| 14 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 8 seconds into the clip, when the tumbler is placed on the counter, where exactly is it put down? |
| 15 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 9 seconds into the clip, when the tumbler is placed on the counter, where is it put down? |
| 16 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.31, 0.73, 0.41, 0.82] | 33.2, 67.2, 45.3, 79.5 | What is the bounding box of the water cooler's drip tray in the first frame of the clip? |
| 17 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.569, 0.631, 0.902, 0.899] | 53.0, 57.3, 81.7, 76.2 | What is the bounding box of the pressure cooker in the first frame of the clip? |
| 18 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.19, 0.526, 0.314, 0.629] | 16.6, 67.5, 31.0, 83.4 | What is the bounding box of the bowl in the first frame of the clip? |

## L2 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | sound_action_binding | single_choice | coverage | - | correct | B | B | Which action produced the sound of hard materials scraping or clattering against each other heard in the clip? |
| 2 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | correct | C | C | Which action produced the beep sounds heard in the clip? |
| 3 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | correct | C | C | Which action produced the sound of water pouring heard in the clip? |
| 4 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | correct | A | A | Which action produced the sound of a hard object contacting a ceramic surface heard in the clip? |
| 5 | DIAG | sound_action_binding | short_answer | same_skill_new_event | - | correct | An electronic beep | beep | What sound is produced when the stove knob is turned to adjust the heat? |
| 6 | DIAG | sound_action_binding | short_answer | same_skill_new_event | - | correct | Pouring the rice from the bowl | Pouring rice into the pressure | What action produced the sound of something being poured heard in the clip? |
| 7 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | When the measuring jug is placed down using both hands, where is it placed? |
| 8 | DIAG | object_state_change | single_choice | same_skill_new_event | - | wrong | C | A | When the water cooler's drip tray is removed, where is it put down? |
| 9 | DIAG | object_state_change | single_choice | same_skill_new_event | - | correct | A | A | When the small metallic tumbler is put down, where is it placed? |
| 10 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | When the water cooler's drip tray is pulled out, where is it put down? |
| 11 | DIAG | object_state_change | single_choice | coverage | - | correct | B | B | When the measuring jug is placed down using both hands, where is it placed? |
| 12 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | When the drip tray is removed from the water cooler, where is it placed? |
| 13 | DIAG | object_state_change | short_answer | coverage | - | correct | on the countertop next to the  | On the countertop | When the small metallic tumbler is put down, where is it placed? |
| 14 | DIAG | object_state_change | short_answer | coverage | - | correct | On the kitchen counter next to | next to the sink | When the drip tray is removed from the water cooler, where is it placed? |
| 15 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | In what order are the tumbler and the measuring jug placed on the counter? |
| 16 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | A | A | Which of the following sequences of actions occurs in the clip? |
| 17 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | A | A | In what order are the measuring jug and the wooden spatula picked up? |
| 18 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | C | C | Which of the following sequences of actions occurs in the clip? |
| 19 | DIAG | action_temporal_order | short_answer | same_skill_new_event | - | correct | Stirring the contents of the p | stirring the contents of the p | What action does the camera wearer perform immediately after adjusting the heat on the electric hob? |
| 20 | DIAG | action_temporal_order | short_answer | same_skill_new_event | - | correct | Pour the basmati rice from the | Pouring the basmati rice into  | What action does the camera wearer perform immediately after shaking the wooden spatula over the pressure cook |
| 21 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | What action is performed with the tumbler after it is picked up from the countertop? |
| 22 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | A | A | What action is performed with the metallic tumbler immediately after the stream of water from the cooler is st |
| 23 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | A | A | What action is performed with the wooden spatula while water is being poured from the measuring jug into the p |
| 24 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | A | A | What action is performed with the sliced lemon while it is held over the spoon? |
| 25 | DIAG | action_recognition | short_answer | coverage | - | correct | stirs the contents of the pres | Stirring the contents of the p | What action does the camera wearer perform with the wooden spatula while holding the handlebar of the pressure |
| 26 | DIAG | action_recognition | short_answer | same_skill_new_event | - | correct | Pours the rice into the pressu | pours the rice into the pressu | What action does the camera wearer perform with the bowl of basmati rice after picking it up from the wooden c |
| 27 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | Which object is placed at the corner of the countertop near the water cooler using both hands? |
| 28 | DIAG | event_object_role | single_choice | same_skill_new_event | - | correct | A | A | When water is poured into the measuring jug, from which object is it poured? |
| 29 | DIAG | event_object_role | single_choice | same_skill_new_event | - | correct | C | C | When water is poured into the pressure cooker, from which object is it poured? |
| 30 | DIAG | event_object_role | single_choice | same_skill_new_event | - | correct | C | C | When the lemon is squeezed, what object is held directly below it to catch the juice? |
| 31 | DIAG | event_object_role | short_answer | same_skill_new_event | - | correct | A wooden spatula | wooden spatula | When the contents of the pressure cooker are stirred, what tool is used? |
| 32 | DIAG | event_object_role | short_answer | same_skill_new_event | - | correct | A white bowl | A bowl | When the basmati rice is poured, from what object is it poured? |
| 33 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | correct | A | A | When the sound of a door closing is heard, which of the following objects is nearest to the measuring jug (sce |
| 34 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | wrong | C | A | When the measuring jug is placed on the counter and a clattering sound is heard, which of the following object |
| 35 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | correct | C | C | When the plastic measuring jug is moved, from the camera wearer's own viewpoint at that moment (egocentric: th |
| 36 | DIAG | sound_movement_binding | single_choice | coverage | - | wrong | B | A | Which movement produced the sound of a metal or plastic collision heard in the clip? |
| 37 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | Which movement produced the sounds of plastic and metal colliding heard in the clip? |
| 38 | DIAG | sound_movement_binding | single_choice | coverage | - | correct | A | A | Which movement produced the sound of a metal or plastic collision heard in the clip? |
| 39 | DIAG | sound_movement_binding | - | request_verification | - | evidence_unresolved | None | None |  |

## L3 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | When water is poured from the tumbler, which container receives the water? |
| 2 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | B | B | When the lemon is squeezed, what liquid is already in the pressure cooker? |
| 3 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | B | B | When the contents of the pressure cooker are stirred with the spatula, which ingredient was most recently adde |
| 4 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | wrong | C | B | When the sound of water running into the measuring jug is heard, where was the jug retrieved from? |
| 5 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | A | A | When water is poured from the measuring jug into the pressure cooker, how did the water get into the jug? |
| 6 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | When the contents of the pressure cooker are stirred with the wooden spatula, which ingredient was added to th |
| 7 | DIAG | hidden_state_inference | single_choice | coverage | - | wrong | B | A | When the basmati rice is poured into the pressure cooker, what is the heat level of the electric hob? |
| 8 | DIAG | hidden_state_inference | single_choice | same_skill_new_event | - | wrong | C | A | When the basmati rice is added to the pressure cooker, what is the heat setting of the electric hob? |
| 9 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | correct | B | B | Which earlier action provided the water that is poured from the measuring jug into the pressure cooker? |

## L4 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | C | C | What is the next step the person will take to complete the task they are doing? |
| 2 | DIAG | goal_conditioned_planning | single_choice | same_skill_new_event | - | correct | C | C | What is the next step the person will take to complete the task they are doing? |
| 3 | DIAG | goal_conditioned_planning | plan | same_skill_new_event | - | correct | ['Add the drained basmati rice | 1. Put the basmati rice into t | List the remaining stages, in order, to complete the task the camera wearer is doing. |

## Gemini 用量

| role | calls | errors | tok_in | tok_out | tok_think |
|---|---|---|---|---|---|
| examiner | 75 | 0 | 1987202 | 45183 | 244154 |
| judge | 18 | 0 | 5991 | 1206 | 2746 |
| solver | 204 | 0 | 1987662 | 3490 | 0 |
