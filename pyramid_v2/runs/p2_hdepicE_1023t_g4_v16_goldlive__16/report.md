# pyramid2 run `p2_hdepicE_1023t_g4_v16_goldlive__16`

dataset hdepic_e · videos 1 · examiner `gcp/google/gemini-3.1-pro-preview` · solver `gcp/google/gemini-4-argon` · n_per_layer 200 · seed 1023 · prompt physical-mental-draft2-hdepic-e+v16sg

**结果为 provisional**:gold = Examiner 的 proposed_reference_answer,未经人工核验;open/plan 题由 Gemini judge 判。

## 每层概览

| layer | stop | turns | scored | correct | raw acc | cluster-dedup acc | follow-up | invalid/unresolved | confirmation |
|---|---|---|---|---|---|---|---|---|---|
| L1 | STAIRCASE_COMPLETE | 25 | 21 | 16 | 0.762 | 0.75 | 0 | 0/3 | - |
| L2 | STAIRCASE_COMPLETE | 42 | 33 | 26 | 0.788 | 0.806 | 0 | 0/9 | - |
| L3 | STAIRCASE_COMPLETE | 12 | 12 | 12 | 1.0 | 1.0 | 0 | 0/0 | - |
| L4 | STAIRCASE_COMPLETE | 1 | 1 | 1 | 1.0 | 1.0 | 0 | 0/0 | - |

## 每层 × skill 诊断结论

| layer | skill | verdict | scored | correct | clusters | first-try correct | supported hypotheses | confirmation |
|---|---|---|---|---|---|---|---|---|
| L1 | spatial_near | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L1 | spatial_side | boundary<1 | 2 | 1 | 1 |  | - | - |
| L1 | object_recognition | boundary>=4 | 9 | 8 | 9 |  | - | - |
| L1 | object_location_at_time | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L1 | object_grounding | boundary<1 | 4 | 1 | 4 |  | - | - |
| L2 | sound_action_binding | boundary 2.5 | 5 | 4 | 5 |  | - | - |
| L2 | object_state_change | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | action_temporal_order | boundary 2 | 2 | 2 | 2 |  | - | - |
| L2 | action_recognition | boundary 3.5 | 7 | 6 | 7 |  | - | - |
| L2 | event_object_role | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L2 | sound_anchored_spatial_near | boundary<1 | 2 | 1 | 1 |  | - | - |
| L2 | sound_anchored_spatial_side | boundary<1 | 4 | 1 | 3 |  | - | - |
| L2 | sound_movement_binding | boundary 2 | 1 | 0 | 1 |  | - | - |
| L3 | cross_event_integration | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L3 | hidden_state_inference | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | spatial_state_integration | not_evaluated |  |  |  |  | - | no expected-event cluster for this skill on this task (sg mode) |
| L3 | causal_prerequisite_reasoning | boundary>=4 | 6 | 6 | 6 |  | - | - |
| L4 | goal_conditioned_planning | boundary 2.0 | 1 | 1 | 1 |  | - | - |

## L1 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | spatial_side | - | - | - | env_failure | None | None |  |
| 2 | DIAG | spatial_side | - | request_verification | - | evidence_unresolved | None | None |  |
| 3 | DIAG | spatial_side | single_choice | coverage | - | wrong | C | B | About 1.5 seconds into the clip, when the bowl is placed on the counter, from the camera wearer's own viewpoin |
| 4 | DIAG | spatial_side | single_choice | coverage | - | correct | C | C | About 1.5 seconds into the clip, when the bowl is placed on the counter, from the camera wearer's own viewpoin |
| 5 | DIAG | object_recognition | single_choice | coverage | - | wrong | C | A | About 5.5 seconds into the clip, when the chicken pieces are washed under running water, what specific parts o |
| 6 | DIAG | object_recognition | - | request_verification | - | evidence_unresolved | None | None |  |
| 7 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | About 3 seconds into the clip, when the remaining chicken pieces are washed under the tap, what part of the ta |
| 8 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | At the start of the clip, when vinegar is poured from the bottle, what object is the camera wearer pouring the |
| 9 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | About 3 seconds into the clip, when soy sauce is poured into the bowl, what object is the camera wearer holdin |
| 10 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | About 4 seconds into the clip, when the lemon half is squeezed over the bowl, what object is the camera wearer |
| 11 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | About 0.5 seconds into the clip, when the lemon is positioned over the bowl, what object is the camera wearer  |
| 12 | DIAG | object_recognition | single_choice | coverage | - | correct | A | A | About 9 seconds into the clip, when the camera wearer picks up more rosemary to sprinkle into the bowl, what t |
| 13 | DIAG | object_recognition | short_answer | coverage | - | correct | spice jar | jar | About 3 seconds into the clip, when the camera wearer rotates the lid counterclockwise before pouring the spic |
| 14 | DIAG | object_recognition | - | request_verification | - | evidence_unresolved | None | None |  |
| 15 | DIAG | object_recognition | short_answer | coverage | - | correct | a knife | knife | About 1.5 seconds into the clip, when the camera wearer starts to peel the individual garlic clove, what tool  |
| 16 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 8 seconds into the clip, when the chicken pieces are washed under running water, from what location are  |
| 17 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 1.5 seconds into the clip, when the soy sauce bottle is put down before pouring, where is it placed? |
| 18 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 6 seconds into the clip, when the knife is put down, where is it placed? |
| 19 | DIAG | object_location_at_time | single_choice | coverage | - | correct | A | A | About 4 seconds into the clip, when the lemon half is squeezed over the bowl, from what location was the lemon |
| 20 | DIAG | object_location_at_time | short_answer | coverage | - | correct | A white chopping board. | chopping board | At the start of the clip, when the camera wearer prepares to squeeze the newly cut lemon halves into the bowl, |
| 21 | DIAG | object_location_at_time | short_answer | coverage | - | correct | the countertop | the counter | About 4.5 seconds into the clip, when the rosemary is sprinkled into the bowl, from what location was the bag  |
| 22 | DIAG | object_grounding | bbox | coverage | - | correct | [0.56, 0.68, 0.69, 0.82] | 56.4, 71.1, 70.8, 84.3 | What is the bounding box of the chicken piece in the first frame of the clip? |
| 23 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.44, 0.71, 0.61, 0.9] | 51.3, 74.5, 62.6, 93.5 | At the start of the clip, when the chicken pieces are washed under running water, what is the bounding box of  |
| 24 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.823, 0.219, 0.983, 0.417] | 61.2, 58.5, 78.5, 78.8 | At the start of the clip, when the bowl is placed on the counter, what is the bounding box of the bowl in the  |
| 25 | DIAG | object_grounding | bbox | coverage | - | wrong | [0.72, 0.53, 0.98, 0.76] | 59.7, 57.1, 88.0, 80.7 | At the start of the clip, when the bowl is placed on the counter, what is the bounding box of the bowl in the  |

## L2 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | sound_action_binding | single_choice | coverage | - | correct | B | B | Which action produces the sound of plastic hitting against metal? |
| 2 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, which action produces the sound of running water? |
| 3 | DIAG | sound_action_binding | single_choice | coverage | - | wrong | C | A | During the task the camera wearer is doing, which action produces the sound of a metal or plastic collision? |
| 4 | DIAG | sound_action_binding | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, which action produces the sound of a glass collision? |
| 5 | DIAG | sound_action_binding | single_choice | coverage | - | correct | C | C | During the task the camera wearer is doing, which action produces the sound of an object hitting a wooden surf |
| 6 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when the chicken container is moved after being opened, where is i |
| 7 | DIAG | object_state_change | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when the chicken pieces are washed under running water, where are  |
| 8 | DIAG | object_state_change | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, when the remaining chicken pieces are washed under the tap, where  |
| 9 | DIAG | object_state_change | single_choice | coverage | - | correct | B | B | During the task the camera wearer is doing, when the bottle of soy sauce is taken out of the fridge, where is  |
| 10 | DIAG | object_state_change | short_answer | coverage | - | correct | Into the bin | trash bin | During the task the camera wearer is doing, after the first half of the lemon is squeezed, where is it thrown? |
| 11 | DIAG | object_state_change | short_answer | coverage | - | correct | Over the white bowl containing | Over the bowl | During the task the camera wearer is doing, when the lemon juicer is picked up from the chopping board, where  |
| 12 | DIAG | action_temporal_order | - | request_verification | - | evidence_unresolved | None | None |  |
| 13 | DIAG | action_temporal_order | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, which of the following describes the correct order of actions? |
| 14 | DIAG | action_temporal_order | - | request_verification | - | evidence_unresolved | None | None |  |
| 15 | DIAG | action_temporal_order | single_choice | coverage | - | correct | C | C | During the task the camera wearer is doing, when the vinegar bottle is opened, which of the following describe |
| 16 | DIAG | action_temporal_order | - | request_verification | - | evidence_unresolved | None | None |  |
| 17 | DIAG | action_temporal_order | - | request_verification | - | evidence_unresolved | None | None |  |
| 18 | DIAG | action_temporal_order | - | request_verification | - | evidence_unresolved | None | None |  |
| 19 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, how is the chicken container opened? |
| 20 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, how are the two connected chicken pieces separated while being was |
| 21 | DIAG | action_recognition | single_choice | same_skill_new_event | - | correct | A | A | During the task the camera wearer is doing, how does the wearer try to separate the connected chicken pieces i |
| 22 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, how is the vinegar added to the bowl containing the chicken? |
| 23 | DIAG | action_recognition | short_answer | coverage | - | wrong | directly from the soy sauce bo | By tilting and shaking the bot | During the task the camera wearer is doing, how is the soy sauce poured into the bowl? |
| 24 | DIAG | action_recognition | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, how is the fallen lemon seed removed from the bowl? |
| 25 | DIAG | action_recognition | single_choice | coverage | - | correct | B | B | During the task the camera wearer is doing, how are the newly cut lemon halves squeezed into the bowl? |
| 26 | DIAG | event_object_role | single_choice | coverage | - | correct | B | B | During the task the camera wearer is doing, what tool is used to open the chicken container? |
| 27 | DIAG | event_object_role | single_choice | coverage | - | correct | B | B | During the task the camera wearer is doing, when the washed chicken pieces are put down, what are they placed  |
| 28 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when the wearer forcefully pulls the remaining chicken pieces apar |
| 29 | DIAG | event_object_role | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when the vinegar is poured from its bottle, what is it poured into |
| 30 | DIAG | event_object_role | short_answer | coverage | - | correct | a white bowl containing raw ch | A bowl | During the task the camera wearer is doing, when the soy sauce is poured, what is it poured into? |
| 31 | DIAG | event_object_role | short_answer | coverage | - | correct | A lemon squeezer | a lemon squeezer | During the task the camera wearer is doing, when the first lemon half is squeezed, what tool is used? |
| 32 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | wrong | C | A | During the task the camera wearer is doing, when the bowl is placed on the counter, at the moment the sound of |
| 33 | DIAG | sound_anchored_spatial_near | single_choice | coverage | - | correct | C | C | During the task the camera wearer is doing, when the bowl is placed on the counter, at the moment the sound of |
| 34 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | wrong | A | C | During the task the camera wearer is doing, when the bowl is placed on the counter, at the moment the sound of |
| 35 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | correct | A | A | During the task the camera wearer is doing, when the washed food is placed into the dish, at the moment the so |
| 36 | DIAG | sound_anchored_spatial_side | - | request_verification | - | evidence_unresolved | None | None |  |
| 37 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | wrong | D | A | During the task the camera wearer is doing, when the rosemary is sprinkled into the bowl, at the moment the so |
| 38 | DIAG | sound_anchored_spatial_side | single_choice | coverage | - | wrong | A | C | During the task the camera wearer is doing, when the bowl is placed on the counter, at the moment the sound of |
| 39 | DIAG | sound_movement_binding | single_choice | coverage | - | wrong | A | B | During the task the camera wearer is doing, when the bowl is placed on the counter, which movement produces th |
| 40 | DIAG | sound_movement_binding | - | request_verification | - | evidence_unresolved | None | None |  |
| 41 | DIAG | sound_movement_binding | - | request_verification | - | evidence_unresolved | None | None |  |
| 42 | DIAG | sound_movement_binding | - | request_verification | - | evidence_unresolved | None | None |  |

## L3 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | cross_event_integration | single_choice | coverage | - | correct | C | C | When the remaining washed chicken is placed into the bowl, what is already in it? |
| 2 | DIAG | cross_event_integration | single_choice | coverage | - | correct | B | B | When the soy sauce is poured into the bowl, which of these liquid ingredients is already in it? |
| 3 | DIAG | cross_event_integration | single_choice | coverage | - | correct | C | C | How did the state of the garlic change before it was chopped? |
| 4 | DIAG | cross_event_integration | single_choice | coverage | - | correct | A | A | When the chicken pieces are placed into the bowl, what has been done to them beforehand? |
| 5 | DIAG | cross_event_integration | short_answer | coverage | - | correct | It was opened with a knife and | It was opened. | Before the chicken pieces are washed under running water, what was done to their container? |
| 6 | DIAG | cross_event_integration | short_answer | coverage | - | correct | They have been separated, wash | They were washed, separated, a | When the remaining chicken pieces are washed under the tap, what has already been done to the first batch of c |
| 7 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | correct | A | A | What earlier action provided the specific location where the washed chicken pieces are placed? |
| 8 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | correct | A | A | What had to be done to the garlic before the individual cloves could be peeled? |
| 9 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | correct | A | A | Which earlier action provided the receptacle that the washed chicken pieces are placed into? |
| 10 | DIAG | causal_prerequisite_reasoning | single_choice | coverage | - | correct | A | A | What had to be done to the garlic before the individual cloves could be peeled? |
| 11 | DIAG | causal_prerequisite_reasoning | short_answer | coverage | - | correct | Retrieving the white bowl from | The bowl was placed on the cou | Which earlier action provided the receptacle that the washed chicken pieces are placed into? |
| 12 | DIAG | causal_prerequisite_reasoning | short_answer | coverage | - | correct | Separating the cloves from the | The head of garlic had to be b | What had to be done to the garlic before the individual cloves could be peeled? |

## L4 轨迹

| turn | phase | skill | format | strategy | hypothesis | verdict | answer | reference | question |
|---|---|---|---|---|---|---|---|---|---|
| 1 | DIAG | goal_conditioned_planning | single_choice | coverage | - | correct | A | A | Based on the progress shown in the clip, what should the camera wearer do next for the task they are doing? |

## Gemini 用量

| role | calls | errors | tok_in | tok_out | tok_think |
|---|---|---|---|---|---|
| examiner | 84 | 1 | 2322690 | 47293 | 267935 |
| judge | 16 | 0 | 4496 | 821 | 2468 |
| solver | 201 | 0 | 1081716 | 3458 | 0 |
