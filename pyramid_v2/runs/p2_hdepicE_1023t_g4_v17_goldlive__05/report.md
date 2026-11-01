# pyramid2 run `p2_hdepicE_1023t_g4_v17_goldlive__05`

dataset hdepic_e · videos 1 · examiner `gcp/google/gemini-3.1-pro-preview` · solver `gcp/google/gemini-4-argon` · n_per_layer 200 · seed 1023 · prompt physical-mental-draft2-hdepic-e+v16sg

**结果为 provisional**:gold = Examiner 的 proposed_reference_answer,未经人工核验;open/plan 题由 Gemini judge 判。

## 每层概览

| layer | stop | turns | scored | correct | raw acc | cluster-dedup acc | follow-up | invalid/unresolved | confirmation |
|---|---|---|---|---|---|---|---|---|---|
| L1 | EVENT_LOOP_COMPLETE | 19 | 17 | 10 | 0.588 | 0.588 | 0 | 0/2 | - |
| L2 | EVENT_LOOP_COMPLETE | 43 | 43 | 37 | 0.86 | 0.86 | 0 | 0/0 | - |
| L3 | EVENT_LOOP_COMPLETE | 9 | 9 | 7 | 0.778 | 0.778 | 0 | 0/0 | - |
| L4 | STAIRCASE_COMPLETE | 3 | 3 | 3 | 1.0 | 1.0 | 0 | 0/0 | - |

## 每层 × skill 诊断结论

| layer | skill | verdict | scored | correct | clusters | first-try correct | supported hypotheses | confirmation |
|---|---|---|---|---|---|---|---|---|
| L1 | spatial_near | boundary 1.0 | 1 | 1 | 1 |  | - | - |
| L1 | spatial_side | boundary 1.0 | 1 | 1 | 1 |  | - | - |
| L1 | object_recognition | boundary>=4 | 7 | 7 | 7 |  | - | - |
| L1 | object_location_at_time | boundary 2.0 | 2 | 1 | 2 |  | - | - |
| L1 | object_grounding | boundary<1 | 6 | 0 | 6 |  | - | - |
| L2 | sound_action_binding | boundary>=4 | 9 | 9 | 9 |  | - | - |
| L2 | object_state_change | boundary 1.5 | 2 | 1 | 2 |  | - | - |
| L2 | action_temporal_order | boundary 2 | 9 | 7 | 9 |  | - | - |
| L2 | action_recognition | boundary>=4 | 9 | 8 | 9 |  | - | - |
| L2 | event_object_role | boundary>=4 | 9 | 9 | 9 |  | - | - |
| L2 | sound_anchored_spatial_near | boundary 1.0 | 1 | 1 | 1 |  | - | - |
| L2 | sound_anchored_spatial_side | boundary 1.0 | 1 | 0 | 1 |  | - | - |
| L2 | sound_movement_binding | boundary 1.75 | 3 | 2 | 3 |  | - | - |
| L3 | cross_event_integration | boundary 3.5 | 7 | 6 | 7 |  | - | - |
| L3 | hidden_state_inference | boundary 1.0 | 1 | 0 | 1 |  | - | - |
| L3 | spatial_state_integration | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | causal_prerequisite_reasoning | boundary 1.0 | 1 | 1 | 1 |  | - | - |
| L4 | goal_conditioned_planning | boundary 3.5 | 3 | 3 | 3 |  | - | - |

## L1 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | spatial_near | single_choice | coverage | - | correct | B | B | At the start of the clip, when the measuring jug is placed on the counter, which of the following objects is n |
| 2 | DIAG | spatial_side | single_choice | coverage | - | correct | C | C | At the start of the clip, when the measuring jug is placed on the counter, from the camera wearer's own viewpo |
| 3 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | About 4.5 seconds into the clip, when the camera wearer picks up an object from the countertop using the right |
| 4 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 8 seconds into the clip, when the tumbler is put down, where is it placed? |
| 5 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.82, 0.85, 0.99, 1.0] | 56.4, 54.7, 65.0, 66.2 | At the start of the clip, when the measuring jug is placed on the counter, what is the bounding box of the pla |
| 6 | DIAG | object_recognition | single_choice | coverage | - | correct | B | B | About 1 second into the clip, when the camera wearer pulls out an object using the right hand, which object is |
| 7 | DIAG | object_location_at_time | single_choice | same_skill_new_event | - | wrong | B | A | About 5.5 seconds into the clip, when the water cooler's drip tray is put down, where is it placed? |
| 8 | DIAG | object_grounding | bbox | same_skill_new_event | - | wrong | [0.055659999999999994, 0.51513 | 53.5, 55.6, 65.1, 65.8 | At the start of the clip, when the sound of water running and splashing into the jug is heard, what is the bou |
| 9 | DIAG | object_recognition | - | request_verification | - | evidence_unresolved | None | None |  |
| 10 | DIAG | object_recognition | - | request_verification | - | evidence_unresolved | None | None |  |
| 11 | DIAG | object_grounding | bbox | same_skill_new_event | - | wrong | [0.645, 0.567, 0.976, 0.682] | 48.9, 61.7, 71.8, 69.6 | At the start of the clip, when the wooden spatula is picked up from the pressure cooker, what is the bounding  |
| 12 | DIAG | object_recognition | single_choice | same_skill_new_event | - | correct | B | B | About 6.5 seconds into the clip, when the camera wearer tips the spoon to transfer the lemon juice, which obje |
| 13 | DIAG | object_recognition | single_choice | same_skill_new_event | - | correct | C | C | At the start of the clip, when the camera wearer stirs the contents of the pressure cooker, which object is he |
| 14 | DIAG | object_recognition | short_answer | same_skill_new_event | - | correct | wooden spoon | wooden spatula | About 9 seconds into the clip, after the stove knob is turned to adjust the heat, which object is put down usi |
| 15 | DIAG | object_grounding | bbox | same_skill_new_event | - | wrong | [0.6, 0.56, 0.72, 0.65] | 67.4, 67.5, 80.2, 78.3 | At the start of the clip, when the wooden spatula is put down back in the pressure cooker, what is the boundin |
| 16 | DIAG | object_recognition | short_answer | same_skill_new_event | - | correct | saucepan | pressure cooker | About 7 seconds into the clip, when the camera wearer tips the bowl of basmati rice, which object is the bowl  |
| 17 | DIAG | object_grounding | bbox | same_skill_new_event | - | wrong | [0.423, 0.559, 0.68, 0.742] | 53.0, 57.3, 81.7, 76.2 | At the start of the clip, when the contents of the pressure cooker are being stirred, what is the bounding box |
| 18 | DIAG | object_recognition | short_answer | same_skill_new_event | - | correct | a wooden spoon | wooden spatula | At the start of the clip, when the camera wearer stirs the contents of the pressure cooker, which object is he |
| 19 | DIAG | object_grounding | bbox | same_skill_new_event | - | wrong | [0.196, 0.526, 0.305, 0.629] | 16.6, 67.5, 31.0, 83.4 | At the start of the clip, when the rice and masala are gently mixed together with a spatula, what is the bound |

## L2 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, a closing sound is heard. Which action produced this sound? |
| 2 | DIAG | object_state_change | single_choice | coverage | - | wrong | A | C | During the task the camera wearer is doing, the measuring jug is placed down using both hands. Where does the  |
| 3 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, the camera wearer transfers the measuring jug between hands. Which |
| 4 | DIAG | action_recognition | single_choice | coverage | - | wrong | B | A | During the task the camera wearer is doing, what does the camera wearer do with the measuring jug after holdin |
| 5 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, the camera wearer uses both hands to place an object at the corner |
| 6 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, an opening or closing sound is heard. At that moment, which of the |
| 7 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | wrong | D | A | During the task the camera wearer is doing, the measuring jug is placed on the counter. At the moment a collis |
| 8 | DIAG | sound_movement_binding | single_choice | coverage | - | wrong | C | B | During the task the camera wearer is doing, the measuring jug is placed on the counter. Before it is placed, a |
| 9 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | correct | B | B | During the task the camera wearer is doing, a sound of running water is heard. Which of the following actions  |
| 10 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, the camera wearer pulls out the water cooler's drip tray and puts  |
| 11 | DIAG | action_temporal_order | single_choice | coverage | - | wrong | C | A | During the task the camera wearer is doing, the camera wearer places the measuring jug at the corner of the co |
| 12 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, the camera wearer interacts with the water cooler's drip tray. Wha |
| 13 | DIAG | event_object_role | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, the camera wearer pulls out an object to create space for placing  |
| 14 | DIAG | sound_movement_binding | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, several collision sounds are heard as objects are moved. Which obj |
| 15 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, a sound of water is heard. Which of the following actions produced |
| 16 | DIAG | action_temporal_order | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, the camera wearer tips the tumbler over the measuring jug to pour  |
| 17 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, what does the camera wearer do with the tumbler immediately after  |
| 18 | DIAG | event_object_role | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, the camera wearer tips the tumbler to pour water. Into which objec |
| 19 | DIAG | sound_movement_binding | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, the sound of water is heard multiple times. Which movement produce |
| 20 | DIAG | sound_action_binding | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, a continuous sound of water is heard. Which of the following actio |
| 21 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, the camera wearer slightly stirs the contents of the pressure cook |
| 22 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, the camera wearer holds the measuring jug over the pressure cooker |
| 23 | DIAG | event_object_role | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, the camera wearer tips the measuring jug to pour water. Into which |
| 24 | DIAG | sound_action_binding | short_answer | coverage | - | correct | picking up the spoon from the  | picking up the tablespoon from | During the task the camera wearer is doing, lemon juice is squeezed from a lemon half into the pressure cooker |
| 25 | DIAG | action_temporal_order | single_choice | coverage | - | correct | B | B | During the task the camera wearer is doing, the camera wearer squeezes the lemon for the first time to get jui |
| 26 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, the camera wearer holds the spoon under the lemon. What action do  |
| 27 | DIAG | event_object_role | short_answer | same_skill_new_event | - | correct | The spoon | spoon | During the task the camera wearer is doing, the camera wearer squeezes the lemon to extract juice. Into which  |
| 28 | DIAG | sound_action_binding | short_answer | coverage | - | correct | stirring the contents with a w | stirring with a spatula | During the task the camera wearer is doing, a continuous mixing sound is heard. What action involving the liqu |
| 29 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, the camera wearer stirs the contents of the pressure cooker with t |
| 30 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, the camera wearer holds the wooden spatula in their right hand whi |
| 31 | DIAG | event_object_role | short_answer | coverage | - | correct | wooden spatula | wooden spatula | During the task the camera wearer is doing, the camera wearer stirs the contents of the pressure cooker. What  |
| 32 | DIAG | sound_action_binding | short_answer | coverage | - | correct | pressing the stove button | pressing the button on the ele | During the task the camera wearer is doing, a beep sound is heard. What specific action, corresponding to the  |
| 33 | DIAG | action_temporal_order | single_choice | coverage | - | wrong | D | A | During the task the camera wearer is doing, the camera wearer adjusts the heat on the stove. They press the pl |
| 34 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, the camera wearer interacts with the interface of the electric hob |
| 35 | DIAG | event_object_role | short_answer | coverage | - | correct | the button on the induction st | plus shaped button | During the task the camera wearer is doing, the camera wearer adjusts the heat on the electric hob. What speci |
| 36 | DIAG | sound_action_binding | short_answer | coverage | - | correct | pouring basmati rice into the  | pouring the basmati rice into  | During the task the camera wearer is doing, the sound of something being poured is heard. What action produced |
| 37 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, the camera wearer shakes the wooden spatula over the pressure cook |
| 38 | DIAG | action_recognition | short_answer | coverage | - | correct | tip | pour the rice into the pressur | During the task the camera wearer is doing, the camera wearer positions the bowl of basmati rice over the pres |
| 39 | DIAG | event_object_role | short_answer | coverage | - | correct | pressure cooker | pressure cooker | During the task the camera wearer is doing, the camera wearer transfers basmati rice. Into which object is the |
| 40 | DIAG | sound_action_binding | short_answer | coverage | - | correct | pressing the induction stove b | pressing the button on the ele | During the task the camera wearer is doing, the rice and masala are gently mixed together with a spatula. Whil |
| 41 | DIAG | action_temporal_order | single_choice | coverage | - | correct | B | B | During the task the camera wearer is doing, the camera wearer stirs the contents of the pressure cooker to mix |
| 42 | DIAG | action_recognition | short_answer | coverage | - | correct | Stirring or mixing with a wood | stirring with a wooden spatula | During the task the camera wearer is doing, the camera wearer combines the rice and masala in the pressure coo |
| 43 | DIAG | event_object_role | short_answer | coverage | - | correct | pressure cooker | pressure cooker | During the task the camera wearer is doing, the camera wearer mixes the rice with the masala using a wooden sp |

## L3 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | When water is poured into the measuring jug, where had the jug been placed beforehand? |
| 2 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | B | B | When water is poured from the tumbler, which container is it poured into? |
| 3 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | A | A | When water is poured from the measuring jug into the pressure cooker, how was the jug filled earlier? |
| 4 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | correct | A | A | Which earlier action provided the water that is poured from the measuring jug into the pressure cooker? |
| 5 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | B | B | When the lemon is squeezed, what liquid is already in the pressure cooker? |
| 6 | DIAG | cross_event_integration | short_answer | same_skill_new_event | - | wrong | rice | lemon juice | What ingredient is added to the pressure cooker just before its contents are stirred with the wooden spatula? |
| 7 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | A | A | Before the basmati rice is poured into the pressure cooker, what was done to the contents already in the cooke |
| 8 | DIAG | hidden_state_inference | single_choice | coverage | - | wrong | B | A | When the basmati rice is poured into the pressure cooker, what is the heat setting of the electric hob? |
| 9 | DIAG | cross_event_integration | single_choice | same_skill_new_event | - | correct | A | A | When the contents of the pressure cooker are stirred with the wooden spatula, what ingredient is being mixed w |

## L4 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | C | C | Based on the task the camera wearer is doing, what is the next step they will take immediately after the clip  |
| 2 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | C | C | Based on the task the camera wearer is doing, what is the next step they will take immediately after the clip  |
| 3 | DIAG | goal_conditioned_planning | plan | coverage | - | correct | ['Pour the rice from the bowl  | 1. Put the basmati rice into t | Based on the task the camera wearer is doing, what are the remaining stages, in order, that they will carry ou |

## Gemini 用量

| role | calls | errors | tok_in | tok_out | tok_think |
|---|---|---|---|---|---|
| examiner | 84 | 0 | 2266833 | 51444 | 258707 |
| judge | 21 | 0 | 7085 | 1352 | 3298 |
| solver | 216 | 0 | 2059911 | 3766 | 0 |
